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
    dict(
        game_id="zigroll",
        name="ZigRoll",
        tagline="One tap. Don't fall off.",
        android_url="",
        priority=90,
    ),
    dict(
        game_id="bridgehop",
        name="BridgeHop",
        tagline="Grow the beam. Nail the gap.",
        android_url="",
        priority=80,
    ),
    dict(
        game_id="openlab",
        name="OpenLab",
        tagline="A whole city to mess with.",
        android_url="",
        priority=70,
    ),
    dict(
        game_id="mechlab",
        name="MechLab",
        tagline="Every mechanic. One museum.",
        android_url="",
        priority=60,
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
    },
    "zigroll": {
        "speed": 4.2,            # ball units/sec at start
        "speed_gain": 0.05,      # added per tile crossed
        "max_speed": 9.5,
        "gem_rate": 0.16,        # chance a tile carries a gem
        "gem_bonus": 5,          # score per gem
        "drop_margin": 0.22,     # forgiveness at tile edges (bigger = easier)
        "interstitial_every_n_deaths": 3,
        "crosspromo_enabled": True,
    },
    "bridgehop": {
        "grow_speed": 5.5,       # beam units/sec while holding
        "gap_min": 1.2,
        "gap_max": 4.0,
        "width_min": 1.0,
        "width_max": 2.4,
        "perfect_zone": 0.22,    # half-width of the red center strip
        "perfect_bonus": 1,      # extra score for a perfect landing
        "interstitial_every_n_deaths": 3,
        "crosspromo_enabled": True,
    },
    "mechlab": {
        # Gate which mechanic demos show in the menu (kill/stage remotely):
        "enabled_demos": ["snake", "breakout", "asteroids", "sokoban", "flappy",
                          "match3", "sling", "rhythm", "towerdef", "idle"],
        "interstitial_every_n_deaths": 5,
        "crosspromo_enabled": True,
    },
    "openlab": {
        "npc_count": 14,             # civilians in the city
        "day_length_s": 150.0,       # full day/night cycle duration
        "wanted_decay_s": 18.0,      # seconds without offenses to lose the stars
        "busted_penalty": 50,        # score lost when the cops catch you
        "mission_reward_deliver": 100,
        "checkpoint_bonus": 20,
        "race_complete_bonus": 60,
        "interstitial_every_n_deaths": 4,
        "crosspromo_enabled": True,
    },
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
