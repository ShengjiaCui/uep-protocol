# UEP v2 Protocol Specification (SPEC) — English Edition

> **Status**: translated from the **signed Chinese baseline** (signed into effect 2026-07-04; protocol version stays `2.0.0-draft` until the phase-4 public finalization). This edition tracks Chinese doc v1.3.
> **Authority**: the Chinese edition ([uep-v2-spec.md](uep-v2-spec.md)) is the technical authority during the draft period — on any discrepancy the Chinese text prevails; per goals §5, precedence switches to the English edition at v1.0 finalization (revisitable). Upstream documents: goals `docs/uep-v2-goals.md`, PRD, action plan. When an implementation conflicts with this spec, fix the implementation; revisions to this spec require the owner's confirmation.
> **Language policy**: drafted Chinese-first; field names and enum values are English throughout; this English edition ships with phase 4.
> **Clean-room statement**: this specification is a clean-room design — no code or data from the legacy project (`ref/`) was consulted; only its requirement ideas are carried over.

---

## 1. Design principles (six hard constraints, all from owner rulings)

| # | Principle | Origin |
|---|-----------|--------|
| P1 | Same semantics → same canonical field (task prototyping) | "No field reuse is just nonsense" |
| P2 | A Verifier self-contains its full scoring payload (taken alone, it is a complete executable spec) | Three principles ② |
| P3 | `extras` holds runner-specific parameters only; task substance in extras = defect (linted) | Three principles ③ |
| P4 | Expressiveness ceiling = the AI-agent task space; static QA is the degenerate form | Scope principle |
| P5 | Chinese and English are equal citizens (content / scoring / vocabulary / tooling — four layers) | Bilingual commitment |
| P6 | Naming and structure follow industry practice and domain expertise; on conflict prefer the professional term, bring in a human when hard to decide | Six elegance criteria + arbitration rule |

## 2. Protocol skeleton: EvalItem

One evaluation item. Field names are English (P6: industry practice); **the task statement lives in `task`, scoring lives in `verifiers`** — correct answers exist only inside Verifiers (single source of truth, fully self-contained).

| Field | Type | Req. | Description |
|-------|------|:---:|-------------|
| `uep_version` | str | ✓ | Protocol version, e.g. `"2.0"` (see §9 versioning discipline) |
| `id` | str | ✓ | Unique within the dataset |
| `lang` | list[str] | ✓ | BCP-47 (`"zh-CN"`/`"en"`); multiple values for mixed language; no implicit English default |
| `task` | Task (discriminated union) | ✓ | Task prototype (§3) — the carrier of field reuse |
| `context` | Context | – | Execution environment (§4) |
| `trajectory` | list[Step] | – | Multi-turn interaction trajectory (§4, agent-ceiling field) |
| `verifiers` | list[Verifier] ≥1 | ✓ | Scoring intent (§5), self-contained |
| `evidence` | list[Evidence] | – | Source attestation: `{source, span, content}` |
| `source` | Provenance | – | Conversion provenance (§7): adapter / version / mapping table / date |
| `source_map` | dict[str,str] | – | Canonical field ← original field path (fallback for irregular items, §7) |
| `metadata` | dict | – | Free-form tags (difficulty/domain/tags…); the protocol assigns no semantics |
| `extras` | dict | – | Runner-specific parameters. **P3 discipline jurisdiction** |

**Text normalization**: all strings are UTF-8; Unicode NFC normalization on ingest; no layer of the protocol applies default ASCII folding or case folding (P5).

## 3. Task prototypes v1 (Task, discriminator `type`)

Only five empirically induced prototypes; uncovered shapes go through the governed escape hatch `custom` (§8 evolution mechanism).

### 3.1 `qa` (the base — the degenerate form of every generative task)
| Field | Type | Description |
|-------|------|-------------|
| `question` | str | Task statement |

### 3.2 `choices` (multiple choice)
| Field | Type | Description |
|-------|------|-------------|
| `question` | str | Stem |
| `options` | list[{`id`: str, `text`: str}] | Options; `id` like `"A"`/`"0"`, source convention preserved |
| `multi_select` | bool = false | Multi-select or not |

The correct option(s) live in the `choice_match` Verifier (P2).

