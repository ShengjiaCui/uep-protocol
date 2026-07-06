"""Manifest 数据集卡模型（FR-4.2）。"""

import pytest
from pydantic import ValidationError

from uep.schema import Manifest

BASE = {
    "name": "demo-choices-zh",
    "license": "MIT",
    "languages": ["zh-CN"],
    "task_types": {"choices": 2},
    "size": 2,
    "origin": {"format": "demo_csv"},
    "description": {"zh": "演示用中文选择题集", "en": "Demo Chinese multiple-choice set"},
}


@pytest.mark.fr("FR-4.2")
class TestManifest:
    def test_valid_manifest(self):
        manifest = Manifest.model_validate(BASE)
        assert manifest.license == "MIT"
        assert manifest.task_types == {"choices": 2}

    def test_task_types_must_sum_to_size(self):
        with pytest.raises(ValidationError):
            Manifest.model_validate({**BASE, "size": 5})

    def test_license_required(self):
        data = dict(BASE)
        del data["license"]
        with pytest.raises(ValidationError):
            Manifest.model_validate(data)

    def test_bad_language_tag_rejected(self):
        with pytest.raises(ValidationError):
            Manifest.model_validate({**BASE, "languages": ["中文"]})


@pytest.mark.fr("FR-4.2")
class TestContainsPii:
    """旧 NFR4 承接（2026-07-05 用户裁决）：可选三态合规位，与 license 同哲学。"""

    def test_declared_true_roundtrips(self):
        manifest = Manifest.model_validate({**BASE, "contains_pii": True})
        assert manifest.contains_pii is True
        assert '"contains_pii":true' in manifest.model_dump_json(exclude_none=True)

    def test_declared_false_is_distinct_from_undeclared(self):
        declared = Manifest.model_validate({**BASE, "contains_pii": False})
        undeclared = Manifest.model_validate(BASE)
        assert declared.contains_pii is False
        assert undeclared.contains_pii is None, "缺省=未声明，不折叠成 false"
        assert "contains_pii" not in undeclared.model_dump_json(exclude_none=True)

    def test_non_boolean_rejected(self):
        with pytest.raises(ValidationError):
            Manifest.model_validate({**BASE, "contains_pii": "yes"})
