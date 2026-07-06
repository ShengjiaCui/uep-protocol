"""NFR-1（SPEC §10，旧 NFR3 承接，2026-07-05 用户裁决）：
1 万条 qa 级 CSV 的库层转换（导入 + 落盘）必须 < 3 秒。

2026-07-05 实测：CLI 全链每动词 <0.4s（含解释器启动）——8 倍余量；
本测试守的是数量级回归线，不追求微基准精度。
"""

import csv
import time

import pytest

from uep.adapters.csv_qa import import_csv
from uep.dataset_io import write_dataset

N_ROWS = 10_000
BUDGET_S = 3.0


@pytest.mark.nfr("NFR-1")
def test_ten_thousand_row_csv_converts_under_three_seconds(tmp_path):
    src = tmp_path / "big.csv"
    with src.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["question", "answer"])
        writer.writeheader()
        writer.writerows(
            {"question": f"第 {i} 题：{i} 加 {i} 等于多少？", "answer": str(i + i)}
            for i in range(N_ROWS)
        )

    start = time.perf_counter()
    items = import_csv(src, content_lang="zh-CN")
    write_dataset(items, tmp_path / "ds", name="bench", license="unknown")
    elapsed = time.perf_counter() - start

    assert len(items) == N_ROWS
    assert elapsed < BUDGET_S, f"1 万条转换耗时 {elapsed:.2f}s ≥ {BUDGET_S}s（NFR-1 回归）"
