"""管理动词的纯操作层（FR-5.1–5.7 的数据语义，无 IO、无文案）。

不可变约定：一律返回新列表，绝不改动传入条目。
用户可见报错文案在 CLI 层（uep/i18n.py），本层只表达数据事实。
"""

import random
from collections import Counter
from collections.abc import Sequence

from uep.schema import EvalItem

_GIST_WIDTH = 40
# 各任务原型的"题面"字段，按判别类型逐一列举（新原型入列时此表须同步）
_GIST_FIELDS = ("question", "prompt", "problem_statement", "query", "schema_ref")


def item_gist(item: EvalItem, width: int = _GIST_WIDTH) -> str:
    """单条目的一行摘要（list 动词用）：题面压平空白后截断。"""
    for name in _GIST_FIELDS:
        value = getattr(item.task, name, None)
        if value:
            text = " ".join(str(value).split())
            return text if len(text) <= width else text[: width - 1] + "…"
    return ""


def lang_matches(tag: str, query: str) -> bool:
    """BCP-47 基本过滤（RFC 4647）：``zh`` 命中 ``zh`` 与 ``zh-CN``，不命中 ``zho``。"""
    tag_low, query_low = tag.lower(), query.lower()
    return tag_low == query_low or tag_low.startswith(query_low + "-")


def filter_items(
    items: Sequence[EvalItem], *, task_type: str | None = None, lang: str | None = None
) -> list[EvalItem]:
    """谓词 AND 组合筛选；谓词全空时原样返回（是否拒绝由 CLI 层裁决）。"""

    def keep(item: EvalItem) -> bool:
        if task_type is not None and item.task.type != task_type:
            return False
        if lang is not None and not any(lang_matches(tag, lang) for tag in item.lang):
            return False
        return True

    return [item for item in items if keep(item)]


def slice_items(items: Sequence[EvalItem], start: int, stop: int) -> list[EvalItem]:
    """半开区间 [start, stop)，Python 切片语义（stop 越界宽容截断）。"""
    return list(items[start:stop])


def sample_items(items: Sequence[EvalItem], n: int, seed: int) -> list[EvalItem]:
    """定 seed 随机抽 n 条，按原库顺序返回（可复现 + 保序，n 合法性由 CLI 层把关）。"""
    indices = sorted(random.Random(seed).sample(range(len(items)), n))
    return [items[i] for i in indices]


def merge_items(groups: Sequence[Sequence[EvalItem]]) -> tuple[list[EvalItem], list[str]]:
    """顺序合并，返回 (合并结果, 冲突 id 清单)——冲突绝不静默去重，处置权在 CLI 层。"""
    seen: set[str] = set()
    merged: list[EvalItem] = []
    conflicts: list[str] = []
    for group in groups:
        for item in group:
            if item.id in seen:
                conflicts.append(item.id)
            else:
                seen.add(item.id)
                merged.append(item)
    return merged, sorted(set(conflicts))


def dataset_stats(items: Sequence[EvalItem]) -> dict[str, Counter]:
    """三个分布：任务类型 / 语言标签 / 验证器类型（size 由 len 直接得）。"""
    return {
        "task_types": Counter(item.task.type for item in items),
        "languages": Counter(tag for item in items for tag in item.lang),
        "verifiers": Counter(v.type for item in items for v in item.verifiers),
    }
