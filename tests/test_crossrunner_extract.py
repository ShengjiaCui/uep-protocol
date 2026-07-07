import pytest

from scripts.crossrunner_extract import extract_number


class TestExtractNumber:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("The answer is 42.", "42"),
            ("首先 3+5=8，所以最终答案是 18", "18"),  # 取最后一个数值（求解式收尾约定）
            ("1,234 apples then 5,678", "5678"),  # 取最后一个、去千分位逗号
            ("no digits here", None),
            ("-7 degrees", "-7"),
            ("pi is about 3.14", "3.14"),  # 小数保留
            ("total: 1,000.50 dollars", "1000.50"),  # 逗号 + 小数
            ("", None),
        ],
    )
    def test_extract_last_number(self, text, expected):
        assert extract_number(text) == expected

    def test_none_input_is_safe(self):
        assert extract_number(None) is None