### 3.3 `code_generation`
| Field | Type | Description |
|-------|------|-------------|
| `prompt` | str | Task statement (incl. signature / docstring etc.) |
| `language` | str | Target language, e.g. `"python"` |
| `starter_code` | str? | Starter code |

The test payload lives in the `execution` Verifier (P2 — fixing the legacy defect of "the verifier does not know what to execute").

### 3.4 `patch_repair` (repository-level repair)
| Field | Type | Description |
|-------|------|-------------|
| `repo` | str | Repository identifier |
| `base_commit` | str | Base commit |
| `problem_statement` | str | Problem description |

### 3.5 `retrieval`
| Field | Type | Description |
|-------|------|-------------|
| `query` | str | Query |
| `corpus` | {`uri`: str} \| {`docs`: list[{`doc_id`,`title`?,`text`}]} | Corpus: by reference or inline (large corpora MUST be by reference to prevent OOM) |

Relevance judgments live in the `retrieval` Verifier (P2).

### 3.6 `custom` (governed escape hatch)
| Field | Type | Description |
|-------|------|-------------|
| `schema_ref` | str | Points to a registered prototype proposal ID (§8); no proposal reference = lint violation |
| `payload` | dict | Structure defined by the proposal |

### Bilingual example (choices, synthetic)

```json
{"uep_version":"2.0","id":"demo_zh_001","lang":["zh-CN"],
 "task":{"type":"choices","question":"水的化学式是什么？",
   "options":[{"id":"A","text":"H2O"},{"id":"B","text":"CO2"}]},
 "verifiers":[{"type":"choice_match","answer_ids":["A"]}]}
```

## 4. Context and Trajectory (agent-ceiling fields, in the skeleton from day one)

**Context**:
| Field | Type | Description |
|-------|------|-------------|
| `environment` | str? | Runtime / image identifier |
| `setup` | str \| dict? | Initialization description or declarative config |
| `assets` | list[{`uri`, `media_type`?, `lang`?}] | External asset references (s3/http/relative path); no large binaries embedded |

**Step (trajectory element)**:
| Field | Type | Description |
|-------|------|-------------|
| `role` | `"user"`\|`"assistant"`\|`"system"`\|`"tool"` | Speaker |
| `content` | str \| dict | Content |
| `tool_call` | {`name`, `arguments`}? | Tool invocation |
| `tool_result` | any? | Tool return value |
| `state_delta` | dict? | Trace of environment state change (declares What, does not define How) |
| `at` | float? | Timestamp |

## 5. Verifier catalog (discriminator `type`; each is self-contained and independently executable)

| type | Payload fields | Purpose |
|------|----------------|---------|
| `choice_match` | `answer_ids: list[str]` | Multiple-choice scoring |
| `text_match` | `expected: str\|list[str]`, `normalize: Normalization` | Exact / set text matching |
| `regex` | `pattern`, `flags?`, `target_group?` | Pattern extraction comparison |
| `execution` | `tests: TestSuite`, `sandbox: Sandbox` | Execution scoring (payload self-contained) |
| `retrieval` | `relevance: list[{doc_id, grade:int}]`, `metrics: list[str]` | Retrieval scoring (e.g. `"ndcg@10"`) |
| `llm_judge` | `model:{provider,name,version}`, `prompt_template`, `template_hash`, `temperature=0`, `rubric?` | Judge model (exact version + template hash against drift; templates must work in both zh and en) |
| `composite` | `mode:"all_of"\|"any_of"\|"weighted"`, `children:[Verifier]`, `weights?` | Composite verification (the norm for agent tasks) |

**Normalization** (the mechanical landing point of P5 bilingual safety):
`{unicode:"NFC", case_fold:false, strip_whitespace:true, width_fold:true, cjk_punct_fold:false}` — case folding off by default (a Latin-alphabet concept); full-width/half-width folding on by default; CJK punctuation folding explicitly opt-in. Full behavior matrix in the Test Specification.

