"""認証ポリシー・アカウント・セッションの入出力。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Account(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    login_name: str


class SessionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    account: Account
    csrf_token: str
    expires_at: datetime


class StoredSession(BaseModel):
    model_config = ConfigDict(frozen=True)
    account: Account
    csrf_token_hash: str
    expires_at: datetime


class AuthPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_hours: int
    password_min_length: int
    password_max_length: int
    attempt_window_minutes: int
    attempt_limit: int
