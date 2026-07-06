"""条目与 Manifest 校验 + extras 纪律 lint（FR-4.1 / FR-1.4）。

报错做到行/字段级；文案 zh/en 双语（结构性文案双语，Pydantic 细节保留英文，
完整中文细节目录属阶段 3 FR-5.8）。
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from uep.schema import EvalItem, Manifest

#: 疑似任务本体数据的键——出现在 extras 即告警（P3 纪律，FR-1.4）
CANONICAL_KEYS = frozenset(
    {
        "question",
        "options",
        "choices",
        "answer",
        "answers",
        "answer_ids",
        "expected",
        "reference_answer",
        "prompt",
        "query",
        "tests",
        "test_code",
        "assertions",
        "corpus",
        "docs",
        "solution",
        "patch",
    }
)


@dataclass(frozen=True)
class Issue:
    severity: Literal["error", "warning"]
    line: int | None
    field: str
    detail: str

    def render(self, lang: str = "zh") -> str:
        if lang not in ("zh", "en"):
            lang = "zh"
        label = {
            "error": {"zh": "错误", "en": "error"},
            "warning": {"zh": "警告", "en": "warning"},
        }[self.severity][lang]
        if self.line is None:
            loc = "文件" if lang == "zh" else "file"
        else:
            loc = f"第 {self.line} 行" if lang == "zh" else f"line {self.line}"
        sep = "：" if lang == "zh" else ": "
        return f"[{label}] {loc} · {self.field}{sep}{self.detail}"


def _pydantic_issues(err: ValidationError, line: int | None) -> list[Issue]:
    issues = []
    for e in err.errors():
        field = ".".join(str(p) for p in e["loc"]) or "<root>"
        issues.append(Issue("error", line, field, e["msg"]))
    return issues


def lint_extras(item: EvalItem, line: int | None = None) -> list[Issue]:
    """任务本体数据出现在 extras = 适配器缺陷（告警）。"""
    issues = []
    for key in item.extras:
        if key.lower() in CANONICAL_KEYS:
            issues.append(
                Issue(
                    "warning",
                    line,
                    f"extras.{key}",
                    "疑似任务本体数据进入 extras（应归入规范字段）"
                    f" / suspected task payload in extras: {key!r}",
                )
            )
    return issues


def validate_items_jsonl(path: str | Path) -> list[Issue]:
    issues: list[Issue] = []
    for line_no, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            issues.append(Issue("error", line_no, "<json>", f"JSON 解析失败 / bad JSON: {exc}"))
            continue
        try:
            item = EvalItem.model_validate(data)
        except ValidationError as exc:
            issues.extend(_pydantic_issues(exc, line_no))
            continue
        issues.extend(lint_extras(item, line_no))
    return issues


def validate_manifest(path: str | Path) -> list[Issue]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Issue("error", None, "<json>", f"JSON 解析失败 / bad JSON: {exc}")]
    try:
        Manifest.model_validate(data)
    except ValidationError as exc:
        return _pydantic_issues(exc, None)
    return []
