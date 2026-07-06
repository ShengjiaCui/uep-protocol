# UEP v2 协议规范（SPEC）

> **状态**：**已签字生效**（2026-07-04 用户 "go"）——协议 v2.0 规范基线（协议版本保持 `2.0.0-draft` 直至阶段 4 对外定稿）。文档 v1.0。
> **地位**：协议的**技术权威**。上游：目标 `docs/uep-v2-goals.md`、需求 `.claude/PRPs/prds/uep-v2.prd.md`、计划 `docs/uep-v2-action-plan.md`。实现与本文冲突时，以本文为准修实现；本文修订须经用户确认。
> **语言政策**：中文先行撰写；字段名/枚举值一律英文；英文版已随阶段 4 发布：[uep-v2-spec.en.md](uep-v2-spec.en.md)（起草期分歧以中文版为准，v1.0 定稿后按 goals §5 转以英文版为准、可复议）。
> **零参考声明**：本规范为 clean-room 设计，不参考旧项目（ref/）代码与数据，仅承接其需求理念。

---

## 1. 设计原则（六条硬约束，全部来自用户裁定）

| # | 原则 | 出处 |
|---|------|------|
| P1 | 同类语义 → 同一规范字段（任务原型化） | "没有字段复用就是瞎搞" |
| P2 | Verifier 自含打分全部载荷（单独拿出即完整可执行规格） | 三原则② |
| P3 | `extras` 只放 runner 专属参数；任务本体入 extras = 缺陷（工具 lint） | 三原则③ |
| P4 | 表达力上限 = AI Agent 任务空间；静态 QA 是退化形态 | 范围原则 |
| P5 | 中英双语平权（内容/打分/词汇/工具四层） | 双语承诺 |
| P6 | 命名与结构遵循行业习惯与领域专业认知；冲突时优先专业，难决引入 human | 优雅六判据+裁决原则 |

## 2. 协议骨架：EvalItem

一条评测项。字段名英文（P6：行业惯例）；**题面归 task、打分归 verifiers**——正确答案只存在于 Verifier（单一事实源，彻底自含）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `uep_version` | str | ✓ | 协议版本，形如 `"2.0"`（见 §9 版本纪律） |
| `id` | str | ✓ | 数据集内唯一 |
| `lang` | list[str] | ✓ | BCP-47（`"zh-CN"`/`"en"`），混语多值；无英文默认假设 |
| `task` | Task 判别联合 | ✓ | 任务原型（§3）——字段复用的载体 |
| `context` | Context | – | 执行环境（§4） |
| `trajectory` | list[Step] | – | 多轮交互轨迹（§4，Agent 上限字段） |
| `verifiers` | list[Verifier] ≥1 | ✓ | 打分意图（§5），自含 |
| `evidence` | list[Evidence] | – | 出处佐证：`{source, span, content}` |
| `source` | Provenance | – | 转换留痕（§7）：适配器/版本/映射表/时间 |
| `source_map` | dict[str,str] | – | 规范字段 ← 原字段路径（不规则条目兜底，§7） |
| `metadata` | dict | – | 自由标签（difficulty/domain/tags…），协议不赋语义 |
| `extras` | dict | – | runner 专属参数。**P3 纪律辖区** |

**文本规范化**：所有字符串 UTF-8；入库时 Unicode NFC 规范化；协议任何层不做默认 ASCII 化/大小写折叠（P5）。

## 3. 任务原型 v1（Task，判别字段 `type`）

只收实证归纳的五种；未覆盖形态走受控逃生舱 `custom`（§8 演进机制）。

### 3.1 `qa`（底座——一切 generative 任务的退化形态）
| 字段 | 类型 | 说明 |
|------|------|------|
| `question` | str | 题面 |

### 3.2 `choices`（选择题）
| 字段 | 类型 | 说明 |
|------|------|------|
| `question` | str | 题干 |
| `options` | list[{`id`: str, `text`: str}] | 选项；`id` 如 `"A"`/`"0"`，保留源习惯 |
| `multi_select` | bool = false | 是否多选 |

正确项在 `choice_match` Verifier 中（P2）。

