"""execution 载荷试金石（FR-2.6 同构复制到执行类原型）——只依赖协议类型。

合同：输入为任何通过 ``uep validate``、含 ``execution`` Verifier 的
code_generation 条目，输出自含可执行规格 ``PackedExecution``——它必须携带
"跑起来"所需的一切（题面、载荷、入口、沙箱参数），不得回查任何源格式。
本文件源码不得出现任何已接入格式/数据集名（禁名 lint 强制）。
"""

from dataclasses import dataclass

from touchstones import TouchstoneError
from uep.schema import CodeGenerationTask, EvalItem, ExecutionVerifier


@dataclass(frozen=True)
class PackedExecution:
    prompt: str
    language: str
    test_code: str | None
    assertions: list[str]
    entry_point: str | None
    harness: str
    timeout_s: int
    network: bool
    memory_mb: int
    text: str  # 人类可读渲染：题面 + 判分载荷摘要


def pack(item: EvalItem) -> PackedExecution:
    task = item.task
    if not isinstance(task, CodeGenerationTask):
        raise TouchstoneError(f"{item.id}: 执行试金石仅接受 code_generation，得到 {task.type!r}")
    verifier = next((v for v in item.verifiers if isinstance(v, ExecutionVerifier)), None)
    if verifier is None:
        raise TouchstoneError(f"{item.id}: 缺 execution Verifier（打分意图不完整）")
    tests = verifier.tests
    if tests.language != task.language:
        raise TouchstoneError(
            f"{item.id}: 载荷语言 {tests.language!r} 与任务语言 {task.language!r} 不符"
        )
    payload = tests.test_code or "\n".join(tests.assertions)
    lines = [
        task.prompt,
        "",
        "=== 判分载荷（自含） ===",
        f"language: {tests.language} · harness: {tests.harness}"
        f" · entry_point: {tests.entry_point or '-'}",
        f"sandbox: timeout={verifier.sandbox.timeout_s}s"
        f" network={verifier.sandbox.network} memory={verifier.sandbox.memory_mb}MB",
        "",
        payload,
    ]
    return PackedExecution(
        prompt=task.prompt,
        language=task.language,
        test_code=tests.test_code,
        assertions=list(tests.assertions),
        entry_point=tests.entry_point,
        harness=tests.harness,
        timeout_s=verifier.sandbox.timeout_s,
        network=verifier.sandbox.network,
        memory_mb=verifier.sandbox.memory_mb,
        text="\n".join(lines),
    )
