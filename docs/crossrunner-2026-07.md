# 双 Runner 分数级对分报告（2026-07）

> 同一份 UEP 数据集，分别喂给 **lm-eval-harness** 与 **Inspect AI** 两个独立 Runner，
> 同模型（gemma3:27b）、同条目、**两侧强制贪婪解码**各自实跑，比对逐条判分。
> **结论：UEP 把评测数据忠实传输到两个 Runner 的数据层——分数是否一致，取决于
> Runner 各自的提示构造层与解码配置，而非协议是否丢语义。** 这把互操作主张从
> "格式能导出"升级为"分数级可对证"。

复现命令见文末（含受控实验的一等 `--qa-suffix` 开关）；判分核心（一致性表/解析器/
数值抽取）有单元测试背书（`tests/test_crossrunner_*.py`）。

---

## 一、为什么做这件事

A1 判分闭环证明了"UEP 数据能被真实 Runner 跑出分"。但"能出分"不等于"两个 Runner
出的分对得上"。若同一份 UEP 数据进两个 Runner 得到南辕北辙的分数、且说不清为什么，
那"互操作"就还停在格式层。本轮把**同一份数据**送进两个 Runner，量化一致性、
**并对每一处偏差追根溯源**——偏差能被干净归因，恰恰是"数据没丢"的证明。

## 二、方法（可对证的前提）

| 维度 | 做法 |
|------|------|
| 数据 | 同一 UEP 切片，一次切到 n=50，两侧消费**同一份**条目（同条目同条数） |
| 模型 | 本地 Ollama `gemma3:27b`，两侧同模型 |
| 解码 | **两侧强制贪婪**：lm-eval 导出即 `do_sample=false, temperature=0`；**Inspect 若不显式传温度，Ollama 会套 gemma3 modelfile 默认 `temperature=1.0` 采样**，故本编排显式传 `--temperature 0 --top-p 1 --seed 0`（贪婪 + 可复现） |
| 判分机理 | **同族**：lm-eval 走 `generate_until`（生成式），Inspect choices 走 `multiple_choice()`（同为生成式，模型输出 "ANSWER: X" 再解析）——两侧都是"生成→抽取→比对"，非 loglikelihood |
| 对齐 join | 按 UEP item id 关联，与顺序无关；两侧 id 集合不一致即点名报错，绝不静默截断 |

> **一个曾被漏掉、后由对抗式复审抓出的坑（已修正）**：初版误以为"Inspect
> `generate()` 默认贪婪"。实测日志显示 Inspect 不显式传温度时，请求里没有温度字段，
> Ollama 套用模型默认 `temp=1.0`——即在采样。这会让 Inspect 侧每个数字都是单次抽样、
> 不可复现。修正后**显式强制 `temperature=0`**，本报告全部数字均为两侧贪婪重跑所得。

对齐解码后，分数偏差**主要**源于两处——**提示模板** 与 **答案抽取**。另有一处次要
变量如实披露：两侧**生成长度上限**不同（lm-eval 导出设 `max_gen_toks` 64/256，
Inspect 不设上限）；本轮实测它未影响结论（MMLU 输出仅 1–2 字符、远未触顶；GSM8K 的
背离由提示指令而非长度截断造成，见第四节受控实验）。

原型选择：`choices` 用 **MMLU**，`qa` 用 **GSM8K**——协议永不做 Runner，两侧跑分/
判分逻辑全部居于 `scripts/`（`crossrunner_run.py` 编排、`inspect_crossrunner_task.py`
判分），`uep/` 包本轮**零改动**。

## 三、一致性表

### MMLU（choices，n=50，贪婪）——开箱即对齐

| Runner | 正确率 | | |
|--------|:---:|---|---|
| lm-eval | **0.52** | Δ = **0.00** | 逐条一致率 **0.92** |
| Inspect | **0.52** | | |

四象限：同对 24 / 同错 22 / 仅 lm-eval 对 2 / 仅 Inspect 对 2。

