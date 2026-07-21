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
        # --- mechanics lab ---
        # Which modes appear in the menu (remove a key to kill a mode remotely):
        "enabled_modes": ["classic", "pendulum", "pulse", "wind", "rush"],
        # Per-mode tuning overrides; any key from Stack.gd::_mode_params().
        "modes": {
            "classic":  {"base_speed": 260.0, "speed_per_layer": 6.0,
                         "max_speed": 700.0, "perfect_window": 7.0},
            "pendulum": {"rope_length": 430.0, "swing_amp": 1.05,
                         "swing_speed": 2.4, "momentum_factor": 0.9,
                         "perfect_window": 10.0},
            "pulse":    {"pulse_speed": 2.6, "pulse_min": 0.35,
                         "pulse_max": 1.45, "perfect_window": 9.0},
            "wind":     {"wind_max": 220.0, "perfect_window": 9.0},
            "rush":     {"base_speed": 300.0, "chaos_flip_chance": 0.4,
                         "chaos_burst": 1.8},
        },
        # --- shared ---
        "fever_streak": 5,
        "regrow_on_perfect": 4.0,
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
