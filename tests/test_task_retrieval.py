"""retrieval 原型（FR-2.5）——单元层双语夹具：语料两形态与相关性载荷。"""

import pytest
from pydantic import ValidationError

from uep.schema import EvalItem, RetrievalTask, RetrievalVerifier

_ZH = {
    "id": "retr_zh_001",
    "lang": ["zh-CN"],
    "task": {
        "type": "retrieval",
        "query": "长江的主要支流有哪些？",
        "corpus": {
            "docs": [
                {"doc_id": "d1", "title": "汉江", "text": "汉江是长江最长的支流。"},
                {"doc_id": "d2", "title": "黄河", "text": "黄河是中国第二长河。"},
            ]
        },
    },
    "verifiers": [{"type": "retrieval", "relevance": [{"doc_id": "d1", "grade": 1}]}],
}


@pytest.mark.fr("FR-2.5")
class TestRetrievalPrototype:
    def test_zh_inline_corpus_item_valid(self):
        item = EvalItem.model_validate(_ZH)
        assert isinstance(item.task, RetrievalTask)
        verifier = item.verifiers[0]
        assert isinstance(verifier, RetrievalVerifier)
        assert verifier.metrics == ["ndcg@10"], "判分指标默认自含"
        assert verifier.relevance[0].doc_id == "d1"

    def test_reference_corpus_form_valid(self):
        item = EvalItem.model_validate(_ZH).model_dump()
        item["task"]["corpus"] = {"uri": "hf:example/corpus"}
        assert EvalItem.model_validate(item).task.corpus.uri == "hf:example/corpus"

    def test_corpus_requires_exactly_one_form(self):
        both = EvalItem.model_validate(_ZH).model_dump()
        both["task"]["corpus"]["uri"] = "hf:example/corpus"
        with pytest.raises(ValidationError, match="之一"):
            EvalItem.model_validate(both)
        neither = EvalItem.model_validate(_ZH).model_dump()
        neither["task"]["corpus"] = {}
        with pytest.raises(ValidationError, match="之一"):
            EvalItem.model_validate(neither)

    def test_empty_relevance_rejected(self):
        bad = EvalItem.model_validate(_ZH).model_dump()
        bad["verifiers"][0]["relevance"] = []
        with pytest.raises(ValidationError):
            EvalItem.model_validate(bad)

    def test_serialization_roundtrip_lossless(self):
        item = EvalItem.model_validate(_ZH)
        again = EvalItem.model_validate_json(item.model_dump_json())
        assert again.model_dump() == item.model_dump()