**聚合分完全相同，逐条 92% 一致。** 8% 的分歧（4 条）逐一复核：

| item | 正确答案 | lm-eval | Inspect | 抽取 |
|------|:---:|:---:|:---:|------|
| mmlu-test-0002 | D | D ✓ | C ✗ | 两侧均干净 |
| mmlu-test-0027 | B | D ✗ | B ✓ | 两侧均干净 |
| mmlu-test-0033 | C | A ✗ | C ✓ | 两侧均干净 |
| mmlu-test-0043 | C | C ✓ | D ✗ | 两侧均干净 |

**归因**：4 条分歧无一例是抽取故障或数据错位——每条两侧 gold 完全一致、两侧抽取都
干净成功。分歧是 gemma3:27b 在两个 Runner **不同的提示模板**下（lm-eval 用
"A. 0 …Respond with the id"；Inspect 的 `multiple_choice()` 自建 "A) 0 …ANSWER:"
模板，含前导语）给出了不同字母。**两侧均贪婪、确定性输出**——所以这 4 条是可复现的
模板致翻转，不是采样噪声。方向上无一方明显占优（2:2，n=4 仅供参考；更硬的无偏证据是
聚合 Δ=0）。这是模型对模板的边缘敏感性，**非 UEP 失真**。

### GSM8K（qa，n=50，贪婪）——开箱大幅背离，且已定位真因

| Runner | 正确率 | | |
|--------|:---:|---|---|
| lm-eval | **0.36** | Δ = **−0.56** | 逐条一致率 **0.44** |
| Inspect | **0.92** | | |

四象限：同对 18 / 同错 4 / 仅 lm-eval 对 0 / **仅 Inspect 对 28**（完全不对称）。

这**不是**边缘噪声，是系统性背离，必须查清。扒两侧真实输出：

- **lm-eval 侧输出是裸数字**——`"26"`、`"$40,000"`、`"60"`（2–7 字符，零推理）；
- **Inspect 侧是完整链式推理**——约 257–2179 字符（中位数约 760），结尾
  `Final Answer: \boxed{18}`。

根因：UEP 的 lm-eval 适配器给 qa 题面**追加了指令**——GSM8K 为英文条目，追加的是
`_QA_INSTRUCTION_EN` = "Respond with the final answer only, no explanation. Answer:"。
gemma3 老实照做、跳过思维链——而 GSM8K 是多步数学推理，无思维链几乎必错。Inspect 侧
无此指令，模型照常推理，答对。

## 四、受控证伪实验：把真因钉死

"是那句指令"是假设，不是证明。做单变量受控实验——**给 Inspect qa 也追加同一句英文
指令**（`--qa-suffix` 开关），解码同为贪婪、数据同为这 50 条，其余不变，看 Inspect
是否塌向 lm-eval：

| GSM8K 条件（均贪婪） | Inspect 正确率 | Δ vs lm-eval(0.36) | 逐条一致率 |
|-----------|:---:|:---:|:---:|
| Inspect 默认（允许推理） | 0.92 | −0.56 | 0.44 |
| **Inspect + "仅答案"指令** | **0.36** | **0.00** | **1.00** |

**只改这一个变量（那句指令），Inspect 从 0.92 塌到 0.36，与 lm-eval 分毫不差
（Δ=0），并在全部 50 条上逐条判定完全一致。** 解码已控（两侧贪婪、seed 固定，可复现），
数据同一份——所以这是干净的单变量实验：**那句指令是 GSM8K 背离的决定性成因**，它一手
造成了整个 0.56 的差。

**但要诚实——拆开这 100% 一致：**

