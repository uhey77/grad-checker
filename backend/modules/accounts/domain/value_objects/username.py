"""ログイン名の制約と正規化。"""

import re


def normalize_username(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_]{3,32}", value) is None:
        raise ValueError("invalid_username")
    return value.lower()
