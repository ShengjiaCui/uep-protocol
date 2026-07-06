# UEP v2 Mainstream-Dataset Validation Report

**Date**: 2026-07-04　**Protocol**: 2.0.0-draft　**Nature**: protocol interoperability
validation in the field (not a model leaderboard)

> English edition of [validation-report-2026-07.md](validation-report-2026-07.md).
> This is a point-in-time snapshot: numbers (test counts, scores) are as of the
> validation date; on discrepancy the Chinese edition prevails.

## Conclusion (TL;DR)

**Eight mainstream open benchmarks, 804 real items, all through the full UEP chain**:
import → protocol validation → lossless inversion back to the source format →
touchstone rendering → lm-eval-harness export → real scores from a local model.
Every dataset's score profile matches its publicly known difficulty, showing the
scoring chain is faithful; Chinese data (C-Eval, Chinese character riddles) and
English data produce valid scores through **the same code path** — bilingual parity
is a measurement, not a claim. The validation surfaced and fixed three real defects
(see "Findings"), which is exactly what field validation is for.

## Method

```
HF/GitHub upstream (revision + sha256 locked)
   │ scripts/fetch_slices.py
   ▼
real slices (≥100 items per set; data itself not committed)
   │ declarative mapping tables (mapping.yaml, restricted operators,
   │ provenance stamped per item)
   ▼
UEP EvalItem ──┬── uep validate (protocol validation)
               ├── invert_mapping: lossless inversion, field-by-field semantic
               │   equality with source rows (NFC procedure)
               ├── touchstone rendering (assertion set ①–④ + byte-exact goldens)
               └── lm-eval task-package export (generate_until + regex extraction
                      │ + exact_match), scripts/dogfood_run.py
                      ▼
               Ollama gemma3:27b (LAN, temperature=0, first 10 items per set)
```

- **Environment**: lm-eval-harness (separate venv, Python 3.12); Ollama
  OpenAI-compatible chat endpoint; zero paid APIs.
- **Answering convention v1 (direct answer)**: prompt = touchstone rendering +
  zh/en instruction selected by the item's `lang` ("output only the option id /
  final answer, no explanation"); choices extraction takes the first option id
  (dynamically built alternation, longest-first), qa extraction takes the last
  numeric value (pattern overridable).
- Every conversion is test-backed: `make check` = 137 tests green, coverage 94%
  (at validation time).

## Results

| Dataset | Upstream (split) | License | Prototype | Slice | Validate | Lossless inversion | Touchstone | Real-run exact_match (n=10) |
|---------|------------------|---------|-----------|------:|:---:|:---:|:---:|:---:|
| MMLU | cais/mmlu (test) | MIT | choices | 100 | ✅ | ✅ | ✅+golden | **0.60** ±0.16 |
| ARC-Challenge | allenai/ai2_arc (test) | CC-BY-SA-4.0 | choices | 100 | ✅ | ✅ | ✅+golden | **0.80** ±0.13 |
| HellaSwag | Rowan/hellaswag (val) | MIT | choices | 100 | ✅ | ✅ | ✅+golden | **0.70** ±0.15 |
| CommonsenseQA | tau/commonsense_qa (val) | MIT | choices | 100 | ✅ | ✅ | ✅+golden | **0.90** ±0.10 |
| TruthfulQA (mc1) | truthfulqa/truthful_qa (val) | Apache-2.0 | choices | 100 | ✅ | ✅ | ✅+golden | **1.00** ±0.00 |
| C-Eval (Chinese) | ceval/ceval-exam (val, economics+accounting) | CC-BY-NC-SA-4.0 | choices | 104 | ✅ | ✅ | ✅ (no golden†) | **0.70** ±0.15 |
| GSM8K | openai/gsm8k (test) | MIT | **qa** | 100 | ✅ | ✅ | n/a‡ | **0.40** ±0.16 |
| Chinese riddles | openai/evals `Chinese_character_riddles` @8eac7a7d | MIT | **qa** | 100 | ✅ | ✅ (bidirectional) | n/a‡ | **0.20** ±0.13 |

