# 提案：成对偏好一等原型（SPEC §8 流程）

**日期**：2026-07-07　**状态**：待裁决　**影响**：SPEC §3（新增任务原型）+ §5（新增 Verifier），协议处 2.0.0-draft（草案期修订；定稿后同类变更须 minor+1）

**提案 ID**：`proposal:2026-07-pairwise-preference`（RewardBench 适配器 `task.schema_ref` 已引用本 ID）

## 动机

成对偏好（奖励建模 / 人类反馈对齐）是一类**独立的评测形态**：给定题面 `prompt` 与两个候选回答 `chosen`（更优）/`rejected`（更差），被测方（奖励模型或裁判）正确当且仅当它把偏好判给 `chosen`。这是 A2 普查标记的**头号分类学缺口（成对偏好）**，21 个 custom 集里的一大簇。

现行五原型无处安放它：

- **不是 choices**：没有固定选项集；本质是两个自由文本回答的**相对偏好/边际**，而非从枚举项里选一个。
- **不是 qa / text_match**：不是"生成某参考答案"，是"在两个给定回答间判优劣"。
- **不是 execution / retrieval**：无代码执行、无语料检索。

**当前过渡表达（本批 RewardBench 适配器实际所用）**：`task.type=custom` + `choice_match(answer_ids=["chosen"])`。这把偏好**退化为二选优**，丢失了：

1. **奖励边际**（chosen 比 rejected 好多少，非二值）；
2. **位置偏置**处理（裁判对 A/B 呈现顺序敏感，须对称评测）；
3. **平局 / 等价**语义（部分集允许 tie）；
4. **多回答排序**（k 路排序，非仅成对）。

## 提案

### 新任务原型 `preference`（SPEC §3）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"preference"` | 判别标签 |
| `prompt` | NFCStr | 题面（被评回答所应答的问题/指令） |
| `candidates` | list[Candidate] | 候选回答（≥2）；Candidate = {id, text, model?} |

### 新 Verifier `preference`（SPEC §5，答案只存 Verifier，P2）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"preference"` | 判别标签 |
| `preferred` | list[str] | 偏好序（candidate id 从优到劣）；成对即 `[chosen_id, rejected_id]` |
| `ties` | list[list[str]]? | 等价组（可选，允许平局的集用） |
| `margin` | float? | 偏好强度/奖励边际（可选，连续奖励集用） |
| `symmetric_required` | bool | 是否要求消除位置偏置（默认 true，裁判须对称呈现两序） |

**自含性规则**：`preference` Verifier 合法 ⇔ `preferred` 非空且其 id 全属 `task.candidates`（同 retrieval 的 relevance⊆corpus 互洽校验）。

命名照搬领域术语（判据 P6 优先专业）：`chosen/rejected/preferred/margin` 为奖励建模通行词。

## 实证（§8 要求 ≥2 个真实数据集）

- **RewardBench**（allenai/reward-bench，odc-by；本批已适配为 custom 过渡态，`prompt/chosen/rejected/subset` 字段实测）——2985 条 filtered 成对；
- **UltraFeedback / Nectar / Anthropic-hh**（同款 chosen/rejected 成对或 k 路排序，沿用同判据；部分带连续奖励分→`margin` 字段）；
- **Chatbot Arena**（lmsys，成对人评 + tie→`ties` 字段）。

三源覆盖：纯成对（RewardBench）、带边际（UltraFeedback）、带平局（Arena）——恰对应提案的 `preferred/margin/ties` 三档。

## 示例（中文题面，缩略）

```json
{"uep_version":"2.0","id":"demo_pref_zh_001","lang":["zh-CN"],
 "task":{"type":"preference","prompt":"用一句话解释光合作用。",
   "candidates":[{"id":"a","text":"植物把光能转化为化学能储存在葡萄糖里。","model":"m1"},
                 {"id":"b","text":"光合作用就是植物晒太阳。","model":"m2"}]},
 "verifiers":[{"type":"preference","preferred":["a","b"],"symmetric_required":true}]}
```

## 迁移与兼容

- 全新增，不破坏既有数据（同 patch 字段提案的向后兼容基调）。
- 过渡态迁移：RewardBench 适配器从 custom（choice_match 过渡判据）改挂 `preference` 原型；`task.schema_ref` 引用退役，payload → 一等字段。
- 试金石：新增 `assemble_preference`（题面 + 候选 + 偏好序自含，同 retrieval 组装物形态）。

## 待裁决

1. 是否接纳 `preference` 为第六原型（vs 继续留 custom）；
2. `margin`/`ties`/`symmetric_required` 是否首日入骨架（vs 仅 `preferred` 起步、其余二期）；
3. 裁判类判分（llm_judge）与偏好判据的关系（偏好可由 llm_judge 执行，但**真值**是 `preferred` 序，二者分层）。
