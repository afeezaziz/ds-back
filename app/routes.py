"""All API routes for the Dream Studio platform backend (v1)."""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import current_player, make_token
from .db import get_db
from .models import CloudSave, Event, GameEntry, Player, RemoteConfig, Score

router = APIRouter(prefix="/v1")

MAX_EVENTS_PER_BATCH = 100
MAX_SAVE_BYTES = 256 * 1024


# ---------- auth ----------

class DeviceAuthIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=128)
    display_name: str | None = None


class AuthOut(BaseModel):
    player_id: str
    token: str
    display_name: str
    created: bool


@router.post("/auth/device", response_model=AuthOut)
def device_auth(body: DeviceAuthIn, db: Session = Depends(get_db)):
    player = db.execute(
        select(Player).where(Player.device_id == body.device_id)
    ).scalar_one_or_none()
    created = False
    if player is None:
        player = Player(device_id=body.device_id)
        if body.display_name:
            player.display_name = body.display_name[:64]
        db.add(player)
        db.commit()
        created = True
    if player.banned:
        raise HTTPException(status_code=403, detail="Banned")
    return AuthOut(
        player_id=player.id,
        token=make_token(player.id),
        display_name=player.display_name,
        created=created,
    )


# ---------- player profile ----------

class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)


@router.get("/players/me")
def get_me(player: Player = Depends(current_player)):
    return {
        "player_id": player.id,
        "display_name": player.display_name,
        "created_at": player.created_at,
    }


@router.put("/players/me")
def update_me(
    body: ProfileIn,
    player: Player = Depends(current_player),
    db: Session = Depends(get_db),
):
    player.display_name = body.display_name.strip()[:64]
    db.commit()
    return {"ok": True, "display_name": player.display_name}


# ---------- cloud save ----------

class SaveIn(BaseModel):
    data: dict
    version: int = 0


@router.get("/saves/{game_id}")
def get_save(
    game_id: str,
    player: Player = Depends(current_player),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(CloudSave).where(
            CloudSave.player_id == player.id, CloudSave.game_id == game_id
        )
    ).scalar_one_or_none()
    if row is None:
        return {"data": {}, "version": 0, "updated_at": 0}
    return {
        "data": json.loads(row.data),
        "version": row.version,
        "updated_at": row.updated_at,
    }


@router.put("/saves/{game_id}")
def put_save(
    game_id: str,
    body: SaveIn,
    player: Player = Depends(current_player),
    db: Session = Depends(get_db),
):
    blob = json.dumps(body.data)
    if len(blob) > MAX_SAVE_BYTES:
        raise HTTPException(status_code=413, detail="Save too large")
    row = db.execute(
        select(CloudSave).where(
            CloudSave.player_id == player.id, CloudSave.game_id == game_id
        )
    ).scalar_one_or_none()
    if row is None:
        row = CloudSave(player_id=player.id, game_id=game_id)
        db.add(row)
    elif body.version < row.version:
        # Stale client write: reject so the client can pull and merge.
        raise HTTPException(status_code=409, detail="Stale save version")
    row.data = blob
    row.version = body.version + 1
    row.updated_at = time.time()
    db.commit()
    return {"ok": True, "version": row.version}


# ---------- leaderboards ----------

class ScoreIn(BaseModel):
    score: int = Field(ge=0, le=1_000_000_000)
    board: str = "main"


@router.post("/scores/{game_id}")
def submit_score(
    game_id: str,
    body: ScoreIn,
    player: Player = Depends(current_player),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(Score).where(
            Score.player_id == player.id,
            Score.game_id == game_id,
            Score.board == body.board,
        )
    ).scalar_one_or_none()
    improved = False
    if row is None:
        row = Score(
            player_id=player.id, game_id=game_id, board=body.board, best=body.score
        )
        db.add(row)
        improved = True
    elif body.score > row.best:
        row.best = body.score
        row.updated_at = time.time()
        improved = True
    db.commit()
    rank = db.execute(
        select(func.count())
        .select_from(Score)
        .where(Score.game_id == game_id, Score.board == body.board, Score.best > row.best)
    ).scalar_one() + 1
    return {"ok": True, "best": row.best, "improved": improved, "rank": rank}


@router.get("/leaderboards/{game_id}")
def leaderboard(
    game_id: str,
    board: str = "main",
    limit: int = 10,
    player: Player = Depends(current_player),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    top = db.execute(
        select(Score, Player.display_name)
        .join(Player, Player.id == Score.player_id)
        .where(Score.game_id == game_id, Score.board == board)
        .order_by(Score.best.desc(), Score.updated_at.asc())
        .limit(limit)
    ).all()
    entries = [
        {"rank": i + 1, "name": name, "score": s.best, "you": s.player_id == player.id}
        for i, (s, name) in enumerate(top)
    ]
    mine = db.execute(
        select(Score).where(
            Score.player_id == player.id, Score.game_id == game_id, Score.board == board
        )
    ).scalar_one_or_none()
    me = None
    if mine is not None:
        my_rank = db.execute(
            select(func.count())
            .select_from(Score)
            .where(Score.game_id == game_id, Score.board == board, Score.best > mine.best)
        ).scalar_one() + 1
        me = {"rank": my_rank, "score": mine.best}
    return {"entries": entries, "me": me}


# ---------- remote config ----------

@router.get("/config/{game_id}")
def get_config(game_id: str, db: Session = Depends(get_db)):
    row = db.get(RemoteConfig, game_id)
    if row is None:
        return {"data": {}, "version": 0}
    return {"data": json.loads(row.data), "version": row.version}


# ---------- analytics events ----------

class EventIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    props: dict = {}
    ts: float = 0.0


class EventBatchIn(BaseModel):
    game_id: str
    events: list[EventIn]


@router.post("/events")
def ingest_events(
    body: EventBatchIn,
    player: Player = Depends(current_player),
    db: Session = Depends(get_db),
):
    batch = body.events[:MAX_EVENTS_PER_BATCH]
    for e in batch:
        db.add(
            Event(
                player_id=player.id,
                game_id=body.game_id,
                name=e.name,
                props=json.dumps(e.props),
                client_ts=e.ts,
            )
        )
    db.commit()
    return {"ok": True, "accepted": len(batch)}


# ---------- cross-promo ----------

@router.get("/crosspromo/{game_id}")
def crosspromo(game_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        select(GameEntry)
        .where(GameEntry.active == True, GameEntry.game_id != game_id)  # noqa: E712
        .order_by(GameEntry.priority.desc())
        .limit(10)
    ).scalars().all()
    return {
        "games": [
            {
                "game_id": g.game_id,
                "name": g.name,
                "tagline": g.tagline,
                "android_url": g.android_url,
                "ios_url": g.ios_url,
                "icon_url": g.icon_url,
            }
            for g in rows
        ]
    }


@router.get("/health")
def health():
    return {"ok": True, "ts": time.time()}
