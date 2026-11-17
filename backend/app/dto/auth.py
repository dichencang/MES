from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def password_bytes(value: str) -> str:
    if len(value.encode()) > 72:
        raise ValueError("密码超过 72 字节")
    return value


Password = Annotated[str, Field(min_length=1), AfterValidator(password_bytes)]


class AuthBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(AuthBody):
    username: str = Field(min_length=1, max_length=64)
    password: Password


class Refresh(AuthBody):
    refreshToken: str = Field(min_length=1, max_length=256)


class ChangePassword(AuthBody):
    oldPassword: Password
    newPassword: Password
