#!/usr/bin/env python3
"""流式构建 T2Ranking 候选池：全部相关段落 + 每 200 行系统抽样负例（≈1 万条）。

collection.tsv 3.6GB 不落盘不整读：HTTP 流式逐行解析，只留需要的行。
产出 data/corpus/t2ranking_pool.jsonl（gitignored）。诚实边界：这是判分链验证
用的池化候选，不是全量 200 万段落的检索系统工程。
"""

import io
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

URL = "https://huggingface.co/datasets/THUIR/T2Ranking/resolve/main/data/collection.tsv"
OUT = ROOT / "data" / "corpus" / "t2ranking_pool.jsonl"
SAMPLE_EVERY = 200  # ≈2,000,000 / 200 ≈ 10,000 负例


def wanted_pids() -> set[int]:
    slice_path = ROOT / "data" / "real" / "t2ranking.jsonl"
    pids: set[int] = set()
    for line in slice_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pids.update(int(q["corpus-id"]) for q in row["qrels"])
    return pids


def main() -> int:
    need = wanted_pids()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    req = urllib.request.Request(URL, headers={"User-Agent": "uep-t2r-pool/0.1"})
    with (
        urllib.request.urlopen(req, timeout=120) as resp,
        OUT.open("w", encoding="utf-8") as out,  # noqa: S310
    ):
        text = io.TextIOWrapper(resp, encoding="utf-8", newline="")
        next(text)  # 表头 pid\ttext
        for line_no, line in enumerate(text):
            tab = line.find("\t")
            if tab <= 0:
                continue
            pid = int(line[:tab])
            if pid in need or line_no % SAMPLE_EVERY == 0:
                out.write(
                    json.dumps(
                        {"pid": pid, "text": line[tab + 1 :].rstrip("\n")},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                kept += 1
            if kept and kept % 2000 == 0:
                print(f"  kept={kept} line={line_no}", file=sys.stderr)
    print(f"池化完成：{kept} 条 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
