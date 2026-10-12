# Sheldon science daily question generator

Lightweight pack builder for **Matthew** (STC Year 7 / MYP 1). Unit 1.2 *Investigative Science* is the roadmap; stretch into related ideas (e.g. kinetic energy) when he’s ready.

Nordic-minimal: short prompts, mixed formats, points + streak, adaptive mix from recent results. Stdlib only.

## Quick start

```bash
cd /workspace/sheldon-science-generator
python3 generate_daily.py                 # write today's pack
python3 generate_daily.py --date 2026-10-13
python3 generate_daily.py --record ft-w03 correct
python3 generate_daily.py --record en-s01 wrong
python3 generate_daily.py --stats
```

Outputs:

- `packs/YYYY-MM-DD.json` — structured pack (for Sheldon / tools)
- `packs/YYYY-MM-DD.md` — chat-friendly markdown (answer key included for Sheldon)
- `sheldon_progress.db` — SQLite log (asks, results, streak/points)

## Formats

| Format | Use |
|--------|-----|
| `mc` | Classic multiple choice |
| `spot_unfair` | Find the broken fair test |
| `if_then_because` | Complete / pick a hypothesis shape |
| `match` | Link IV / DV / controls (choices wrap the pairing) |
| `diagram_describe` | Text stand-in for a lab sketch or energy chain |

No home chem / hot practicals in the seed bank.

## Points & streak

| Difficulty | Points if correct |
|------------|-------------------|
| warm | +1 |
| core | +2 |
| stretch | +3 |

- **Streak:** +1 on correct, reset to 0 on wrong.
- **Milestones** (light celebrate): 3 → “Nice spark”, 5 → “On a roll”, 10 → “Science streak!”.
- Wrong answers still get logged (for adapting); they award 0 points.

## Adaptive difficulty

`generate_daily.py` looks at the last ~10 logged results:

| Recent accuracy | Mode | Pack mix (of 5) |
|-----------------|------|-----------------|
| none yet | `steady` | 1 warm · 3 core · 1 stretch |
| ≥ 80% | `stretch` | 0 warm · 2 core · 3 stretch |
| < 50% | `support` | 3 warm · 2 core · 0 stretch |
| otherwise | `steady` | 1 warm · 3 core · 1 stretch |

Recent question IDs are avoided when the bank allows. Curriculum stays a **roadmap**: stretch items pull in energy / reliability / nature-of-science once he’s landing core fair-test ideas.

## How Sheldon uses this daily

1. Run `python3 generate_daily.py` (or open today’s files in `packs/`).
2. Present 3–5 items in chat — prefer buttons / choices for MC-style formats; keep prompts short.
3. After Matthew answers, record:  
   `python3 generate_daily.py --record <id> correct|wrong`
4. Celebrate streak milestones lightly; dig into the `science_idea` line when he’s curious.
5. Dennis dry-runs ≠ Matthew — only log Matthew’s attempts for adapting.

## Seed bank

`questions.json` — 24 items across warm / core / stretch:

- Fair tests, IV / DV / controls, hypothesis (If–then–because)
- Everyday unfair tests, reliability, confounding
- Stretch: kinetic energy, GPE→KE, energy chains, critique of messy methods

Add questions by appending objects with: `id`, `topic`, `difficulty`, `format`, `prompt`, `choices`, `answer`, `explanation`, optional `pairs`, `science_idea`, `tags`.

## Schema (SQLite)

- **asks** — each question placed in a pack (`pack_date`, `question_id`, difficulty/format/topic)
- **results** — each scored attempt (`correct`, `points_awarded`)
- **meta** — `streak`, `best_streak`, `total_points`

Optional future: export JSONL mirror; Notion sync of the log.

## Design choices

- **Stdlib only** — easy to run on Sheldon’s box with no install.
- **Deterministic daily shuffle** — RNG seeded by pack date (override with `--seed`).
- **Answer key in markdown** — Sheldon-facing; strip before showing Matthew if needed.
- **Diagram format is text v1** — real images can slot in later without changing IDs.
- **Match format** uses a single correct choice that encodes the pairing (chat-button friendly).
