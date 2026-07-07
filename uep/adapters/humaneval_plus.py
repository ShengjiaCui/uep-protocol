"""HumanEval+（evalplus/humanevalplus）↔ UEP code_generation 适配器；见 mappings/humaneval_plus.yaml。

注册名 humaneval_plus（不用 "humaneval+"：加号会破坏禁名 lint 的 \\b 词边界匹配）。
"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "evalplus/humanevalplus"
_NAME = "humaneval_plus"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
