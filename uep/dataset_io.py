"""数据集落盘约定（SPEC §6）：``items.jsonl`` 与 ``manifest.json`` 同目录。

convert 动词（FR-5.9）的核心：条目逐行序列化 + 清单从条目机械汇总
（languages/task_types/size 不手填，杜绝清单与数据漂移）。
"""

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from uep import SUPPORTED_PROTOCOL
from uep.schema import EvalItem, Manifest


def read_items(path: str | Path) -> list[EvalItem]:
    """逐行读入并校验；坏行报行号后抛 ValueError（fail fast）。"""
    items: list[EvalItem] = []
    for line_no, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            items.append(EvalItem.model_validate_json(raw))
        except Exception as exc:
            raise ValueError(f"第 {line_no} 行无效 / line {line_no} invalid: {exc}") from exc
    return items


def write_dataset(
    items: Iterable[EvalItem],
    out_dir: str | Path,
    *,
    name: str,
    license: str,
    contains_pii: bool | None = None,
) -> tuple[Path, Path]:
    """落盘数据集目录，返回 (items 路径, manifest 路径)。"""
    items = list(items)
    if not items:
        raise ValueError("空数据集不落盘 / refusing to write empty dataset")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items_path = out_dir / "items.jsonl"
    items_path.write_text(
        "".join(item.model_dump_json(exclude_none=True) + "\n" for item in items),
        encoding="utf-8",
    )
    manifest = Manifest(
        uep_version=SUPPORTED_PROTOCOL,
        name=name,
        license=license,
        contains_pii=contains_pii,
        languages=sorted({tag for item in items for tag in item.lang}),
        task_types=dict(Counter(item.task.type for item in items)),
        size=len(items),
    )
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            json.loads(manifest.model_dump_json(exclude_none=True)), ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    return items_path, manifest_path
