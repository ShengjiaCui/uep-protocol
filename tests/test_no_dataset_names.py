"""禁名 lint（FR-2.6，测试规格书 §①）——协议核心与试金石源码不得出现已接入格式名。

黑名单从适配器注册表**动态生成**（不手写）；扫描 touchstones/ 与 uep/
（uep/adapters/ 除外——格式名的唯一合法居所）。按词边界匹配，
避免普通标识符误伤（如 ``re.search`` 中的 search 含子串 arc）。
"""

import re
from pathlib import Path

import pytest

from uep.adapters import banned_format_names

ROOT = Path(__file__).resolve().parents[1]
ADAPTERS_DIR = ROOT / "uep" / "adapters"


def _scanned_files() -> list[Path]:
    files = sorted((ROOT / "touchstones").rglob("*.py"))
    files += sorted(p for p in (ROOT / "uep").rglob("*.py") if ADAPTERS_DIR not in p.parents)
    return files


@pytest.mark.fr("FR-2.6")
def test_no_format_names_in_core_sources():
    banned = banned_format_names()
    assert banned, "注册表为空，黑名单失效"
    patterns = {n: re.compile(rf"\b{re.escape(n)}\b", re.IGNORECASE) for n in banned}
    hits: list[str] = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        for name, pattern in patterns.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                hits.append(f"{path.relative_to(ROOT)}:{line}: {name!r}")
    assert not hits, "协议核心/试金石源码出现格式名（只允许存在于 uep/adapters/）:\n" + "\n".join(
        hits
    )


@pytest.mark.fr("FR-2.6")
def test_scan_actually_covers_core_tree():
    """防呆：扫描集必须非空且覆盖核心模块（否则 lint 形同虚设）。"""
    names = {p.name for p in _scanned_files()}
    assert {"schema.py", "matching.py", "validate.py", "render_choices.py"} <= names
    assert "engine.py" not in names, "适配器目录应被排除"
