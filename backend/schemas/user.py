# 定义注册用户的格式
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

class UserCreate(BaseModel):
    """注册用户时，前端需要提交的数据。"""

    # 用户名只能包含英文字母、数字和下划线
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_]+$",
    )

    # EmailStr 会检查邮箱格式是否合法
    email: EmailStr

    # SecretStr 可以避免密码在日志或调试输出中直接显示
    password: SecretStr = Field(
        min_length=8,
        max_length=128,
    )


class UserResponse(BaseModel):
    """注册成功后，接口可以返回给前端的用户信息。"""

    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # 允许 Pydantic 读取 SQLAlchemy User 对象
    model_config = ConfigDict(from_attributes=True)