# UEP — Universal AI Evaluation Protocol (v2)

[中文](README.md) | **English**

> **Status: under active development (protocol `2.0.0-draft`), validated end-to-end
> on 8 mainstream open benchmarks, 804 real items** (import → validate → lossless
> inversion → export → real scores from a local model,
> [validation report](docs/validation-report-2026-07.md)). Interfaces and fields may
> still change; formalization follows the versioning discipline in
> [SPEC §9](docs/uep-v2-spec.md). Criticism welcome — please open an issue.

**UEP is an interoperability layer for AI evaluation data**: it "translates"
heterogeneous benchmark data into one task-prototype-based protocol, then exports it
losslessly to any evaluation runner. UEP is deliberately **never a runner** — it does
not call models or compute scores; it only keeps semantics intact while data flows
across the ecosystem.

```
datasets ──import──▶ UEP items (protocol) ──export──▶ runner formats
    ▲                                                      │
    └────────── reversible (mapping tables invert mechanically) ◀──┘
```

## Five minutes: one CSV → two runners

```bash
# 0) Install (Python ≥3.10; uv recommended. The venv then has the `uep` command)
uv venv && uv pip install -e '.[dev]'
source .venv/bin/activate

# 1) Two-column Q&A CSV → UEP dataset directory (items.jsonl + manifest.json)
uep convert examples/quiz.csv --from csv -o my_ds --content-lang zh-CN --license unknown
#    If your columns are not question/answer: --question-col NAME --answer-col NAME

# 2) Validate + inspect
uep validate my_ds/items.jsonl
uep list  my_ds/items.jsonl        # one line per item: id / type / lang / gist
uep stats my_ds/items.jsonl        # size + type / language / verifier distributions

# 3) Export the same data to two runner formats
uep export my_ds/items.jsonl --to lmeval     -o my_ds_lmeval    # lm-eval-harness task
uep export my_ds/items.jsonl --to inspect_ai -o my_ds_inspect   # Inspect AI samples
```

Every verb supports `--lang zh|en` (or the `UEP_LANG` environment variable).
For a timed self-test, use the
[five-minute task card](docs/task-cards/five-minute.en.md).

## Verbs at a glance

| Verb | Purpose |
|------|---------|
| `validate` | Validate items.jsonl / manifest.json (line/field-level bilingual errors) |
| `convert` | Source format → UEP dataset directory (`--from` names come from the adapter registry) |
| `export` | UEP → runner task package (`--to lmeval` / `--to inspect_ai`) |
| `list` / `show` / `stats` | Inspect: per-line overview / full JSON by id / distributions |
| `filter` | Compose: select by `--type` (task type) and `--task-lang` (BCP-47 prefix match) |
| `slice` | Compose: `--range START:STOP` half-open slice |
| `sample` | Compose: `--n N --seed S` seeded sampling (reproducible, source order kept) |
| `merge` | Compose: merge item files (id conflicts are named and rejected, never deduped silently) |
| `conform` | Conformance self-check ([kit docs](docs/conformance.en.md)): schema + touchstone-consumable + manifest consistency |

Composition verbs write a new dataset directory (manifest aggregated mechanically
from items), immediately ready for `validate` / `export` again — converted, composed,
and exported datasets are the same first-class citizen:

```bash
uep filter my_ds/items.jsonl -o zh_qa  --type qa --task-lang zh   # Chinese Q&A subset
uep sample bank/items.jsonl  -o quiz10 --n 10 --seed 7            # reproducible 10-item quiz
```

## Design principles (six hard constraints, see [SPEC §1](docs/uep-v2-spec.md))

1. Same semantics → same canonical field (task prototypes: `qa` / `choices` /
   `code_generation` / `patch_repair` / `retrieval`)
2. A Verifier is self-contained: everything needed to score lives in it
   (correct answers exist only inside Verifiers)
3. `extras` holds runner-specific parameters only; task substance in extras is a
   defect (linted by tooling)
4. Expressiveness ceiling = the AI-agent task space (environment / trajectory /
   composite verification are in the skeleton from day one)
5. Chinese and English are equal citizens (content, scoring semantics, vocabulary,
   tooling — all four layers)
6. Naming follows industry practice and domain expertise; on conflict prefer the
   professional term, and bring in a human when it is hard to decide

## What works today (all backed by tests)

- **Import 11 mainstream datasets** (covering all five task prototypes):
  MMLU / ARC-Challenge / HellaSwag / CommonsenseQA / TruthfulQA /
  **C-Eval (Chinese)** (choices), **GSM8K** (qa), **HumanEval** (code_generation),
  **SWE-bench Lite** (patch_repair), **SciFact** / **T2Ranking (Chinese)**
  (retrieval) → UEP — accepted against real slices of ≥100 items per set,
  declarative mapping tables + provenance stamps, **all losslessly invertible
  back to the source format**
- **Bidirectional round-trip**: OpenAI Evals ↔ UEP (100 real Chinese character
  riddles, semantically equivalent item by item)
