"""SciFact 真实切片导入（FR-2.5 集成层）——引用式语料 + 相关性载荷 + 无损反演。

切片为三表连接产物（配方与修订在 slices.lock.json）；语料保持引用式
（SPEC §3.5：大语料必须引用防 OOM），相关性标注全部自含在 Verifier。
"""

import pytest
from test_import_choices_real import load_slice

from uep.adapters import load_mapping, nfcorpus, scifact, t2ranking
from uep.equivalence import diff_paths, normalize_tree
from uep.schema import RetrievalTask


@pytest.mark.fr("FR-2.5")
class TestRetrievalRealImport:
    def test_full_slice_imports_and_validates(self):
        rows = load_slice("scifact")
        assert len(rows) >= 100
        items = scifact.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, RetrievalTask) for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids)

    def test_corpus_stays_by_reference(self):
        """引用式语料：uri 就位、无内联 docs（防 OOM 是协议义务）。"""
        for item in scifact.import_rows(load_slice("scifact")):
            assert item.task.corpus.uri and item.task.corpus.uri.startswith("hf:")
            assert item.task.corpus.docs is None

    def test_relevance_payload_self_contained(self):
        for item in scifact.import_rows(load_slice("scifact")):
            verifier = item.verifiers[0]
            assert verifier.type == "retrieval"
            assert verifier.relevance, f"{item.id}: 相关性标注为空"
            assert all(label.grade >= 0 for label in verifier.relevance)
            assert verifier.metrics == ["ndcg@10"]

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("scifact").mapping.covered_source_fields()
        for row in load_slice("scifact"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self):
        """qrels（int id）与查询文本逐字段还原。"""
        rows = load_slice("scifact")
        restored = scifact.export_rows(scifact.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"


@pytest.mark.fr("FR-2.5")
class TestT2RankingRealImport:
    """中文检索切片（Apache-2.0）——评审卡挂账议题兑现，双语平权在检索原型受检。"""

    def test_full_slice_imports_and_validates(self):
        rows = load_slice("t2ranking")
        assert len(rows) >= 100
        items = t2ranking.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, RetrievalTask) for item in items)
        assert all(item.lang == ["zh"] for item in items)

    def test_queries_are_chinese(self):
        items = t2ranking.import_rows(load_slice("t2ranking"))
        with_cjk = [item for item in items if any("一" <= ch <= "鿿" for ch in item.task.query)]
        assert len(with_cjk) == len(items), "中文切片的查询须含 CJK 字符"

    def test_corpus_stays_by_reference(self):
        for item in t2ranking.import_rows(load_slice("t2ranking")):
            assert item.task.corpus.uri and item.task.corpus.uri.startswith("hf:")
            assert item.task.corpus.docs is None

    def test_relevance_payload_self_contained(self):
        for item in t2ranking.import_rows(load_slice("t2ranking")):
            verifier = item.verifiers[0]
            assert verifier.type == "retrieval"
            assert verifier.relevance, f"{item.id}: 相关性标注为空"
            assert all(label.grade == 1 for label in verifier.relevance), "二元 qrels 应全为 1"

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("t2ranking").mapping.covered_source_fields()
        for row in load_slice("t2ranking"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self):
        rows = load_slice("t2ranking")
        restored = t2ranking.export_rows(t2ranking.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"


@pytest.mark.fr("FR-2.5")
class TestNfCorpusRealImport:
    """医学检索切片（CC-BY-SA-4.0）——字符串 doc id（MED-/PLAIN-），id_dtype=str 受检。"""

    def test_full_slice_imports_and_validates(self):
        rows = load_slice("nfcorpus")
        assert len(rows) >= 100
        items = nfcorpus.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, RetrievalTask) for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids)

    def test_corpus_stays_by_reference(self):
        for item in nfcorpus.import_rows(load_slice("nfcorpus")):
            assert item.task.corpus.uri and item.task.corpus.uri.startswith("hf:")
            assert item.task.corpus.docs is None

    def test_relevance_payload_self_contained(self):
        for item in nfcorpus.import_rows(load_slice("nfcorpus")):
            verifier = item.verifiers[0]
            assert verifier.type == "retrieval"
            assert verifier.relevance, f"{item.id}: 相关性标注为空"
            assert all(label.grade >= 0 for label in verifier.relevance)
            assert verifier.metrics == ["ndcg@10"]

    def test_doc_ids_are_string_typed(self):
        """字符串 doc id 是本集特征：反演须还原字符串（非数字化）。"""
        for item in nfcorpus.import_rows(load_slice("nfcorpus")):
            for label in item.verifiers[0].relevance:
                assert (
                    not label.doc_id.isdigit()
                ), f"NFCorpus doc id 应为 MED-/PLAIN- 形态: {label.doc_id}"

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("nfcorpus").mapping.covered_source_fields()
        for row in load_slice("nfcorpus"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self):
        """qrels（str id）与查询文本逐字段还原。"""
        rows = load_slice("nfcorpus")
        restored = nfcorpus.export_rows(nfcorpus.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"
