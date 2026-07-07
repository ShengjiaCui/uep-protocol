"""适配器注册表——已接入格式名的**唯一合法居所**。

禁名 lint（tests/test_no_dataset_names.py，FR-2.6）以本注册表动态生成黑名单，
扫描 touchstones/ 与 uep/（本目录除外）源码；协议核心出现任何注册表内的
格式名即视为耦合缺陷。新增适配器 = 注册表加一行 + mappings/ 加一张表。
"""

from dataclasses import dataclass
from pathlib import Path

from uep.adapters.engine import LoadedMapping

_MAPPINGS_DIR = Path(__file__).parent / "mappings"


@dataclass(frozen=True)
class AdapterInfo:
    name: str  # 规范名，也是禁名词干
    mapping_file: str | None  # mappings/ 下的映射表文件名；纯导出渲染器为 None
    module: str  # 适配器模块路径
    aliases: tuple[str, ...] = ()  # 额外禁名词（同一格式的别写法）


REGISTRY: tuple[AdapterInfo, ...] = (
    AdapterInfo("mmlu", "mmlu.yaml", "uep.adapters.mmlu"),
    AdapterInfo(
        "mmlu_pro", "mmlu_pro.yaml", "uep.adapters.mmlu_pro", aliases=("mmlu-pro", "mmlu_pro")
    ),
    AdapterInfo("medmcqa", "medmcqa.yaml", "uep.adapters.medmcqa"),
    AdapterInfo("svamp", "svamp.yaml", "uep.adapters.svamp"),
    AdapterInfo(
        "math",
        "math.yaml",
        "uep.adapters.hendrycks_math",
        aliases=("hendrycks_math", "hendrycks-math", "competition_math"),
    ),
    AdapterInfo("arc", "arc.yaml", "uep.adapters.arc", aliases=("ai2_arc", "ai2-arc")),
    AdapterInfo("hellaswag", "hellaswag.yaml", "uep.adapters.hellaswag"),
    AdapterInfo(
        "openai_evals",
        "openai_evals.yaml",
        "uep.adapters.openai_evals",
        aliases=("openai-evals", "openai evals"),
    ),
    AdapterInfo(
        "commonsense_qa",
        "commonsense_qa.yaml",
        "uep.adapters.commonsense_qa",
        aliases=("commonsenseqa", "csqa"),
    ),
    AdapterInfo(
        "truthful_qa", "truthful_qa.yaml", "uep.adapters.truthful_qa", aliases=("truthfulqa",)
    ),
    AdapterInfo("gsm8k", "gsm8k.yaml", "uep.adapters.gsm8k"),
    AdapterInfo(
        "humaneval",
        "humaneval.yaml",
        "uep.adapters.humaneval",
        aliases=("human-eval", "human_eval", "openai_humaneval"),
    ),
    AdapterInfo("mbpp", "mbpp.yaml", "uep.adapters.mbpp"),
    AdapterInfo(
        "swebench",
        "swebench.yaml",
        "uep.adapters.swebench",
        aliases=("swe-bench", "swe_bench", "swe-bench_lite", "swe-bench-lite"),
    ),
    AdapterInfo("scifact", "scifact.yaml", "uep.adapters.scifact", aliases=("beir-scifact",)),
    AdapterInfo(
        "nfcorpus", "nfcorpus.yaml", "uep.adapters.nfcorpus", aliases=("beir-nfcorpus", "nf_corpus")
    ),
    AdapterInfo(
        "t2ranking",
        "t2ranking.yaml",
        "uep.adapters.t2ranking",
        aliases=("t2-ranking", "t2_ranking", "t2retrieval"),
    ),
    # 用户自带表格数据：列名运行时给定，映射表运行时构建（无静态映射文件）
    AdapterInfo("csv", None, "uep.adapters.csv_qa"),
    AdapterInfo(
        "ceval", "ceval.yaml", "uep.adapters.ceval", aliases=("c-eval", "c_eval", "ceval-exam")
    ),
    # 运行器导出目标：prompt/样本为组合渲染而非字段对应，无可诚实声明的映射表
    AdapterInfo(
        "lmeval",
        None,
        "uep.adapters.lmeval",
        aliases=("lm_eval", "lm-eval", "lm eval", "lm-evaluation-harness"),
    ),
    AdapterInfo("inspect_ai", None, "uep.adapters.inspect_ai", aliases=("inspect-ai", "inspectai")),
)


def banned_format_names() -> frozenset[str]:
    """禁名 lint 黑名单（小写）——从注册表动态生成，不手写。"""
    names: set[str] = set()
    for info in REGISTRY:
        names.add(info.name.lower())
        names.update(alias.lower() for alias in info.aliases)
    return frozenset(names)


def load_mapping(name: str) -> LoadedMapping:
    """按注册名加载映射表（含内容哈希）。"""
    for info in REGISTRY:
        if info.name == name:
            if info.mapping_file is None:
                raise KeyError(f"适配器 {name!r} 是导出渲染器，无映射表")
            return LoadedMapping.from_file(_MAPPINGS_DIR / info.mapping_file)
    raise KeyError(f"未注册的适配器: {name!r}")