- **Export to two runners**: lm-eval-harness task packages (choices and qa) and
  Inspect AI samples. lm-eval ran against a local Ollama model on 8 sets
  (gemma3:27b, 10 items each): CommonsenseQA 0.90 / ARC 0.80 / HellaSwag 0.70 /
  C-Eval 0.70 / MMLU 0.60 / GSM8K 0.40 / Chinese riddles 0.20 / TruthfulQA 1.00 —
  the difficulty profile matches public expectations, so the scoring chain is
  faithful (details in the [validation report](docs/validation-report-2026-07.md))
- **Real scores for four prototypes + mechanically verifiable patch payloads**:
  codegen pass@1 (Inspect local sandbox), retrieval ndcg@10 bilingual (BM25
  baseline), patch grading payloads mechanically verifiable + official-harness
  integration (docker boundary stated honestly) — see [scoring closure report](docs/scoring-closure-2026-07.md)
- **Score-level interoperability, cross-verified**: the same UEP dataset run
  through both lm-eval and Inspect AI, **both forced to greedy decoding** — MMLU
  aggregate scores identical (Δ=0, 92% per-item agreement); GSM8K diverges 0.56 on
  a single prompt instruction, **root cause pinned by a controlled experiment**
  (aligning the prompt makes per-item verdicts identical, Δ=0). Interoperability
  holds at the **data layer**; score-level parity = data alignment (protocol) +
  prompt/decoding alignment (caller's choice) — see
  [cross-runner report](docs/crossrunner-2026-07.md)
- **Native Chinese codegen sample set**: 20 **UEP-native** (not converted)
  Chinese-prompt Python codegen problems (self-written Apache-2.0, data committed at
  `examples/zh-codegen/`) — the author writes only problem content; the schema + a
  66-line builder fill in all protocol scaffolding (easier than hand-writing
  items.jsonl). Passes `validate`/`conform` (3 layers) + 20 reference-solution
  self-tests, scored end-to-end through the A1 closure at **pass@1=1.00** (gemma3:27b
  greedy; a negative control confirms the scorer fails wrong code). Fills the Chinese
  codegen licensing gap — see [native zh-codegen report](docs/zh-codegen-2026-07.md)
- **Management CLI (11 verbs, bilingual)**: convert / validate / export +
  list / show / stats + filter / slice / sample / merge + **conform (the
  conformance kit — self-check for newly built datasets)** — composed outputs
  are datasets in their own right; bilingual parity is enforced by mechanism
  (the message catalog is asserted key-by-key for zh/en completeness and
  placeholder equality), not by discipline
- **Performance**: a 10,000-row CSV converts at <0.4s per verb as measured
  (interpreter startup included; an NFR-1 benchmark test guards the 3-second line)
- **Conformance machinery**: FR↔test mapping meta-test, touchstone renderers +
  golden files, name-ban lint (no dataset name may appear in protocol-core
  source), coverage gate ≥80%

## Going further: real dataset slices and dogfooding

```bash
# Full check (lint + format + tests + coverage gate)
make check          # note: integration tests need the real slices first (next step)

# Fetch real data slices (script + checksums are committed; data itself is not)
python scripts/fetch_slices.py

# Dogfooding: real slices → UEP → lm-eval → local Ollama scores
python scripts/dogfood_run.py --slice mmlu --limit 10 --model gemma3:27b

# Reproduce the four qualification gates end to end (universal touchstones /
# lossless round-trip / zero-code chain / zero spec drift)
make demo
```

## Document map

| Document | Content |
|----------|---------|
| [docs/uep-v2-goals.md](docs/uep-v2-goals.md) | Goal authority: mission, adoption north star, six elegance criteria, bilingual commitment |
| [docs/uep-v2-spec.en.md](docs/uep-v2-spec.en.md) | **The protocol SPEC (English edition)**: skeleton, five prototypes, seven verifier kinds, mapping provenance, evolution mechanism, FR ledger ([Chinese authority](docs/uep-v2-spec.md)) |
| [docs/uep-v2-test-spec.md](docs/uep-v2-test-spec.md) | Test spec: assertion-level grounding of the verification pyramid |
| [docs/uep-v2-action-plan.md](docs/uep-v2-action-plan.md) | Action plan and phase status |
| [docs/validation-report-2026-07.en.md](docs/validation-report-2026-07.en.md) | **Validation report (English edition)**: full-chain results and findings on 8 mainstream datasets ([Chinese original](docs/validation-report-2026-07.md)) |
| [docs/task-cards/five-minute.en.md](docs/task-cards/five-minute.en.md) | Five-minute task card (for the L2 timed test; one page each in zh/en) |
| [docs/conformance.en.md](docs/conformance.en.md) | **Conformance kit**: three-layer self-check for new datasets (one page each in zh/en) |

Working language: the SPEC is drafted Chinese-first; the English edition is now
published (the Chinese text prevails on discrepancies during the draft period,
switching to English precedence at v1.0 finalization, revisitable — bilingual
parity is a protocol commitment, see goals).

## License

[Apache-2.0](LICENSE) (owner ruling, 2026-07-06). Third-party dataset excerpts in
golden files remain under their original licenses — attribution ledger at
[tests/golden/choices/README.md](tests/golden/choices/README.md); dataset slices
themselves are never committed.
