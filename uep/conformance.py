"""一致性检查（FR-6.2）——L1 验证金字塔对第三方数据集的打包。

服务"新建 benchmark 参考我们"的创建者：schema 合法之上再验两层——
①试金石可消费：打分意图对零数据集名的标准消费者自明；
②manifest 一致：size/task_types/languages 从条目机械复核（防清单漂移）。
custom 原型是受控逃生舱（SPEC §3.6），计数跳过不判失败。
问题明细用符号式中立文案（字段名+数值）；标签层双语在 CLI（i18n）。
"""

from collections import Counter
from dataclasses import dataclass, field

from touchstones import (
    TouchstoneError,
    assemble_retrieval,
    check_patch,
    pack_execution,
    render_choices,
    render_qa,
)
from uep.schema import EvalItem, Manifest

#: 原型 → 标准消费者（键=任务原型——与 make demo 关卡 1 同一张表）
CONSUMERS = {
    "choices": render_choices.render,
    "qa": render_qa.render,
    "code_generation": pack_execution.pack,
    "patch_repair": check_patch.check,
    "retrieval": assemble_retrieval.assemble,
}


@dataclass(frozen=True)
class CheckResult:
    name: str  # "touchstones" | "manifest"
    status: str  # "pass" | "fail"
    problems: list[str] = field(default_factory=list)
    skipped: int = 0  # custom 逃生舱条数（touchstones 检查专用）


def check_touchstones(items: list[EvalItem]) -> CheckResult:
    problems: list[str] = []
    skipped = 0
    for item in items:
        consumer = CONSUMERS.get(item.task.type)
        if consumer is None:  # custom：受控逃生舱不在试金石辖区
            skipped += 1
            continue
        try:
            consumer(item)
        except TouchstoneError as exc:
            problems.append(str(exc))
    return CheckResult("touchstones", "fail" if problems else "pass", problems, skipped=skipped)


def check_manifest(items: list[EvalItem], manifest: Manifest) -> CheckResult:
    problems: list[str] = []
    if manifest.size != len(items):
        problems.append(f"size: {manifest.size} ≠ {len(items)}")
    actual_types = dict(Counter(item.task.type for item in items))
    if manifest.task_types != actual_types:
        problems.append(f"task_types: {manifest.task_types} ≠ {actual_types}")
    actual_langs = sorted({tag for item in items for tag in item.lang})
    if manifest.languages != actual_langs:
        problems.append(f"languages: {manifest.languages} ≠ {actual_langs}")
    return CheckResult("manifest", "fail" if problems else "pass", problems)