### 3.3 `code_generation`（代码生成）
| 字段 | 类型 | 说明 |
|------|------|------|
| `prompt` | str | 题面（含签名/文档串等） |
| `language` | str | 目标语言，如 `"python"` |
| `starter_code` | str? | 起始代码 |

测试载荷在 `execution` Verifier 中（P2——修复旧协议"验证器不知道要执行什么"）。

### 3.4 `patch_repair`（仓库级修复）
| 字段 | 类型 | 说明 |
|------|------|------|
| `repo` | str | 仓库标识 |
| `base_commit` | str | 基准提交 |
| `problem_statement` | str | 问题描述 |

### 3.5 `retrieval`（检索）
| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | str | 查询 |
| `corpus` | {`uri`: str} \| {`docs`: list[{`doc_id`,`title`?,`text`}]} | 语料：引用式或内联（大语料必须引用式防 OOM） |

相关性标注在 `retrieval` Verifier 中（P2）。

### 3.6 `custom`（受控逃生舱）
| 字段 | 类型 | 说明 |
|------|------|------|
| `schema_ref` | str | 指向已登记的原型提案 ID（§8）；无提案引用即 lint 违规 |
| `payload` | dict | 提案定义的结构 |

### 双语示例（choices，合成样例）

```json
{"uep_version":"2.0","id":"demo_zh_001","lang":["zh-CN"],
 "task":{"type":"choices","question":"水的化学式是什么？",
   "options":[{"id":"A","text":"H2O"},{"id":"B","text":"CO2"}]},
 "verifiers":[{"type":"choice_match","answer_ids":["A"]}]}
```

## 4. Context 与 Trajectory（Agent 上限字段，第一天在骨架）

**Context**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `environment` | str? | 运行时/镜像标识 |
| `setup` | str \| dict? | 初始化描述或声明式配置 |
| `assets` | list[{`uri`, `media_type`?, `lang`?}] | 外部资产引用（s3/http/相对路径），不内嵌大二进制 |

**Step（trajectory 元素）**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | `"user"`\|`"assistant"`\|`"system"`\|`"tool"` | 发言方 |
| `content` | str \| dict | 内容 |
| `tool_call` | {`name`, `arguments`}? | 工具调用 |
| `tool_result` | any? | 工具返回 |
| `state_delta` | dict? | 环境状态变化痕迹（声明 What 不定义 How） |
| `at` | float? | 时间戳 |

## 5. Verifier 目录（判别字段 `type`；每个都自含、可单独执行）

| type | 载荷字段 | 用途 |
|------|---------|------|
| `choice_match` | `answer_ids: list[str]` | 选择题判分 |
| `text_match` | `expected: str\|list[str]`, `normalize: Normalization` | 文本精确/集合匹配 |
| `regex` | `pattern`, `flags?`, `target_group?` | 模式抽取比对 |
| `execution` | `tests: TestSuite`, `sandbox: Sandbox` | 执行判分（载荷自含） |
| `retrieval` | `relevance: list[{doc_id, grade:int}]`, `metrics: list[str]` | 检索判分（如 `"ndcg@10"`） |
| `llm_judge` | `model:{provider,name,version}`, `prompt_template`, `template_hash`, `temperature=0`, `rubric?` | 裁判模型（精确版本+模板哈希防漂移；模板须中英可用） |
| `composite` | `mode:"all_of"\|"any_of"\|"weighted"`, `children:[Verifier]`, `weights?` | 复合验证（Agent 任务常态） |

**Normalization**（P5 双语安全的机械落点）：
`{unicode:"NFC", case_fold:false, strip_whitespace:true, width_fold:true, cjk_punct_fold:false}` ——大小写折叠默认关（拉丁字母概念）；全半角折叠默认开；中文标点折叠显式可选。行为矩阵详见《测试规格书》。

**TestSuite**：`{language, setup?, files?:list[{path,content}], test_code?, assertions?:list[str], entry_point?, harness:"pytest"|"exec", test_patch?, fail_to_pass?:list[str], pass_to_pass?:list[str]}`
——载荷合法 ⇔ `test_code` / `assertions` / (`test_patch`+`fail_to_pass`) 三者其一；修复判分三字段（判分用测试变更 diff、败转胜清单、回归保持清单）经 2026-07-04 提案批准加入（docs/proposals/2026-07-patch-grading-fields.md）
**Sandbox**：`{timeout_s:int, network:bool=false, memory_mb:int, image?:str}`

