# UEP v2 主流数据集实战验证报告

**日期**：2026-07-04　**协议**：2.0.0-draft　**验证性质**：协议互操作性实战验证（非模型榜单）
**English edition**: [validation-report-2026-07.en.md](validation-report-2026-07.en.md)（时点快照，分歧以中文版为准）

## 结论（TL;DR）

**8 个主流开源评测数据集、804 条真实数据全部走通 UEP 全链**：导入 → 协议校验 →
无损反演回源格式 → 试金石渲染 → lm-eval-harness 导出 → 本地模型实跑出分。
每个数据集的分数轮廓与其公认难度一致，证明判分链忠实；中文数据（C-Eval、
中文字谜）与英文数据走**同一条代码路径**得到有效分数——双语平权不是声明，是实测。
验证过程暴露并修复了 3 个真实缺陷（详见"发现"），这正是实战验证的价值。

## 方法

```
HF/GitHub 上游（版本+sha256 锁定）
   │ scripts/fetch_slices.py
   ▼
真实切片（每集 ≥100 条，本体不入库）
   │ 声明式映射表（mapping.yaml，受限算子，逐条盖溯源戳）
   ▼
UEP EvalItem ──┬── uep validate（协议校验）
               ├── invert_mapping：无损反演，与源行逐字段语义等价（NFC 规程）
               ├── 试金石渲染（断言集 ①–④ + 黄金文件逐字节比对）
               └── lm-eval 任务包导出（generate_until + 正则抽取 + exact_match）
                      │ scripts/dogfood_run.py
                      ▼
               Ollama gemma3:27b（局域网，temperature=0，每集前 10 条）
```

- **环境**：lm-eval-harness（独立 venv，Python 3.12）；Ollama OpenAI 兼容 chat 端点；零付费 API。
- **作答约定 v1（直答）**：提示 = 试金石渲染 + 按条目 `lang` 的中/英指令
  （"只输出正确选项的标号/最终答案，不要解释"）；choices 抽取首个选项 id
  （动态构建、最长优先），qa 抽取最后一个数值（模式可覆写）。
- 全部转换有测试背书：`make check` = 137 tests 全绿，覆盖率 94%。

## 结果总表

| 数据集 | 上游（split） | 许可 | 原型 | 切片 | 校验 | 无损反演 | 试金石 | 实跑 exact_match（n=10） |
|--------|--------------|------|------|-----:|:---:|:---:|:---:|:---:|
| MMLU | cais/mmlu（test） | MIT | choices | 100 | ✅ | ✅ | ✅+黄金 | **0.60** ±0.16 |
| ARC-Challenge | allenai/ai2_arc（test） | CC-BY-SA-4.0 | choices | 100 | ✅ | ✅ | ✅+黄金 | **0.80** ±0.13 |
| HellaSwag | Rowan/hellaswag（val） | MIT | choices | 100 | ✅ | ✅ | ✅+黄金 | **0.70** ±0.15 |
| CommonsenseQA | tau/commonsense_qa（val） | MIT | choices | 100 | ✅ | ✅ | ✅+黄金 | **0.90** ±0.10 |
| TruthfulQA (mc1) | truthfulqa/truthful_qa（val） | Apache-2.0 | choices | 100 | ✅ | ✅ | ✅+黄金 | **1.00** ±0.00 |
| C-Eval（中文） | ceval/ceval-exam（val，经济+会计） | CC-BY-NC-SA-4.0 | choices | 104 | ✅ | ✅ | ✅（无黄金†） | **0.70** ±0.15 |
| GSM8K | openai/gsm8k（test） | MIT | **qa** | 100 | ✅ | ✅ | n/a‡ | **0.40** ±0.16 |
| 中文字谜 | openai/evals `Chinese_character_riddles` @8eac7a7d | MIT | **qa** | 100 | ✅ | ✅（双向往返） | n/a‡ | **0.20** ±0.13 |

