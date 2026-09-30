# 提供校验密码和生成JWT的方法
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from backend.core.config import get_settings


settings = get_settings()

# 使用 pwdlib 推荐的密码哈希算法，目前默认使用 Argon2
password_hash = PasswordHash.recommended()

# 用户不存在时仍然执行一次密码校验，降低用户名探测风险
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-user-password")


# 注册
def hash_password(plain_password: str) -> str:
    """将用户输入的明文密码转换为不可逆的哈希值。"""

    return password_hash.hash(plain_password)


# 用于登录校验，verify函数可以直接校验
def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """检查用户输入的密码是否与数据库中的哈希值匹配。"""

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(subject: str) -> str:
    """为登录成功的用户生成带有过期时间的JWT。"""

    current_time = datetime.now(timezone.utc)
    expire_time = current_time + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    # sub保存用户标识，iat和exp分别表示签发及过期时间
    payload = {
        "sub": subject,
        "iat": current_time,
        "exp": expire_time,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

def decode_access_token(token: str) -> str | None:
    """验证并解析JWT，成功时返回令牌中的用户标识。"""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError:
        # 令牌伪造、格式错误或已经过期时都会进入这里
        return None

    subject = payload.get("sub")

    # JWT中的sub应当是字符串
    if not isinstance(subject, str):
        return None

    return subject