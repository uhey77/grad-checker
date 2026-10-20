from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuthCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["register", "recover", "login", "session", "logout", "config"]
    login_name: str = Field(default="", max_length=32)
    recovery_code: str = Field(default="", max_length=128)
    password: str = Field(default="", max_length=1024)
    token: str = Field(default="", max_length=128)
    csrf: str = Field(default="", max_length=128)
    client_key: str = Field(default="", max_length=128)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        required = {
            "config": set(),
            "register": {"login_name", "password", "client_key"},
            "recover": {"login_name", "recovery_code", "password", "client_key"},
            "login": {"login_name", "password", "client_key"},
            "session": {"token"},
            "logout": {"token", "csrf"},
        }[self.operation]
        for field in (
            "login_name",
            "recovery_code",
            "password",
            "token",
            "csrf",
            "client_key",
        ):
            if bool(getattr(self, field)) != (field in required):
                raise ValueError("operation and arguments do not match")
        return self
