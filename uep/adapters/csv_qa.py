"""CSV（问答两列）→ UEP qa 导入适配器。

列名由用户给定，故映射表在**运行时构建**（仍走同一引擎与算子集，
溯源戳照盖——mapping_hash 对构建出的表求哈希，留痕不豁免）。
"""

import csv
from pathlib import Path

from uep.adapters.engine import LoadedMapping, apply_mapping
from uep.schema import EvalItem


def import_csv(
    path: str | Path,
    *,
    question_col: str = "question",
    answer_col: str = "answer",
    content_lang: str = "en",
    id_prefix: str = "item",
) -> list[EvalItem]:
    source = Path(path)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("CSV 为空或缺表头 / empty CSV or missing header")
    mapping = {
        "format": "csv:qa",
        "version": "1.0.0",
        "table": {"task.question": question_col},
        "transforms": [
            {"op": "const", "target": "task.type", "value": "qa"},
            {"op": "const", "target": "lang", "value": [content_lang]},
            {"op": "format_id", "template": id_prefix + "-{row_idx:04d}"},
            {"op": "text_match_from_ideal", "source": answer_col},
        ],
    }
    loaded = LoadedMapping.from_dict(mapping, name="csv_qa(runtime)")
    return apply_mapping(rows, loaded, dataset=source.name, adapter="csv")
