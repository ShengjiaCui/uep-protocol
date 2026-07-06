"""patch_repair 判分载荷试金石（FR-2.6 同构复制）——只依赖协议类型。

合同：输入为任何通过 ``uep validate``、含修复判分三要素的 patch_repair 条目，
输出自含检查单 ``CheckedPatch``——复现判分所需的一切（仓库基准、问题陈述、
测试变更、败转胜/回归清单、沙箱参数），不得回查任何源格式。
本文件源码不得出现任何已接入格式/数据集名（禁名 lint 强制）。
"""

from dataclasses import dataclass

from touchstones import TouchstoneError
from uep.schema import EvalItem, ExecutionVerifier, PatchRepairTask


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
