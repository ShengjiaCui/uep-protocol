# UEP — Universal AI Evaluation Protocol（v2）

**中文** | [English](README.en.md)

> **状态：开发中（协议 `2.0.0-draft`），已在 8 个主流开源评测集、804 条真实数据上
> 完成全链实战验证**（导入→校验→无损反演→导出→本地模型实跑出分，
> [验证报告](docs/validation-report-2026-07.md)）。接口与字段仍可能变化；
> 正式化以 [SPEC](docs/uep-v2-spec.md) 版本纪律（§9）为准。欢迎挑刺，问题请直接开 issue。

**UEP 是评测数据的互操作层**：把各家 benchmark 的数据"翻译"成一个任务原型化的
统一协议，再无损导出给任意评测 Runner。UEP **永远不做 Runner**——不调模型、
不算分数，只让数据在生态间流动时不丢语义。

```
各家数据集 ──import──▶ UEP 条目（协议) ──export──▶ 各家 Runner 格式
     ▲                                                    │
     └────────────── 可还原（映射表机械反演）◀─────────────┘
```

## 五分钟上手：一份 CSV → 两个 Runner

```bash
# 0) 安装（Python ≥3.10；推荐 uv。装完 venv 内即有 uep 命令）
uv venv && uv pip install -e '.[dev]'
source .venv/bin/activate

# 1) 两列问答 CSV → UEP 数据集目录（items.jsonl + manifest.json）
uep convert examples/quiz.csv --from csv -o my_ds --content-lang zh-CN --license unknown
#    列名不是 question/answer 时加：--question-col 题面列 --answer-col 答案列

# 2) 校验 + 查看
uep validate my_ds/items.jsonl
uep list  my_ds/items.jsonl        # 逐行概览：id / 类型 / 语言 / 题面摘要
uep stats my_ds/items.jsonl        # 条目数与类型 / 语言 / 验证器分布

# 3) 同一份数据导出两种 Runner 格式
uep export my_ds/items.jsonl --to lmeval     -o my_ds_lmeval    # lm-eval-harness 任务包
uep export my_ds/items.jsonl --to inspect_ai -o my_ds_inspect   # Inspect AI 样本
```

所有动词支持 `--lang zh|en`（或环境变量 `UEP_LANG`）切换输出语言。
计时自测请用 [五分钟任务卡](docs/task-cards/five-minute.zh.md)。

## 动词一览

| 动词 | 作用 |
|------|------|
| `validate` | 校验 items.jsonl / manifest.json（行/字段级双语报错） |
| `convert` | 源格式 → UEP 数据集目录（`--from` 取自适配器注册表） |
| `export` | UEP → Runner 任务包（`--to lmeval` / `--to inspect_ai`） |
| `list` / `show` / `stats` | 查看：逐行概览 / 按 id 单条完整 JSON / 分布统计 |
| `filter` | 组卷：按 `--type`（任务类型）与 `--task-lang`（BCP-47 前缀匹配）筛选 |
| `slice` | 组卷：`--range START:STOP` 半开区间切片 |
| `sample` | 组卷：`--n N --seed S` 定种子抽样（可复现、保原库顺序） |
| `merge` | 组卷：合并多个条目文件（id 冲突即点名拒绝，绝不静默去重） |
| `conform` | 一致性自查（[工具包文档](docs/conformance.zh.md)）：schema + 试金石可消费 + 清单一致 |

组卷动词的产物就是新的数据集目录（清单从条目机械汇总），可立刻再
`validate` / `export`——转换、组卷、导出的产物是同一等公民：

```bash
uep filter my_ds/items.jsonl -o zh_qa  --type qa --task-lang zh   # 中文问答子卷
uep sample bank/items.jsonl  -o quiz10 --n 10 --seed 7            # 可复现抽 10 题
```

## 设计原则（六条硬约束，详见 [SPEC §1](docs/uep-v2-spec.md)）

