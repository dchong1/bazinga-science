# bazinga-science

Daily question packs for **IB MYP Science** (Investigative Science / fair tests as the core roadmap; stretch into related ideas such as energy when the learner is ready).

Nordic-minimal: short prompts, mixed formats, points + streak, adaptive mix from recent results. Stdlib only — no pip install.

## Learner profile

Before generating packs (or when sharing this with someone new), set who the learner is. The tool does **not** hardcode a student or school.

```bash
python3 generate_daily.py --set-profile --name "Alex" --age 12 --level "MYP 1"
python3 generate_daily.py --show-profile
```

| Flag | Meaning | Example |
|------|---------|---------|
| `--name` | Learner display name | Alex |
| `--age` | Age (years) | 12 |
| `--level` | Science level / programme year | MYP 1, MYP 2, beginner |

Profile is stored in the local progress DB (gitignored). Use it so a tutor or LLM can pitch questions at the right level. Defaults are empty / generic — fill them in for your learner.

## Quick start

```bash
cd bazinga-science   # or wherever you cloned the repo
python3 generate_daily.py                 # write today's pack
python3 generate_daily.py --date 2026-10-13
python3 generate_daily.py --record ft-w03 correct
python3 generate_daily.py --record en-s01 wrong
python3 generate_daily.py --stats
```

Outputs:

- `packs/YYYY-MM-DD.json` — structured pack (for tools / tutors)
- `packs/YYYY-MM-DD.md` — chat-friendly markdown (**answer key is facilitator-only**)
- `progress.db` — SQLite log (asks, results, streak/points, learner profile); gitignored

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

Recent question IDs are avoided when the bank allows. Curriculum stays a **roadmap**: stretch items pull in energy / reliability / nature-of-science once core fair-test ideas are landing.

## How a facilitator / tutor uses this daily

1. Set the learner profile once (`--set-profile`).
2. Run `python3 generate_daily.py` (or open today’s files in `packs/`).
3. Present 3–5 items in chat — prefer buttons / choices for MC-style formats; keep prompts short. **Do not show the answer key to the learner.**
4. After the learner answers, record:  
   `python3 generate_daily.py --record <id> correct|wrong`
5. Celebrate streak milestones lightly; dig into the `science_idea` line when they’re curious.
6. Dry-runs by the facilitator should not be logged as learner attempts — only log the learner’s answers for adapting.

## Seed bank

`questions.json` — 24 items across warm / core / stretch:

- Fair tests, IV / DV / controls, hypothesis (If–then–because)
- Everyday unfair tests, reliability, confounding
- Stretch: kinetic energy, GPE→KE, energy chains, critique of messy methods

Add questions by appending objects with: `id`, `topic`, `difficulty`, `format`, `prompt`, `choices`, `answer`, `explanation`, optional `pairs`, `science_idea`, `tags`.

## Schema (SQLite)

- **asks** — each question placed in a pack (`pack_date`, `question_id`, difficulty/format/topic)
- **results** — each scored attempt (`correct`, `points_awarded`)
- **meta** — `streak`, `best_streak`, `total_points`, plus optional `learner_name`, `learner_age`, `learner_level`

Optional future: export JSONL mirror; Notion sync of the log; LLM-assisted generation that reads the learner profile.

## Design choices

- **Stdlib only** — easy to run anywhere with no install.
- **Deterministic daily shuffle** — pack selection RNG seeded by pack date (override with `--seed`). Multiple-choice-style items also get a **per-question choice order shuffle** (seed: pack date + question id) so the correct letter is not stuck on A; the answer key in each pack matches the shuffled order.
- **Answer key in markdown** — facilitator-only; strip before showing the learner if needed.
- **Diagram format is text v1** — real images can slot in later without changing IDs.
- **Match format** uses a single correct choice that encodes the pairing (chat-button friendly).
- **Public-friendly** — no school, student, or parent identifiers in the repo; profile is local and gitignored.
