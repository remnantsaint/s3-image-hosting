# 统一检查用户是否已经登录，并把当前登录的用户对象提供给受保护接口。
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.security import decode_access_token
from backend.db.session import get_db
from backend.models.user import User


# 从Authorization请求头中读取 Bearer Token
bearer_scheme = HTTPBearer(
    auto_error=False,
)

# 获取当前请求使用的数据库会话
DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]

# 获取HTTPBearer解析出来的认证信息
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def get_current_user(
    credentials: BearerCredentials,
    db: DatabaseSession,
) -> User:
    """验证JWT，并查询当前登录用户。"""

    # 请求没有携带Bearer Token
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 解析JWT中的sub字段
    subject = decode_access_token(
        credentials.credentials
    )

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 登录时放入sub的是用户ID字符串
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # 根据JWT中的用户ID查询数据库
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


# 后面的受保护接口可以直接使用CurrentUser
CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]