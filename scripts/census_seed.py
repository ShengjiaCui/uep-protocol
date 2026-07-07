#!/usr/bin/env python3
"""A2 普查种子名单生成器（只读研究脚本，不属协议包，不改 uep/）。

策展 ~100 个主流评测集家族（领域知识给出真实 benchmark 名 + 初判原型 + 来源），
交叉核对 lm-eval 是否覆盖（覆盖者 Task 2 读本地任务 YAML 的 output_type 做高置信 grounding；
未覆盖者走 HF /info 或文档知识）。产出 docs/coverage-map.seed.json 供 Task 2 分批分析。

初判原型仅为种子——最终原型/吻合度/许可/语言由 Task 2 grounded 核定。lm_key 为在 lm-eval
groups+subtasks 里检索该家族的子串（None=预期不在 lm-eval）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 策展列表：(name, prototype_guess, lm_key, sources, note)
# sources 为初判（lmeval 由脚本核定覆盖；inspect/helm/hf 系知识标注，Task 2 可调）
SEED: list[tuple] = [
    # ---- choices（多选题）----
    ("MMLU", "choices", "mmlu", "lmeval,helm,hf", "57 学科 4 选一"),
    ("MMLU-Pro", "choices", "mmlu_pro", "lmeval,hf", "10 选一加强版"),
    ("MMLU-Redux", "choices", "mmlu_redux", "lmeval,hf", "去噪重标"),
    ("ARC-Easy", "choices", "arc_easy", "lmeval,helm,hf", "小学科学"),
    ("ARC-Challenge", "choices", "arc_challenge", "lmeval,helm,hf", "难科学"),
    ("HellaSwag", "choices", "hellaswag", "lmeval,helm,hf", "常识续写 4 选一"),
    ("PIQA", "choices", "piqa", "lmeval,helm,hf", "物理常识"),
    ("Winogrande", "choices", "winogrande", "lmeval,helm,hf", "指代消解二选一"),
    ("OpenBookQA", "choices", "openbookqa", "lmeval,helm,hf", "开卷科学"),
    ("CommonsenseQA", "choices", "commonsense_qa", "lmeval,hf", "常识 5 选一"),
    ("BoolQ", "choices", "boolq", "lmeval,helm,hf", "是非题"),
    ("Social IQa", "choices", "siqa", "lmeval,hf", "社会常识"),
    ("RACE", "choices", "race", "lmeval,helm,hf", "阅读理解 4 选一"),
    ("SciQ", "choices", "sciq", "lmeval,hf", "科学选择"),
    ("LogiQA", "choices", "logiqa", "lmeval,hf", "逻辑推理"),
    ("QASC", "choices", "qasc", "lmeval,hf", "科学多跳选择"),
    ("MedMCQA", "choices", "medmcqa", "lmeval,hf", "医学多选"),
    ("MedQA (USMLE)", "choices", "medqa", "lmeval,hf", "医考选择"),
    ("GPQA", "choices", "gpqa", "lmeval,hf", "研究生级抗搜索"),
    ("TruthfulQA-MC", "choices", "truthfulqa_mc", "lmeval,helm,hf", "真实性多选"),
    ("AGIEval", "choices", "agieval", "lmeval,hf", "人类考试多选为主"),
    ("BBH", "choices", "bbh", "lmeval,helm,hf", "BIG-Bench-Hard 混合"),
    ("ANLI", "choices", "anli", "lmeval,helm,hf", "对抗 NLI 三分类"),
    ("MathQA", "choices", "mathqa", "lmeval,hf", "数学多选"),
    ("HeadQA", "choices", "headqa", "lmeval,hf", "西班牙医考"),
    ("C-Eval", "choices", "ceval", "lmeval,hf", "中文 52 学科"),
    ("CMMLU", "choices", "cmmlu", "lmeval,hf", "中文 67 学科"),
    ("GAOKAO-Bench", "choices", "gaokao", "hf", "中文高考"),
    ("XCOPA", "choices", "xcopa", "lmeval,hf", "跨语言因果二选"),
    ("Belebele", "choices", "belebele", "lmeval,hf", "122 语阅读多选"),
    ("MMMU", "custom", "mmmu", "hf,helm", "多模态多选(图文)——超本轮范围"),
    # ---- qa（开放/短答）----
    ("GSM8K", "qa", "gsm8k", "lmeval,helm,hf", "小学数学求解"),
    ("MATH", "qa", "hendrycks_math", "lmeval,helm,hf", "竞赛数学"),
    ("SVAMP", "qa", "svamp", "lmeval,hf", "算术应用题"),
    ("ASDiv", "qa", "asdiv", "lmeval,hf", "算术多样"),
    ("AQuA-RAT", "qa", "aqua", "lmeval,hf", "代数带推理"),
    ("MGSM", "qa", "mgsm", "lmeval,hf", "多语 GSM8K"),
    ("TriviaQA", "qa", "triviaqa", "lmeval,helm,hf", "闭卷事实"),
    ("Natural Questions", "qa", "nq_open", "lmeval,helm,hf", "开放域问答"),
    ("WebQuestions", "qa", "webqs", "lmeval,hf", "知识库问答"),
    ("SQuAD v2", "qa", "squadv2", "lmeval,helm,hf", "抽取式阅读"),
    ("DROP", "qa", "drop", "lmeval,helm,hf", "离散推理阅读"),
    ("CoQA", "qa", "coqa", "lmeval,hf", "对话式问答"),
    ("SimpleQA", "qa", None, "inspect,hf", "OpenAI 短事实问答"),
    ("IFEval", "qa", "ifeval", "lmeval,inspect,hf", "指令遵循可验证约束"),
    ("MuSR", "qa", "musr", "lmeval,hf", "多步软推理"),
    ("LAMBADA", "qa", "lambada", "lmeval,hf", "末词预测"),
    ("TyDi QA", "qa", "tydiqa", "lmeval,hf", "多语问答"),
    ("MathVista", "custom", None, "hf", "多模态数学——超本轮范围"),
    # ---- code_generation ----
    ("HumanEval", "code_generation", "humaneval", "lmeval,inspect,hf", "函数补全 pass@k"),
    ("HumanEval+", "code_generation", "humanevalplus", "lmeval,hf", "加测例"),
    ("MBPP", "code_generation", "mbpp", "lmeval,inspect,hf", "入门 Python"),
    ("MBPP+", "code_generation", "mbppplus", "lmeval,hf", "加测例"),
    ("APPS", "code_generation", "apps", "hf", "竞赛难度"),
    ("DS-1000", "code_generation", None, "hf", "数据科学补全"),
    ("LiveCodeBench", "code_generation", None, "hf", "防污染滚动"),
    ("BigCodeBench", "code_generation", None, "hf", "复杂库调用"),
    ("MultiPL-E", "code_generation", None, "hf", "多语言 HumanEval"),
    ("HumanEval-X", "code_generation", None, "hf", "多语代码(含中文)"),
    ("ClassEval", "code_generation", None, "hf", "类级生成"),
    ("CodeContests", "code_generation", None, "hf", "编程竞赛"),
    ("Spider", "custom", None, "hf,helm", "text-to-SQL——DB 执行,原型待判"),
    ("MBXP", "code_generation", None, "hf", "多语执行基准"),
    # ---- patch_repair ----
    ("SWE-bench", "patch_repair", None, "inspect,hf", "仓库级补丁"),
    ("SWE-bench Lite", "patch_repair", None, "inspect,hf", "轻量子集"),
    ("SWE-bench Verified", "patch_repair", None, "inspect,hf", "人工验证子集"),
    ("SWE-bench Multimodal", "custom", None, "hf", "含图 UI——超范围"),
    ("Defects4J", "patch_repair", None, "hf", "Java 缺陷修复"),
    ("QuixBugs", "patch_repair", None, "hf", "单行缺陷多语"),
    ("BugsInPy", "patch_repair", None, "hf", "Python 真实缺陷"),
    # ---- retrieval ----
    ("BEIR-SciFact", "retrieval", None, "hf", "科学核查检索"),
    ("BEIR-NFCorpus", "retrieval", None, "hf", "医学检索"),
    ("BEIR-FiQA", "retrieval", None, "hf", "金融观点检索"),
    ("BEIR-TREC-COVID", "retrieval", None, "hf", "COVID 检索"),
    ("BEIR-ArguAna", "retrieval", None, "hf", "论点检索"),
    ("BEIR-Touche2020", "retrieval", None, "hf", "论辩检索"),
    ("BEIR-Quora", "retrieval", None, "hf", "重复问题检索"),
    ("BEIR-HotpotQA", "retrieval", None, "hf", "多跳检索"),
    ("MS-MARCO", "retrieval", None, "hf,helm", "段落排序"),
    ("MTEB", "custom", None, "hf", "嵌入多任务(检索+分类+聚类)——聚合基准"),
    ("T2Ranking", "retrieval", None, "hf", "中文段落排序"),
    ("MIRACL", "retrieval", None, "hf", "多语检索"),
    ("DuReader-Retrieval", "retrieval", None, "hf", "中文检索"),
    ("BRIGHT", "retrieval", None, "hf", "推理密集检索"),
    # ---- custom 候选（故意纳入以暴露分类学缺口）----
    ("GAIA", "custom", None, "hf", "通用助手多步工具——agentic 轨迹"),
    ("WebArena", "custom", None, "inspect", "真实网站交互环境"),
    ("VisualWebArena", "custom", None, "hf", "多模态网页 agent"),
    ("AgentBench", "custom", None, "hf", "多环境 agent"),
    ("tau-bench", "custom", None, "inspect", "工具+用户模拟对话"),
    ("ToolBench", "custom", None, "hf", "API 工具调用"),
    ("OSWorld", "custom", None, "hf", "桌面 GUI agent"),
    ("WebShop", "custom", None, "hf", "购物交互环境"),
    ("SWE-agent (agent tasks)", "custom", None, "inspect", "agentic 修复轨迹"),
    ("MT-Bench", "custom", None, "inspect,hf", "多轮成对/评分——LLM 裁判"),
    ("Arena-Hard", "custom", None, "hf", "成对偏好胜率"),
    ("RewardBench", "custom", None, "hf", "奖励模型成对偏好"),
    ("AlpacaEval 2", "custom", None, "hf", "长度校正胜率"),
    ("Chatbot Arena", "custom", None, "hf", "人类成对投票 Elo"),
    ("HarmBench", "custom", None, "hf", "红队有害行为"),
    ("JailbreakBench", "custom", None, "hf", "越狱鲁棒性"),
    ("XSTest", "custom", None, "hf", "过度拒绝安全"),
    ("RULER", "custom", None, "hf", "长上下文合成——退化 qa 但长度维度"),
    ("LongBench", "custom", None, "hf", "长上下文多任务(中英)"),
    ("Needle-in-Haystack", "custom", None, "hf", "长上下文检索合成"),
    ("AIME 2024", "qa", None, "inspect,hf", "竞赛数学短答"),
    ("USACO", "custom", None, "hf", "算法竞赛带交互/多步"),
]


def _lm_index() -> set[str]:
    from lm_eval import tasks

    tm = tasks.TaskManager()
    names = set(tm.all_tasks) | set(tm.all_groups) | set(tm.all_tags) | set(tm.all_subtasks)
    return {n.lower() for n in names}


def main() -> int:
    lm_names = _lm_index()

    def lm_hit(key):
        """定位 lm-eval 里该家族的规范名（供 Task 2 读配置）。

        优先级：精确 == key > 干净前缀（key 后接 _/- 或结尾，如 mmlu_pro/ceval-valid）
        > 最短 containing。避免子串误命中本地化变体（如 cmmlu 误中 arabi[cmmlu]）。
        """
        if not key:
            return None
        k = key.lower()
        cands = [n for n in lm_names if k in n]
        if not cands:
            return None
        exact = [n for n in cands if n == k]
        if exact:
            return exact[0]
        prefix = sorted(
            (n for n in cands if n.startswith(k) and (len(n) == len(k) or n[len(k)] in "_-")),
            key=len,
        )
        if prefix:
            return prefix[0]
        return min(cands, key=len)  # 最短 containing（最不像本地化变体）

    rows = []
    for name, proto, lm_key, sources, note in SEED:
        hit = lm_hit(lm_key)
        src = set(sources.split(","))
        if hit:
            src.add("lmeval")
        else:
            src.discard("lmeval")  # 未在 lm-eval 就不谎称
        rows.append(
            {
                "name": name,
                "prototype_guess": proto,
                "sources": sorted(src),
                "lmeval_task": hit,  # None=不在 lm-eval, Task 2 走 HF/文档
                "note": note,
            }
        )

    out = ROOT / "docs" / "coverage-map.seed.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter

    protos = Counter(r["prototype_guess"] for r in rows)
    in_lm = sum(1 for r in rows if r["lmeval_task"])
    print(f"种子集数: {len(rows)} → {out}")
    print(f"初判原型分布: {dict(protos)}")
    print(f"lm-eval 可 grounding: {in_lm}/{len(rows)}（其余走 HF/文档）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