> 逐条一致的 50 条里，**18 条同对、32 条同错**。那句"仅答案"指令把两侧都打残，
> 它们在相同的 32 条上以相同方式失败（都吐一个错的裸数字）。所以"逐条判定 100% 一致"
> 证明的是**忠实传输**（同数据 + 同提示 + 同解码 → 逐条同判定，可复现），**不是**
> "两个 Runner 都擅长 GSM8K"（带指令时它们都不擅长，正确率仅 0.36）。**判定一致性
> 与模型能力是两根轴**——本实验对证的是前者。

## 五、结论

1. **数据层：UEP 忠实传输。** MMLU 开箱聚合分相同、逐条 92% 一致；GSM8K 一旦把提示与
   解码对齐，两个 Runner 在**全部 50 条上逐条判定完全一致**（Δ=0）。若 UEP 损坏了
   题面/答案键/抽取语义，分歧会是结构性的、gold 会对不上——实测两侧 gold 始终一致，
   分歧全部可溯源到提示层。**互操作在数据层得到验证。**
2. **分数层：一致性 = 数据对齐 + 提示对齐 + 解码对齐。** 提示模板、作答指令、解码温度
   都是 Runner/适配器各自的选择，会实打实影响分数（GSM8K 一句指令 = 0.56 的差；解码
   一个未显式的温度 = 采样 vs 贪婪）。这与 UEP 设计一致：协议携带**语义**，不规定
   Runner 的运行时提示与解码；渲染/解码是面向 Runner 的、属 `extras`/适配器层。

## 六、诚实边界与一处发现

- **发现（值得记一笔）**：UEP 的 lm-eval 适配器给 qa 统一追加"只输出最终答案，不要
  解释"，对简单事实型 qa 能让抽取干净，但对**需要推理的 qa（如 GSM8K）会抑制思维链、
  显著压低真实能力分**（本实验：0.92 → 0.36）。这是一处真实的适配器设计缺陷，候选
  改进：qa 默认允许/鼓励链式推理，再从完整输出里抽取答案。**本轮不改**——修它要动
  `uep/` 协议包，越出 A3 红线（判分/渲染实验只进 `scripts/`）；作为发现登记，走 SPEC
  演进机制另议。
- **一次自我纠错**：初版报告曾误称"两侧均贪婪"（Inspect 实为 temp=1.0 采样），由对抗式
  多视角复审抓出并修正、贪婪重跑。本报告数字为修正后结果。
- **范围**：单模型（gemma3:27b）、n=50/原型、贪婪解码、仅 choices/qa 两原型。这是
  "判分链忠实性"的对证，**非模型能力排行**；换模型/更大 n 结论方向应不变（数据层结论
  与模型无关），但绝对数字会变。codegen 不在本报告范围（见 A1 判分闭环报告）。

## 七、复现命令

```bash
# 前置：切片已取（scripts/fetch_slices.py）；.venv-lmeval 与 .venv-inspect 已建；
#       Ollama 可达（export UEP_OLLAMA_BASE=http://<host>:11434/v1/chat/completions）

# MMLU（choices）对分——复现 0.52 = 0.52、逐条 92%
python scripts/crossrunner_run.py --slice mmlu --limit 50 --model gemma3:27b

# GSM8K（qa）对分——复现 0.36 vs 0.92 的背离
python scripts/crossrunner_run.py --slice gsm8k --limit 50 --model gemma3:27b

# 受控证伪实验（turnkey）：给 Inspect qa 追加 lm-eval 的"仅答案"指令，
# 复现 Inspect 0.92→0.36、逐条一致率 1.00（产物入 build/crossrunner/gsm8k-exp/）
python scripts/crossrunner_run.py --slice gsm8k --limit 50 --model gemma3:27b \
  --qa-suffix "Respond with the final answer only, no explanation. Answer:"
```

判分核心的单元测试：`.venv/bin/python -m pytest tests/test_crossrunner_*.py`
（一致性表四象限、两侧日志解析、数值抽取；真实日志裁剪 fixture 驱动）。
两侧 Inspect 运行均以 `--temperature 0 --top-p 1 --seed 0` 强制贪婪、可复现。
