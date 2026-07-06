"""OpenAI Evals samples ↔ UEP qa 双向适配器；见 mappings/openai_evals.yaml。

样本行 = ``{"input": [chat 消息], "ideal": str | list[str]}``。
上游部分文件是无换行的 JSON 对象串联（非规范 JSONL），read_samples 做增量解码兼容；
导出一律写规范 JSONL。lang 与数据集标识由调用方给出（格式适配器不预设具体数据集）。
"""

import json
from collections.abc import Iterable
from typing import Any

from uep.adapters import load_mapping
from uep.adapters.engine import apply_mapping, invert_mapping
from uep.schema import EvalItem

_NAME = "openai_evals"


def read_samples(text: str) -> list[dict[str, Any]]:
    """解析样本文件：兼容规范 JSONL 与对象串联两种形态。"""
    decoder = json.JSONDecoder()
    rows: list[dict[str, Any]] = []
    pos, length = 0, len(text)
    while pos < length:
        while pos < length and text[pos] in " \t\r\n":
            pos += 1
        if pos >= length:
            break
        obj, pos = decoder.raw_decode(text, pos)
        rows.append(obj)
    return rows


def dump_samples(rows: Iterable[dict[str, Any]]) -> str:
    """导出为规范 JSONL（每行一个对象，UTF-8 原文不转义）。"""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def import_rows(rows: Iterable[dict[str, Any]], *, dataset: str, lang: list[str]) -> list[EvalItem]:
    return apply_mapping(
        rows, load_mapping(_NAME), dataset=dataset, adapter=_NAME, extra_fields={"lang": lang}
    )


def export_rows(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """还原回源行形状（往返义务，FR-3.2）。"""
    return invert_mapping(items, load_mapping(_NAME))