†C-Eval carries a non-commercial license: the assertion-set tests run on the full
local slice, but content excerpts (golden files) are not committed.
‡Touchstone renderer v1 covered the choices prototype only; the qa touchstone was
planned to replicate the same spec in phase 2 (since delivered).

**Examinee**: gemma3:27b (22–27 s per set). The score profile matches the publicly
known difficulty order (common sense 0.8–1.0 > Chinese academic subjects / sentence
completion 0.7 > graduate-level abstract algebra 0.6 > math word problems answered
without chain-of-thought 0.4 > Chinese character riddles 0.2), and two independent
MMLU runs reproduced the score digit-for-digit (0.6000) — the scoring chain is
faithful and deterministic, with no degenerate "all right / all wrong / all invalid"
pipeline behavior.

## Bilingual-parity evidence (P5)

- **One code path**: C-Eval (Chinese) shares the same renderer, exporter,
  extraction, and scoring configuration with the five English choices sets —
  no Chinese special-casing anywhere;
- the Chinese answering instruction switches automatically by the item's `lang`;
  NFC normalization applies through ingest and comparison;
- the Chinese riddles (qa) pass the bidirectional round-trip (100 items,
  field-by-field semantic equality) and then score in a real run — Chinese data
  not only "fits in" but "examines out and inverts back".

## Findings and fixes (direct outputs of this validation)

1. **Multi-character option-id extraction defect** (exposed by TruthfulQA): mc1 has
   12+ options, so ids like "10"/"11" appear; the original extraction regex joined
   alternatives lexicographically, letting "1" match before "11". Fix: sort the
   alternation **longest-first** + a regression test. Real data punctured the naive
   assumption immediately.
2. **Honoring trajectory semantics at export** (exposed by the Chinese riddles):
   the answering convention ("wrap the answer in square brackets") lives in the
   system message; the qa export initially took only `task.question` and lost it.
   Fix: **when a trajectory is present it is the complete task statement** — all
   system/user messages enter the prompt. This validates the protocol's design
   judgment that "question is the degenerate view; trajectory is the substance".
3. **Three new source shapes → three restricted operators** (each with built-in
   inversion): options in separate columns (C-Eval `A/B/C/D`), one-hot answers
   (TruthfulQA `labels`), final-answer suffix convention (GSM8K `#### N`).
   The operator set is closed: every extension goes through the discriminated
   union + tests — not free-form code.
4. **The direct-answer convention depresses reasoning-heavy scores** (GSM8K 0.40
   vs ~0.8+ on chain-of-thought leaderboards): raising the generation cap from
   64 to 256 and removing stop strings changed neither score nor latency — the
   model genuinely obeys "output only the final answer". Conclusion: this is the
   **semantics of the answering convention**, not a pipeline defect; CoT prompting
   is runner-side strategy and the protocol layer does not overreach (recorded as
   a known property of export convention v1).
5. **Upstream ecosystem potholes**: CMMLU (first-choice Chinese set) had migrated
   and is a legacy script-loader dataset no longer served by datasets-server —
   switched to C-Eval; C-Eval's per-subject val splits are each <100 items —
   multi-subject parallel slicing, with the subject composition recorded in the
   lock file (`config_counts`).

## Limitations (stated as-is)

- **n=10 per set is smoke-level scoring**: the goal is "pipeline faithfulness",
  not model ranking; stderr ±0.10–0.16;
- single model (gemma3:27b), temperature=0, single run;
- choices extraction takes the first match; a model that first restates option ids
  from the stem could be misjudged (no such symptom in this round's score profile,
  but it is a known risk surface);
- the qa touchstone and non-choices golden files were pending phase 2
  (since delivered).

## Reproduce

```bash
make check                                   # full-chain assertions incl. the 804-item slices
python scripts/fetch_slices.py               # verify/refill slices per slices.lock.json
python scripts/dogfood_run.py --slice mmlu --limit 10          # real-run any dataset
python scripts/dogfood_run.py --slice openai_evals --limit 10 \
    --answer-pattern '(\[[^\]]+\])'          # Chinese riddles (bracket convention)
```

Raw result JSON lands in `build/dogfood/<slice>/results/` (not committed;
regenerated per run).
