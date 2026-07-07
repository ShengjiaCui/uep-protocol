#!/usr/bin/env python3
"""A3 双 Runner 分数级对分编排（Runner 侧实验脚本，不属协议包）。

同一份 UEP 切片 → lm-eval 与 Inspect AI 各自实跑（同模型同条目）→ 逐条判分 →
一致性表 + 偏差归因素材。纯核（compare/解析器）在 crossrunner_compare.py 且有单测；
本文件只做编排与子进程调度，靠实跑验证（同 A1：dogfood_codegen 编排 + inspect_codegen_task 判分）。

用法：
    python scripts/crossrunner_run.py --slice mmlu  --limit 50 --model gemma3:27b   # choices
    python scripts/crossrunner_run.py --slice gsm8k --limit 50 --model gemma3:27b   # qa
前置：
    1. 切片已获取（scripts/fetch_slices.py），.venv-lmeval 与 .venv-inspect 均已建；
    2. Ollama 可达：UEP_OLLAMA_BASE（默认 http://localhost:11434/v1/chat/completions）。
判分机理同族（对分成立前提）：两侧均生成式（lm-eval generate_until；Inspect
multiple_choice 亦生成 "ANSWER: X" 解析）。**两侧强制贪婪**：lm-eval 导出即
do_sample=false/temperature=0；Inspect 若不显式传温度, Ollama 会套 modelfile
默认 temp=1.0 采样, 故本编排显式传 --temperature 0 --top-p 1 --seed。对齐解码后,
分数偏差主要源于提示模板与抽取规则（生成长度上限等其余配置差异见对分报告如实披露）。
"""

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.crossrunner_compare import (  # noqa: E402
    compare,
    parse_inspect_log,
    parse_lmeval_samples,
)

LM_EVAL_BIN = ROOT / ".venv-lmeval" / "bin" / "lm_eval"
INSPECT_BIN = ROOT / ".venv-inspect" / "bin" / "inspect"
OUT_ROOT = ROOT / "build" / "crossrunner"
#: 切片 → (导入适配器模块, Inspect 任务原型)
SLICES = {"mmlu": ("mmlu", "choices"), "gsm8k": ("gsm8k", "qa")}


def load_items(slice_name: str, limit: int):
    """真实切片（锁校验）→ UEP 条目，取前 limit 条（两侧消费同一份，保同条目同条数）。"""
    import importlib

    lock = json.loads((ROOT / "scripts" / "slices.lock.json").read_text(encoding="utf-8"))[
        slice_name
    ]
    raw = (ROOT / "data" / "real" / f"{slice_name}.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest() != lock["sha256"]:
        raise RuntimeError(f"{slice_name}: 切片与锁不符（先运行 fetch_slices.py）")
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()][:limit]
    module = importlib.import_module(f"uep.adapters.{SLICES[slice_name][0]}")
    return module.import_rows(rows)


def run_lmeval(items, task_name: str, out_dir: Path, model: str, base_full: str) -> dict[str, bool]:
    from uep.adapters.lmeval import export_task

    # 清旧产物：glob[-1] 选最新文件, 避免命中上次运行残留
    shutil.rmtree(out_dir, ignore_errors=True)
    export_task(items, task_name=task_name, out_dir=out_dir)
    results_dir = out_dir / "results"
    cmd = [
        str(LM_EVAL_BIN),
        "--model",
        "local-chat-completions",
        "--model_args",
        f"model={model},base_url={base_full},num_concurrent=1,max_retries=2,tokenized_requests=False",
        "--tasks",
        task_name,
        "--include_path",
        str(out_dir),
        "--limit",
        str(len(items)),
        "--output_path",
        str(results_dir),
        "--apply_chat_template",
        "--log_samples",
    ]
    print("$ lm_eval", task_name, f"({len(items)} 条)", flush=True)
    if subprocess.run(cmd, cwd=ROOT).returncode != 0:
        sys.exit(f"lm_eval 失败: {task_name}")
    hits = sorted(glob.glob(f"{results_dir}/**/samples_{task_name}_*.jsonl", recursive=True))
    if not hits:
        sys.exit(f"未找到 lm-eval samples 于 {results_dir}")
    return parse_lmeval_samples(hits[-1])


