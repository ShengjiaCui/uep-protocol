# UEP 覆盖地图：100+ 主流评测集普查（2026-07）

> 对 **106 个主流评测集**做**桌面 schema 层普查**（不建适配、不下数据切片）：逐集判定归入
> 哪个 UEP 原型、吻合度、许可、语言、判分类型，**每行标 grounding 依据与置信度**。
> **头条**：**85/106（80%）可被五原型 full+partial 容纳**，21/106（20%）
> 现有原型装不下（=分类学缺口，演进机制燃料）。


## 方法与诚实声明

- **样本口径（读 80% 前必看）**：名单是**策展的主流集**，且**故意纳入** agentic/偏好/多模态等 custom 候选以暴露缺口——故容纳率是「主流集」口径、**非随机抽样、非全体评测集**（且故意纳入已知缺口是往下压容纳率、非抬高）。
- **grounding 优先级**：① lm-eval 任务 YAML 的 `output_type`（本地离线、高置信）→ ② HF datasets-server `/info` features + 卡片 → ③ 数据集卡 cardData → ④ 文档知识（低置信）。
- **许可从严**：以卡片实际声明为准，**未声明=`unknown`**，绝不猜许可以求好看。
- 每行经**独立核验相**复查（`full`/`custom` 判定与 `license` 逐一回查——防幻觉）。
- 这是**桌面 schema 分析**，非实测适配（全适配是 A2 纵深）；置信度非均一，如下分布。


## 容纳率与分布

| 维度 | 分布 |
|------|------|
| 吻合度 | **full 69 / partial 16 / custom 21**（容纳 85/106=80%） |
| 归入原型 | choices 31 / qa 20 / code_generation 15 / patch_repair 6 / retrieval 13 / custom 21 |
| 语言 | en 90 / multi 10 / zh 5 / es 1 |
| 置信度 | high 70 / med 35 / low 1 |
| grounding 依据 | lmeval-cfg 50 / hf-info 18 / card 19 / doc 19 |
| 许可 | unknown 22（从严）；其余见下表逐行 |

## 分类学缺口（21 个 custom → SPEC §8 演进候选）

现有五原型装不下的集，按缺失能力聚类——每类是协议演进的燃料（本轮只登记，不改 SPEC）：

- **多模态**（3）：MMMU, MathVista, SWE-bench Multimodal — 缺口：题面/答案含图像——原型均为纯文本表示
- **成对偏好**（3）：Arena-Hard, RewardBench, AlpacaEval 2 — 缺口：成对偏好胜率，判分=偏好而非对错
- **交互环境**（2）：WebArena, WebShop — 缺口：有状态环境交互（点击/购物/浏览），非静态样本
- **安全/红队**（2）：HarmBench, JailbreakBench — 缺口：有害行为判定，判分=行为分类器/裁判
- **聚合基准(嵌入多任务)**（1）：MTEB — 缺口：多任务聚合（检索+分类+聚类），非单原型
- **agentic 多步/工具**（1）：GAIA — 缺口：多轮工具调用轨迹 + 环境状态——退化 QA 装不下
- **多模态+agent**（1）：VisualWebArena — 缺口：多模态 + 交互环境双重缺口
- **agentic 多环境**（1）：AgentBench — 缺口：跨环境 agent 轨迹
- **工具+用户模拟**（1）：tau-bench — 缺口：工具调用 + 模拟用户多轮
- **工具调用**（1）：ToolBench — 缺口：API 工具调用序列判分
- **GUI agent**（1）：OSWorld — 缺口：桌面/GUI 操作序列
- **agentic 轨迹**（1）：SWE-agent (agent tasks) — 缺口：仓库级 agent 修复轨迹（非单 patch）
- **成对/评分裁判**（1）：MT-Bench — 缺口：成对/多轮 LLM 裁判，无单一正解
- **人类成对投票**（1）：Chatbot Arena — 缺口：人类成对投票 Elo，无固定黄金
- **安全/过度拒绝**（1）：XSTest — 缺口：过度拒绝安全，判分语义特殊

**共性**：五原型是**静态样本 → 判分**的形态；缺口集中在 **agentic 轨迹/交互环境**、**成对偏好**、**多模态**、**安全/红队**四大类。这与 goals 的「表达力上限=Agent 任务空间」一致——环境/轨迹/复合验证在骨架里（CustomTask+CompositeVerifier 是逃生舱），但**尚无一等原型**，正是演进机制该逐个转化的燃料。