**TestSuite**: `{language, setup?, files?:list[{path,content}], test_code?, assertions?:list[str], entry_point?, harness:"pytest"|"exec", test_patch?, fail_to_pass?:list[str], pass_to_pass?:list[str]}`
— payload legality ⇔ exactly one of `test_code` / `assertions` / (`test_patch`+`fail_to_pass`); the three repair-scoring fields (scoring test diff, fail-to-pass list, pass-to-pass regression list) were added via the §8 proposal approved 2026-07-04 (docs/proposals/2026-07-patch-grading-fields.md)
**Sandbox**: `{timeout_s:int, network:bool=false, memory_mb:int, image?:str}`

## 6. Manifest (dataset card, designed anew)

Dataset-level metadata; file `manifest.json` sits next to the items file (`items.jsonl`).

| Field | Type | Description |
|-------|------|-------------|
| `uep_version` | str | Protocol version |
| `name` | str | Dataset name |
| `license` | str | SPDX identifier; `"unknown"` must be declared explicitly (compliance risk slot) |
| `contains_pii` | bool? | Strict boolean tri-state: `true` / `false` / **absent = undeclared** (compliance slot; coercions like `"yes"`/`1` are rejected) |
| `languages` | list[str] | BCP-47 |
| `task_types` | dict[str,int] | Prototype composition counts, e.g. `{"choices": 100}` |
| `size` | int | Item count |
| `origin` | {`format`, `uri`?}? | Source format and address |
| `provenance` | Provenance? | Dataset-level conversion provenance |
| `description` | {`zh`?: str, `en`?: str} | Bilingual description |

## 7. Mapping tables · provenance · reversibility (ruling ① landed)

1. **Declarative mapping tables** (first-class maintained artifacts): every adapter ships a `mapping.yaml` — `{format, version, table: {canonical field path: source field path}, transforms?: restricted operators}`; reviewed with the SPEC, changelog kept across versions.
2. **Provenance stamp**: `{dataset, adapter, adapter_version, mapping_table, mapping_hash, converted_at}` — stamped on every converted item; dataset-level aggregate goes into the Manifest.
3. **Per-item `source_map`**: for irregular items the mapping table cannot cover, record "canonical field ← original field path" at item level.
4. **Reversibility obligation**: exporting back to the source format refills original field names via mapping table + source_map; **gate-2 round-trip tests enforce this mechanically** (semantic-equality procedure in the Test Specification).

## 8. Evolution mechanism (the fulfilment of P4; includes a human arbitration point)

1. New prototype / new field = a **proposal** (document: motivation, field table, empirical evidence from ≥2 real datasets, zh+en examples);
2. Passes the **prototype review card** (L3: domain practitioners + owner signature — "prefer the professional; bring in a human when hard to decide");
3. Approval → protocol **minor version +1**; breaking change → **major +1**;
4. Before approval, new shapes use `task.type="custom"` + `schema_ref` pointing to the proposal (a traceable escape hatch; free-form improvisation without a proposal is forbidden).

## 9. Versioning discipline (countermeasure to the legacy version chaos)

- **Protocol version** (declared by this SPEC, semver): currently `2.0.0-draft`; items record `major.minor` in `uep_version`;
- The **Python package version** evolves independently but must declare `supported_protocol` (e.g. `>=2.0,<3.0`);
- **Single source of truth**: the protocol version is declared only in §9 of this SPEC; everywhere else references it; releases CI-verify the three copies agree (SPEC / package metadata / schema default).

## 10. FR ledger (with pyramid layer and acceptance-test mapping — the gate-4 mechanism)

> Marking rule: acceptance tests carry `@pytest.mark.fr("FR-x.y")`; the mapping meta-test turns CI red on any FR without a test. FRs of phase 3+ are listed as placeholders (planned) and get their tests when they land.

