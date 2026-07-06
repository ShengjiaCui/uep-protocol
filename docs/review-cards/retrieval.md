# 【UEP 原型评审卡】原型：retrieval + 相关性载荷　协议版本：2.0.0-draft　日期：2026-07-05

> L3 人本验证（测试规格书 §⑥）。第四张卡——四原型评审卡至此备齐（阶段 2 出口条件之一）。

## 1. 定义表（照抄 SPEC §3.5 与 §5）

**task（type="retrieval"）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | str | 查询 |
| `corpus` | {`uri`} \| {`docs`:[{`doc_id`,`title`?,`text`}]} | 语料：引用式或内联，二选一（大语料必须引用式防 OOM） |

**retrieval Verifier**：`relevance: list[{doc_id, grade:int}]` + `metrics: list[str]`（默认 `["ndcg@10"]`）——相关性标注与判分指标全部自含。

## 2. 样例（经试金石 `touchstones/assemble_retrieval.py` 组装）

**英文样例（真实切片：SciFact 查询 1，CC-BY-SA-4.0，署名见黄金 README）**

```
0-dimensional biomaterials show inductive properties.

=== 判分载荷（自含） ===
corpus: hf:BeIR/scifact:corpus
metrics: ndcg@10
relevance:
  - 31715818 (grade=1)
```

**中文样例（合成夹具 `retr_zh_001`，内联语料形态）**

```
长江的主要支流有哪些？

=== 判分载荷（自含） ===
corpus: 内联 2 篇
metrics: ndcg@10
relevance:
  - d1 (grade=1)
```

> ⚠️ 与前卡同款偏离：中文真实检索切片待物色（首选 MIRACL zh 被 HF 门禁挡住
> datasets-server 不可用；候选 DuRetrieval/T2Ranking 许可待核）。

## 3. 评审问题（评审人作答）

- **Q1** 字段命名（`query`/`corpus`/`doc_id`/`relevance`/`grade`/`metrics`）在你的领域自然吗？哪个别扭？
  答：
- **Q2** 你见过的检索评测数据（多级相关度、多字段文档、会话式检索），有装不进这个结构的吗？
  答：
- **Q3** 哪个字段你第一眼理解错了？
  答：
- **Q4** 缺了什么必要信息（如语料版本锚定、负样本声明）？
  答：
- **Q5** 结论：通过 / 有条件通过（条件：＿＿）/ 打回
  答：**通过**（用户终签，2026-07-06）

> **第一轮评审性质注记**：Q1–Q4 未逐项作答。终签依据 = SciFact（英文，CC-BY-SA-4.0）
> 与 T2Ranking（中文，Apache-2.0）双切片各 100 条全量断言 + 无损反演（qrels int id
> 保真）+ 引用式语料防 OOM 有测试 + **双语平权在检索原型实证**（同一代码路径、
> 双黄金入库）。外部领域评审人第二轮随同行征询进行，届时按模板另行作答 Q1–Q4。

## 4. 评审人：jason（用户本人；领域背景：AI 从业者 / 项目负责人）　日期：2026-07-06

## 5. 用户终签：**jason，2026-07-06**（会话指令原文："签字 testsuite/patch/retrieval"）
