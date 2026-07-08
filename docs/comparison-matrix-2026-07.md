# A4 对比矩阵：UEP 在评测生态里的定位（2026-07）

**目的**：把 UEP 放到同类框架里诚实横评——它跟谁真正同类、跟谁是上下游、独特在哪、又缺在哪。
**方法**：6 个框架经并行调研 + 独立核验相（防幻觉；核验抓出并剔除了一处伪造引文与两处能力误标）。
**诚实边界**：这是 2026-07 的最佳快照，同类框架在快速演进；每个判断附一手来源，低置信处已标注。

## 一、先分清三类，别错位比较

评测生态里的框架不在同一层，硬拉平比是不诚实的：

- **下游 Runner / harness**（跑模型 + 判分）：**lm-eval-harness、Inspect AI、HELM、OpenAI Evals**。
  它们是 UEP 数据的**消费者**，不是竞争者——UEP 明确把同一份数据导出到 lm-eval-harness + Inspect AI。
- **数据集元数据标准**（描述任意数据集，不限评测）：**Croissant**（MLCommons）。与 UEP 部分同轴
  （声明式字段映射、一份描述喂多消费者），但不是评测专用、无判分件。
- **评测数据互操作层**：**unitxt** 与 **UEP** 落在这条轴上——都把异构原始数据集声明式地归一到统一
  接口。**unitxt 是与 UEP 最近的同类物**。但下一节会看到二者的关键分歧。

一句话定位：**UEP 是喂给 Runner 的评测数据互操作协议，从不自己跑模型、从不判分。**

## 二、对比矩阵（最具区分度的维度）

| 维度 | **UEP** | unitxt | Croissant | lm-eval-harness | Inspect AI | HELM | OpenAI Evals |
|------|---------|--------|-----------|-----------------|-----------|------|--------------|
| 主要角色 | **评测数据互操作协议** | 数据准备+评测库（合体） | 数据集元数据标准 | Runner/harness | Runner/harness | Runner/harness(全栈) | Runner/harness+registry |
| 跑模型/判分 | **否（设计如此）** | 是（内跑推理+metric） | 否 | 是 | 是 | 是 | 是 |
| 无损往返（X→内部→X，可反演） | **是（每算子自带 invert）** | 否（算子单向） | 否（单向描述符） | 否 | 否 | 否 | 否 |
| 判分载荷自含于数据 | **是（Verifier 带答案/测试/相关性）** | 部分（答案在数据，判分逻辑在框架） | 无判分件 | 否（逻辑在框架代码） | 部分（答案在数据，逻辑在 scorer） | 否（逻辑在 Metric 类） | 部分（ideal 在数据，逻辑在 eval class） |
| 跨 Runner 导出（一份数据→多运行器） | **是（lm-eval + Inspect）** | 部分（HF 生态兼容） | 是（但消费者是数据平台非 Runner） | 否（本身即 Runner） | 否 | 否 | 否 |
| 声明式字段映射 | 是（mapping.yaml） | 是（preprocess_steps 算子链） | 是（Field.source，单向） | 是（doc_to_text/target/choice） | 部分（FieldSpec 纯改名） | 否（写 Python Scenario） | 部分（registry YAML） |
| 任务原型分类学 | 5 原型 + custom（收敛） | ~21 任务家族（更细） | 无评测原型 | output_type 4 类 | 无 schema 强制 | scenario/adapter 两级 | 按判分策略分类 |
| 溯源/清单/许可 | 是（Provenance+Manifest 专有件） | 有（catalog tags） | 是（元数据标准的本职） | 弱 | 部分 | 配置层 | 弱 |
| 双语/i18n 一等 | **是（中英协议一等）** | 数据多语强、框架/文档英文单语 | 元数据可标语言 | 数据多语、框架英文 | 数据多语、框架英文 | 英文 | 英文 |
| 多模态/agentic | **缺口**（§8 演进候选） | **是（vision/speech + tool_calling）** | 数据可含多模态、无评测语义 | 弱 | agent/工具较强 | 有限（维护模式） | 有（Solver/API） |

## 三、与最近同类的逐一对照

### vs unitxt（IBM Research，最近同类）

**同**：都用声明式机制把异构原始数据集归一到统一 task schema（unitxt 的 `Card.preprocess_steps`
算子链 ≈ UEP 的 `mapping.yaml`），都可序列化为可分享 artifact。

**异（关键）**：
1. **unitxt 是"数据准备 + 评测"合体库，会自己跑推理 + metric 判分**；UEP 是纯协议，**从不运行**。
2. **unitxt 不保证无损往返**——`operators.py` 里 `Copy/Rename/Set/MapInstanceValues/RemoveFields/
   FlattenInstances` 全为单向前向变换，全文无 `invert/inverse/reverse`；它有 output→prediction 的
   "de-verbalization"，但那只规整模型输出、**不反演输入映射重建源数据**。UEP 每算子自带 `invert()`、
   `X→UEP→X` 逐字段无损，是二者最尖锐的对立面。
