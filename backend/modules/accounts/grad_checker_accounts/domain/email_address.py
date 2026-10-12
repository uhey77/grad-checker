"""自己登録で利用できる大学メールアドレスの制約。"""

import re

REGISTRATION_DOMAIN = "edu.teu.ac.jp"
LOCAL_PART = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
)


def validate_registration_email(value: str) -> str:
    """完全一致のドメインのみ許可し、ドメイン部分の大小文字を揃える。"""
    if not isinstance(value, str) or value.count("@") != 1:
        raise ValueError("invalid_registration_email")
    local, domain = value.split("@")
    if (
        len(local) > 64
        or len(value) > 254
        or LOCAL_PART.fullmatch(local) is None
        or domain.lower() != REGISTRATION_DOMAIN
    ):
        raise ValueError("invalid_registration_email")
    return f"{local}@{REGISTRATION_DOMAIN}"
