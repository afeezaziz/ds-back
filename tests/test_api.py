"""End-to-end API tests: the full lifecycle a Godot client goes through."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app

GAME = "skystack"


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def auth(client, device="device-alpha-0001", name=None):
    body = {"device_id": device}
    if name:
        body["display_name"] = name
    r = client.post("/v1/auth/device", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/v1/health").json()["ok"] is True


def test_device_auth_creates_then_reuses(client):
    first = auth(client, name="Afeez")
    again = auth(client)
    assert first["created"] is True
    assert again["created"] is False
    assert first["player_id"] == again["player_id"]
    assert again["display_name"] == "Afeez"


def test_requires_token(client):
    assert client.get("/v1/players/me").status_code == 401
    bad = client.get("/v1/players/me", headers=hdr("garbage"))
    assert bad.status_code == 401


def test_profile_update(client):
    t = auth(client)["token"]
    r = client.put("/v1/players/me", json={"display_name": "SkyKing"}, headers=hdr(t))
    assert r.json()["display_name"] == "SkyKing"
    assert client.get("/v1/players/me", headers=hdr(t)).json()["display_name"] == "SkyKing"


def test_cloud_save_roundtrip_and_conflict(client):
    t = auth(client)["token"]
    empty = client.get(f"/v1/saves/{GAME}", headers=hdr(t)).json()
    assert empty == {"data": {}, "version": 0, "updated_at": 0}

    r = client.put(f"/v1/saves/{GAME}", json={"data": {"coins": 10}, "version": 0}, headers=hdr(t))
    assert r.json()["version"] == 1
    r = client.put(f"/v1/saves/{GAME}", json={"data": {"coins": 25}, "version": 1}, headers=hdr(t))
    assert r.json()["version"] == 2

    # Stale write (an old device) must be rejected with 409
    stale = client.put(f"/v1/saves/{GAME}", json={"data": {"coins": 1}, "version": 0}, headers=hdr(t))
    assert stale.status_code == 409

    got = client.get(f"/v1/saves/{GAME}", headers=hdr(t)).json()
    assert got["data"] == {"coins": 25}


def test_scores_and_leaderboard(client):
    tokens = []
    for i, score in enumerate([50, 120, 80]):
        t = auth(client, device=f"device-lb-{i:04d}", name=f"P{i}")["token"]
        tokens.append(t)
        r = client.post(f"/v1/scores/{GAME}", json={"score": score}, headers=hdr(t))
        assert r.json()["improved"] is True

    # Lower score does not overwrite best
    r = client.post(f"/v1/scores/{GAME}", json={"score": 10}, headers=hdr(tokens[1]))
    assert r.json()["improved"] is False and r.json()["best"] == 120

    lb = client.get(f"/v1/leaderboards/{GAME}", headers=hdr(tokens[0])).json()
    scores = [e["score"] for e in lb["entries"]]
    assert scores == sorted(scores, reverse=True)
    assert lb["entries"][0]["score"] == 120
    assert lb["me"]["score"] == 50
    assert lb["me"]["rank"] == 3
    assert any(e["you"] for e in lb["entries"])


def test_events_batch(client):
    t = auth(client)["token"]
    batch = {
        "game_id": GAME,
        "events": [
            {"name": "session_start", "props": {"v": "0.1"}, "ts": 1000.0},
            {"name": "game_over", "props": {"score": 12, "layers": 12}, "ts": 1060.0},
        ],
    }
    r = client.post("/v1/events", json=batch, headers=hdr(t))
    assert r.json() == {"ok": True, "accepted": 2}


def test_config_empty_then_seeded(client):
    from app.db import SessionLocal
    from app.models import RemoteConfig
    import json as j

    assert client.get(f"/v1/config/{GAME}").json() == {"data": {}, "version": 0}
    db = SessionLocal()
    db.add(RemoteConfig(game_id=GAME, data=j.dumps({"base_speed": 300.0}), version=1))
    db.commit(); db.close()
    cfg = client.get(f"/v1/config/{GAME}").json()
    assert cfg["data"]["base_speed"] == 300.0


def test_boards_are_separate_leaderboards(client):
    """Mechanics-lab requirement: each game mode == its own board."""
    t = auth(client, device="device-boards-01", name="Modey")["token"]
    client.post(f"/v1/scores/{GAME}", json={"score": 40, "board": "classic"}, headers=hdr(t))
    client.post(f"/v1/scores/{GAME}", json={"score": 7, "board": "pendulum"}, headers=hdr(t))

    classic = client.get(f"/v1/leaderboards/{GAME}?board=classic", headers=hdr(t)).json()
    pendulum = client.get(f"/v1/leaderboards/{GAME}?board=pendulum", headers=hdr(t)).json()
    assert classic["me"]["score"] == 40
    assert pendulum["me"]["score"] == 7
    # The default board ("main") from earlier tests is untouched by mode boards
    main = client.get(f"/v1/leaderboards/{GAME}", headers=hdr(t)).json()
    assert main["me"] is None or main["me"]["score"] != 7


def test_crosspromo_excludes_self(client):
    from app.db import SessionLocal
    from app.models import GameEntry

    db = SessionLocal()
    db.add(GameEntry(game_id="skystack", name="Sky Stack", priority=10))
    db.add(GameEntry(game_id="game2", name="Second Game", priority=5))
    db.commit(); db.close()
    r = client.get(f"/v1/crosspromo/{GAME}").json()
    ids = [g["game_id"] for g in r["games"]]
    assert "skystack" not in ids and "game2" in ids
