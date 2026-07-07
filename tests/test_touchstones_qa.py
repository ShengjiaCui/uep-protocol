"""qa 原型试金石断言集（FR-2.6 补全，技术债 #7）——真实切片全绿 + 黄金逐字节一致。

五原型中 qa 此前唯一无试金石；两个 qa 切片许可均为 MIT，黄金可入库。
黄金维护：``UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones_qa.py``。
"""

import os
from pathlib import Path

import pytest
from test_import_choices_real import load_slice
from test_roundtrip_openai_evals import DATASET, load_rows

from touchstones.render_qa import RenderedQa, TouchstoneError, render
from uep.adapters import gsm8k, openai_evals, svamp
from uep.schema import EvalItem

GOLDEN_DIR = Path(__file__).parent / "golden" / "qa"


def _load_math_items():
    return gsm8k.import_rows(load_slice("gsm8k"))


def _load_riddle_items():
    return openai_evals.import_rows(load_rows(), dataset=DATASET, lang=["zh"])


def _load_svamp_items():
    return svamp.import_rows(load_slice("svamp"))


#: (切片名, 加载器)——字谜集带 trajectory（system 作答约定），数学集纯题干
SLICES = [
    ("gsm8k", _load_math_items),
    ("openai_evals", _load_riddle_items),
    ("svamp", _load_svamp_items),  # A2 纵深：算术应用题
]

_SYNTH = {
    "id": "touch_qa_zh_001",
    "lang": ["zh-CN"],
    "task": {"type": "qa", "question": "水的化学式是什么？"},
    "verifiers": [{"type": "text_match", "expected": "H2O"}],
}

_SYNTH_TRAJ = {
    "id": "touch_qa_zh_002",
    "lang": ["zh-CN"],
    "task": {"type": "qa", "question": "谜面：一口咬掉牛尾巴（打一字）"},
    "trajectory": [
        {"role": "system", "content": "你是猜谜高手，只回答一个汉字。"},
        {"role": "user", "content": "谜面：一口咬掉牛尾巴（打一字）"},
    ],
    "verifiers": [{"type": "text_match", "expected": ["告"]}],
}


def _golden_blob(items: list[EvalItem]) -> str:
    blocks = []
    for item in items:
        rendered = render(item)
        blocks.append(
            f"### {item.id}\n{rendered.text}\n>>> 参考: {' | '.join(rendered.expected)}\n"
        )
    return "\n".join(blocks)


@pytest.mark.fr("FR-2.6")
class TestQaTouchstoneAssertions:
    @pytest.mark.parametrize(("name", "loader"), SLICES, ids=[n for n, _ in SLICES])
    def test_assertion_set_on_full_real_slice(self, name, loader):
        """断言 ①–④ 对全部真实切片条目成立（测试规格书 §① 风格，qa 变体）。"""
        items = loader()
        assert items
        for item in items:
            rendered = render(item)
            # ① 题干一致且非空
            assert rendered.question == item.task.question
            assert rendered.question
            # ② 参考答案非空列表，逐项非空
            assert rendered.expected
            assert all(rendered.expected)
            # ③ text 含题干（trajectory 在场时题干在轨迹消息内，仍须可见）
            assert rendered.question in rendered.text
            # ④ 完整题面约定：轨迹中全部文本消息进 text（中文字谜 system 教训）
            for step in item.trajectory or []:
                if isinstance(step.content, str) and step.content:
                    assert step.content in rendered.text

    def test_expected_normalized_to_list(self):
        rendered = render(EvalItem.model_validate(_SYNTH))
        assert isinstance(rendered, RenderedQa)
        assert rendered.expected == ["H2O"]

    def test_answer_never_leaks_into_text(self):
        assert "H2O" not in render(EvalItem.model_validate(_SYNTH)).text
        assert "告" not in render(EvalItem.model_validate(_SYNTH_TRAJ)).text

    def test_trajectory_messages_render_with_roles(self):
        rendered = render(EvalItem.model_validate(_SYNTH_TRAJ))
        assert rendered.context_lines == [
            "[system] 你是猜谜高手，只回答一个汉字。",
            "[user] 谜面：一口咬掉牛尾巴（打一字）",
        ]
        assert rendered.text.count("谜面：一口咬掉牛尾巴（打一字）") == 1, "题干不得因轨迹重复"

    def test_non_qa_item_rejected(self):
        bad = dict(
            _SYNTH,
            task={
                "type": "choices",
                "question": "选哪个？",
                "options": [{"id": "A", "text": "甲"}, {"id": "B", "text": "乙"}],
            },
            verifiers=[{"type": "choice_match", "answer_ids": ["A"]}],
        )
        with pytest.raises(TouchstoneError):
            render(EvalItem.model_validate(bad))

    def test_missing_text_match_rejected(self):
        bad = dict(_SYNTH, verifiers=[{"type": "regex", "pattern": "H2O"}])
        with pytest.raises(TouchstoneError):
            render(EvalItem.model_validate(bad))

    def test_empty_expected_rejected(self):
        bad = dict(_SYNTH, verifiers=[{"type": "text_match", "expected": []}])
        with pytest.raises(TouchstoneError):
            render(EvalItem.model_validate(bad))


@pytest.mark.fr("FR-2.6")
@pytest.mark.parametrize(("name", "loader"), SLICES, ids=[n for n, _ in SLICES])
def test_golden_files_byte_exact(name, loader):
    """断言 ⑤：两个 qa 真实切片各前 5 条渲染与黄金文件逐字节一致（许可均 MIT）。"""
    items = loader()[:5]
    blob = _golden_blob(items).encode("utf-8")
    path = GOLDEN_DIR / f"{name}.txt"
    if os.environ.get("UEP_UPDATE_GOLDENS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    assert path.exists(), f"缺黄金文件 {path.name}——UEP_UPDATE_GOLDENS=1 生成并提交评审"
    assert (
        path.read_bytes() == blob
    ), f"渲染与黄金文件不一致（若渲染变更属预期，重新生成 {path.name}）"
