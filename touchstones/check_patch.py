"""patch_repair 判分载荷试金石（FR-2.6 同构复制）——只依赖协议类型。

合同：输入为任何通过 ``uep validate``、含修复判分三要素的 patch_repair 条目，
输出自含检查单 ``CheckedPatch``——复现判分所需的一切（仓库基准、问题陈述、
测试变更、败转胜/回归清单、沙箱参数），不得回查任何源格式。
本文件源码不得出现任何已接入格式/数据集名（禁名 lint 强制）。
"""

import re
from dataclasses import dataclass

from touchstones import TouchstoneError
from uep.schema import EvalItem, ExecutionVerifier, PatchRepairTask

_HUNK = re.compile(r"^@@ -\d+(,\d+)? \+\d+(,\d+)? @@", re.M)
# pytest 节点 id 形态：path/to/file.py::test_name[参数化 id]（含 ::，结构最强可校验）。
_PYTEST_NODE_ID = re.compile(r"^[\w./\[\]-]+(::[\w\[\]().,'\" =-]+)*$")


def _is_valid_selector(sel: str) -> bool:
    if "::" in sel:
        return bool(_PYTEST_NODE_ID.match(sel))
    # 松弛底线仅防编码级损坏（非空/无首尾空白/可打印 ASCII）——不做结构校验
    # 无 :: 的选择器（如 unittest 方法名+类路径、或用例文档字符串描述）不具备统一
    # 结构语法——以真实切片实测为准放宽：只做机械可校验的最小约束（非空、无首尾
    # 空白/控制字符、可打印 ASCII），不强解具体语法。
    return bool(sel) and sel == sel.strip() and sel.isascii() and sel.isprintable()


def _check_payload(item_id: str, tests) -> None:
    if tests.test_patch is not None:
        has_headers = "--- " in tests.test_patch and "+++ " in tests.test_patch
        if not (has_headers and _HUNK.search(tests.test_patch)):
            raise TouchstoneError(
                f"{item_id}: test_patch 不是合法 unified diff（缺文件头或 hunk 头）"
            )
    for sel in [*tests.fail_to_pass, *tests.pass_to_pass]:
        if not _is_valid_selector(sel):
            raise TouchstoneError(f"{item_id}: 测试选择器格式非法: {sel!r}")


@dataclass(frozen=True)
class CheckedPatch:
    repo: str
    base_commit: str
    problem_statement: str
    test_patch: str
    fail_to_pass: list[str]
    pass_to_pass: list[str]
    harness: str
    timeout_s: int
    network: bool
    memory_mb: int
    environment_ref: str | None  # context.setup 中的环境基准（有则带出）
    text: str  # 人类可读检查单


def check(item: EvalItem) -> CheckedPatch:
    task = item.task
    if not isinstance(task, PatchRepairTask):
        raise TouchstoneError(f"{item.id}: 修复试金石仅接受 patch_repair，得到 {task.type!r}")
    verifier = next((v for v in item.verifiers if isinstance(v, ExecutionVerifier)), None)
    if verifier is None:
        raise TouchstoneError(f"{item.id}: 缺 execution Verifier（打分意图不完整）")
    tests = verifier.tests
    if not tests.test_patch or not tests.fail_to_pass:
        raise TouchstoneError(f"{item.id}: 修复判分需要 test_patch+fail_to_pass（载荷不完整）")
    _check_payload(item.id, tests)
    environment_ref = None
    if item.context is not None and isinstance(item.context.setup, dict):
        value = item.context.setup.get("environment_setup_commit")
        environment_ref = value if isinstance(value, str) else None
    lines = [
        f"repo: {task.repo} @ {task.base_commit}",
        "",
        task.problem_statement,
        "",
        "=== 判分载荷（自含） ===",
        f"harness: {tests.harness} · env_ref: {environment_ref or '-'}",
        f"sandbox: timeout={verifier.sandbox.timeout_s}s"
        f" network={verifier.sandbox.network} memory={verifier.sandbox.memory_mb}MB",
        "fail_to_pass:",
        *[f"  - {t}" for t in tests.fail_to_pass],
        "pass_to_pass:",
        *[f"  - {t}" for t in tests.pass_to_pass],
        "",
        tests.test_patch,
    ]
    return CheckedPatch(
        repo=task.repo,
        base_commit=task.base_commit,
        problem_statement=task.problem_statement,
        test_patch=tests.test_patch,
        fail_to_pass=list(tests.fail_to_pass),
        pass_to_pass=list(tests.pass_to_pass),
        harness=tests.harness,
        timeout_s=verifier.sandbox.timeout_s,
        network=verifier.sandbox.network,
        memory_mb=verifier.sandbox.memory_mb,
        environment_ref=environment_ref,
        text="\n".join(lines),
    )