1. 同类语义 → 同一规范字段（任务原型化：`qa` / `choices` / `code_generation` / `patch_repair` / `retrieval`）
2. Verifier 自含全部打分载荷（正确答案只存 Verifier，单独拿出即完整可执行规格）
3. `extras` 只放 runner 专属参数，任务本体入 extras = 缺陷（工具会 lint）
4. 表达力上限 = AI Agent 任务空间（环境/轨迹/复合验证第一天在骨架里）
5. 中英双语平权（内容、打分语义、词汇、工具四层）
6. 命名遵循行业习惯与领域专业认知；冲突时优先专业，难决引入 human

## 今天已经能做什么（全部有测试背书）

- **导入 11 个主流数据集**（覆盖全部五个任务原型）：MMLU / ARC-Challenge /
  HellaSwag / CommonsenseQA / TruthfulQA / **C-Eval（中文）**（choices）、
  **GSM8K**（qa）、**HumanEval**（code_generation）、**SWE-bench Lite**
  （patch_repair）、**SciFact** / **T2Ranking（中文）**（retrieval）→ UEP——
  真实切片 ≥100 条/集验收，声明式映射表 + 溯源戳，**全部可无损反演回源格式**
- **双向往返**：OpenAI Evals ↔ UEP（100 条真实中文字谜逐条语义等价）
- **导出两个 Runner**：lm-eval-harness 任务包（choices 与 qa）与 Inspect AI
  样本。lm-eval 接本地 Ollama 实跑 8 集（gemma3:27b，每集 10 条）：
  CommonsenseQA 0.90 / ARC 0.80 / HellaSwag 0.70 / C-Eval 0.70 / MMLU 0.60 /
  GSM8K 0.40 / 中文字谜 0.20 / TruthfulQA 1.00——分数轮廓与公认难度一致，
  判分链忠实（详见 [验证报告](docs/validation-report-2026-07.md)）
- **四原型真实出分 + patch 载荷机械可校验**：codegen pass@1（Inspect 本地沙箱
  实跑）、检索 ndcg@10 中英双实跑（BM25 基线）、patch 判分载荷机械可校验+官方
  harness 对接（docker 边界如实）——详见
  [判分闭环报告](docs/scoring-closure-2026-07.md)
- **分数级互操作对证**：同一份 UEP 数据分别喂 lm-eval 与 Inspect 两 Runner、**两侧
  强制贪婪**实跑对分——MMLU 聚合分相同（Δ=0，逐条 92% 一致）；GSM8K 一句提示指令致
  0.56 背离，**受控实验证伪归因**（对齐提示后两侧逐条判定完全一致，Δ=0）。互操作在
  **数据层**得到验证，分数级对证 = 数据对齐（协议保证）+ 提示/解码对齐（使用方控制）
  ——详见 [双 Runner 对分报告](docs/crossrunner-2026-07.md)
- **原生中文 codegen 样例集**：UEP **原生创建**（非转换）20 条中文题面 Python 代码题
  （自写 Apache-2.0，数据入库 `examples/zh-codegen/`）——作者只写题目内容，schema+66 行
  构建器补全全部协议骨架（比手写 items.jsonl 省事）；过 `validate`/`conform` 三层 + 20 条
  参考解自测，经 A1 闭环实跑 **pass@1=1.00**（gemma3:27b 贪婪，负对照证 scorer 判错）。补
  中文 codegen 许可空缺——详见 [原生中文 codegen 报告](docs/zh-codegen-2026-07.md)
- **评测空间覆盖地图**：对 **106 个主流评测集**（策展主流集、**故意纳入 custom 候选以暴露
  缺口**、非随机抽样）做桌面 schema 普查——**85/106（80%）可被五原型 full+partial 容纳**，
  21 个 custom（agentic 轨迹/成对偏好/多模态/安全红队）**如实列为分类学缺口**=演进机制燃料；
  每行标 grounding 依据（48 读 lm-eval 配置）+ 置信度，**许可从严**（未声明=unknown）——详见
  [覆盖地图](docs/coverage-map.md)（其中 **28 集已回填 ✓ 已实测全适配**）
