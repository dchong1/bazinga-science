#!/usr/bin/env python3
"""
bazinga-science — daily IB MYP Science question pack generator (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUESTIONS_PATH = ROOT / "questions.json"
DB_PATH = ROOT / "progress.db"
PACKS_DIR = ROOT / "packs"

POINTS = {"warm": 1, "core": 2, "stretch": 3}
FORMATS = ("mc", "spot_unfair", "if_then_because", "match", "diagram_describe")
PACK_SIZE = 5

MIX = {
    "support": (3, 2, 0),
    "steady": (1, 3, 1),
    "stretch": (0, 2, 3),
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS asks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asked_at TEXT NOT NULL,
            pack_date TEXT NOT NULL,
            question_id TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            format TEXT NOT NULL,
            topic TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            question_id TEXT NOT NULL,
            correct INTEGER NOT NULL,
            points_awarded INTEGER NOT NULL,
            difficulty TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    for key, default in (
        ("streak", "0"),
        ("best_streak", "0"),
        ("total_points", "0"),
        ("learner_name", ""),
        ("learner_age", ""),
        ("learner_level", ""),
    ):
        conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)", (key, default)
        )
    conn.commit()
    return conn


def main() -> None:
    p = argparse.ArgumentParser(description="bazinga-science daily packs")
    p.parse_args()


if __name__ == "__main__":
    main()
