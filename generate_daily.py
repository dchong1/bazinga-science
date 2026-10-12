#!/usr/bin/env python3
"""
bazinga-science — daily IB MYP Science question pack generator (stdlib only).

Usage:
  python generate_daily.py              # today's pack → stdout + packs/
  python generate_daily.py --date 2026-10-12
  python generate_daily.py --record QID correct|wrong   # log a result
  python generate_daily.py --stats                      # streak/points summary
  python generate_daily.py --set-profile --name NAME [--age N] [--level LEVEL]
  python generate_daily.py --show-profile
"""

from __future__ import annotations

import argparse
import hashlib
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

# Adaptive mix targets: (warm, core, stretch) counts for a 5-question pack
MIX = {
    "support": (3, 2, 0),   # recent struggles
    "steady": (1, 3, 1),    # default / balanced
    "stretch": (0, 2, 3),   # recent wins
}


# ── DB ───────────────────────────────────────────────────────────────────────
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
    # Ensure streak/points keys exist
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


def meta_get(conn: sqlite3.Connection, key: str) -> str:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else "0"


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# ── Questions ──────────────────────────────────────────────────────────────
def load_questions() -> list[dict]:
    with QUESTIONS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    for q in data:
        assert q["difficulty"] in POINTS, q["id"]
        assert q["format"] in FORMATS, q["id"]
    return data


