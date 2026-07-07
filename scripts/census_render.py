#!/usr/bin/env python3
"""A2 覆盖地图渲染器（只读研究脚本，不属协议包）。

build/coverage-rows.json（Task 2 grounded 分析 + 核验产物）→ docs/coverage-map.md。
数据部分（统计/106 行表/缺口聚类）由行机械生成，散文部分为常量——全文可从行复现。
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "docs" / "coverage-map.rows.json"  # Task 2 grounded 分析+核验产物（入库可审计）
OUT = ROOT / "docs" / "coverage-map.md"

#: custom 集按缺口主题聚类（判断成分，集中此处可复核）
GAP_THEME = {
    "MMMU": "多模态",
    "MathVista": "多模态",
    "SWE-bench Multimodal": "多模态",
    "VisualWebArena": "多模态+agent",
    "GAIA": "agentic 多步/工具",
    "WebArena": "交互环境",
    "AgentBench": "agentic 多环境",
    "tau-bench": "工具+用户模拟",
    "ToolBench": "工具调用",
    "OSWorld": "GUI agent",
    "WebShop": "交互环境",
    "SWE-agent (agent tasks)": "agentic 轨迹",
    "MT-Bench": "成对/评分裁判",
    "Arena-Hard": "成对偏好",
    "RewardBench": "成对偏好",
    "AlpacaEval 2": "成对偏好",
    "Chatbot Arena": "人类成对投票",
    "HarmBench": "安全/红队",
    "JailbreakBench": "安全/红队",
    "XSTest": "安全/过度拒绝",
    "MTEB": "聚合基准(嵌入多任务)",
}
PROTO_ORDER = ["choices", "qa", "code_generation", "patch_repair", "retrieval", "custom"]


def bar(counter, keys=None):
    keys = keys or sorted(counter, key=lambda k: -counter[k])
    return " / ".join(f"{k} {counter[k]}" for k in keys if counter.get(k))


def main() -> int:
    rows = json.loads(ROWS.read_text(encoding="utf-8"))
    n = len(rows)
    fit = Counter(r["fit"] for r in rows)
    proto = Counter(r["prototype"] for r in rows)
    conf = Counter(r["confidence"] for r in rows)
    ground = Counter(r["grounding"] for r in rows)
    housed = fit["full"] + fit["partial"]

    lang = Counter()
    for r in rows:
        lang[r["languages"]] += 1
    lic = Counter(r["license"] for r in rows)

    L = []
    L.append("# UEP 覆盖地图：100+ 主流评测集普查（2026-07）\n")
    L.append(
        "> 对 **{n} 个主流评测集**做**桌面 schema 层普查**（不建适配、不下数据切片）：逐集判定归入\n"
        "> 哪个 UEP 原型、吻合度、许可、语言、判分类型，**每行标 grounding 依据与置信度**。\n"
        "> **头条**：**{housed}/{n}（{pct:.0f}%）可被五原型 full+partial 容纳**，{cus}/{n}（{cpct:.0f}%）\n"
        "> 现有原型装不下（=分类学缺口，演进机制燃料）。\n".format(
            n=n,
            housed=housed,
            pct=100 * housed / n,
            cus=fit["custom"],
            cpct=100 * fit["custom"] / n,
        )
    )
    L.append("\n## 方法与诚实声明\n")
    L.append(
        "- **样本口径（读 80% 前必看）**：名单是**策展的主流集**，且**故意纳入** agentic/偏好/"
        "多模态等 custom 候选以暴露缺口——故容纳率是「主流集」口径、**非随机抽样、非全体评测集**"
        "（且故意纳入已知缺口是往下压容纳率、非抬高）。\n"
        "- **grounding 优先级**：① lm-eval 任务 YAML 的 `output_type`（本地离线、高置信）→ "
        "② HF datasets-server `/info` features + 卡片 → ③ 数据集卡 cardData → ④ 文档知识（低置信）。\n"
        "- **许可从严**：以卡片实际声明为准，**未声明=`unknown`**，绝不猜许可以求好看。\n"
        "- 每行经**独立核验相**复查（`full`/`custom` 判定与 `license` 逐一回查——防幻觉）。\n"
        "- 这是**桌面 schema 分析**，非实测适配（全适配是 A2 纵深）；置信度非均一，如下分布。\n"
    )
    L.append("\n## 容纳率与分布\n")
    L.append("| 维度 | 分布 |\n|------|------|")
    L.append(
        f"| 吻合度 | **full {fit['full']} / partial {fit['partial']} / custom {fit['custom']}**（容纳 {housed}/{n}={100*housed/n:.0f}%） |"
    )
    L.append(f"| 归入原型 | {bar(proto, PROTO_ORDER)} |")
    L.append(f"| 语言 | {bar(lang)} |")
    L.append(f"| 置信度 | {bar(conf, ['high','med','low'])} |")
    L.append(f"| grounding 依据 | {bar(ground, ['lmeval-cfg','hf-info','card','doc'])} |")
    L.append(f"| 许可 | unknown {lic['unknown']}（从严）；其余见下表逐行 |")

    # 缺口聚类
    L.append("\n## 分类学缺口（21 个 custom → SPEC §8 演进候选）\n")
    L.append(
        "现有五原型装不下的集，按缺失能力聚类——每类是协议演进的燃料（本轮只登记，不改 SPEC）：\n"
    )
    theme_members = {}
    for r in rows:
        if r["fit"] == "custom":
            t = GAP_THEME.get(r["name"], "其他")
            theme_members.setdefault(t, []).append(r["name"])
    theme_gap = {
        "多模态": "题面/答案含图像——原型均为纯文本表示",
        "多模态+agent": "多模态 + 交互环境双重缺口",
        "agentic 多步/工具": "多轮工具调用轨迹 + 环境状态——退化 QA 装不下",
        "交互环境": "有状态环境交互（点击/购物/浏览），非静态样本",
        "agentic 多环境": "跨环境 agent 轨迹",
        "工具+用户模拟": "工具调用 + 模拟用户多轮",
        "工具调用": "API 工具调用序列判分",
        "GUI agent": "桌面/GUI 操作序列",
        "agentic 轨迹": "仓库级 agent 修复轨迹（非单 patch）",
        "成对/评分裁判": "成对/多轮 LLM 裁判，无单一正解",
        "成对偏好": "成对偏好胜率，判分=偏好而非对错",
        "人类成对投票": "人类成对投票 Elo，无固定黄金",
        "安全/红队": "有害行为判定，判分=行为分类器/裁判",
        "安全/过度拒绝": "过度拒绝安全，判分语义特殊",
        "聚合基准(嵌入多任务)": "多任务聚合（检索+分类+聚类），非单原型",
    }
    for t in sorted(theme_members, key=lambda x: -len(theme_members[x])):
        gap = theme_gap.get(t, "")
        L.append(
            f"- **{t}**（{len(theme_members[t])}）：{', '.join(theme_members[t])} — 缺口：{gap}"
        )
    L.append(
        "\n**共性**：五原型是**静态样本 → 判分**的形态；缺口集中在 **agentic 轨迹/交互环境**、"
        "**成对偏好**、**多模态**、**安全/红队**四大类。这与 goals 的「表达力上限=Agent 任务空间」一致——"
        "环境/轨迹/复合验证在骨架里（CustomTask+CompositeVerifier 是逃生舱），但**尚无一等原型**，"
        "正是演进机制该逐个转化的燃料。\n"
    )

    # 106 行表
    L.append(f"\n## 逐集普查表（{n} 行）\n")
    L.append("| # | 集 | 原型 | 吻合 | 许可 | 语言 | 判分 | 依据 | 置信 | 备注 |")
    L.append("|--:|----|------|------|------|------|------|------|------|------|")
    ordered = sorted(rows, key=lambda r: (PROTO_ORDER.index(r["prototype"]), r["fit"], r["name"]))
    for i, r in enumerate(ordered, 1):
        note = r["notes"].replace("|", "/").replace("\n", " ")
        lic_disp = r["license"].lower()  # SPDX id 显示统一小写（agents 返回大小写不一）
        L.append(
            f"| {i} | {r['name']} | {r['prototype']} | {r['fit']} | {lic_disp} | "
            f"{r['languages']} | {r['scoring']} | {r['grounding']} | {r['confidence']} | {note} |"
        )

    L.append("\n## 边界（如实）\n")
    L.append(
        "- **桌面 schema 分析**，非实测全适配——full/partial 是「schema 层可容纳」判断，实建可能暴露细节损失（A2 纵深才实建全适配 + 接入成本表）。\n"
        "- **置信度非均一**：{high} 高（lm-eval 配置/HF 核验）/ {med} 中 / {low} 低（文档知识）；低置信与部分 `card`/`doc` 行需外部复核。\n".format(
            high=conf["high"], med=conf["med"], low=conf["low"]
        )
    )
    L.append(
        "- **许可从严**：{unk} 个未声明→`unknown`；采用前须逐一核实上游许可（本表不构成许可意见）。\n".format(
            unk=lic["unknown"]
        )
    )
    L.append(
        "- **名单策展**：100+ 是量级目标；lm-eval 14222 子任务归并到家族有判断成分（归并规则见 `scripts/census_seed.py`）；custom 候选系**故意纳入以暴露缺口**，非随机抽样，故容纳率是「主流集」口径而非「全体评测集」。\n"
    )
    L.append(
        "\n---\n*生成：`scripts/census_render.py` 读 `docs/coverage-map.rows.json`（Task 2 grounded 分析+核验产物，入库可审计）。可复现。*\n"
    )

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"写出 {OUT}（{n} 行；容纳 {housed}/{n}={100*housed/n:.0f}%，custom {fit['custom']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
