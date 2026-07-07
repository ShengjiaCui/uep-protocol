#!/usr/bin/env python3
"""下载真实数据集切片（集成层夹具）——脚本+校验和入库，数据本体不入库。

用法：
    python scripts/fetch_slices.py                # 按 slices.lock.json 下载并校验
    python scripts/fetch_slices.py --check        # 只离线校验已有文件（无网络）
    python scripts/fetch_slices.py --update-lock  # 重新下载并改写锁（维护操作，须评审）

切片声明在 SLICES；锁文件记录 sha256/上游修订/许可，测试据此校验完整性。
"""

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "real"
LOCK_PATH = Path(__file__).resolve().parent / "slices.lock.json"
DS_SERVER = "https://datasets-server.huggingface.co/rows"
TIMEOUT_S = 60

#: 切片声明——改这里必须走 --update-lock 并把锁文件变更提交评审
SLICES: dict[str, dict[str, Any]] = {
    "mmlu": {
        "kind": "hf_rows",
        "dataset": "cais/mmlu",
        "config": "all",
        "split": "test",
        "offset": 0,
        "length": 100,
        "license": "MIT",
    },
    "mmlu_pro": {  # A2 纵深：10 选一加强版（TIGER-Lab/MMLU-Pro）
        "kind": "hf_rows",
        "dataset": "TIGER-Lab/MMLU-Pro",
        "config": "default",
        "split": "test",
        "offset": 0,
        "length": 100,
        "license": "MIT",
    },
    "medmcqa": {  # A2 纵深：医学 4 选一（opa–opd 分离字段，cop 索引）
        "kind": "hf_rows",
        "dataset": "openlifescienceai/medmcqa",
        "config": "default",
        "split": "validation",  # test split 不含 cop 标签
        "offset": 0,
        "length": 100,
        "license": "Apache-2.0",
    },
    "svamp": {  # A2 纵深：算术应用题 qa（Answer 即 ideal）
        "kind": "hf_rows",
        "dataset": "ChilleD/SVAMP",
        "config": "default",
        "split": "test",
        "offset": 0,
        "length": 100,
        "license": "MIT",
    },
    "arc": {
        "kind": "hf_rows",
        "dataset": "allenai/ai2_arc",
        "config": "ARC-Challenge",
        "split": "test",
        "offset": 0,
        "length": 100,
        "license": "CC-BY-SA-4.0",
    },
    "hellaswag": {
        "kind": "hf_rows",
        "dataset": "Rowan/hellaswag",
        "config": "default",
        "split": "validation",
        "offset": 0,
        "length": 100,
        "license": "MIT",
    },
    "openai_evals": {
        "kind": "github_lfs",
        "repo": "openai/evals",
        "commit": "8eac7a7de5215c907fbddc30efdaf316913eccdd",
        "path": "evals/registry/data/Chinese_character_riddles/samples.jsonl",
        "license": "MIT",
    },
    "commonsense_qa": {
        "kind": "hf_rows",
        "dataset": "tau/commonsense_qa",
        "config": "default",
        "split": "validation",  # test split 不含 answerKey
        "offset": 0,
        "length": 100,
        "license": "MIT",
    },
    "truthful_qa": {
        "kind": "hf_rows",
        "dataset": "truthfulqa/truthful_qa",
        "config": "multiple_choice",
        "split": "validation",
        "offset": 0,
        "length": 100,
        "license": "Apache-2.0",
    },
    "gsm8k": {
        "kind": "hf_rows",
        "dataset": "openai/gsm8k",
        "config": "main",
        "split": "test",
        "offset": 0,
        "length": 100,
        "license": "MIT",
    },
    "humaneval": {
        "kind": "hf_rows",
        "dataset": "openai/openai_humaneval",
        "config": "openai_humaneval",
        "split": "test",
        "offset": 0,
        "length": 100,  # 全集 164，取前 100 满足集成层门槛
        "license": "MIT",
    },
    "swebench": {
        "kind": "hf_rows",
        "dataset": "princeton-nlp/SWE-bench_Lite",
        "config": "default",
        "split": "test",
        "offset": 0,
        "length": 100,
        # HF 卡片未声明许可（上游 GitHub 仓库 MIT）——按"许可不明确"从严：
        # 本地验证可用，任何内容摘录不入库（无黄金文件）
        "license": "unknown",
    },
    "scifact": {
        "kind": "hf_beir_join",  # BEIR 三表：queries + qrels 连接为自含行；corpus 保持引用式
        "dataset": "BeIR/scifact",
        "queries_split": "queries",
        "qrels_dataset": "BeIR/scifact-qrels",
        "qrels_config": "default",
        "qrels_split": "test",
        "num_queries": 100,
        "license": "CC-BY-SA-4.0",
    },
    "ceval": {
        "kind": "hf_rows_multi",  # 单科 val 均 <100 条，多科并联凑集成层门槛
        "dataset": "ceval/ceval-exam",
        "configs": ["college_economics", "accountant"],
        "split": "val",  # test split 不含 answer
        "min_rows": 100,
        "license": "CC-BY-NC-SA-4.0",  # 仅本地验证用；任何内容摘录不入库
    },
    "t2ranking": {
        # 上游带加载脚本、datasets-server 拒服务 → 直连非 LFS 小 TSV；
        # 二元 qrels 依 TREC 惯例落 score=1；collection（3.6GB）保持引用式不下载
        "kind": "hf_tsv_qrels_join",
        "repo": "THUIR/T2Ranking",
        "queries_path": "data/queries.dev.tsv",  # qid \t text
        "qrels_path": "data/qrels.retrieval.dev.tsv",  # qid \t pid（二元）
        "num_queries": 100,
        "license": "Apache-2.0",
    },
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "uep-fetch-slices/0.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 - https only
        return resp.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hf_revision(dataset: str) -> str:
    info = json.loads(_get(f"https://huggingface.co/api/datasets/{dataset}"))
    return info["sha"]


def _fetch_hf_rows(spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """datasets-server /rows → 规范化 JSONL（sort_keys+ensure_ascii=False，字节可复现）。"""
    query = urllib.parse.urlencode(
        {
            "dataset": spec["dataset"],
            "config": spec["config"],
            "split": spec["split"],
            "offset": spec["offset"],
            "length": spec["length"],
        }
    )
    payload = json.loads(_get(f"{DS_SERVER}?{query}"))
    rows = payload["rows"]
    if len(rows) != spec["length"]:
        raise RuntimeError(f"{spec['dataset']}: 期望 {spec['length']} 行，得到 {len(rows)}")
    truncated = [r["row_idx"] for r in rows if r.get("truncated_cells")]
    if truncated:
        raise RuntimeError(f"{spec['dataset']}: 行 {truncated} 有截断单元格，切片不完整")
    lines = [json.dumps(r["row"], ensure_ascii=False, sort_keys=True) for r in rows]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    return data, {"hf_revision": _hf_revision(spec["dataset"])}


def _rows_for_config(dataset: str, config: str, split: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {"dataset": dataset, "config": config, "split": split, "offset": 0, "length": 100}
    )
    payload = json.loads(_get(f"{DS_SERVER}?{query}"))
    truncated = [r["row_idx"] for r in payload["rows"] if r.get("truncated_cells")]
    if truncated:
        raise RuntimeError(f"{dataset}/{config}: 行 {truncated} 有截断单元格")
    return [r["row"] for r in payload["rows"]]


def _all_rows(dataset: str, config: str, split: str) -> list[dict[str, Any]]:
    """整个 split 分页取全（datasets-server 每页上限 100）。"""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {"dataset": dataset, "config": config, "split": split, "offset": offset, "length": 100}
        )
        payload = json.loads(_get(f"{DS_SERVER}?{query}"))
        page = payload["rows"]
        truncated = [r["row_idx"] for r in page if r.get("truncated_cells")]
        if truncated:
            raise RuntimeError(f"{dataset}/{config}: 行 {truncated} 有截断单元格")
        rows.extend(r["row"] for r in page)
        if not page or offset + len(page) >= payload["num_rows_total"]:
            return rows
        offset += len(page)


def _fetch_hf_beir_join(spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """三表检索结构 → 自含行：qrels 按查询分组 + 查询文本连接（语料保持引用式）。"""
    qrels = _all_rows(spec["qrels_dataset"], spec["qrels_config"], spec["qrels_split"])
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for entry in qrels:
        qid = str(entry["query-id"])
        if qid not in grouped:
            grouped[qid] = []
            order.append(qid)
        grouped[qid].append({"corpus-id": entry["corpus-id"], "score": entry["score"]})
    selected = order[: spec["num_queries"]]
    if len(selected) < spec["num_queries"]:
        raise RuntimeError(
            f"{spec['qrels_dataset']}: 仅 {len(selected)} 个查询 < {spec['num_queries']}"
        )
    queries = {
        str(r["_id"]): r for r in _all_rows(spec["dataset"], "queries", spec["queries_split"])
    }
    rows = []
    for qid in selected:
        source = queries.get(qid)
        if source is None:
            raise RuntimeError(f"{spec['dataset']}: 查询 {qid} 在 queries 表缺失")
        rows.append(
            {"_id": qid, "title": source["title"], "text": source["text"], "qrels": grouped[qid]}
        )
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    return data, {"hf_revision": _hf_revision(spec["dataset"]), "num_queries": len(rows)}


def _fetch_hf_tsv_qrels_join(spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """直连仓内小体量 TSV 的检索三表路线（datasets-server 因加载脚本拒服务时用）。

    qrels（qid\\tpid，二元）按 qid 分组取前 num_queries 个查询连接查询文本；
    二元相关依 TREC 惯例落 score=1；语料保持引用式，不下载 collection。
    行形状与 hf_beir_join 对齐：{_id, text, qrels:[{corpus-id:int, score:int}]}。
    """
    revision = _hf_revision(spec["repo"])
    base = f"https://huggingface.co/datasets/{spec['repo']}/resolve/{revision}"
    qrels_text = _get(f"{base}/{spec['qrels_path']}").decode("utf-8")
    queries_text = _get(f"{base}/{spec['queries_path']}").decode("utf-8")

    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for entry in csv.DictReader(io.StringIO(qrels_text), delimiter="\t"):
        qid = entry["qid"]
        if qid not in grouped:
            grouped[qid] = []
            order.append(qid)
        grouped[qid].append({"corpus-id": int(entry["pid"]), "score": 1})
    selected = order[: spec["num_queries"]]
    if len(selected) < spec["num_queries"]:
        raise RuntimeError(f"{spec['repo']}: 仅 {len(selected)} 个查询 < {spec['num_queries']}")
    queries = {
        row["qid"]: row["text"] for row in csv.DictReader(io.StringIO(queries_text), delimiter="\t")
    }
    rows = []
    for qid in selected:
        text = queries.get(qid)
        if not text:
            raise RuntimeError(f"{spec['repo']}: 查询 {qid} 在 queries 表缺失或为空")
        rows.append({"_id": qid, "text": text, "qrels": grouped[qid]})
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    return data, {"hf_revision": revision, "num_queries": len(rows)}


def _fetch_hf_rows_multi(spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """多 config 并联切片（各 config 全量 ≤100 行，按声明顺序拼接）。"""
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for config in spec["configs"]:
        config_rows = _rows_for_config(spec["dataset"], config, spec["split"])
        counts[config] = len(config_rows)
        rows.extend(config_rows)
    if len(rows) < spec["min_rows"]:
        raise RuntimeError(f"{spec['dataset']}: 并联后 {len(rows)} 行 < {spec['min_rows']}")
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    return data, {"hf_revision": _hf_revision(spec["dataset"]), "config_counts": counts}


def _fetch_github_lfs(spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """GitHub LFS 媒体端点，按 commit 锁定；上游字节原样保存（最强留痕）。"""
    url = (
        f"https://media.githubusercontent.com/media/{spec['repo']}/{spec['commit']}/{spec['path']}"
    )
    data = _get(url)
    if data.startswith(b"version https://git-lfs"):
        raise RuntimeError(f"{spec['repo']}: 拿到的是 LFS 指针而非内容，端点有变")
    return data, {"commit": spec["commit"]}


def fetch_one(name: str, spec: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    if spec["kind"] == "hf_rows":
        data, extra = _fetch_hf_rows(spec)
    elif spec["kind"] == "hf_rows_multi":
        data, extra = _fetch_hf_rows_multi(spec)
    elif spec["kind"] == "hf_beir_join":
        data, extra = _fetch_hf_beir_join(spec)
    elif spec["kind"] == "hf_tsv_qrels_join":
        data, extra = _fetch_hf_tsv_qrels_join(spec)
    elif spec["kind"] == "github_lfs":
        data, extra = _fetch_github_lfs(spec)
    else:
        raise RuntimeError(f"未知切片类型: {spec['kind']}")
    meta = {k: v for k, v in spec.items() if k != "kind"} | extra
    meta["sha256"] = _sha256(data)
    meta["bytes"] = len(data)
    return data, meta


def _verify(name: str, lock: dict[str, Any]) -> str | None:
    """返回错误描述；None 表示通过。"""
    path = DATA_DIR / f"{name}.jsonl"
    if name not in lock:
        return f"{name}: 锁文件无此条目（先运行 --update-lock）"
    if not path.exists():
        return f"{name}: 缺文件 {path}"
    actual = _sha256(path.read_bytes())
    if actual != lock[name]["sha256"]:
        return f"{name}: sha256 不符（锁 {lock[name]['sha256'][:12]}…，实际 {actual[:12]}…）"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只离线校验，不下载")
    parser.add_argument("--update-lock", action="store_true", help="重新下载并改写锁文件")
    parser.add_argument("--only", default=None, help="只处理指定切片名（单切片维护，不动其余锁项）")
    args = parser.parse_args(argv)
    if args.only and args.only not in SLICES:
        parser.error(f"未知切片名: {args.only}（可用: {', '.join(sorted(SLICES))}）")
    targets = {args.only: SLICES[args.only]} if args.only else SLICES

    lock: dict[str, Any] = {}
    if LOCK_PATH.exists():
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    if args.check:
        errors = [e for name in targets if (e := _verify(name, lock))]
        for err in errors:
            print(f"✗ {err}", file=sys.stderr)
        if not errors:
            print(f"✓ {len(targets)} 个切片全部与锁一致")
        return 1 if errors else 0

    if not args.update_lock and not lock:
        print(f"锁文件不存在: {LOCK_PATH}（首次获取请用 --update-lock）", file=sys.stderr)
        return 2

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, spec in targets.items():
        try:
            data, meta = fetch_one(name, spec)
        except Exception as exc:  # noqa: BLE001 - 汇总报告后非零退出
            print(f"✗ {name}: 下载失败 — {exc}", file=sys.stderr)
            failures += 1
            continue
        if not args.update_lock and meta["sha256"] != lock.get(name, {}).get("sha256"):
            print(f"✗ {name}: 下载内容与锁不符（上游变了？核实后 --update-lock）", file=sys.stderr)
            failures += 1
            continue
        (DATA_DIR / f"{name}.jsonl").write_bytes(data)
        lock[name] = meta
        print(f"✓ {name}: {meta['bytes']} bytes, sha256 {meta['sha256'][:12]}…")

    if args.update_lock and not failures:
        LOCK_PATH.write_text(
            json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"锁已写入 {LOCK_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
