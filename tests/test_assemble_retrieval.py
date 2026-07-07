"""retrieval 试金石断言集（FR-2.6 同构复制）——真实切片全绿 + 黄金文件。

黄金文件维护：``UEP_UPDATE_GOLDENS=1 pytest tests/test_assemble_retrieval.py``。
切片许可 CC-BY-SA-4.0（英文集，此署名即归属）/ Apache-2.0（中文集）——黄金摘录
均可入库（归属账本见 tests/golden/choices/README.md）。
"""

import os
from pathlib import Path

import pytest
from test_import_choices_real import load_slice
from test_task_retrieval import _ZH

from touchstones import TouchstoneError
from touchstones.assemble_retrieval import AssembledRetrieval, assemble
from uep.adapters import nfcorpus, scifact, t2ranking
from uep.schema import EvalItem

GOLDEN_DIR = Path(__file__).parent / "golden" / "retrieval"
#: (切片名, 适配器)——英文集 + 中文集 + 医学检索（字符串 id），双语平权在检索试金石上受检
SLICES = [("scifact", scifact), ("t2ranking", t2ranking), ("nfcorpus", nfcorpus)]
_SLICE_IDS = [name for name, _ in SLICES]


@pytest.mark.fr("FR-2.6")
class TestAssembleRetrievalAssertions:
    @pytest.mark.parametrize(("name", "adapter"), SLICES, ids=_SLICE_IDS)
    def test_assertion_set_on_full_real_slice(self, name, adapter):
        """组装单自含：查询/语料引用/相关性/指标逐项与条目一致。"""
        for item in adapter.import_rows(load_slice(name)):
            assembled = assemble(item)
            verifier = item.verifiers[0]
            # ① 查询一致且非空
            assert assembled.query == item.task.query and assembled.query
            # ② 相关性与指标逐项来自 Verifier（单一事实源）
            assert assembled.relevance == [(r.doc_id, r.grade) for r in verifier.relevance]
            assert assembled.metrics == verifier.metrics
            # ③ 引用式语料带出
            assert assembled.corpus_ref == item.task.corpus.uri
            assert assembled.doc_count is None
            # ④ text 含查询、语料引用与全部相关 id
            assert assembled.query in assembled.text
            assert assembled.corpus_ref in assembled.text
            for doc_id, _ in assembled.relevance:
                assert doc_id in assembled.text

    def test_synthetic_zh_inline_corpus(self):
        assembled = assemble(EvalItem.model_validate(_ZH))
        assert isinstance(assembled, AssembledRetrieval)
        assert assembled.doc_count == 2 and assembled.corpus_ref is None
        assert "长江" in assembled.text

    def test_relevance_outside_inline_corpus_rejected(self):
        bad = EvalItem.model_validate(_ZH).model_dump()
        bad["verifiers"][0]["relevance"] = [{"doc_id": "d99", "grade": 1}]
        with pytest.raises(TouchstoneError, match="不在内联语料"):
            assemble(EvalItem.model_validate(bad))

    def test_non_retrieval_rejected(self):
        qa = {
            "id": "ar_bad_001",
            "lang": ["zh-CN"],
            "task": {"type": "qa", "question": "一加一等于几？"},
            "verifiers": [{"type": "text_match", "expected": "2"}],
        }
        with pytest.raises(TouchstoneError):
            assemble(EvalItem.model_validate(qa))


@pytest.mark.fr("FR-2.6")
@pytest.mark.parametrize(("name", "adapter"), SLICES, ids=_SLICE_IDS)
def test_golden_file_byte_exact(name, adapter):
    """真实切片前 5 条的组装渲染与黄金文件逐字节一致（两切片许可均允许入库）。"""
    items = adapter.import_rows(load_slice(name))[:5]
    blocks = [f"### {item.id}\n{assemble(item).text}\n" for item in items]
    blob = "\n".join(blocks).encode("utf-8")
    path = GOLDEN_DIR / f"{name}.txt"
    if os.environ.get("UEP_UPDATE_GOLDENS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    assert path.exists(), f"缺黄金文件 {path.name}——UEP_UPDATE_GOLDENS=1 生成并提交评审"
    assert path.read_bytes() == blob, f"渲染与黄金不一致（若属预期，重新生成 {path.name}）"
