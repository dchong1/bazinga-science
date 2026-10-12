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
MIX = {"support": (3, 2, 0), "steady": (1, 3, 1), "stretch": (0, 2, 3)}

# NOTE: truncated for test