## 逐集普查表（106 行）

| # | 集 | 原型 | 吻合 | 许可 | 语言 | 判分 | 依据 | 置信 | 备注 |
|--:|----|------|------|------|------|------|------|------|------|
| 1 | ANLI | choices | full | cc-by-nc-4.0 | en | loglikelihood | lmeval-cfg | high | 3-way NLI (True/Neither/False) multiple_choice; cc-by-nc-4.0 verified |
| 2 | AQuA-RAT | choices | full | apache-2.0 | en | loglikelihood | lmeval-cfg | high | lm-eval scores 5-way MC via agieval; rationale unused; apache-2.0 upstream AQuA |
| 3 | ARC-Challenge | choices | full | cc-by-sa-4.0 | en | loglikelihood/acc | lmeval-cfg | high | include arc_easy.yaml; 难题子集; multiple_choice |
| 4 | ARC-Easy | choices | full | cc-by-sa-4.0 | en | loglikelihood/acc | lmeval-cfg | high | multiple_choice; 小学科学; ai2_arc卡片=cc-by-sa-4.0 |
| 5 | Belebele | choices | full | cc-by-sa-4.0 | multi | loglikelihood | lmeval-cfg | high | 122-lang reading comp, 4 options; multiple_choice; cc-by-sa-4.0 verified |
| 6 | BoolQ | choices | full | cc-by-sa-3.0 | en | loglikelihood/acc | lmeval-cfg | high | 是非→no/yes二选; super_glue聚合标other, 但google/boolq卡片=cc-by-sa-3.0 |
| 7 | C-Eval | choices | full | cc-by-nc-sa-4.0 | zh | loglikelihood | lmeval-cfg | high | Chinese 52-subject A-D MCQ; multiple_choice; cc-by-nc-sa-4.0 verified |
| 8 | CMMLU | choices | full | cc-by-nc-4.0 | zh | loglikelihood | lmeval-cfg | high | Chinese 67-subject A-D MCQ; multiple_choice; cc-by-nc-4.0 now verified via HF |
| 9 | CommonsenseQA | choices | full | mit | en | loglikelihood/acc | lmeval-cfg | high | 常识5选一; multiple_choice; tau/commonsense_qa卡片=mit |
| 10 | GPQA | choices | full | cc-by-4.0 | en | loglikelihood | lmeval-cfg | high | 4-option graduate MCQ; output_type multiple_choice; cc-by-4.0 verified via HF |
| 11 | HeadQA | choices | full | unknown | es | loglikelihood | lmeval-cfg | med | Spanish medical-exam MCQ; multiple_choice; card license 'other'->unknown; en variant exists |
| 12 | HellaSwag | choices | full | unknown | en | loglikelihood/acc | lmeval-cfg | high | 常识续写4选; Rowan/hellaswag卡片未声明许可→unknown(从严) |
| 13 | LogiQA | choices | full | other | en | loglikelihood/acc | lmeval-cfg | high | 逻辑推理MC(英译版); EleutherAI/logiqa卡片license:other |
| 14 | MMLU | choices | full | mit | en | loglikelihood/acc | lmeval-cfg | high | output_type=multiple_choice; 57学科4选一; cais/mmlu卡片=mit |
| 15 | MMLU-Pro | choices | full | mit | en | exact_match | lmeval-cfg | high | generate_until+regex抽字母; 10选一单一正解仍属choices; TIGER-Lab卡片=mit |
| 16 | MMLU-Redux | choices | full | cc-by-4.0 | en | loglikelihood/acc | hf-info | med | 本版无lm-eval配置; features有choices/answer; 卡片=cc-by-4.0 |
| 17 | MathQA | choices | full | apache-2.0 | en | loglikelihood | lmeval-cfg | high | 5-option math MCQ; multiple_choice acc/acc_norm; apache-2.0 verified via HF |
| 18 | MedMCQA | choices | full | apache-2.0 | en | loglikelihood/acc | lmeval-cfg | high | 医学4选一; medmcqa→openlifescienceai/medmcqa卡片=apache-2.0 |
| 19 | MedQA (USMLE) | choices | full | cc-by-sa-4.0 | en | loglikelihood/acc | lmeval-cfg | high | medqa_4options; USMLE4选一; GBaker镜像卡片=cc-by-sa-4.0 |
| 20 | MuSR | choices | full | cc-by-4.0 | en | loglikelihood (acc_norm) | lmeval-cfg | high | 多步软推理，output_type multiple_choice，acc_norm |
| 21 | OpenBookQA | choices | full | unknown | en | loglikelihood/acc | lmeval-cfg | high | 开卷科学4选; allenai/openbookqa卡片显式license:unknown |
| 22 | PIQA | choices | full | unknown | en | loglikelihood/acc | lmeval-cfg | high | 物理常识二选; ybisk/piqa卡片显式license:unknown |
| 23 | QASC | choices | full | cc-by-4.0 | en | loglikelihood/acc | hf-info | med | 8选一多跳科学; 无lm-eval任务; allenai/qasc卡片=cc-by-4.0 |
| 24 | RACE | choices | full | other | en | loglikelihood/acc | lmeval-cfg | high | 阅读理解4选一; EleutherAI/race卡片license:other |
| 25 | SciQ | choices | full | cc-by-nc-3.0 | en | loglikelihood/acc | lmeval-cfg | high | 科学4选(3干扰+正解); allenai/sciq卡片=cc-by-nc-3.0 |
| 26 | Social IQa | choices | full | unknown | en | loglikelihood/acc | lmeval-cfg | high | 3选一MC; 配置为英文social_iqa; allenai/social_i_qa卡片未声明→unknown |
| 27 | Winogrande | choices | full | unknown | en | loglikelihood/acc | lmeval-cfg | high | 指代消解二选; allenai/winogrande卡片未声明→unknown |
| 28 | XCOPA | choices | full | cc-by-4.0 | multi | loglikelihood | lmeval-cfg | high | 11-lang causal 2-choice; multiple_choice; cc-by-4.0 verified |
| 29 | AGIEval | choices | partial | mit | multi | loglikelihood | lmeval-cfg | med | exam suite; cloze/fill-in subtasks; MIT from upstream Microsoft repo, HF mirror undeclared |
| 30 | GAOKAO-Bench | choices | partial | apache-2.0 | zh | loglikelihood | lmeval-cfg | med | proxied to AGIEval gaokao MC subset; full bench has fill-in/open; apache-2.0 OpenLMLab repo |
| 31 | TruthfulQA-MC | choices | partial | apache-2.0 | en | loglikelihood(prob-mass) | lmeval-cfg | high | mc1 single-true + mc2 multi-true breaks one-canonical; apache-2.0 verified |
| 32 | AIME 2024 | qa | full | mit | en | exact_match | lmeval-cfg | high | lmeval确认generate_until+exact_match;整数答案精确匹配;qa无损;MIT card核实 |
| 33 | DROP | qa | full | cc-by-4.0 | en | exact_match/f1 | lmeval-cfg | high | 离散推理阅读，EM+F1；license 实为 cc-by-4.0（非 SA） |
| 34 | GSM8K | qa | full | mit | en | exact_match | lmeval-cfg | high | grade-school math; generate_until, regex last-number; mit verified via HF |
| 35 | MATH | qa | full | mit | en | exact_match | lmeval-cfg | high | competition math; generate_until + math-equivalence match; mit verified via HF |
| 36 | MGSM | qa | full | cc-by-sa-4.0 | multi | exact_match | lmeval-cfg | high | generate_until，数值答案 EM；多语 GSM8K；juletxara/mgsm |
| 37 | Natural Questions | qa | full | cc-by-sa-3.0 | en | exact_match | lmeval-cfg | high | nq_open，开放域短答案 EM，generate_until |
| 38 | SVAMP | qa | full | mit | en | exact_match | hf-info | med | no lmeval; schema Body/Question/Answer; short numeric answer; mit verified |
| 39 | SimpleQA | qa | full | mit | en | model_graded | card | med | 短事实问答，LLM 评分 correct/incorrect/not_attempted；无 lmeval 配置 |
| 40 | TriviaQA | qa | full | unknown | en | exact_match | lmeval-cfg | high | 闭卷事实，别名集 EM；card 标 license:unknown |
| 41 | ASDiv | qa | partial | cc-by-nc-4.0 | en | loglikelihood(acc) | lmeval-cfg | high | default output_type loglikelihood (not free-gen); short numeric; cc-by-nc-4.0 verified |
| 42 | BBH | qa | partial | mit | en | exact_match | lmeval-cfg | med | generate_until+regex; mixed MC/short-answer; MIT upstream suzgunmirac, mirror undeclared |
| 43 | CoQA | qa | partial | other | en | exact_match/f1 | lmeval-cfg | high | 对话式多轮，qa 丢失对话状态；EM/F1；card license:other |
| 44 | IFEval | qa | partial | apache-2.0 | en | programmatic (strict/loose acc) | lmeval-cfg | high | 可验证指令约束，Python 程序校验非 LLM 评分；verifiable-reward 缺口 |
| 45 | LAMBADA | qa | partial | mit | en | loglikelihood (acc+perplexity) | lmeval-cfg | high | 末词 cloze，loglikelihood acc+perplexity，非标准问答；lambada_openai MIT |
| 46 | LongBench | qa | partial | unknown | multi | F1/ROUGE-L/edit-sim(程序化) | lmeval-cfg | high | 长上下文多任务zh/en混合判分,含摘要/代码子任务;card未声明license；有 lm-eval 配置,判分全程序化无 LLM 裁判 |
| 47 | Needle-in-Haystack | qa | partial | unknown | en | model_graded/exact_match | doc | med | 取回上下文事实按匹配判,非文档排序,不入retrieval;方法库无声明license |
| 48 | RULER | qa | partial | apache-2.0 | en | exact_match | lmeval-cfg | high | 长上下文合成串匹配判分;qa可承但丢长度压力维度;Apache-2.0 GitHub核实 |
| 49 | SQuAD v2 | qa | partial | cc-by-sa-4.0 | en | exact_match/f1 | lmeval-cfg | high | generate_until，squad_v2 EM/F1，含不可答 NoAns 判定 |
| 50 | TyDi QA | qa | partial | apache-2.0 | multi | exact_match/f1 | card | med | 多语抽取式，含段落选择子任务；无 lmeval 配置 |
| 51 | WebQuestions | qa | partial | unknown | en | loglikelihood/exact_match | lmeval-cfg | high | config 为 multiple_choice 包装答案集，实为开放 QA；license unknown |
| 52 | APPS | code_generation | full | mit | en | execution | card | med | 竞赛级代码，执行测试用例；无 lmeval 配置；codeparrot/apps MIT |
| 53 | BigCodeBench | code_generation | full | apache-2.0 | en | execution | hf-info | high | features test+entry_point 执行判分;卡 apache-2.0 已核实 |
| 54 | ClassEval | code_generation | full | mit | en | execution | card | med | 类级生成跑单测判分;卡 mit 已核实 |
| 55 | CodeContests | code_generation | full | cc-by-4.0 | en | execution | card | high | 竞赛题对隐藏测试执行;卡 cc-by-4.0(task_cats 误标 translation) |
| 56 | DS-1000 | code_generation | full | cc-by-sa-4.0 | en | execution | hf-info | high | features code_context+test_case_cnt 执行判分;卡 cc-by-sa-4.0 已核实 |
| 57 | HumanEval | code_generation | full | mit | en | execution | lmeval-cfg | high | 函数补全，执行测试 pass@k(unsafe_code) |
| 58 | HumanEval+ | code_generation | full | apache-2.0 | en | execution | lmeval-cfg | high | humaneval_plus，扩充测例，执行 pass@k；evalplus apache-2.0 |
| 59 | HumanEval-X | code_generation | full | apache-2.0 | en | execution | card | high | 多编程语言执行;数据集已迁 zai-org,卡 apache-2.0 已核实 |
| 60 | LiveCodeBench | code_generation | full | unknown | en | execution | doc | med | 执行判分代码生成;/info 不可用,卡仅标 generic cc 无 SPDX 变体→unknown |
| 61 | MBPP | code_generation | full | cc-by-4.0 | en | execution | lmeval-cfg | high | 入门 Python，执行断言 pass@1(unsafe_code) |
| 62 | MBPP+ | code_generation | full | apache-2.0 | en | execution | lmeval-cfg | high | mbpp_plus，扩充测例，执行判分；evalplus apache-2.0 |
| 63 | MBXP | code_generation | full | apache-2.0 | en | execution | doc | med | MBPP 译多语跑测试;HF /info 空配置,许可据 mxeval 仓 apache-2.0 |
| 64 | MultiPL-E | code_generation | full | mit | en | execution | hf-info | high | features tests 逐编程语言执行;卡 mit 已核实 |
| 65 | Spider | code_generation | partial | cc-by-sa-4.0 | en | execution(DB 结果集匹配) | card | med | text-to-SQL 需 DB 执行结果集匹配非单测,故 partial;卡 cc-by-sa-4.0 |
| 66 | USACO | code_generation | partial | unknown | en | execution | doc | med | 算法竞赛执行测试判分;丢多步/检索脚手架;HF与GitHub均无声明license |
| 67 | BugsInPy | patch_repair | full | unknown | en | execution | doc | low | Python 真实缺陷跑项目测试;soarsmu 仓无许可文件→unknown |
| 68 | Defects4J | patch_repair | full | mit | en | execution | doc | med | Java 缺陷跑 JUnit 触发测试;许可 rjust/defects4j 仓 MIT 已核实 |
| 69 | QuixBugs | patch_repair | full | mit | en | execution | doc | med | 单行缺陷 Py/Java 跑测试;许可 jkoppel 仓 spdx MIT 已核实 |
| 70 | SWE-bench | patch_repair | full | unknown | en | execution | hf-info | high | features patch/test_patch/FAIL_TO_PASS 跑仓库测试;卡未声明许可→unknown |
| 71 | SWE-bench Lite | patch_repair | full | unknown | en | execution | card | high | 轻量子集,同 patch+跑测试;卡 license None→unknown |
| 72 | SWE-bench Verified | patch_repair | full | unknown | en | execution | card | high | 人工验证子集,补丁+跑仓库测试;卡 license None→unknown |
| 73 | BEIR-ArguAna | retrieval | full | cc-by-sa-4.0 | en | ndcg@10 | hf-info | high | text-retrieval，反论点检索，已验证 license |
| 74 | BEIR-FiQA | retrieval | full | cc-by-sa-4.0 | en | ndcg@10 | hf-info | high | HF task_categories=text-retrieval，金融观点检索，qrels+ndcg 判分 |
| 75 | BEIR-HotpotQA | retrieval | full | cc-by-sa-4.0 | en | ndcg@10 | hf-info | high | BEIR 版仅排序段落，text-retrieval，无损 |
| 76 | BEIR-NFCorpus | retrieval | full | cc-by-sa-4.0 | en | ndcg | card | high | 医学检索 text-retrieval;卡 cc-by-sa-4.0;nDCG@10/recall |
| 77 | BEIR-Quora | retrieval | full | cc-by-sa-4.0 | en | ndcg@10 | hf-info | high | text-retrieval，重复问题检索，已验证 license |
| 78 | BEIR-SciFact | retrieval | full | cc-by-sa-4.0 | en | ndcg | card | high | 科学核查检索;task_categories text-retrieval;卡 cc-by-sa-4.0;nDCG@10 |
| 79 | BEIR-TREC-COVID | retrieval | full | cc-by-sa-4.0 | en | ndcg@10 | hf-info | high | text-retrieval，COVID 文献检索，已验证 license |
| 80 | BEIR-Touche2020 | retrieval | full | cc-by-sa-4.0 | en | ndcg@10 | hf-info | high | text-retrieval，论辩检索，已验证 license |
| 81 | BRIGHT | retrieval | full | cc-by-4.0 | en | ndcg@10 | hf-info | high | text-retrieval；推理密集但判分仍 ndcg，已验证 cc-by-4.0 |
| 82 | DuReader-Retrieval | retrieval | full | unknown | zh | mrr/ndcg | doc | med | 中文段落检索；HF 上均未声明 license，unknown |
| 83 | MIRACL | retrieval | full | apache-2.0 | multi | ndcg@10 | hf-info | high | text-retrieval，18 语多语检索，已验证 apache-2.0 |
| 84 | MS-MARCO | retrieval | full | unknown | en | mrr@10/ndcg | hf-info | med | 段落排序；microsoft/ms_marco 未声明 license，非商用，从严 unknown |
| 85 | T2Ranking | retrieval | full | apache-2.0 | zh | mrr@10/ndcg | hf-info | high | text-retrieval，中文段落排序，已验证 apache-2.0 |
| 86 | AgentBench | custom | custom | apache-2.0 | en | success_rate/reward | doc | med | 多环境 agent(OS/DB/KG/web)，交互轨迹；license 经 GitHub 验证 |
| 87 | AlpacaEval 2 | custom | custom | cc-by-nc-4.0 | en | pairwise | card | high | 长度校正胜率LLM裁判;CC-BY-NC-4.0 HF核实 |
| 88 | Arena-Hard | custom | custom | unknown | en | pairwise | doc | med | 成对偏好胜率GPT裁判;仓库无LICENSE文件故unknown,由high降med |
| 89 | Chatbot Arena | custom | custom | unknown | multi | pairwise | card | med | 人类成对投票Elo不可自动判;card仅泛标cc故unknown |
| 90 | GAIA | custom | custom | unknown | en | exact_match(final) | doc | med | HF gated 且未声明 license；EM 判分但需 agent 工具+多模态，轨迹丢失 |
| 91 | HarmBench | custom | custom | mit | en | model_graded | card | high | 红队有害行为分类器判;安全类;MIT HF核实 |
| 92 | JailbreakBench | custom | custom | mit | en | model_graded | card | high | 越狱攻击成功率判分;安全类;MIT HF核实 |
| 93 | MMMU | custom | custom | apache-2.0 | en | exact_match/model-graded | lmeval-cfg | high | multimodal image+text (doc_to_image); no text-only prototype; apache-2.0 verified |
| 94 | MT-Bench | custom | custom | apache-2.0 | en | model_graded | card | med | 多轮LLM裁判评分;prompts+FastChat均Apache-2.0核实 |
| 95 | MTEB | custom | custom | apache-2.0 | multi | mixed(ndcg/accuracy/spearman/v-measure) | doc | med | 聚合嵌入基准(检索+分类+聚类+STS)；license 经 GitHub 验证 |
| 96 | MathVista | custom | custom | cc-by-sa-4.0 | multi | exact_match/model_graded | card | med | 多模态视觉数学(image+text)，超五原型范围 |
| 97 | OSWorld | custom | custom | apache-2.0 | en | execution | doc | med | 桌面GUI agent交互环境,多步轨迹按环境状态判分;Apache-2.0 GitHub核实 |
| 98 | RewardBench | custom | custom | odc-by | en | pairwise | card | high | 奖励模型成对偏好chosen>rejected准确率;odc-by HF核实 |
| 99 | SWE-agent (agent tasks) | custom | custom | mit | en | execution | doc | med | agentic多轮修复轨迹跑仓库测试,非单步diff;MIT GitHub核实 |
| 100 | SWE-bench Multimodal | custom | custom | unknown | en | execution | hf-info | med | 补丁+跑测本可入 patch_repair,但 features 含 image_assets 多模态超范围 |
| 101 | ToolBench | custom | custom | apache-2.0 | en | model_graded(pass/win rate) | doc | med | API 工具调用，ToolEval 模型评判；license 经 GitHub 验证 |
| 102 | VisualWebArena | custom | custom | mit | en | task_success | doc | med | 多模态网页 agent，交互式；license 经 GitHub 验证 |
| 103 | WebArena | custom | custom | apache-2.0 | en | task_success | doc | med | 真实网站交互环境，程序化奖励；license 经 GitHub 验证 |
| 104 | WebShop | custom | custom | mit | en | execution | doc | med | 购物交互环境,多步动作按reward判分;MIT GitHub核实 |
| 105 | XSTest | custom | custom | cc-by-4.0 | en | model_graded | card | high | 过度拒绝判错误拒答;安全类;CC-BY-4.0 HF核实 |
| 106 | tau-bench | custom | custom | mit | en | success_rate(pass^k) | doc | med | 工具+用户模拟多轮对话；license 经 GitHub 验证 |

## 边界（如实）

- **桌面 schema 分析**，非实测全适配——full/partial 是「schema 层可容纳」判断，实建可能暴露细节损失（A2 纵深才实建全适配 + 接入成本表）。
- **置信度非均一**：70 高（lm-eval 配置/HF 核验）/ 35 中 / 1 低（文档知识）；低置信与部分 `card`/`doc` 行需外部复核。

- **许可从严**：22 个未声明→`unknown`；采用前须逐一核实上游许可（本表不构成许可意见）。

- **名单策展**：100+ 是量级目标；lm-eval 14222 子任务归并到家族有判断成分（归并规则见 `scripts/census_seed.py`）；custom 候选系**故意纳入以暴露缺口**，非随机抽样，故容纳率是「主流集」口径而非「全体评测集」。


---
*生成：`scripts/census_render.py` 读 `docs/coverage-map.rows.json`（Task 2 grounded 分析+核验产物，入库可审计）。可复现。*

