"""MATH（EleutherAI/hendrycks_math）↔ UEP qa 适配器；字段对应见 mappings/math.yaml。

模块名用 hendrycks_math 而非 math，避开对标准库 ``math`` 的文件名遮蔽；
注册名仍为 "math"（与兄弟适配器同用通行基准名）。
"""

from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

DATASET = "EleutherAI/hendrycks_math"
_NAME = "math"


def import_rows(rows: Iterable[dict[str, Any]]) -> list[EvalItem]:
    return apply_mapping(rows, load_mapping(_NAME), dataset=DATASET, adapter=_NAME)


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（还原义务，SPEC §7.4）。"""
    return invert_mapping(items, load_mapping(_NAME))
