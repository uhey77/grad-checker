"""Argon2idによるパスワードの保存・照合。"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from modules.accounts.grad_checker_accounts.application.auth import Passwords


class ArgonPasswords(Passwords):
    def __init__(self) -> None:
        self.hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
        # 未登録アカウントでも同じハッシュ照合を行う。
        self.dummy = self.hasher.hash("unused-dummy-password")

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        try:
            matched = self.hasher.verify(password_hash or self.dummy, password)
            return matched and password_hash is not None
        except VerificationError, InvalidHashError:
            return False
