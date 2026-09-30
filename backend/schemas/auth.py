from pydantic import BaseModel, Field, SecretStr

class LoginRequest(BaseModel):
    """用户登录时提交的数据。"""

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_]+$",
    )

    password: SecretStr = Field(
        min_length=8,
        max_length=128,
    )


class TokenResponse(BaseModel):
    """登录成功后返回的访问令牌。"""

    access_token: str
    token_type: str = "bearer"