## 6. Manifest（数据集卡，全新设计）

数据集级元数据，文件 `manifest.json` 与条目文件（`items.jsonl`）同目录。

| 字段 | 类型 | 说明 |
|------|------|------|
| `uep_version` | str | 协议版本 |
| `name` | str | 数据集名 |
| `license` | str | SPDX 标识；`"unknown"` 显式声明（合规风险位） |
| `contains_pii` | bool? | 严格布尔三态：`true` / `false` / **缺省=未声明**（合规位；不接受 `"yes"`/`1` 等强转） |
| `languages` | list[str] | BCP-47 |
| `task_types` | dict[str,int] | 原型构成计数，如 `{"choices": 100}` |
| `size` | int | 条目数 |
| `origin` | {`format`, `uri`?}? | 来源格式与地址 |
| `provenance` | Provenance? | 数据集级转换留痕 |
| `description` | {`zh`?: str, `en`?: str} | 双语描述 |

## 7. 映射表 · 留痕 · 还原（裁决①落地）

1. **声明式映射表**（一等维护物）：每个适配器附 `mapping.yaml`——`{format, version, table: {规范字段路径: 源字段路径}, transforms?: 受限算子}`；进 SPEC 评审、随版本变更留 changelog。
2. **Provenance（溯源戳）**：`{dataset, adapter, adapter_version, mapping_table, mapping_hash, converted_at}`——每条转换产物必盖；数据集级汇总入 Manifest。
3. **逐条 `source_map`**：映射表覆盖不了的不规则条目，条目级记录"规范字段←原字段路径"。
4. **还原义务**：导出回源格式时按映射表+source_map 回填原字段名；**关卡 2 往返测试机械强制**（语义等价判定规程见《测试规格书》）。

## 8. 演进机制（P4 的兑现；含 human 仲裁点）

1. 新原型/新字段 = **提案**（proposal 文档：动机、字段表、≥2 个真实数据集实证、中英示例）；
2. 过**原型评审卡**（L3：领域实践者 + 用户签字——"优先专业，难决引入 human"）；
3. 批准 → 协议 **minor 版本 +1**；破坏性变更 → **major +1**；
4. 未批准前的新形态用 `task.type="custom"` + `schema_ref` 指向提案（可追踪的逃生舱，禁止无提案的自由发挥）。

## 9. 版本纪律（反制旧项目版本混乱）

- **协议版本**（本 SPEC 声明，semver）：当前 `2.0.0-draft`；条目 `uep_version` 记 `major.minor`；
- **Python 包版本**独立演进，但必须声明 `supported_protocol`（如 `>=2.0,<3.0`）；
- **单一事实源**：协议版本只在本 SPEC §9 声明，其余处引用；发布时 CI 校验三处一致（SPEC/包元数据/Schema 默认值）。

## 10. FR 清单（含金字塔层与验收测试映射——关卡 4 机制）

> 标记规则：验收测试打 `@pytest.mark.fr("FR-x.y")`；映射元测试发现无测试 FR 即 CI 红。阶段 3+ 的 FR 先列名占位（planned），落地时补测试。

