"""Seed the cross-promo catalog and remote config for Sky Stack.

Run once after first boot:  python seed.py
Idempotent — safe to run again after adding new games.
"""
import json

from app.db import Base, SessionLocal, engine
from app.models import GameEntry, RemoteConfig

Base.metadata.create_all(bind=engine)

GAMES = [
    dict(
        game_id="skystack",
        name="Sky Stack",
        tagline="How high can you go?",
        android_url="",  # fill with Play Store URL after publishing
        priority=100,
    ),
]

CONFIGS = {
    "skystack": {
        # Tune the live game without shipping an update:
        "base_speed": 260.0,          # px/sec initial slide speed
        "speed_per_layer": 6.0,       # speed added per stacked layer
        "max_speed": 700.0,
        "perfect_window": 7.0,        # px tolerance for a perfect drop
        "fever_streak": 5,            # perfects in a row to trigger fever
        "regrow_on_perfect": 4.0,     # px width regained on perfect
        "interstitial_every_n_deaths": 3,
        "crosspromo_enabled": True,
    }
}

def main():
    db = SessionLocal()
    for g in GAMES:
        if db.get(GameEntry, g["game_id"]) is None:
            db.add(GameEntry(**g))
    for game_id, data in CONFIGS.items():
        row = db.get(RemoteConfig, game_id)
        if row is None:
            db.add(RemoteConfig(game_id=game_id, data=json.dumps(data), version=1))
        else:
            row.data = json.dumps(data)
            row.version += 1
    db.commit()
    db.close()
    print("Seeded.")

if __name__ == "__main__":
    main()
