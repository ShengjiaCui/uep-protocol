"""IFEval（google/IFEval）↔ UEP custom 适配器（指令跟随逃生舱）；见 mappings/ifeval.yaml。

约束=程序化判据无现有 verifier→custom + schema_ref 挂 §8 提案
（docs/proposals/2026-07-instruction-following.md）。
"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "google/IFEval"
_NAME = "ifeval"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
