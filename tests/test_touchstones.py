"""choices 试金石断言集（FR-2.6，测试规格书 §①）——真实切片全绿 + 黄金文件逐字节一致。

黄金文件维护：渲染或映射表变更后运行
``UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones.py`` 重新生成并提交评审。
"""

import os
from pathlib import Path

import pytest
from test_import_choices_real import ADAPTERS, load_slice

from touchstones.render_choices import RenderedChoice, TouchstoneError, render
from uep.schema import EvalItem

GOLDEN_DIR = Path(__file__).parent / "golden" / "choices"

#: NC 许可数据集的内容摘录不入库——黄金文件跳过，但断言集测试仍全量覆盖
_NC_ADAPTERS = {"ceval", "beavertails"}  # CC-BY-NC(-SA)：从严无 golden
GOLDEN_ADAPTERS = [(name, adapter) for name, adapter in ADAPTERS if name not in _NC_ADAPTERS]

_SYNTH = {
    "id": "touch_zh_001",
    "lang": ["zh-CN"],
    "task": {
        "type": "choices",
        "question": "长江流经下列哪个城市？",
        "options": [{"id": "A", "text": "北京"}, {"id": "B", "text": "武汉"}],
    },
    "verifiers": [{"type": "choice_match", "answer_ids": ["B"]}],
}


def _golden_blob(items: list[EvalItem]) -> str:
    blocks = []
    for item in items:
        rendered = render(item)
        blocks.append(
            f"### {item.id}\n{rendered.text}\n>>> 正确: {', '.join(rendered.correct_ids)}\n"
        )
    return "\n".join(blocks)


@pytest.mark.fr("FR-2.6")
class TestTouchstoneAssertions:
    @pytest.mark.parametrize(("name", "adapter"), ADAPTERS, ids=[n for n, _ in ADAPTERS])
    def test_assertion_set_on_full_real_slice(self, name, adapter):
        """断言 1–4 对全部真实切片条目成立（测试规格书 §①）。"""
        items = adapter.import_rows(load_slice(name))
        for item in items:
            rendered = render(item)
            # ① 题干一致且非空
            assert rendered.question == item.task.question
            assert rendered.question
            # ② 选项数量与顺序一致（顺序是语义，不得重排）
            assert rendered.options == [(o.id, o.text) for o in item.task.options]
            # ③ correct_ids ⊆ 选项 id 集合
            assert set(rendered.correct_ids) <= {oid for oid, _ in rendered.options}
            # ④ text 含题干与全部选项文本
            assert rendered.question in rendered.text
            for _, text in rendered.options:
                assert text in rendered.text

    def test_correct_ids_taken_from_choice_match(self):
        rendered = render(EvalItem.model_validate(_SYNTH))
        assert isinstance(rendered, RenderedChoice)
        assert rendered.correct_ids == ["B"]

    def test_non_choices_item_rejected(self):
        qa = dict(_SYNTH, task={"type": "qa", "question": "长江有多长？"})
        qa["verifiers"] = [{"type": "text_match", "expected": "约6300公里"}]
        with pytest.raises(TouchstoneError):
            render(EvalItem.model_validate(qa))

    def test_missing_choice_match_rejected(self):
        bad = dict(_SYNTH, verifiers=[{"type": "text_match", "expected": "B"}])
        with pytest.raises(TouchstoneError):
            render(EvalItem.model_validate(bad))

    def test_answer_outside_options_rejected(self):
        bad = dict(_SYNTH, verifiers=[{"type": "choice_match", "answer_ids": ["Z"]}])
        with pytest.raises(TouchstoneError):
            render(EvalItem.model_validate(bad))


@pytest.mark.fr("FR-2.6")
@pytest.mark.parametrize(("name", "adapter"), GOLDEN_ADAPTERS, ids=[n for n, _ in GOLDEN_ADAPTERS])
def test_golden_files_byte_exact(name, adapter):
    """断言 ⑤：三个真实切片各前 5 条的渲染与黄金文件逐字节一致。"""
    items = adapter.import_rows(load_slice(name))[:5]
    blob = _golden_blob(items).encode("utf-8")
    path = GOLDEN_DIR / f"{name}.txt"
    if os.environ.get("UEP_UPDATE_GOLDENS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    assert path.exists(), f"缺黄金文件 {path.name}——UEP_UPDATE_GOLDENS=1 生成并提交评审"
    assert (
        path.read_bytes() == blob
    ), f"渲染与黄金文件不一致（若渲染变更属预期，重新生成 {path.name}）"
