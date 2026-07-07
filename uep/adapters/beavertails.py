"""BeaverTails（PKU-Alignment/BeaverTails）↔ UEP choices 适配器（回答安全判定）。

替代 GPQA（gated）；新信号=安全域。CC-BY-NC→从严无 golden。见 mappings/beavertails.yaml。
"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "PKU-Alignment/BeaverTails"
_NAME = "beavertails"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
