"""カリキュラムの適用範囲を確認できているかを表す状態。"""

from enum import StrEnum


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
