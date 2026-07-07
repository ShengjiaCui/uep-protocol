#!/usr/bin/env python3
"""UEP 原生中文 codegen 数据集构建器（A5，用协议而非实现 Runner，居 scripts/）。

简洁作者源 zh_codegen_problems.py（每题 5 字段）→ 完整 EvalItem（schema 补全骨架）
→ write_dataset 落 examples/zh-codegen/{items.jsonl, manifest.json}。
证明"UEP 原生创作比自造 items.jsonl 省事"：作者只写题面+入口+解+测试，schema/清单机械生成。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.zh_codegen_problems import PROBLEMS  # noqa: E402
from uep.dataset_io import write_dataset  # noqa: E402
from uep.schema import (  # noqa: E402
    CodeGenerationTask,
    EvalItem,
    ExecutionVerifier,
    Sandbox,
    TestSuite,
)

OUT_DIR = ROOT / "examples" / "zh-codegen"
#: 参考解仅供自测（tests/test_zh_codegen.py），绝不入 item——它是答案，会泄题
_SOLUTION_KEY = "solution"


def build_items() -> list[EvalItem]:
    """题库 → UEP EvalItem 列表（纯构造，不落盘；供构建器与测试共用）。"""
    items: list[EvalItem] = []
    for p in PROBLEMS:
        items.append(
            EvalItem(
                id=p["id"],
                lang=["zh-CN"],
                task=CodeGenerationTask(prompt=p["prompt"], language="python"),
                verifiers=[
                    ExecutionVerifier(
                        tests=TestSuite(
                            language="python",
                            test_code=p["test_code"],
                            entry_point=p["entry_point"],
                            harness="exec",
                        ),
                        sandbox=Sandbox(timeout_s=10, network=False, memory_mb=512),
                    )
                ],
                metadata={"authored": "native"},  # 原生创作无转换来源, source=None
            )
        )
    return items


def main() -> int:
    items = build_items()
    items_path, manifest_path = write_dataset(
        items, OUT_DIR, name="uep-zh-codegen", license="Apache-2.0"
    )
    print(f"写出 {len(items)} 条 → {items_path} / {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
