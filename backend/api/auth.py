import hashlib
import logging
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.user import UserCreate, UserResponse
from backend.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from backend.schemas.auth import LoginRequest, TokenResponse
from redis.exceptions import RedisError
from backend.services.cache import get_redis_client

logger = logging.getLogger(__name__)

# 同一IP和用户名，60秒内最多允许5次密码失败
LOGIN_MAX_FAILED_ATTEMPTS = 5
LOGIN_RATE_LIMIT_SECONDS = 60


def create_login_rate_limit_key(
    username: str,
    client_ip: str,
) -> str:
    """根据用户名和IP生成Redis限流键。"""

    # 转换成哈希，避免直接在Redis键中保存用户名和IP
    identifier = (
        f"{client_ip}:{username.strip().lower()}"
    )
    identifier_hash = hashlib.sha256(
        identifier.encode("utf-8")
    ).hexdigest()

    return f"rate_limit:login:{identifier_hash}"

def check_login_rate_limit(key: str) -> None:
    """登录前检查当前失败次数是否已经达到限制。"""

    try:
        redis_client = get_redis_client()

        attempts = int(redis_client.get(key) or 0)

        if attempts >= LOGIN_MAX_FAILED_ATTEMPTS:
            # 获取这个限流记录还剩多少秒过期
            retry_after = redis_client.ttl(key)

            if retry_after <= 0:
                retry_after = LOGIN_RATE_LIMIT_SECONDS

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts",
                headers={
                    "Retry-After": str(retry_after),
                },
            )
    except RedisError:
        # Redis故障不阻止正常登录，只暂时失去限流保护
        logger.exception(
            "Failed to check login rate limit"
        )

def record_failed_login(key: str) -> None:
    """在Redis中增加一次登录失败记录。"""

    try:
        redis_client = get_redis_client()

        # pipeline中的命令会通过Redis事务一起执行：
        # 失败次数加一，并把有效期重新设置为60秒
        redis_client.pipeline(
            transaction=True
        ).incr(
            key
        ).expire(
            key,
            LOGIN_RATE_LIMIT_SECONDS,
        ).execute()
    except RedisError:
        # Redis故障时仍然允许登录流程继续
        logger.exception(
            "Failed to record login attempt"
        )


def clear_login_rate_limit(key: str) -> None:
    """登录成功后删除对应的失败计数。"""

    try:
        get_redis_client().delete(key)
    except RedisError:
        logger.exception(
            "Failed to clear login rate limit"
        )


# 该文件中的接口都以 /auth 开头
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

# 从 get_db() 获取一次请求所使用的数据库会话
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: DatabaseSession,
) -> User:
    """注册新用户，并将用户信息保存到数据库。"""

    # 检查用户名是否已经存在
    existing_username = db.scalar(
        select(User.id).where(
            User.username == user_data.username,
        )
    )

    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )

    # 将邮箱统一转换为小写后再保存和查询
    normalized_email = str(user_data.email).lower()

    # 检查邮箱是否已经存在
    existing_email = db.scalar(
        select(User.id).where(
            User.email == normalized_email,
        )
    )

    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    # 创建 SQLAlchemy 用户对象
    new_user = User(
        username=user_data.username,
        email=normalized_email,
        password_hash=hash_password(
            user_data.password.get_secret_value()
        ),
    )

    # 将新用户加入当前数据库会话
    db.add(new_user)

    try:
        # 提交事务，真正把用户写入 MySQL
        db.commit()
    except IntegrityError as exc:
        # 提交失败后必须回滚，才能继续使用该数据库会话
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
        ) from exc

    # 重新读取数据库生成的 id、创建时间等字段
    db.refresh(new_user)

    return new_user

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    login_data: LoginRequest,
    request: Request,
    db: DatabaseSession,
) -> TokenResponse:
    """校验用户名和密码，登录成功后返回JWT。"""

    # 获取当前请求的客户端IP
    client_ip = (
        request.client.host
        if request.client is not None
        else "unknown"
    )
    rate_limit_key = create_login_rate_limit_key(
        username=login_data.username,
        client_ip=client_ip,
    )
    # 达到失败次数限制时，这里直接返回429
    check_login_rate_limit(rate_limit_key)

    # 根据用户名查询用户
    user = db.scalar(
        select(User).where(
            User.username == login_data.username,
        )
    )

    plain_password = login_data.password.get_secret_value()

    if user is None:
        # 即使用户不存在，也执行一次哈希校验
        verify_password(
            plain_password,
            DUMMY_PASSWORD_HASH,
        )

        # 用户不存在同样记为一次失败
        record_failed_login(rate_limit_key)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户输入的密码是否正确
    if not verify_password(
        plain_password,
        user.password_hash,
    ):
        # 密码错误，redis 失败次数加一
        record_failed_login(rate_limit_key)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 密码正确，清除之前的失败记录
    clear_login_rate_limit(rate_limit_key)

    # 被停用的账户不能登录
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # 将用户ID放入JWT的sub字段
    access_token = create_access_token(
        subject=str(user.id)
    )

    return TokenResponse(
        access_token=access_token,
    )