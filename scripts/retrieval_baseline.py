#!/usr/bin/env python3
"""retrieval 判分闭环：BM25 基线实跑 → 用 UEP retrieval Verifier 载荷算 ndcg@10。

实验脚本（Runner 侧）：检索系统与 ndcg 实现都不属于协议包。
用法：
    .venv/bin/python scripts/retrieval_baseline.py --slice scifact
    .venv/bin/python scripts/retrieval_baseline.py --slice t2ranking   # 先建池（build_t2r_pool.py）
"""

import argparse
import hashlib
import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402  （随 rank-bm25 就位）
from rank_bm25 import BM25Okapi  # noqa: E402

from uep.adapters import scifact as scifact_adapter  # noqa: E402
from uep.adapters import t2ranking as t2ranking_adapter  # noqa: E402

CORPUS_DIR = ROOT / "data" / "corpus"
DS_SERVER = "https://datasets-server.huggingface.co/rows"
PAGE_PAUSE_S = 0.5  # 页间礼貌限速：连发分页会触发 datasets-server 限流
RETRY_DELAYS_S = (5, 10, 20, 40, 80)  # 429/5xx/瞬断指数退避（单页最多重试 5 次）


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "uep-retrieval-baseline/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return resp.read()


def _get_with_retry(url: str) -> bytes:
    """单页取数：429/5xx 与瞬断（URLError/SSL EOF）按 RETRY_DELAYS_S 退避重试，超限抛出。"""
    for delay in RETRY_DELAYS_S:
        try:
            return _get(url)
        except (urllib.error.URLError, ssl.SSLEOFError) as exc:
            is_retryable_http = isinstance(exc, urllib.error.HTTPError) and (
                exc.code == 429 or exc.code >= 500
            )
            if isinstance(exc, urllib.error.HTTPError) and not is_retryable_http:
                raise
            time.sleep(delay)
    return _get(url)


def _all_rows(dataset: str, config: str, split: str) -> list[dict]:
    rows, offset = [], 0
    while True:
        query = urllib.parse.urlencode(
            {
                "dataset": dataset,
                "config": config,
                "split": split,
                "offset": offset,
                "length": 100,
            }
        )
        payload = json.loads(_get_with_retry(f"{DS_SERVER}?{query}"))
        page = payload["rows"]
        rows.extend(r["row"] for r in page)
        if not page or offset + len(page) >= payload["num_rows_total"]:
            return rows
        offset += len(page)
        time.sleep(PAGE_PAUSE_S)


def load_slice(name: str) -> list[dict]:
    lock = json.loads((ROOT / "scripts" / "slices.lock.json").read_text(encoding="utf-8"))[name]
    raw = (ROOT / "data" / "real" / f"{name}.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest() != lock["sha256"]:
        raise RuntimeError(f"{name}: 切片与锁不符")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def ensure_scifact_corpus() -> list[dict]:
    cache = CORPUS_DIR / "scifact.jsonl"
    if not cache.exists():
        CORPUS_DIR.mkdir(parents=True, exist_ok=True)
        rows = _all_rows("BeIR/scifact", "corpus", "corpus")
        cache.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
    return [
        json.loads(line) for line in cache.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def tokenize(text: str, lang: str) -> list[str]:
    if lang == "zh":
        import jieba

        return [t for t in jieba.lcut(text) if t.strip()]
    return text.lower().split()


def ndcg_at_k(ranked_doc_ids: list, relevance, k: int = 10) -> float:
    grades = {str(r.doc_id): r.grade for r in relevance}
    got = [grades.get(str(d), 0) for d in ranked_doc_ids[:k]]
    ideal = sorted(grades.values(), reverse=True)[:k]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(got))
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def run(slice_name: str) -> float:
    if slice_name == "scifact":
        items = scifact_adapter.import_rows(load_slice("scifact"))
        corpus = ensure_scifact_corpus()
        doc_ids = [str(r["_id"]) for r in corpus]
        doc_texts = [((r.get("title") or "") + " " + r["text"]) for r in corpus]
        lang = "en"
    else:
        items = t2ranking_adapter.import_rows(load_slice("t2ranking"))
        pool_path = CORPUS_DIR / "t2ranking_pool.jsonl"
        if not pool_path.exists():
            raise SystemExit("缺 t2ranking 候选池：先跑 scripts/build_t2r_pool.py")
        pool = [
            json.loads(line)
            for line in pool_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        doc_ids = [str(r["pid"]) for r in pool]
        doc_texts = [r["text"] for r in pool]
        lang = "zh"

    bm25 = BM25Okapi([tokenize(t, lang) for t in doc_texts])
    scores = []
    for item in items:
        query_scores = bm25.get_scores(tokenize(item.task.query, lang))
        top = np.argsort(query_scores)[::-1][:10]
        ranking = [doc_ids[i] for i in top]
        scores.append(ndcg_at_k(ranking, item.verifiers[0].relevance, k=10))
    return sum(scores) / len(scores)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", choices=["scifact", "t2ranking"], required=True)
    args = parser.parse_args()
    print(f"{args.slice} ndcg@10 = {run(args.slice):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
