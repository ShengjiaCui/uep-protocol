# choices 试金石黄金文件

由 `UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones.py` 生成；每文件为对应真实切片
**前 5 条**经 `touchstones/render_choices.py` 的渲染，`tests/test_touchstones.py`
逐字节比对（FR-2.6 断言 ⑤）。渲染或映射表变更后须重新生成并提交评审。

## 数据归属（仅含 5 条摘录/文件，用于测试夹具）

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| mmlu.txt | MMLU（hendrycks 等，HF `cais/mmlu` test 切片） | MIT |
| arc.txt | AI2 Reasoning Challenge（Allen Institute for AI，HF `allenai/ai2_arc` ARC-Challenge test 切片） | CC-BY-SA-4.0（此署名即归属声明） |
| hellaswag.txt | HellaSwag（Zellers 等，HF `Rowan/hellaswag` validation 切片） | MIT |
| commonsense_qa.txt | CommonsenseQA（Talmor 等，HF `tau/commonsense_qa` validation 切片） | MIT |
| truthful_qa.txt | TruthfulQA（Lin 等，HF `truthfulqa/truthful_qa` mc1 validation 切片） | Apache-2.0 |

C-Eval（CC-BY-NC-SA-4.0，非商业条款）**无黄金文件**：内容摘录不入库；
其试金石断言集测试仍在本地切片上全量运行（tests/test_touchstones.py 的
`GOLDEN_ADAPTERS` 排除项）。

完整切片（各 100 条）不入库：`scripts/fetch_slices.py` 获取，
`scripts/slices.lock.json` 以 sha256 与上游修订锁定。

## 执行类黄金文件（tests/golden/execution/）

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| humaneval.txt | HumanEval（Chen 等，HF `openai/openai_humaneval` test 切片前 5 条，经 `touchstones/pack_execution.py` 打包） | MIT |

## 检索类黄金文件（tests/golden/retrieval/）

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| scifact.txt | SciFact（Wadden 等，HF `BeIR/scifact` 三表连接切片前 5 条，经 `touchstones/assemble_retrieval.py` 组装） | CC-BY-SA-4.0（此署名即归属声明） |
| t2ranking.txt | T2Ranking（Xie 等，HF `THUIR/T2Ranking` dev 查询+二元 qrels 连接切片前 5 条，经 `touchstones/assemble_retrieval.py` 组装；中文） | Apache-2.0 |

## qa 类黄金文件（tests/golden/qa/）

由 `UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones_qa.py` 生成。

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| gsm8k.txt | GSM8K（Cobbe 等，HF `openai/gsm8k` main/test 切片前 5 条，经 `touchstones/render_qa.py` 渲染） | MIT |
| openai_evals.txt | 中文字谜（GitHub `openai/evals` Chinese_character_riddles 切片前 5 条，经 `touchstones/render_qa.py` 渲染） | MIT |

patch_repair 原型（上游卡未声明许可）**无黄金文件**：从严不入库任何内容摘录，
断言集测试仍在本地切片全量运行——与 C-Eval 同一豁免阶梯。