†C-Eval 为非商业许可：断言集测试在本地切片全量运行，但内容摘录（黄金文件）不入库。
‡试金石渲染器 v1 只覆盖 choices 原型；qa 试金石按计划随阶段 2 复制同构规格。

**考生**：gemma3:27b（每集用时 22–27 秒）。分数轮廓与公认难度序一致
（常识类 0.8–1.0 > 中文学科/句子补全 0.7 > 研究生级抽象代数 0.6 > 无思维链直答的
数学应用题 0.4 > 中文字谜 0.2），且 MMLU 两次独立运行分数逐位复现（0.6000）——
判分链是忠实且确定的，不存在"全对/全错/全 invalid"式的退化管道。

## 双语平权证据（P5）

- **同一条代码路径**：C-Eval（中文）与五个英文 choices 集共用同一渲染器、同一导出器、
  同一抽取与判分配置，无任何中文特判分支；
- 中文作答指令按条目 `lang` 自动切换；NFC 规范化贯穿入库与比对；
- 中文字谜（qa）走双向往返（100 条逐字段语义等价）后再实跑出分——
  中文数据不但能"装进来"，还能"考出去、还原回去"。

## 发现与修复（本轮验证的直接产出）

1. **多字符选项 id 的抽取缺陷**（TruthfulQA 暴露）：mc1 最多 12+ 个选项，id
   出现 "10"/"11"；原抽取正则按字典序拼接，"1" 会先于 "11" 命中导致误判。
   修复：备选式按**最长优先**排序 + 回归测试。真实数据一来就打穿了想当然的假设。
2. **trajectory 语义在导出端的兑现**（中文字谜暴露）：作答约定（"把答案用方括号
   括起来"）在 system 消息里，qa 导出最初只取 `task.question` 会丢掉它。修复：
   **trajectory 在场时即完整题面**，system/user 消息全部进提示——这验证了协议
   "question 是退化视图、trajectory 是本体"的设计判断。
3. **三种新的源形态 → 三个受限算子**（全部自带反演）：选项在独立列
   （C-Eval `A/B/C/D`）、one-hot 答案（TruthfulQA `labels`）、最终答案后缀约定
   （GSM8K `#### N`）。算子集是封闭的：每次扩充都过判别联合 + 测试，不是自由代码。
4. **直答约定压低推理型任务分数**（GSM8K 0.40 vs 思维链榜单 ~0.8+）：把生成上限
   从 64 提到 256、去掉停止串后分数与用时均不变——模型确实在服从"只输出最终答案"。
   结论：这是**作答约定的语义**而非管道缺陷；思维链提示属 Runner 侧策略，
   协议层不越界（记录为导出约定 v1 的已知特性）。
5. **上游生态的坑**：CMMLU（首选中文集）已迁移且为旧式脚本数据集，datasets-server
   不再支持——换 C-Eval；C-Eval 单科 val 均 <100 条——多科并联切片，
   科目构成记录进锁文件（`config_counts`）。

## 局限（如实声明）

- **n=10/集 的冒烟级跑分**：验证目标是"管道忠实"，不是模型排名；stderr ±0.10–0.16。
- 单模型（gemma3:27b）、temperature=0 单次运行；
- choices 抽取取首个匹配，模型若先复述题面中的选项标号可能误判（本轮分数轮廓
  未见此症状，但属已知风险面）；
- qa 试金石与非 choices 黄金文件待阶段 2。

## 复现

```bash
make check                                   # 137 tests，含 804 条切片的全链断言
python scripts/fetch_slices.py               # 按 slices.lock.json 校验/补齐切片
python scripts/dogfood_run.py --slice mmlu --limit 10          # 任一数据集实跑
python scripts/dogfood_run.py --slice openai_evals --limit 10 \
    --answer-pattern '(\[[^\]]+\])'          # 中文字谜（方括号作答约定）
```

原始结果 JSON 在 `build/dogfood/<slice>/results/`（不入库，随跑随生成）。
