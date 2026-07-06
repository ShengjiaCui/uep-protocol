"""FR↔测试映射元测试（FR-0.1）——"承诺=测试"的机械裁判。

规则（docs/uep-v2-test-spec.md §⑦）：
- 解析 SPEC §10 表格得到全部 FR 及其所属阶段；
- 激活阶段（环境变量 UEP_ACTIVE_PHASES，如 "1" 或 "1,2"）内的每条 FR，
  必须存在未被跳过的 ``@pytest.mark.fr("FR-x.y")`` 测试；
- 带 skip/skipif 的测试从严视为未覆盖（防空壳）；
- 引用 SPEC 中不存在的 FR 的标记 → 失败。

日常 ``make check`` 不设激活阶段（只查未知引用，保持绿）；
阶段出口跑 ``make phase1-exit`` 强制红绿——红名单即未兑现清单。
"""

import os
import re
from pathlib import Path

import pytest

SPEC_PATH = Path(__file__).resolve().parents[1] / "docs" / "uep-v2-spec.md"
FR_RANGE = re.compile(r"^FR-(\d+)\.(\d+)–(\d+)\.(\d+)$")


def _expand(fr_field: str) -> list[str]:
    """展开区间行，如 ``FR-5.1–5.7`` → FR-5.1 … FR-5.7。"""
    m = FR_RANGE.match(fr_field)
    if not m:
        return [fr_field]
    major, start, major2, end = (int(g) for g in m.groups())
    if major != major2:
        raise ValueError(f"跨大类区间不支持: {fr_field}")
    return [f"FR-{major}.{i}" for i in range(start, end + 1)]


def spec_fr_phases() -> dict[str, set[int]]:
    frs: dict[str, set[int]] = {}
    for line in SPEC_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| FR-"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        phases = {int(d) for d in re.findall(r"\d+", cells[-1])}
        for fr in _expand(cells[0]):
            frs[fr] = phases
    return frs


def _covered_frs(items) -> set[str]:
    covered: set[str] = set()
    for item in items:
        if item.get_closest_marker("skip") or item.get_closest_marker("skipif"):
            continue
        for mark in item.iter_markers("fr"):
            covered.add(mark.args[0])
    return covered


@pytest.mark.fr("FR-0.1")
def test_fr_mapping(request):
    frs = spec_fr_phases()
    assert frs, f"未能从 SPEC 解析出任何 FR: {SPEC_PATH}"
    covered = _covered_frs(request.session.items)

    unknown = covered - frs.keys()
    assert not unknown, f"标记引用了 SPEC 不存在的 FR: {sorted(unknown)}"

    active_raw = os.environ.get("UEP_ACTIVE_PHASES", "")
    active = {int(x) for x in active_raw.split(",") if x.strip()}
    required = {fr for fr, phases in frs.items() if phases & active}
    missing = sorted(required - covered)
    assert (
        not missing
    ), f"激活阶段 {sorted(active)} 内缺失验收测试的 FR（{len(missing)} 条）: {missing}"
