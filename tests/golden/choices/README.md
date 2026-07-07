# choices 试金石黄金文件

由 `UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones.py` 生成；每文件为对应真实切片
**前 5 条**经 `touchstones/render_choices.py` 的渲染，`tests/test_touchstones.py`
逐字节比对（FR-2.6 断言 ⑤）。渲染或映射表变更后须重新生成并提交评审。

## 数据归属（仅含 5 条摘录/文件，用于测试夹具）

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| mmlu.txt | MMLU（hendrycks 等，HF `cais/mmlu` test 切片） | MIT |
| mmlu_pro.txt | MMLU-Pro（TIGER-Lab，HF `TIGER-Lab/MMLU-Pro` test 切片） | MIT |
| medmcqa.txt | MedMCQA（openlifescienceai，HF `openlifescienceai/medmcqa` validation 切片，医学 4 选一） | Apache-2.0 |
| gaokao.txt | GAOKAO（AGIEval 高考语文子集，HF `dmayhem93/agieval-gaokao-chinese` test 切片，中文高考；gold 下标列表） | MIT |
| arc.txt | AI2 Reasoning Challenge（Allen Institute for AI，HF `allenai/ai2_arc` ARC-Challenge test 切片） | CC-BY-SA-4.0（此署名即归属声明） |
| hellaswag.txt | HellaSwag（Zellers 等，HF `Rowan/hellaswag` validation 切片） | MIT |
| commonsense_qa.txt | CommonsenseQA（Talmor 等，HF `tau/commonsense_qa` validation 切片） | MIT |
| truthful_qa.txt | TruthfulQA（Lin 等，HF `truthfulqa/truthful_qa` mc1 validation 切片） | Apache-2.0 |

C-Eval（CC-BY-NC-SA-4.0）与 BeaverTails（CC-BY-NC-4.0，安全判定，替代 GPQA）
**无黄金文件**：非商业条款，内容摘录不入库；其试金石断言集测试仍在本地切片上全量
运行（tests/test_touchstones.py 的 `GOLDEN_ADAPTERS` 排除项 `_NC_ADAPTERS`）。

完整切片（各 100 条）不入库：`scripts/fetch_slices.py` 获取，
`scripts/slices.lock.json` 以 sha256 与上游修订锁定。

## 执行类黄金文件（tests/golden/execution/）

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| humaneval.txt | HumanEval（Chen 等，HF `openai/openai_humaneval` test 切片前 5 条，经 `touchstones/pack_execution.py` 打包） | MIT |
| mbpp.txt | MBPP（Austin 等，HF `google-research-datasets/mbpp` full/test 切片前 5 条，Python 编程；测试为断言列表 `test_list`） | CC-BY-4.0 |
| ds1000.txt | DS-1000（Lai 等，HF `xlangai/DS-1000` test 切片前 5 条，数据科学代码；code_context 插入式测试模板） | CC-BY-SA-4.0 |
| quixbugs.txt | QuixBugs（Lin 等，HF `Muennighoff/quixbugs` 全集 40 题前 5 条，单行 bug 修复；tests 为 assert 块） | MIT |
| humanevalpack_java.txt | HumanEvalPack-Java（Muennighoff 等，HF `bigcode/humanevalpack` java/test 切片前 5 条，Java 代码；替代 Defects4J，首个非 Python 语言） | MIT |

## 检索类黄金文件（tests/golden/retrieval/）

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| scifact.txt | SciFact（Wadden 等，HF `BeIR/scifact` 三表连接切片前 5 条，经 `touchstones/assemble_retrieval.py` 组装） | CC-BY-SA-4.0（此署名即归属声明） |
| t2ranking.txt | T2Ranking（Xie 等，HF `THUIR/T2Ranking` dev 查询+二元 qrels 连接切片前 5 条，经 `touchstones/assemble_retrieval.py` 组装；中文） | Apache-2.0 |
| nfcorpus.txt | NFCorpus（Boteva 等，HF `BeIR/nfcorpus` 三表连接切片前 5 条，医学检索；doc id 为字符串 MED-/PLAIN-） | CC-BY-SA-4.0（此署名即归属声明） |
| fiqa.txt | FiQA（Maia 等，HF `BeIR/fiqa` 三表连接切片前 5 条，金融检索；doc id 为整数） | CC-BY-SA-4.0（此署名即归属声明） |

## qa 类黄金文件（tests/golden/qa/）

由 `UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones_qa.py` 生成。

| 文件 | 来源数据集 | 许可 |
|------|-----------|------|
| gsm8k.txt | GSM8K（Cobbe 等，HF `openai/gsm8k` main/test 切片前 5 条，经 `touchstones/render_qa.py` 渲染） | MIT |
| svamp.txt | SVAMP（Patel 等，HF `ChilleD/SVAMP` test 切片前 5 条，算术应用题） | MIT |
| math.txt | MATH（Hendrycks 等，HF `EleutherAI/hendrycks_math` algebra/test 切片前 5 条，竞赛数学；最终答案自 solution 的 `\boxed{}` 提取） | MIT |
| mgsm.txt | MGSM（Shi 等，HF `juletxara/mgsm` zh/test 切片前 5 条，中文数学应用题；answer_number 裸整数） | CC-BY-SA-4.0 |
| drop.txt | DROP（Dua 等，HF `ucinlp/drop` validation 切片前 5 条，离散推理阅读理解；partial：passage 进 metadata） | CC-BY-4.0 |
| openai_evals.txt | 中文字谜（GitHub `openai/evals` Chinese_character_riddles 切片前 5 条，经 `touchstones/render_qa.py` 渲染） | MIT |

patch_repair 原型（上游卡未声明许可）**无黄金文件**：从严不入库任何内容摘录，
断言集测试仍在本地切片全量运行——与 C-Eval 同一豁免阶梯。