3. **判分**：unitxt 答案随数据走，但判分逻辑在框架 metric 库（`metrics.bleu` 等字符串 ID 引用）；
   UEP 的 Verifier 把判分载荷（答案/测试/相关性）**完全自含在数据里**，运行方不需回查框架。
4. **unitxt 反而更强的地方（UEP 的缺口）**：任务分类学更细（~21 家族 vs 5 原型）、原生**多模态 +
   工具调用（agentic）**、catalog 更成熟。这些正是 UEP census 标记的前沿缺口 / §8 演进候选。

来源：[IBM/unitxt](https://github.com/IBM/unitxt)、[unitxt docs](https://www.unitxt.ai/)、
[operators.py](https://github.com/IBM/unitxt/blob/main/src/unitxt/operators.py)、[NAACL 2024 demo](https://aclanthology.org/2024.naacl-demo.21.pdf)。

### vs Croissant（MLCommons，元数据标准）

**同**：都是声明式"一份描述喂多消费者"，都有字段映射与溯源/许可元数据。

**异**：Croissant 是**通用数据集元数据标准（JSON-LD），不限评测、无判分语义**——无答案键、无测试、
无相关性判、无任务原型、无无损往返（`Field.source` 的 `extract+transform` 是单向抽取）。它的消费者是
**数据平台**（HF/Kaggle/OpenML/TFDS，合计 40 万+ 数据集），不是评测 Runner。UEP 是**评测专用**、带
自含判分载荷。（注意别混：Croissant 仓库确有一个名为 `Verifier` 的组件，那是**规范校验工具**，不是
判分 verifier。）Croissant 与 UEP 真正可比的是**溯源/清单**那一层，不是判分层。

来源：[mlcommons/croissant](https://github.com/mlcommons/croissant)、[Croissant spec](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)、[arXiv 2403.19546](https://arxiv.org/html/2403.19546v2)。

## 四、与下游 Runner 的关系：喂料，不是竞争

lm-eval-harness / Inspect AI / HELM / OpenAI Evals 都是**跑模型 + 判分的运行器**，它们各自的任务/数据
格式是**单运行器专有的、不跨框架导出**（lm-eval 的 YAML、Inspect 的 Sample、HELM 的 Scenario、Evals
的 jsonl+eval class 都锁在自己框架里），判分逻辑也都在框架代码里。UEP 的定位正是它们**上游的互操作
层**：一份 UEP 数据可导出去驱动其中多个（本项目实测导出 lm-eval + Inspect，并做过双 Runner 分数级对
分）。所以矩阵里它们与 UEP 不在"无损往返/跨 Runner"轴上竞争——它们是 UEP 要喂的对象。

（备注：HELM 已于 2026-06 进入维护模式；各 Runner 均支持多**模型后端**，但那与 UEP 的"一份数据×多
**运行器**"是两回事。）

来源：[lm-eval-harness](https://github.com/EleutherAI/lm-evaluation-harness)、[Inspect AI](https://inspect.aisi.org.uk/)、[HELM](https://github.com/stanford-crfm/helm)、[openai/evals](https://github.com/openai/evals)。

## 五、UEP 的独特组合与诚实缺口

**独特组合**（无任何单一同类框架同时具备这五条）：
1. **从不跑模型/判分**（纯数据层）——区别于所有 Runner *与* unitxt。
2. **无损往返**（每算子自带 invert）——**无同类具备**（unitxt/Croissant/Runner 全单向）。
3. **跨 Runner 导出**（同一份数据 → lm-eval + Inspect，且做过分数级对分）——Runner 单框架、unitxt HF 原生、Croissant 面向数据平台。
4. **自含判分载荷**的 Verifier——同类都把判分逻辑留在框架代码。
5. **声明式映射作一等维护物**（进评审、留 changelog、带溯源哈希）。

**诚实缺口**（同类领先处）：
- **多模态 + agentic**：unitxt（vision/speech/tool_calling）与部分 Runner 明显更强；UEP 目前是文本/代码/
  检索为主，多模态与 agent 工具调用是 census 缺口 + §8 演进候选，**尚无一等原型**。
- **任务分类学广度**：unitxt ~21 家族 vs UEP 5 原型——UEP 是**刻意收敛**（少而稳），但广度确实窄。
- **成熟度/生态**：Runner 与 unitxt/Croissant 有大规模既有 catalog（Croissant 覆盖 40 万+ 数据集），UEP 尚早期。

## 结论

UEP 不与评测 Runner 竞争——它是喂给它们的**评测数据互操作协议**。在真正同轴的同类里（unitxt、Croissant），
UEP 的**无损往返 + 从不运行 + 自含判分载荷 + 跨 Runner 导出**是无同类具备的组合；代价是**多模态/agentic
与任务广度、生态成熟度**上落后于 unitxt。诚实地说：UEP 在"互操作纪律"上独特，在"能力覆盖广度"上仍需
借演进机制（§8）追赶前沿。