| FR | Content | Layer | Acceptance test (path) | Phase |
|----|---------|-------|------------------------|:---:|
| FR-0.1 | FR↔test mapping meta-test | L1 | `tests/test_fr_mapping.py` | 1 |
| FR-0.2 | Coverage gate ≥80% | L1 | `make check` (pytest --cov) | 1 |
| FR-1.1 | EvalItem skeleton and discriminated-union validation | L1 | `tests/test_schema_core.py` | 1 |
| FR-1.2 | lang metadata + NFC normalization | L1 | `tests/test_lang_normalization.py` | 1 |
| FR-1.3 | Provenance + source_map | L1 | `tests/test_provenance.py` | 1 |
| FR-1.4 | extras discipline lint | L1 | `tests/test_extras_lint.py` | 1 |
| FR-1.5 | composite verifier | L1 | `tests/test_verifier_composite.py` | 1 |
| FR-1.6 | Skeleton accommodation probe (real agent sample, built from public sources) | L1 | `tests/test_skeleton_probe.py` | 1 |
| FR-2.1 | choices prototype | L1 | `tests/test_task_choices.py` | 1 |
| FR-2.2 | qa prototype | L1 | `tests/test_task_qa.py` | 1 |
| FR-2.3 | code_generation + self-contained execution | L1 | `tests/test_task_codegen.py` | 2 |
| FR-2.4 | patch_repair prototype | L1 | `tests/test_task_patch.py` | 2 |
| FR-2.5 | retrieval prototype | L1 | `tests/test_task_retrieval.py` | 2 |
| FR-2.6 | Touchstone programs × prototypes + name-ban lint | L1 | `touchstones/` + `tests/test_touchstones.py` + `tests/test_no_dataset_names.py` | 1↦2 |
| FR-2.7 | Bilingual behavior matrix (Normalization CJK safety) | L1 | `tests/test_verifier_cjk.py` | 1 |
| FR-3.1 | Declarative mapping-table mechanism | L1 | `tests/test_mapping_tables.py` | 1 |
| FR-3.2 | OpenAI Evals bidirectional round-trip (semantic equality) | L1 | `tests/test_roundtrip_openai_evals.py` | 1 |
| FR-3.3 | MMLU/ARC/HellaSwag import (real slices) | L1 | `tests/test_import_choices_real.py` | 1 |
| FR-3.4 | lm-eval-harness export + real Ollama run | L1+L2 | `tests/test_export_lmeval.py` + `scripts/dogfood_run.py` | 1 |
| FR-4.1 | `uep validate` (items + manifest, line/field-level errors, zh/en) | L1 | `tests/test_cli_validate.py` | 1 |
| FR-4.2 | Manifest model | L1 | `tests/test_manifest.py` | 1 |
| FR-5.1–5.7 | Management verbs list/show/filter/slice/sample/merge/stats | L1 | `tests/test_cli_verbs.py` | 3 |
| FR-5.8 | Bilingual CLI (zh/en) | L1 | `tests/test_cli_i18n.py` | 3 |
| FR-5.9 | `uep convert`: source format → items.jsonl+manifest.json on disk (fulfilment of test-spec §⑤) | L1 | `tests/test_cli_convert.py` | 3 |
| FR-5.10 | `uep export`: items.jsonl → runner task package (ditto) | L1 | `tests/test_cli_export.py` | 3 |
| FR-6.1 | Inspect AI export | L1 | `tests/test_export_inspect_ai.py` | 2 |
| FR-6.2 | Conformance kit packaging — `uep conform` three-layer self-check | L1 | `tests/test_cli_conform.py` | 4 |

### Non-functional commitments (NFR) — legacy PRD ideas carried over (owner ruling 2026-07-05)

| NFR | Commitment | Verification | Phase |
|-----|------------|--------------|-------|
| NFR-1 | Performance: library-level conversion (import + write) of a 10,000-row qa-grade CSV < 3 seconds | `tests/test_performance.py` (measured 2026-07-05: full CLI chain <0.4s per verb, 8× headroom) | 3 |

Legacy NFR mapping: NFR1 lossless round-trip has been promoted to mechanically enforced FRs; NFR2 external asset references partially landed (`corpus.uri` by-reference against OOM), multimodal assets parked pending prototype evolution; NFR3 = NFR-1 above; NFR4 PII marker = §6 `contains_pii`.

## 11. Non-goals (not defined by this specification)

Runner execution semantics, model scheduling, scoring-algorithm implementations, platform/Hub APIs (parking lot).

---

*Protocol version 2.0.0-draft · English edition tracking Chinese doc v1.3 (see the Chinese edition's footer for the full changelog; changes go through §8/§9). During the draft period the Chinese edition prevails on discrepancies; precedence switches to English at v1.0 finalization per goals §5 (revisitable).*
