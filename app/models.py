"""SQLAlchemy models — deliberately multi-game from day one.

Every table that stores gameplay data carries a game_id so the same backend
serves the entire portfolio.
"""
import time
import uuid

from sqlalchemy import Boolean, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def now_ts() -> float:
    return time.time()


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    device_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), default="Player")
    country: Mapped[str] = mapped_column(String(8), default="")
    created_at: Mapped[float] = mapped_column(Float, default=now_ts)
    last_seen_at: Mapped[float] = mapped_column(Float, default=now_ts)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)


class CloudSave(Base):
    __tablename__ = "cloud_saves"
    __table_args__ = (UniqueConstraint("player_id", "game_id", name="uq_save"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String(32), index=True)
    game_id: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[str] = mapped_column(Text, default="{}")  # JSON blob
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[float] = mapped_column(Float, default=now_ts)


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", "board", name="uq_score"),
        Index("ix_board_best", "game_id", "board", "best"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String(32), index=True)
    game_id: Mapped[str] = mapped_column(String(64))
    board: Mapped[str] = mapped_column(String(64), default="main")
    best: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[float] = mapped_column(Float, default=now_ts)


class RemoteConfig(Base):
    __tablename__ = "remote_configs"

    game_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[str] = mapped_column(Text, default="{}")  # JSON blob
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[float] = mapped_column(Float, default=now_ts)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String(32), index=True)
    game_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    props: Mapped[str] = mapped_column(Text, default="{}")  # JSON blob
    client_ts: Mapped[float] = mapped_column(Float, default=0.0)
    server_ts: Mapped[float] = mapped_column(Float, default=now_ts)


class GameEntry(Base):
    """Cross-promo catalog: every game in the portfolio."""

    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    tagline: Mapped[str] = mapped_column(String(256), default="")
    android_url: Mapped[str] = mapped_column(String(512), default="")
    ios_url: Mapped[str] = mapped_column(String(512), default="")
    icon_url: Mapped[str] = mapped_column(String(512), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
