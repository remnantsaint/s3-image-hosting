# 负责四个接口：
# GET /health 检查FastAPI
# GET /health/database 检查MySQL连接
# GET /health/storage 检查Garage对象存储连接
# GET /health/redis 检查Redis连接

import logging
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.core.config import get_settings
from backend.db.session import engine
from backend.schemas.health import (
    DatabaseHealthResponse,
    HealthResponse,
    RedisHealthResponse,
    StorageHealthResponse,
)
from backend.services.storage import get_s3_client
from redis.exceptions import RedisError
from backend.services.cache import get_redis_client

logger = logging.getLogger(__name__) # 创建日志记录器
settings = get_settings() # 读取项目配置

# 创建一组路由，装饰器 @router.get() 最终访问地址会加上 /health
router = APIRouter(
    prefix="/health", # 表示这个 router 中的所有接口都自动以 /health 开头
    tags=["system"], # 表示在 /docs 接口文档中，把这些接口放进 system 分组
)
# 还需要在主程序注册： app.include_router(router)


# response_model 表示接口向外返回的数据长什么样，HealthResponse 是在 schemas/health.py 定义的
@router.get("", response_model=HealthResponse) 
def health_check() -> HealthResponse:
    """检查FastAPI服务是否正常运行。"""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
    )


@router.get("/database", response_model=DatabaseHealthResponse)
def database_health_check() -> DatabaseHealthResponse:
    """执行简单SQL语句，确认MySQL可以正常连接。"""

    try:
        with engine.connect() as connection: # 从 SQLAlchemy 连接池取出一个数据库连接
            # 执行 SQL：SELECT DATABASE(), VERSION();
            row = connection.execute(
                text("SELECT DATABASE(), VERSION()")
            ).one() # 取出唯一的一行结果
    except SQLAlchemyError as exc:
        # 记录内部错误，但不把数据库密码等细节返回给用户
        # 且日志记录完整错误
        logger.exception("Database health check failed")

        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from exc

    # 成功时返回查询到的东西
    return DatabaseHealthResponse(
        status="ok",
        database=str(row[0]),
        version=str(row[1]),
    )


@router.get("/storage", response_model=StorageHealthResponse)
def storage_health_check() -> StorageHealthResponse:
    """检查Garage及目标存储桶是否可以正常访问。"""

    try:
        # 检查存储桶是否存在，同时验证访问密钥是否正确
        get_s3_client().head_bucket(Bucket=settings.s3_bucket)
    except (BotoCoreError, ClientError) as exc:
        # 在服务器日志中记录完整错误
        logger.exception("Object storage health check failed")

        # 只向外返回简单错误，避免泄露密钥等配置信息
        raise HTTPException(
            status_code=503,
            detail="Object storage is unavailable",
        ) from exc

    return StorageHealthResponse(
        status="ok",
        bucket=settings.s3_bucket,
    )


@router.get("/redis", response_model=RedisHealthResponse)
def redis_health_check() -> RedisHealthResponse:
    """发送PING命令，检查Redis是否可以正常连接。"""

    try:
        # Redis正常时，ping()会返回True
        is_alive = get_redis_client().ping()
    except RedisError as exc:
        logger.exception("Redis health check failed")

        raise HTTPException(
            status_code=503,
            detail="Redis is unavailable",
        ) from exc

    if not is_alive:
        raise HTTPException(
            status_code=503,
            detail="Redis is unavailable",
        )

    return RedisHealthResponse(
        status="ok",
        service="redis",
    )