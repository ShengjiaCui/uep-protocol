"""MIRACL-zh（Hieuman/zh_MIRACL）↔ UEP retrieval 适配器（中文内联对比式）；见 mappings/miracl_zh.yaml。

原 MIRACL queries/qrels gated → 用 zh 再加工版（内联正/负段落）；卡未声明许可，从严无 golden。
"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "Hieuman/zh_MIRACL"
_NAME = "miracl_zh"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
