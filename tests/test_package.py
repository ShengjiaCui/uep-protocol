"""基础打包与协议常量测试。"""

from pathlib import Path

import pytest

import uep


def test_supported_protocol():
    assert uep.SUPPORTED_PROTOCOL == "2.0"


@pytest.mark.fr("FR-0.2")
def test_coverage_gate_configured():
    """覆盖率闸门（≥80%）必须钉死在 make check 里——FR-0.2 的机械见证。"""
    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")
    assert "--cov-fail-under=80" in makefile
