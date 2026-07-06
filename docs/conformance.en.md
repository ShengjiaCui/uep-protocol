# UEP Conformance Kit

[中文版](conformance.zh.md)

For **benchmark creators**: a three-layer self-check in one command. Passing means
your dataset is mechanically consumable by the standard toolchain — validatable,
composable, exportable, with self-evident scoring intent.

```bash
uep conform my_ds/items.jsonl
```

## The three layers

| Layer | What it checks | What failing means |
|---|---------|---------------|
| 1 schema | every line is a valid EvalItem (bad lines reported with line numbers, bilingual) | the data is not UEP yet |
| 2 touchstone-consumable | every item renders through the **standard consumer for its prototype** (consumer source contains zero dataset names) | scoring intent is not self-evident — standard runners cannot score it mechanically |
| 3 manifest consistency | manifest size / task_types / languages are **recomputed from items** and compared | manifest drift (the manifest says one thing, the data is another) |

## Boundaries and conventions

- **custom prototype** items (the governed escape hatch, SPEC §3.6) skip layer 2
  with a counted note — the escape hatch is outside touchstone jurisdiction by design;
- **missing manifest.json** = layer 3 skipped with a note (shipping items.jsonl
  alone is a legitimate form);
- **items scored only by llm_judge**: schema-valid but fail layer 2 — deliberately:
  L1 conformance = mechanical consumability; subjective scoring is beyond the L1 promise;
- exit codes: `0` pass / `1` fail / `2` usage error; `--lang zh|en` switches output.

## Relation to the verification pyramid

`uep conform` packages this repository's L1 mechanical layer for third-party
datasets: the same touchstones and the same manifest recomputation that our own
12 integrated datasets pass on every CI run (reproducible via gate 1 of
`make demo`). If your dataset passes conform, it stands on the same foundation.