def run_inspect(
    items,
    kind: str,
    out_dir: Path,
    model: str,
    base_api: str,
    *,
    seed: int = 0,
    qa_suffix: str = "",
) -> dict[str, bool]:
    from uep.adapters.inspect_ai import dump_jsonl, export_samples

    shutil.rmtree(out_dir, ignore_errors=True)  # 同 lmeval：清旧日志, 保 glob[-1] 命中本次
    out_dir.mkdir(parents=True, exist_ok=True)
    samples_path = out_dir / "samples.jsonl"
    samples_path.write_text(dump_jsonl(export_samples(items)), encoding="utf-8")
    log_dir = out_dir / "logs"
    env = os.environ | {
        "UEP_XR_TASK": kind,
        "UEP_SAMPLES": str(samples_path),  # 必绝对：json_dataset 相对路径按任务文件目录解析
        "OPENAI_BASE_URL": base_api,
        "OPENAI_API_KEY": "ollama",
        "PYTHONUNBUFFERED": "1",
    }
    if qa_suffix:  # 受控归因实验：令 inspect qa 提示与 lm-eval 的"仅答案"指令对齐
        env["UEP_XR_QA_SUFFIX"] = qa_suffix
    cmd = [
        str(INSPECT_BIN),
        "eval",
        "scripts/inspect_crossrunner_task.py",  # 相对路径 + cwd=ROOT（A1 校准：绝对路径触发 glob 报错）
        "--model",
        f"openai/{model}",
        "--log-dir",
        str(log_dir),
        "--log-format",
        "json",
        # 贪婪解码 + 固定种子, 与 lm-eval(do_sample=false, temperature=0) 对齐——
        # 否则 inspect 不发温度, Ollama 套 modelfile 默认 temp=1.0 采样(引入未控变量)
        "--temperature",
        "0.0",
        "--top-p",
        "1.0",
        "--seed",
        str(seed),
    ]
    print("$ inspect eval", kind, f"({len(items)} 条)", flush=True)
    if subprocess.run(cmd, env=env, cwd=ROOT).returncode != 0:
        sys.exit(f"inspect eval 失败: {kind}")
    hits = sorted(glob.glob(f"{log_dir}/*.json"))
    if not hits:
        sys.exit(f"未找到 Inspect 日志于 {log_dir}")
    return parse_inspect_log(hits[-1])


def print_table(report, slice_name: str) -> None:
    print("\n=== A3 分数级对分 ===")
    print(f"切片: {slice_name}  条数 n={report.n}")
    print(f"  {report.label_a:<10} 正确率: {report.acc_a:.4f}")
    print(f"  {report.label_b:<10} 正确率: {report.acc_b:.4f}")
    print(f"  Δ(a-b): {report.delta:+.4f}   逐条一致率: {report.agreement_rate:.4f}")
    print(
        f"  四象限: 同对={report.both_correct} 同错={report.both_wrong} "
        f"仅{report.label_a}={report.a_only} 仅{report.label_b}={report.b_only}"
    )
    if report.disagreements:
        print(f"  分歧条目({len(report.disagreements)}): {report.disagreements}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", choices=sorted(SLICES), default="mmlu")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--model", default="gemma3:27b")
    parser.add_argument(
        "--seed", type=int, default=0, help="Inspect 侧随机种子（贪婪下仅保可复现）"
    )
    parser.add_argument(
        "--qa-suffix",
        default="",
        help="受控归因实验：追加到 inspect qa 题面的指令（对齐 lm-eval 的'仅答案'指令）；产物入 <slice>-exp",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("UEP_OLLAMA_BASE", "http://localhost:11434/v1/chat/completions"),
    )
    args = parser.parse_args()

    _, kind = SLICES[args.slice]
    base_full = args.base_url  # lm-eval local-chat-completions 要完整 chat 端点
    base_api = base_full.removesuffix("/chat/completions")  # OpenAI 客户端要 /v1 基址

    items = load_items(args.slice, args.limit)
    out_dir = OUT_ROOT / (f"{args.slice}-exp" if args.qa_suffix else args.slice)
    lm_res = run_lmeval(items, f"uep_xr_{args.slice}", out_dir / "lmeval", args.model, base_full)
    in_res = run_inspect(
        items,
        kind,
        out_dir / "inspect",
        args.model,
        base_api,
        seed=args.seed,
        qa_suffix=args.qa_suffix,
    )

    report = compare(lm_res, in_res, label_a="lm-eval", label_b="inspect")
    print_table(report, args.slice)

    report_path = out_dir / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "slice": args.slice,
                "model": args.model,
                "report": asdict(report),
                "lm_eval": lm_res,
                "inspect": in_res,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n报告: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