- **30 个真实数据集全适配 + 接入成本表**：把已适配集从 12 扩到 **30**（三批 18 新集，每集
  全闸门：源字段全覆盖 mapping + 集成层真实切片测试 + 许可阶梯黄金 + 无损往返 + 双仓 sha256
  一致）。**成本曲线**：18 集里 9 集 **0 新算子**纯复用、2 集算子增强、5 集全新小算子
  （类体 ~22–40 行，均对应真实结构新形态）、2 集走 custom 逃生舱 + **§8 演进提案**（成对偏好/
  指令跟随，命中普查前沿缺口）。覆盖 choices/qa/retrieval（引用式+内联）/code（Python+Java）/
  custom，中文 5 集——详见 [A2 纵深报告](docs/a2-depth-2026-07.md)
- **管理面 CLI（11 个动词，中英双语）**：convert / validate / export +
  list / show / stats + filter / slice / sample / merge + **conform（一致性
  工具包——给新建数据集自查）**——组卷产物即数据集；双语平权是机制
  （文案目录逐键断言 zh/en 齐备且占位符一致），不是自觉
- **性能**：1 万条 CSV 转换实测 <0.4 秒/动词（含解释器启动；NFR-1 基准测试守 3 秒线）
- **一致性机制**：FR↔测试映射元测试、试金石渲染 + 黄金文件、禁名 lint
  （协议核心源码禁止出现任何数据集名）、覆盖率闸门 ≥80%

## 进阶：主流数据集切片与 dogfooding

```bash
# 全量检查（lint + format + 测试 + 覆盖率闸门）
make check          # 注：集成测试需先获取真实切片（下一步）

# 获取真实数据切片（脚本+校验和入库，数据本体不入库）
python scripts/fetch_slices.py

# dogfooding：真实切片 → UEP → lm-eval → Ollama 出分
python scripts/dogfood_run.py --slice mmlu --limit 10 --model gemma3:27b

# 资格线四关卡端到端复现（试金石通用性/无损往返/零代码链路/SPEC 零漂移）
make demo
```

## 文档地图

| 文档 | 内容 |
|------|------|
| [docs/uep-v2-goals.md](docs/uep-v2-goals.md) | 目标权威：使命、采纳真北、优雅六判据、双语承诺 |
| [docs/uep-v2-spec.md](docs/uep-v2-spec.md) | **协议规范（SPEC）**：骨架、五原型、七类 Verifier、映射留痕、演进机制、FR 清单（[English edition](docs/uep-v2-spec.en.md)） |
| [docs/uep-v2-test-spec.md](docs/uep-v2-test-spec.md) | 测试规格书：验证金字塔的断言级落地 |
| [docs/uep-v2-action-plan.md](docs/uep-v2-action-plan.md) | 行动计划与阶段状态 |
| [docs/validation-report-2026-07.md](docs/validation-report-2026-07.md) | **实战验证报告**：8 个主流数据集全链实测与发现（[English edition](docs/validation-report-2026-07.en.md)） |
| [docs/coverage-map.md](docs/coverage-map.md) | **评测空间覆盖地图**：106 集桌面普查（28 集已回填 ✓ 全适配） |
| [docs/a2-depth-2026-07.md](docs/a2-depth-2026-07.md) | **A2 纵深报告**：18 集全适配 + 接入成本表 + 7 算子/2 §8 提案 + 万级转换 |
| [docs/proposals/2026-07-pairwise-preference.md](docs/proposals/2026-07-pairwise-preference.md) · [instruction-following](docs/proposals/2026-07-instruction-following.md) | **§8 演进提案**：成对偏好 / 指令跟随原型（RewardBench / IFEval 触发） |
| [docs/task-cards/five-minute.zh.md](docs/task-cards/five-minute.zh.md) | 五分钟上手任务卡（L2 实测用，中英各一页） |
| [docs/conformance.zh.md](docs/conformance.zh.md) | **一致性工具包**：新建数据集三层自查（中英各一页） |

工作语言：SPEC 中文先行，英文版已发布（起草期分歧以中文版为准，定稿后转英文为准、
可复议——双语平权是协议承诺，见 goals §双语）。README 教程亦中英双版。

## License

[Apache-2.0](LICENSE)（2026-07-06 用户裁决）。黄金文件中的第三方数据摘录仍属其
原始许可，归属账本见 [tests/golden/choices/README.md](tests/golden/choices/README.md)；
数据集切片本体不入库。
