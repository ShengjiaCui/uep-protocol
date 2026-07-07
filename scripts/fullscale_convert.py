#!/usr/bin/env python3
"""全量转换规模验证（A2 纵深 Task 3）——整 split（非 100 条切片）过适配器。

量三件事：①规模（整 split 条数，坐实"万级"）②转换吞吐（items/sec）③无损抽验
（首 N 条 import→export 语义等价，确认切片上验证的无损性在全量成立）。
数据本体不入库；摘要 JSON 写 outputs/（gitignored）。

用法：python scripts/fullscale_convert.py mmlu_pro medmcqa
"""

import argparse
import importlib
import json
import time
from pathlib import Path

from fetch_slices import SLICES, _all_rows

from uep.adapters import REGISTRY
from uep.equivalence import diff_paths, normalize_tree

OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
ROUNDTRIP_SAMPLE = 200  # 全量转换 + 抽 N 条无损抽验（全量往返翻倍耗时，抽验足证保形）


def _adapter(name: str):
    for info in REGISTRY:
        if info.name == name:
            return importlib.import_module(info.module)
    raise KeyError(f"未注册适配器: {name}")


def convert_full(name: str) -> dict:
    spec = SLICES[name]
    if spec["kind"] != "hf_rows":
        raise SystemExit(f"{name}: 仅支持 hf_rows 配方的全量转换（当前 {spec['kind']}）")
    adapter = _adapter(name)
    t0 = time.perf_counter()
    rows = _all_rows(spec["dataset"], spec["config"], spec["split"])
    t_fetch = time.perf_counter() - t0

    t1 = time.perf_counter()
    items = adapter.import_rows(rows)
    t_convert = time.perf_counter() - t1

    # 无损抽验（首 N 条）
    sample = rows[:ROUNDTRIP_SAMPLE]
    restored = adapter.export_rows(adapter.import_rows(sample))
    diffs = sum(
        1
        for r, b in zip(sample, restored, strict=True)
        if diff_paths(normalize_tree(r), normalize_tree(b))
    )
    return {
        "dataset": spec["dataset"],
        "split": spec["split"],
        "n_items": len(items),
        "fetch_s": round(t_fetch, 1),
        "convert_s": round(t_convert, 3),
        "items_per_s": round(len(items) / t_convert, 0) if t_convert else None,
        "roundtrip_sample": len(sample),
        "roundtrip_diffs": diffs,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+", help="切片名（须为 hf_rows 配方）")
    args = ap.parse_args()
    results = [convert_full(n) for n in args.names]
    total = sum(r["n_items"] for r in results)
    summary = {"total_items": total, "sets": results}
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "fullscale-2026-07.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for r in results:
        print(
            f"✓ {r['dataset']} {r['split']}: {r['n_items']} 条 / "
            f"转换 {r['convert_s']}s ({r['items_per_s']}/s) / 抽验 {r['roundtrip_diffs']} 差异"
        )
    print(f"合计 {total} 条（数据本体不入库；摘要 outputs/fullscale-2026-07.json）")


if __name__ == "__main__":
    main()
