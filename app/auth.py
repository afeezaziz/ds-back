"""Device-based anonymous auth with JWT sessions.

Flow: client sends its stable device_id once -> gets a player_id + JWT.
All subsequent calls carry `Authorization: Bearer <token>`.
Set JWT_SECRET in the environment for production.
"""
import os
import time

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import Player

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me-0123456789abcdef")
JWT_ALGO = "HS256"
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


def make_token(player_id: str) -> str:
    payload = {"sub": player_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def current_player(request: Request, db: Session = Depends(get_db)) -> Player:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    player = db.get(Player, payload.get("sub", ""))
    if player is None or player.banned:
        raise HTTPException(status_code=401, detail="Unknown or banned player")
    player.last_seen_at = time.time()
    db.commit()
    return player