def recent_accuracy(conn: sqlite3.Connection, n: int = 10) -> float | None:
    rows = conn.execute(
        "SELECT correct FROM results ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    if not rows:
        return None
    return sum(r["correct"] for r in rows) / len(rows)


def choose_mode(conn: sqlite3.Connection) -> str:
    acc = recent_accuracy(conn)
    if acc is None:
        return "steady"
    if acc >= 0.8:
        return "stretch"
    if acc < 0.5:
        return "support"
    return "steady"


def recently_asked_ids(conn: sqlite3.Connection, days_back_packs: int = 7) -> set[str]:
    """Avoid immediate repeats from recent packs."""
    rows = conn.execute(
        "SELECT DISTINCT question_id FROM asks ORDER BY id DESC LIMIT ?",
        (days_back_packs * PACK_SIZE,),
    ).fetchall()
    return {r["question_id"] for r in rows}


def pick_pack(questions: list[dict], conn: sqlite3.Connection, rng: random.Random) -> tuple[list[dict], str]:
    mode = choose_mode(conn)
    targets = {"warm": MIX[mode][0], "core": MIX[mode][1], "stretch": MIX[mode][2]}
    avoid = recently_asked_ids(conn)

    by_diff: dict[str, list[dict]] = {"warm": [], "core": [], "stretch": []}
    for q in questions:
        by_diff[q["difficulty"]].append(q)

    chosen: list[dict] = []
    used_formats: set[str] = set()

    def score(q: dict) -> tuple:
        # Prefer unseen formats, then not-recently-asked
        return (
            0 if q["format"] in used_formats else 1,
            0 if q["id"] in avoid else 1,
            rng.random(),
        )

    for diff, n in targets.items():
        pool = by_diff[diff][:]
        for _ in range(n):
            if not pool:
                break
            pool.sort(key=score, reverse=True)
            q = pool.pop(0)
            # Remove from further consideration in this pool
            chosen.append(q)
            used_formats.add(q["format"])
            pool = [p for p in pool if p["id"] != q["id"]]

    if len(chosen) < PACK_SIZE:
        leftover = [q for q in questions if q["id"] not in {c["id"] for c in chosen}]
        leftover.sort(key=score, reverse=True)
        chosen += leftover[: PACK_SIZE - len(chosen)]

    rng.shuffle(chosen)
    return chosen[:PACK_SIZE], mode


CHOICE_KEYS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def choice_shuffle_rng(pack_date: str, question_id: str) -> random.Random:
    """Stable per (pack date, question id) — same pack regenerates the same lettering."""
    digest = hashlib.sha256(f"{pack_date}:{question_id}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def shuffle_choices_for_pack(q: dict, pack_date: str) -> dict:
    """Shuffle lettered choices for output; remap answer key. Bank copy is unchanged."""
    choices = q.get("choices")
    if not choices:
        return q

    out = {k: v for k, v in q.items() if k not in ("choices", "answer")}
    shuffled = [dict(c) for c in choices]
    correct_key = q["answer"]
    rng = choice_shuffle_rng(pack_date, q["id"])
    rng.shuffle(shuffled)

    new_answer: str | None = None
    relabeled: list[dict] = []
    for i, c in enumerate(shuffled):
        if c["key"] == correct_key:
            new_answer = CHOICE_KEYS[i]
        relabeled.append({"key": CHOICE_KEYS[i], "text": c["text"]})

    if new_answer is None:
        raise ValueError(f"Answer key {correct_key!r} not found in choices for {q['id']}")

    out["choices"] = relabeled
    out["answer"] = new_answer
    return out


def prepare_pack_questions(pack: list[dict], pack_date: str) -> list[dict]:
    return [shuffle_choices_for_pack(q, pack_date) for q in pack]


# ── Render ───────────────────────────────────────────────────────────────────
def render_question_md(i: int, q: dict) -> str:
    points = POINTS[q["difficulty"]]
    lines = [
        f"### Q{i}. [{q['difficulty'].upper()} · {q['format']} · +{points} pt] `{q['id']}`",
        "",
        q["prompt"],
        "",
    ]
    if q.get("choices"):
        for c in q["choices"]:
            lines.append(f"- **{c['key']}.** {c['text']}")
        lines.append("")
    if q.get("pairs"):
        lines.append("_Match pairs (reference):_")
        for p in q["pairs"]:
            lines.append(f"- {p['left']} ↔ {p['right']}")
        lines.append("")
    lines.append(f"_Answer key (facilitator only):_ **{q['answer']}** — {q['explanation']}")
    if q.get("science_idea"):
        lines.append(f"_Science idea:_ {q['science_idea']}")
    lines.append("")
    return "\n".join(lines)


def pack_to_markdown(pack_date: str, mode: str, questions: list[dict], streak: int, points: int) -> str:
    header = [
        f"# Bazinga daily pack — {pack_date}",
        "",
        f"Mode: **{mode}** · Current streak: **{streak}** · Total points: **{points}**",
        "",
        "Formats: MC · Spot-the-unfair · If–then–because · Match · Diagram/describe",
        "",
        "---",
        "",
    ]
    body = [render_question_md(i, q) for i, q in enumerate(questions, 1)]
    footer = [
        "---",
        "",
        "**Points:** warm +1 · core +2 · stretch +3. Streak +1 on correct, reset on wrong.",
        "Milestones: 3 (Nice spark), 5 (On a roll), 10 (Science streak!).",
        "",
    ]
    return "\n".join(header + body + footer)


def pack_to_json(pack_date: str, mode: str, questions: list[dict], streak: int, points: int) -> dict:
    return {
        "pack_date": pack_date,
        "mode": mode,
        "streak": streak,
        "total_points": points,
        "points_rules": POINTS,
        "questions": [
            {
                **{k: q[k] for k in (
                    "id", "topic", "difficulty", "format", "prompt",
                    "choices", "pairs", "answer", "explanation", "science_idea", "tags",
                ) if k in q},
                "points_if_correct": POINTS[q["difficulty"]],
            }
            for q in questions
        ],
    }


# ── Actions ──────────────────────────────────────────────────────────────────
def generate(pack_date: str, seed: int | None = None) -> Path:
    questions = load_questions()
    rng = random.Random(seed if seed is not None else pack_date)
    conn = connect()
    pack, mode = pick_pack(questions, conn, rng)
    pack = prepare_pack_questions(pack, pack_date)
    streak = int(meta_get(conn, "streak"))
    total_points = int(meta_get(conn, "total_points"))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for q in pack:
        conn.execute(
            "INSERT INTO asks(asked_at, pack_date, question_id, difficulty, format, topic) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now, pack_date, q["id"], q["difficulty"], q["format"], q["topic"]),
        )
    conn.commit()

    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    payload = pack_to_json(pack_date, mode, pack, streak, total_points)
    json_path = PACKS_DIR / f"{pack_date}.json"
    md_path = PACKS_DIR / f"{pack_date}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(pack_to_markdown(pack_date, mode, pack, streak, total_points), encoding="utf-8")

    # Console summary
    formats = Counter(q["format"] for q in pack)
    diffs = Counter(q["difficulty"] for q in pack)
    print(f"Pack {pack_date}  mode={mode}  streak={streak}  points={total_points}")
    print(f"  difficulties: {dict(diffs)}")
    print(f"  formats:      {dict(formats)}")
    print(f"  ids: {[q['id'] for q in pack]}")
    print(f"  wrote {json_path}")
    print(f"  wrote {md_path}")
    conn.close()
    return json_path


def celebrate(streak: int) -> str | None:
    milestones = {3: "Nice spark ✨", 5: "On a roll 🔥", 10: "Science streak! 🏆"}
    return milestones.get(streak)


def record_result(question_id: str, correct: bool) -> None:
    questions = {q["id"]: q for q in load_questions()}
    if question_id not in questions:
        raise SystemExit(f"Unknown question id: {question_id}")
    q = questions[question_id]
    diff = q["difficulty"]
    pts = POINTS[diff] if correct else 0

    conn = connect()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO results(recorded_at, question_id, correct, points_awarded, difficulty) "
        "VALUES (?, ?, ?, ?, ?)",
        (now, question_id, 1 if correct else 0, pts, diff),
    )

    streak = int(meta_get(conn, "streak"))
    best = int(meta_get(conn, "best_streak"))
    total = int(meta_get(conn, "total_points"))

    if correct:
        streak += 1
        total += pts
        best = max(best, streak)
    else:
        streak = 0

    meta_set(conn, "streak", str(streak))
    meta_set(conn, "best_streak", str(best))
    meta_set(conn, "total_points", str(total))
    conn.commit()

    msg = f"Recorded {question_id}: {'correct' if correct else 'wrong'} (+{pts}). streak={streak} best={best} total_points={total}"
    note = celebrate(streak) if correct else None
    if note:
        msg += f"  → {note}"
    print(msg)
    conn.close()



def set_profile(name: str | None, age: str | None, level: str | None) -> None:
    """Store generic learner profile in meta (local DB only; not committed)."""
    conn = connect()
    if name is not None:
        meta_set(conn, "learner_name", name.strip())
    if age is not None:
        meta_set(conn, "learner_age", str(age).strip())
    if level is not None:
        meta_set(conn, "learner_level", level.strip())
    conn.commit()
    print("Profile updated.")
    show_profile(conn)
    conn.close()


def show_profile(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    if own:
        conn = connect()
    name = meta_get(conn, "learner_name") or "(unset)"
    age = meta_get(conn, "learner_age") or "(unset)"
    level = meta_get(conn, "learner_level") or "(unset)"
    print(f"Learner profile: name={name}  age={age}  level={level}")
    print("(Use with a tutor/LLM to pitch IB MYP Science questions at the right level.)")
    if own:
        conn.close()


def show_stats() -> None:
    conn = connect()
    streak = meta_get(conn, "streak")
    best = meta_get(conn, "best_streak")
    total = meta_get(conn, "total_points")
    n = conn.execute("SELECT COUNT(*) AS c FROM results").fetchone()["c"]
    right = conn.execute("SELECT COUNT(*) AS c FROM results WHERE correct=1").fetchone()["c"]
    acc = (right / n) if n else None
    mode = choose_mode(conn)
    print(f"Results logged: {n}  correct: {right}  accuracy: {acc if acc is None else f'{acc:.0%}'}")
    print(f"Streak: {streak}  best: {best}  total_points: {total}")
    print(f"Next pack adaptive mode: {mode}")
    recent = conn.execute(
        "SELECT question_id, correct, points_awarded, recorded_at FROM results ORDER BY id DESC LIMIT 5"
    ).fetchall()
    if recent:
        print("Recent:")
        for r in recent:
            flag = "✓" if r["correct"] else "✗"
            print(f"  {flag} {r['question_id']} +{r['points_awarded']}  {r['recorded_at']}")
    conn.close()


def main() -> None:
    p = argparse.ArgumentParser(
        description="bazinga-science — daily IB MYP Science question packs"
    )
    p.add_argument("--date", default=None, help="Pack date YYYY-MM-DD (default: today local)")
    p.add_argument("--seed", type=int, default=None, help="Optional RNG seed override")
    p.add_argument(
        "--record",
        nargs=2,
        metavar=("QID", "correct|wrong"),
        help="Log a result for adaptive difficulty + points",
    )
    p.add_argument("--stats", action="store_true", help="Show streak/points/accuracy")
    p.add_argument(
        "--set-profile",
        action="store_true",
        help="Store learner profile (use with --name / --age / --level)",
    )
    p.add_argument("--show-profile", action="store_true", help="Print stored learner profile")
    p.add_argument("--name", default=None, help="Learner name (generic; not committed)")
    p.add_argument("--age", default=None, help="Learner age in years (optional)")
    p.add_argument(
        "--level",
        default=None,
        help="Science level, e.g. MYP 1, MYP 2, beginner (optional)",
    )
    args = p.parse_args()

    if args.show_profile:
        show_profile()
        return
    if args.set_profile:
        if args.name is None and args.age is None and args.level is None:
            raise SystemExit("Pass at least one of --name, --age, --level with --set-profile")
        set_profile(args.name, args.age, args.level)
        return
    if args.stats:
        show_stats()
        return
    if args.record:
        qid, flag = args.record
        flag = flag.lower()
        if flag not in ("correct", "wrong", "1", "0", "true", "false"):
            raise SystemExit("Use correct|wrong")
        correct = flag in ("correct", "1", "true")
        record_result(qid, correct)
        return

    pack_date = args.date or date.today().isoformat()
    generate(pack_date, seed=args.seed)


if __name__ == "__main__":
    main()
