# A2 纵深：18 新集选集定档（12→30 全适配）

> 从 A2 普查（`docs/coverage-map.rows.json`）挑多样性最大子集，把全适配数据集从 **12 补到 30**。
> 许可取自普查（从严阶梯）：permissive→golden 入库；NC/未声明→无 golden 仅本地切片验证。
> 硬约束达成：**每原型 ≥3**、**中文 ≥5**、域散（数学/医疗/金融/科学/代码/指令/Java/多语）。

## 补齐后原型分布（12+18=30）

| 原型 | 现有 | 新增 | 合计 |
|------|-----:|-----:|-----:|
| choices | 6 | 5 | 11 |
| qa | 1 | 5 | 6 |
| code_generation | 1 | 3 | 4 |
| patch_repair | 1 | 2 | 3 |
| retrieval | 2 | 3 | 5 |

中文合计 ≥5：C-Eval + T2Ranking（已适配）+ CMMLU + GAOKAO（新，纯中文）+ MGSM/MIRACL（含中文子集）。

## 18 新集（按批；许可/语言取自普查）

| 批 | 集 | 原型 | 许可 | 语言 | 域 | golden | 预期新算子 |
|--:|----|------|------|------|----|:------:|-----------|
| 1 | MMLU-Pro | choices | mit | en | 通识(难) | ✓ | 复用(choice_match) |
| 1 | MedMCQA | choices | apache-2.0 | en | 医疗 | ✓ | 复用 |
| 1 | MATH | qa | mit | en | 数学 | ✓ | 复用(text_match) |
| 1 | SVAMP | qa | mit | en | 数学(应用题) | ✓ | 复用 |
| 1 | BEIR-NFCorpus | retrieval | cc-by-sa-4.0 | en | 医学检索 | ✓ | 复用(relevance_from_qrels) |
| 1 | MBPP | code_generation | cc-by-4.0 | en | 代码入门 | ✓ | 复用(execution) |
| 2 | CMMLU | choices | cc-by-nc-4.0 | zh | 中文通识 | ✗ NC | 复用 |
| 2 | GAOKAO-Bench | choices | apache-2.0 | zh | 中文高考 | ✓ | 复用/partial |
| 2 | MGSM | qa | cc-by-sa-4.0 | multi(含zh) | 多语数学 | ✓ | 复用 |
| 2 | DROP | qa | cc-by-4.0 | en | 离散推理 | ✓ | 复用/partial |
| 2 | BEIR-FiQA | retrieval | cc-by-sa-4.0 | en | 金融检索 | ✓ | 复用 |
| 2 | HumanEval+ | code_generation | apache-2.0 | en | 代码(加测) | ✓ | 复用 |
| 3 | GPQA | choices | cc-by-4.0 | en | 研究生科学 | ✓ | 复用 |
| 3 | DS-1000 | code_generation | cc-by-sa-4.0 | en | 数据科学 | ✓ | 复用/新? |
| 3 | MIRACL | retrieval | apache-2.0 | multi(含zh) | 多语检索 | ✓ | 复用 |
| 3 | IFEval | qa | apache-2.0 | en | 指令遵循 | ✓ | **预期新算子**(可验证约束) |
| 3 | QuixBugs | patch_repair | mit | en | 单行缺陷 | ✓ | 复用/新? |
| 3 | Defects4J | patch_repair | mit | en(Java) | Java 缺陷 | ✓ | **预期新算子/partial** |

## 批次策略

- **Batch 1**（6，全 permissive full、高复用）：热身+验证流水线（MMLU-Pro/MedMCQA/MATH/SVAMP/NFCorpus/MBPP）。
- **Batch 2**（6，补中文+域）：CMMLU（NC 无 golden 演示从严阶梯）/GAOKAO/MGSM/DROP/FiQA/HumanEval+。
- **Batch 3**（6，难/新算子候选）：GPQA/DS-1000/MIRACL/**IFEval**/QuixBugs/**Defects4J**——最可能触发新算子或 partial，压到最后（前两批先建立基线）。

## 诚实注记

- 选集优先 permissive（17/18 可入 golden）；CMMLU（NC）故意纳入以演示"从严阶梯→无 golden 仅本地"路径。
- IFEval / Defects4J / DS-1000 / QuixBugs **预期可能需新算子或只能标 partial**——如实标注，新算子进 engine（判别联合+invert+单测）计入成本，可触发 §8 演进。
- 每原型 ≥3、中文 ≥5 为硬约束；若某集 schema/门禁受阻，按从严阶梯替换同类候选（池中尚有 MMLU-Redux/QASC/MathQA/BEIR-其余/APPS/MBPP+ 等），不硬凑、不降闸门。
