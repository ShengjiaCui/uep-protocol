#!/usr/bin/env python3
"""codegen 判分闭环 dogfooding：真实切片 → UEP → Inspect 样本 → 沙箱判分 → pass@1。

用法：
    .venv/bin/python scripts/dogfood_codegen.py --limit 10 --model gemma3:27b
前置：
    1. 切片已获取（scripts/fetch_slices.py）
    2. .venv-inspect 已建（uv venv --python 3.12 .venv-inspect && uv pip install inspect-ai openai）
    3. Ollama 可达：UEP_OLLAMA_BASE（默认 http://localhost:11434/v1/chat/completions）
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uep.adapters import humaneval  # noqa: E402
from uep.adapters.inspect_ai import export_samples  # noqa: E402

INSPECT_BIN = ROOT / ".venv-inspect" / "bin" / "inspect"
OUT_ROOT = ROOT / "build" / "dogfood-codegen"


def load_slice(name: str) -> list[dict]:
    lock = json.loads((ROOT / "scripts" / "slices.lock.json").read_text(encoding="utf-8"))[name]
    raw = (ROOT / "data" / "real" / f"{name}.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest() != lock["sha256"]:
        raise RuntimeError(f"{name}: 切片与锁不符（先运行 fetch_slices.py）")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--model", default="gemma3:27b")
    parser.add_argument(
        "--items",
        default=None,
        help="直读 UEP items.jsonl（原生数据集，如 A5 zh-codegen），替代 humaneval 切片",
    )
    args = parser.parse_args()

    if args.items:
        from uep.dataset_io import read_items

        items = read_items(args.items)[: args.limit]
        out_root = ROOT / "build" / f"dogfood-codegen-{Path(args.items).resolve().parent.name}"
    else:
        items = humaneval.import_rows(load_slice("humaneval"))[: args.limit]
        out_root = OUT_ROOT
    samples = export_samples(items)
    out_root.mkdir(parents=True, exist_ok=True)
    samples_path = out_root / "samples.jsonl"
    samples_path.write_text(
        "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples),
        encoding="utf-8",
    )

    base = os.environ.get("UEP_OLLAMA_BASE", "http://localhost:11434/v1/chat/completions")
    api_base = base.removesuffix("/chat/completions")
    env = os.environ | {
        "UEP_SAMPLES": str(samples_path),
        "OPENAI_BASE_URL": api_base,
        "OPENAI_API_KEY": "ollama",
    }
    cmd = [
        # 任务路径须相对（API 校准，见 report 偏差记录②）：inspect-ai 0.3.244 把
        # 非 glob 的任务参数当 glob 交给 root_dir.glob()，绝对路径会触发
        # pathlib 的 NotImplementedError("Non-relative patterns are unsupported")。
        # 用相对路径 + 显式 cwd=ROOT 规避，不依赖调用方当前工作目录。
        str(INSPECT_BIN),
        "eval",
        "scripts/inspect_codegen_task.py",
        "--model",
        f"openai/{args.model}",
        "--log-dir",
        str(out_root / "logs"),
        # 贪婪确定性 pass@1（A3 教训：inspect 不传温度→Ollama 默认 temp=1.0 采样）
        "--temperature",
        "0.0",
        "--top-p",
        "1.0",
        "--seed",
        "0",
    ]
    print("$", " ".join(cmd))
    return subprocess.run(cmd, env=env, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
