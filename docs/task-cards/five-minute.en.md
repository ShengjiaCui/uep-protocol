# UEP Five-Minute Task Card (L2 timed test)

[中文版](five-minute.zh.md)

## Goal (what, never how)

Turn an unfamiliar two-column Q&A CSV into a UEP dataset and export it to **two**
runner formats:

1. the converted dataset (items.jsonl + manifest.json) passes `uep validate`;
2. both runner export artifacts are written successfully.

> Find the steps yourself in the README — the README is part of what is being tested.

## Preconditions (not timed)

- Python ≥3.10 and uv installed; this repository cloned; network available;
- time spent installing dependencies or downloading models/data does **not** count.

## Timing window

From receiving this card and the CSV file until both goals above are met:
**pass at ≤ 5:00**.

Material: any two-column Q&A CSV (`examples/quiz.csv` works if you have none).

## Real scoring (optional, not timed)

Run the exported lm-eval task package against a local Ollama model with
`--limit 3`, recorded separately (model speed is not protocol usability).

## Record sheet

| Field | Entry |
|-------|-------|
| Tester / background / date | |
| Start time | |
| End time | |
| Duration | |
| Blockers encountered | |
| One-sentence verdict | |
| Result (pass ≤5:00 / fail) | |

Rule: on failure, fix the docs first; one retest with a different person is allowed
(test spec §⑤).
