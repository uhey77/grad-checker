"""ユーザー名の境界と正規化。"""

import pytest

from modules.accounts.grad_checker_accounts.domain.username import normalize_username


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ab",
        "a" * 33,
        "あいう",
        "abc-def",
        "a b",
        " abc",
        "abc\n",
        "abc@edu.teu.ac.jp",
        "ＡＢＣ",
    ],
)
def test_rejects_invalid_username(value):
    with pytest.raises(ValueError, match="invalid_username"):
        normalize_username(value)


@pytest.mark.parametrize("value", ["Ab_", "a" * 32, "123"])
def test_normalizes_username(value):
    assert normalize_username(value) == value.lower()
