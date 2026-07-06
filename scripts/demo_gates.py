#!/usr/bin/env python3
"""资格线四关卡端到端演示（goals §6）——一条命令复现：``make demo``。

关卡 1 通用消费者试金石：零数据集名的消费程序对全部已接入切片工作；
关卡 2 无损往返：每个格式 X→UEP→X 逐条语义等价；
关卡 3 五分钟零代码：CSV→UEP→校验→两个 Runner 任务包，纯 CLI；
关卡 4 SPEC 零漂移：全测试套件 + FR↔测试映射（阶段 1–3 激活）子进程实跑。

全程离线（本地锁定切片）；任一关不过即非零退出。
关卡 3 的人工计时属 L2 实测（状态见行动计划 3.3），本演示复现其机械链路。
"""

import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstones import assemble_retrieval, check_patch, pack_execution  # noqa: E402
from touchstones import render_choices, render_qa  # noqa: E402
from uep.adapters import REGISTRY, banned_format_names  # noqa: E402
from uep.cli import main as uep_main  # noqa: E402
from uep.equivalence import diff_paths, normalize_tree  # noqa: E402

LOCK_PATH = ROOT / "scripts" / "slices.lock.json"
DATA_DIR = ROOT / "data" / "real"

#: 原型 → 消费程序（键是任务原型，不是数据集名——关卡 1 的活体现）
CONSUMERS = {
    "choices": render_choices.render,
    "qa": render_qa.render,
    "code_generation": pack_execution.pack,
    "patch_repair": check_patch.check,
    "retrieval": assemble_retrieval.assemble,
}


def _load_slice(name: str) -> list[dict]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))[name]
    raw = (DATA_DIR / f"{name}.jsonl").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != lock["sha256"]:
        raise RuntimeError(f"{name}: 切片与锁不符（先运行 fetch_slices.py）")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def _import_items(name: str, rows: list[dict]):
    info = next(entry for entry in REGISTRY if entry.name == name)
    module = importlib.import_module(info.module)
    if name == "openai_evals":  # 双向格式：导入参数随源约定（见 dogfood_run.py）
        return module.import_rows(rows, dataset="openai/evals:Chinese_character_riddles", lang=["zh"])
    return module.import_rows(rows)


def _slice_names() -> list[str]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    return sorted(lock)


def gate1_universal_consumers() -> tuple[bool, str]:
    total, per_type = 0, {}
    for name in _slice_names():
        for item in _import_items(name, _load_slice(name)):
            CONSUMERS[item.task.type](item)  # 渲染失败即异常 → 关卡失败
            per_type[item.task.type] = per_type.get(item.task.type, 0) + 1
            total += 1
    banned = banned_format_names()
    detail = ", ".join(f"{k}={v}" for k, v in sorted(per_type.items()))
    return True, (
        f"{len(_slice_names())} 切片 {total} 条全部经 {len(CONSUMERS)} 个试金石消费"
        f"（{detail}）；消费程序源码零数据集名（禁名词 {len(banned)} 个，lint 在关卡 4 套件内强制）"
    )


def gate2_lossless_roundtrip() -> tuple[bool, str]:
    checked = 0
    for name in _slice_names():
        rows = _load_slice(name)
        info = next(entry for entry in REGISTRY if entry.name == name)
        module = importlib.import_module(info.module)
        restored = module.export_rows(_import_items(name, rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            if diffs:
                return False, f"{name} 第 {idx} 行还原不等价: {diffs[:3]}"
            checked += 1
    return True, f"{len(_slice_names())} 格式 × 共 {checked} 条 X→UEP→X 逐条语义等价（0 差异）"


def gate3_five_minute_chain() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        ds = Path(tmp) / "ds"
        steps = [
            ["convert", str(ROOT / "examples" / "quiz.csv"), "--from", "csv", "-o", str(ds),
             "--content-lang", "zh-CN", "--license", "unknown"],
            ["validate", str(ds / "items.jsonl")],
            ["export", str(ds / "items.jsonl"), "--to", "lmeval", "-o", str(Path(tmp) / "lm")],
            ["export", str(ds / "items.jsonl"), "--to", "inspect_ai", "-o", str(Path(tmp) / "ins")],
        ]
        for argv in steps:
            if uep_main(argv) != 0:
                return False, f"CLI 步骤失败: uep {' '.join(argv[:2])} …"
    return True, "CSV→UEP→校验✓→lm-eval+Inspect AI 双任务包，纯 CLI 零代码（人工计时=L2，见行动计划 3.3）"


def gate4_spec_zero_drift() -> tuple[bool, str]:
    env = os.environ | {"UEP_ACTIVE_PHASES": "1,2,3"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-200:]
    match = re.search(r"(\d+) passed", tail)
    passed = match.group(1) if match else "?"
    if proc.returncode != 0:
        return False, f"测试套件非绿：{tail}"
    return True, f"pytest {passed} passed；FR↔测试映射按阶段 1–3 激活强制（{tail}）"


GATES = [
    ("关卡 1 通用消费者试金石", gate1_universal_consumers),
    ("关卡 2 无损往返", gate2_lossless_roundtrip),
    ("关卡 3 五分钟零代码链路", gate3_five_minute_chain),
    ("关卡 4 SPEC 零漂移", gate4_spec_zero_drift),
]


def main() -> int:
    print("UEP 资格线四关卡（goals §6）· 一条命令复现\n")
    failures = 0
    for title, gate in GATES:
        try:
            ok, evidence = gate()
        except Exception as exc:  # noqa: BLE001 - 演示逐关汇报，不中断后续关卡
            ok, evidence = False, f"异常: {exc}"
        mark = "✓" if ok else "✗"
        print(f"{mark} {title}\n    {evidence}")
        failures += 0 if ok else 1
    print()
    if failures:
        print(f"资格线未达：{failures} 关未过")
        return 1
    print("资格线：四关全绿 ✓（通过≠成功；成功=被采纳，见 goals §2）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
