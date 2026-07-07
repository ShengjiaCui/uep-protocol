"""MMLU-Pro（TIGER-Lab/MMLU-Pro）↔ UEP choices 适配器；字段对应见 mappings/mmlu_pro.yaml。"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "TIGER-Lab/MMLU-Pro"
_NAME = "mmlu_pro"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
