"""RewardBench（allenai/reward-bench）↔ UEP custom 适配器（成对偏好逃生舱）；见 mappings/rewardbench.yaml。

UEP 暂无成对偏好一等原型，走 custom + schema_ref 挂 §8 演进提案
（docs/proposals/2026-07-pairwise-preference.md）。
"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "allenai/reward-bench"
_NAME = "rewardbench"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
