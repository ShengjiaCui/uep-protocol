import pytest

from scripts.crossrunner_compare import ConsistencyReport, compare


class TestCompare:
    def test_all_agree_all_correct(self):
        a = {"i1": True, "i2": True}
        b = {"i1": True, "i2": True}
        r = compare(a, b, label_a="lmeval", label_b="inspect")
        assert isinstance(r, ConsistencyReport)
        assert r.n == 2
        assert r.acc_a == 1.0 and r.acc_b == 1.0
        assert r.both_correct == 2 and r.both_wrong == 0
        assert r.a_only == 0 and r.b_only == 0
        assert r.agreement_rate == 1.0
        assert r.delta == 0.0
        assert r.disagreements == []

    def test_mixed_agreement_and_disagreement(self):
        a = {"i1": True, "i2": True, "i3": False, "i4": True}
        b = {"i1": True, "i2": False, "i3": False, "i4": False}
        r = compare(a, b, label_a="lmeval", label_b="inspect")
        assert r.n == 4
        assert r.acc_a == 0.75 and r.acc_b == 0.25
        assert r.both_correct == 1
        assert r.both_wrong == 1
        assert r.a_only == 2
        assert r.b_only == 0
        assert r.agreement_rate == 0.5
        assert r.delta == 0.5
        assert r.disagreements == ["i2", "i4"]

    def test_id_mismatch_raises(self):
        with pytest.raises(ValueError):
            compare({"i1": True}, {"i2": True}, label_a="x", label_b="y")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            compare({}, {}, label_a="x", label_b="y")
