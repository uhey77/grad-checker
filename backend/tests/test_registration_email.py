"""大学ドメイン制限が類似ドメインや不正入力で回避されないことを確認する。"""

import pytest

from modules.accounts.grad_checker_accounts.domain.email_address import (
    validate_registration_email,
)


@pytest.mark.parametrize(
    "address",
    [
        "student@gmail.com",
        "student@teu.ac.jp",
        "student@sub.edu.teu.ac.jp",
        "student@edu.teu.ac.jp.example.com",
        "student@fakeedu.teu.ac.jp",
        "student@edu.teu.ac.jp.",
        "student@edu.teu.ac.jp\n",
        " student@edu.teu.ac.jp",
        "student@@edu.teu.ac.jp",
        "@edu.teu.ac.jp",
        ".student@edu.teu.ac.jp",
        "student..name@edu.teu.ac.jp",
        "Student <student@edu.teu.ac.jp>",
        "student＠edu.teu.ac.jp",
        "a" * 65 + "@edu.teu.ac.jp",
    ],
)
def test_rejects_other_domains_and_malformed_addresses(address: str) -> None:
    with pytest.raises(ValueError, match="invalid_registration_email"):
        validate_registration_email(address)


def test_allows_exact_domain_case_insensitively() -> None:
    assert (
        validate_registration_email("Student.Name@EDU.TEU.AC.JP")
        == "Student.Name@edu.teu.ac.jp"
    )
