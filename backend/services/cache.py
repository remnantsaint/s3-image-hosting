from functools import lru_cache

from redis import Redis

from backend.core.config import get_settings

settings = get_settings()

@lru_cache
def get_redis_client() -> Redis:
    """创建并缓存Redis客户端。"""

    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value(),

        # 读取字符串时直接返回str，而不是bytes
        decode_responses=True,

        # Redis无法连接时尽快报错，避免请求长时间等待
        socket_connect_timeout=3,
        socket_timeout=3,

        # 定期发送PING，检查连接是否仍然有效
        health_check_interval=30,
    )