"""CLI 双语文案目录（FR-5.8 的机制基座）——键控目录 + ``t()``。

新增动词的全部用户可见文案必须进本目录（zh/en 双写）；
validate 动词的存量文案将在双语收口时并入。
"""

import os

MESSAGES: dict[str, dict[str, str]] = {
    "validate.ok": {"zh": "校验通过 ✓", "en": "validation passed ✓"},
    "validate.summary": {
        "zh": "共 {errors} 个错误，{warnings} 个警告",
        "en": "{errors} error(s), {warnings} warning(s)",
    },
    "io.missing": {"zh": "文件不存在：{path}", "en": "file not found: {path}"},
    "io.invalid_items": {
        "zh": "条目文件校验失败：{detail}",
        "en": "items file failed validation: {detail}",
    },
    "convert.ok": {
        "zh": "已落盘 {count} 条 → {items}（清单 {manifest}）",
        "en": "wrote {count} item(s) → {items} (manifest {manifest})",
    },
    "convert.unknown_format": {
        "zh": "未知源格式：{name}（可用：{known}）",
        "en": "unknown source format: {name} (known: {known})",
    },
    "convert.unsupported": {
        "zh": "该格式需专用参数，convert 暂不支持：{name}",
        "en": "format needs bespoke arguments, not convert-able yet: {name}",
    },
    "export.ok": {"zh": "任务包已写出 → {path}", "en": "task package written → {path}"},
    "export.unknown_target": {
        "zh": "未知导出目标：{name}（可用：{known}）",
        "en": "unknown export target: {name} (known: {known})",
    },
    "export.failed": {"zh": "导出失败：{detail}", "en": "export failed: {detail}"},
    "dataset.wrote": {
        "zh": "已落盘 {count} 条 → {items}（清单 {manifest}）",
        "en": "wrote {count} item(s) → {items} (manifest {manifest})",
    },
    "verbs.empty": {
        "zh": "结果为空，不落盘",
        "en": "empty result, refusing to write",
    },
    "list.total": {"zh": "共 {n} 条", "en": "{n} item(s) total"},
    "show.not_found": {"zh": "未找到条目：{id}", "en": "item not found: {id}"},
    "filter.no_predicate": {
        "zh": "至少给一个筛选条件（--type / --task-lang）",
        "en": "at least one predicate required (--type / --task-lang)",
    },
    "slice.bad_range": {
        "zh": "区间须为 START:STOP（半开，START<STOP）：{value}",
        "en": "range must be START:STOP (half-open, START<STOP): {value}",
    },
    "sample.bad_n": {"zh": "抽样数须 ≥1：{n}", "en": "sample size must be ≥1: {n}"},
    "sample.too_large": {
        "zh": "抽样数 {n} 超过条目总数 {size}",
        "en": "sample size {n} exceeds dataset size {size}",
    },
    "sample.seed": {"zh": "seed={seed}（可复现）", "en": "seed={seed} (reproducible)"},
    "merge.need_two": {
        "zh": "merge 至少需要两个输入文件",
        "en": "merge needs at least two input files",
    },
    "merge.conflict": {
        "zh": "条目 id 冲突，拒绝合并：{ids}",
        "en": "conflicting item ids, refusing to merge: {ids}",
    },
    "conform.schema.pass": {"zh": "schema 合法 ✓（{n} 条）", "en": "schema valid ✓ ({n} item(s))"},
    "conform.touchstones.pass": {
        "zh": "试金石可消费 ✓（打分意图自明）",
        "en": "touchstone-consumable ✓ (scoring intent self-evident)",
    },
    "conform.touchstones.fail": {
        "zh": "试金石消费失败 ✗（{n} 条）：",
        "en": "touchstone consumption failed ✗ ({n} item(s)):",
    },
    "conform.custom_note": {
        "zh": "（custom 逃生舱跳过 {n} 条）",
        "en": "(skipped {n} custom item(s))",
    },
    "conform.manifest.pass": {
        "zh": "清单一致 ✓（size/task_types/languages 机械复核）",
        "en": "manifest consistent ✓ (size/task_types/languages recomputed)",
    },
    "conform.manifest.fail": {
        "zh": "清单与条目不一致 ✗：",
        "en": "manifest inconsistent with items ✗:",
    },
    "conform.manifest.skip": {
        "zh": "清单检查跳过（未找到 {path}）",
        "en": "manifest check skipped (no {path})",
    },
    "conform.manifest.invalid": {
        "zh": "清单不合法 ✗：{detail}",
        "en": "manifest invalid ✗: {detail}",
    },
    "conform.ok": {"zh": "一致性检查通过 ✓", "en": "conformance passed ✓"},
    "conform.fail": {"zh": "一致性检查未通过", "en": "conformance failed"},
    "stats.size": {"zh": "条目数：{n}", "en": "items: {n}"},
    "stats.task_types": {"zh": "任务类型：{detail}", "en": "task types: {detail}"},
    "stats.languages": {"zh": "语言：{detail}", "en": "languages: {detail}"},
    "stats.verifiers": {"zh": "验证器：{detail}", "en": "verifiers: {detail}"},
}


def resolve_lang(value: str | None = None) -> str:
    candidate = value or os.environ.get("UEP_LANG") or "zh"
    return candidate if candidate in ("zh", "en") else "zh"


def t(key: str, lang: str, **kwargs: object) -> str:
    return MESSAGES[key][lang].format(**kwargs)