| FR | 内容 | 层 | 验收测试（规划路径） | 阶段 |
|----|------|----|--------------------|:---:|
| FR-0.1 | FR↔测试映射元测试 | L1 | `tests/test_fr_mapping.py` | 1 |
| FR-0.2 | 覆盖率闸门 ≥80% | L1 | `make check`（pytest --cov） | 1 |
| FR-1.1 | EvalItem 骨架与判别联合校验 | L1 | `tests/test_schema_core.py` | 1 |
| FR-1.2 | lang 元数据 + NFC 规范化 | L1 | `tests/test_lang_normalization.py` | 1 |
| FR-1.3 | Provenance + source_map | L1 | `tests/test_provenance.py` | 1 |
| FR-1.4 | extras 纪律 lint | L1 | `tests/test_extras_lint.py` | 1 |
| FR-1.5 | composite 复合验证器 | L1 | `tests/test_verifier_composite.py` | 1 |
| FR-1.6 | 骨架容纳探针（真实 Agent 样例，公开源新建） | L1 | `tests/test_skeleton_probe.py` | 1 |
| FR-2.1 | choices 原型 | L1 | `tests/test_task_choices.py` | 1 |
| FR-2.2 | qa 原型 | L1 | `tests/test_task_qa.py` | 1 |
| FR-2.3 | code_generation + execution 自含 | L1 | `tests/test_task_codegen.py` | 2 |
| FR-2.4 | patch_repair 原型 | L1 | `tests/test_task_patch.py` | 2 |
| FR-2.5 | retrieval 原型 | L1 | `tests/test_task_retrieval.py` | 2 |
| FR-2.6 | 试金石程序 × 原型 + 禁名 lint | L1 | `touchstones/` + `tests/test_touchstones.py` + `tests/test_no_dataset_names.py` | 1↦2 |
| FR-2.7 | 双语行为矩阵（Normalization CJK 安全） | L1 | `tests/test_verifier_cjk.py` | 1 |
| FR-3.1 | 声明式映射表机制 | L1 | `tests/test_mapping_tables.py` | 1 |
| FR-3.2 | OpenAI Evals 双向往返（语义等价） | L1 | `tests/test_roundtrip_openai_evals.py` | 1 |
| FR-3.3 | MMLU/ARC/HellaSwag 导入（真实切片） | L1 | `tests/test_import_choices_real.py` | 1 |
| FR-3.4 | lm-eval-harness 导出 + Ollama 实跑 | L1+L2 | `tests/test_export_lmeval.py` + `scripts/dogfood_run.py` | 1 |
| FR-4.1 | `uep validate`（条目+manifest，行/字段级报错，zh/en） | L1 | `tests/test_cli_validate.py` | 1 |
| FR-4.2 | Manifest 模型 | L1 | `tests/test_manifest.py` | 1 |
| FR-5.1–5.7 | 管理面动词 list/show/filter/slice/sample/merge/stats | L1 | `tests/test_cli_verbs.py` | 3 |
| FR-5.8 | CLI 双语（zh/en） | L1 | `tests/test_cli_i18n.py` | 3 |
| FR-5.9 | `uep convert`：源格式 → items.jsonl+manifest.json 落盘（测试规格书 §⑤ 承诺的兑现） | L1 | `tests/test_cli_convert.py` | 3 |
| FR-5.10 | `uep export`：items.jsonl → Runner 任务包（同上） | L1 | `tests/test_cli_export.py` | 3 |
| FR-6.1 | Inspect AI 导出 | L1 | `tests/test_export_inspect_ai.py` | 2 |
| FR-6.2 | 一致性工具包（conformance kit）打包——`uep conform` 三层自查 | L1 | `tests/test_cli_conform.py` | 4 |

### 非功能承诺（NFR）——旧 PRD 理念承接（2026-07-05 用户裁决）

| NFR | 承诺 | 验证 | 阶段 |
|-----|------|------|------|
| NFR-1 | 性能：1 万条 qa 级 CSV 库层转换（导入+落盘）< 3 秒 | `tests/test_performance.py`（2026-07-05 实测 CLI 全链 <0.4s/动词，8 倍余量） | 3 |

旧 NFR 承接对照：NFR1 无损往返已升格为 FR 机械强制；NFR2 外部资产引用已部分落地
（`corpus.uri` 引用式防 OOM），多模态资产挂停车场随原型演进；NFR3 = 上表 NFR-1；
NFR4 PII 标记 = §6 `contains_pii`。

## 11. 非目标（本规范不定义）

Runner 执行语义、模型调度、评分算法实现、平台/Hub API（停车场）。

---

*协议版本 2.0.0-draft · 文档 v1.3（2026-07-05：§6 Manifest 增 `contains_pii` 严格三态合规位、§10 增 NFR-1 性能承诺——旧 PRD NFR3/NFR4 理念承接，阶段 0 挂起议题经用户裁决关闭）· 文档 v1.2（2026-07-05：§10 增 FR-5.9/5.10——convert/export 落盘动词；系签字测试规格书 §⑤ 已承诺能力的补行，非新增承诺，经用户确认追认）· 文档 v1.1（2026-07-04：§5 TestSuite 增修复判分三字段，走 §8 提案流程经用户批准）· 签字基线 v1.0（2026-07-04）。变更走 §8/§9 流程。*
