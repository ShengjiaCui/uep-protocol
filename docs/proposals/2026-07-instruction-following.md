# 提案：指令跟随可验证约束一等原型（SPEC §8 流程）

**日期**：2026-07-07　**状态**：待裁决　**影响**：SPEC §5（新增 Verifier）±§3，协议处 2.0.0-draft（草案期修订；定稿后同类变更须 minor+1）

**提案 ID**：`proposal:2026-07-instruction-following`（IFEval 适配器 `task.schema_ref` 已引用本 ID）

## 动机

指令跟随（IFEval 式"可验证指令"）判分靠一组**程序化约束检查**：题面附带 `instruction_id_list`（命名判据，如 `punctuation:no_comma`、`length_constraints:number_words`、`detectable_format:number_highlighted_sections`）与对应 `kwargs`（参数，如 `num_words=300`、`relation="at least"`）。被测输出逐条过检查即通过。

现行七类 Verifier 无一能表达它：

- **regex** 只覆盖一小撮（`no_comma` 可用 regex），但"至少 300 词""恰好 3 个高亮段""首词必须是 X"等**计数/结构约束不是正则**；
- **text_match / choice_match** 无参考答案可比（约束是生成侧规则，非固定答案）；
- **llm_judge** 可近似但**丢失确定性**（IFEval 的价值正是程序化可复现，非裁判打分）；
- **composite** 能组合已有判据，但底层缺"单条命名约束"这个原子。

**当前过渡表达（本批 IFEval 适配器实际所用）**：`task.type=custom` + `regex(".+")`。regex 下限仅验"产出非空"，**判不了任何具体约束**；完整约束谱（instruction_id_list + kwargs）原样存 `task.payload`，等本提案落地。

## 提案

### 新 Verifier `instruction_following`（SPEC §5，答案只存 Verifier，P2）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"instruction_following"` | 判别标签 |
| `constraints` | list[Constraint] | 约束清单（≥1）；Constraint = {id, kwargs} |
| `mode` | `"all_of" \| "count"` | 全过 / 计过数（IFEval 报 strict/loose 两口径，count 支持后者） |

其中 `Constraint.id` 取自封闭命名判据表（`punctuation:*`/`length_constraints:*`/`detectable_format:*`/`keywords:*`/`startend:*`/…，照搬 IFEval 判据库命名——判据 P6 优先专业），`kwargs` 为该判据参数字典。

**自含性规则**：`instruction_following` Verifier 合法 ⇔ `constraints` 非空且每条 `id` 属命名判据表。判据实现（检查函数）随试金石消费者提供，不入数据（同 execution 的 harness 约定：数据带"查什么"，运行方带"怎么查"）。

### 试金石

新增 `check_instructions`（题面 + 约束清单自含，对标准判据库逐条求值；判据库=零数据集名的通用消费者）。

## 实证（§8 要求 ≥2 个真实数据集）

- **已实测适配 1 个**：**IFEval**（google/IFEval，Apache-2.0；本批已适配为 custom 过渡态，`instruction_id_list`+`kwargs` 字段在真实切片 100 条实测无损往返，25 类判据）；
- **同族结构候选（未逐一适配）**：**IFEval-zh / Multi-IFEval**（中文/多语，沿用同款命名判据 + 参数，验判据表跨语言）、**FollowBench**（多级约束，`mode=count` 分级计过数）。

三档（英文全过 / 跨语言 / 分级计数）分别由 IFEval（已实测）、Multi-IFEval、FollowBench 覆盖。**诚实口径**：仅 IFEval 经真实切片适配实测，其余为结构性候选（同族 schema，落地时须逐一验证）。

## 示例（中文题面，缩略）

```json
{"uep_version":"2.0","id":"demo_if_zh_001","lang":["zh-CN"],
 "task":{"type":"qa","question":"用不少于 100 字介绍长江，且不要使用逗号。"},
 "verifiers":[{"type":"instruction_following","mode":"all_of",
   "constraints":[{"id":"length_constraints:number_words","kwargs":{"num_words":100,"relation":"at least"}},
                  {"id":"punctuation:no_comma","kwargs":{}}]}]}
```

注：`instruction_following` 可挂在 `qa`（题面即指令）之上，无需新任务原型——与 preference 提案（须新原型）不同，本提案**仅新增 Verifier**，改动更小。

## 待裁决

1. 是否接纳 `instruction_following` Verifier（vs 继续留 custom + regex 下限）；
2. 命名判据表是否首日全量入 SPEC（25+ 条）还是分档纳入；
3. strict/loose 两口径（`mode=all_of` vs `count`）是否首日入骨架；
4. 判据实现归属：随试金石库（本提案默认）vs 独立判据服务。
