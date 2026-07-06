#!/usr/bin/env python3
"""dogfooding 实跑（FR-3.4 的 L2 部分）——真实切片 → UEP → lm-eval 任务包 → Ollama 出分。

用法：
    python scripts/dogfood_run.py                       # 默认：mmlu 切片前 10 条
    python scripts/dogfood_run.py --slice arc --limit 10
    python scripts/dogfood_run.py --model qwen3:8b

前置：
    1. 切片已获取：python scripts/fetch_slices.py
    2. 独立运行环境：uv venv --python 3.12 .venv-lmeval
       uv pip install --python .venv-lmeval/bin/python "lm-eval[api]"
    3. Ollama 可达：默认 http://localhost:11434，或设环境变量
       UEP_OLLAMA_BASE=http://<你的端点>:11434/v1/chat/completions（--base-url 亦可覆写）

"最小可行跑通"（行动计划）：验证 Runner 侧集成正确，不追求模型成绩；
考生 = 本地小模型（裁决④，零付费 API）。
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # 允许脚本直跑（uep 未装进 lmeval venv）

from uep.adapters import REGISTRY, lmeval  # noqa: E402

DEFAULT_BASE = os.environ.get("UEP_OLLAMA_BASE", "http://localhost:11434/v1/chat/completions")
LM_EVAL_BIN = ROOT / ".venv-lmeval" / "bin" / "lm_eval"
OUT_ROOT = ROOT / "build" / "dogfood"


def load_items(slice_name: str, limit: int):
    """真实切片 → UEP 条目（复用适配器注册表，不重复映射逻辑）。"""
    slice_path = ROOT / "data" / "real" / f"{slice_name}.jsonl"
    if not slice_path.exists():
        sys.exit(f"缺切片 {slice_path}——先运行: python scripts/fetch_slices.py")
    info = next((i for i in REGISTRY if i.name == slice_name and i.mapping_file), None)
    if info is None:
        sys.exit(f"未注册的导入切片: {slice_name}")
    module = importlib.import_module(info.module)
    text = slice_path.read_text(encoding="utf-8")
    if slice_name == "openai_evals":
        # 该格式的 lang 与数据集标识由调用方给出；切片为中文字谜（见 slices.lock.json）
        rows = module.read_samples(text)
        lock = json.loads((ROOT / "scripts" / "slices.lock.json").read_text(encoding="utf-8"))
        dataset = f"{lock[slice_name]['repo']}:{Path(lock[slice_name]['path']).parent.name}"
        return module.import_rows(rows[:limit], dataset=dataset, lang=["zh"])
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return module.import_rows(rows[:limit])


def run_lm_eval(task_yaml: Path, task_name: str, model: str, base_url: str, limit: int) -> Path:
    if not LM_EVAL_BIN.exists():
        sys.exit(f"缺 {LM_EVAL_BIN}——见本脚本 docstring 前置 2 安装 lm-eval")
    out_dir = task_yaml.parent / "results"
    cmd = [
        str(LM_EVAL_BIN),
        "--model",
        "local-chat-completions",
        "--model_args",
        f"model={model},base_url={base_url},num_concurrent=1,max_retries=2,tokenized_requests=False",
        "--tasks",
        task_name,
        "--include_path",
        str(task_yaml.parent),
        "--limit",
        str(limit),
        "--output_path",
        str(out_dir),
        "--apply_chat_template",
    ]
    print("$", " ".join(cmd), flush=True)
    started = time.monotonic()
    proc = subprocess.run(cmd, check=False)
    elapsed = time.monotonic() - started
    if proc.returncode != 0:
        sys.exit(f"lm_eval 退出码 {proc.returncode}（耗时 {elapsed:.0f}s）")
    print(f"lm_eval 完成，耗时 {elapsed:.0f}s")
    return out_dir


def report(out_dir: Path, task_name: str) -> None:
    results = sorted(out_dir.rglob("results_*.json"))
    if not results:
        sys.exit(f"未找到结果文件于 {out_dir}")
    payload = json.loads(results[-1].read_text(encoding="utf-8"))
    metrics = payload["results"][task_name]
    print("\n=== dogfooding 里程碑 ===")
    print(f"任务: {task_name}")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print(f"完整结果: {results[-1]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", default="mmlu", help="真实切片名（注册表内导入适配器）")
    parser.add_argument("--limit", type=int, default=10, help="条数（最小可行 ≥10）")
    parser.add_argument("--model", default="gemma3:27b", help="Ollama 模型名")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="OpenAI 兼容 chat 端点")
    parser.add_argument(
        "--answer-pattern", default=None, help="qa 任务的答案抽取正则（默认取最后一个数值）"
    )
    args = parser.parse_args()

    items = load_items(args.slice, args.limit)
    task_name = f"uep_{args.slice}_dogfood"
    out_dir = OUT_ROOT / args.slice
    task_yaml = lmeval.export_task(
        items, task_name=task_name, out_dir=out_dir, answer_pattern=args.answer_pattern
    )
    print(f"任务包: {task_yaml}（{len(items)} 条）")
    results_dir = run_lm_eval(task_yaml, task_name, args.model, args.base_url, args.limit)
    report(results_dir, task_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
