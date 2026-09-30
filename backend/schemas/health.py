# 定义健康检查接口的返回格式，使 Swagger 文档不再显示 additionalprop1
from pydantic import BaseModel

# 规范接口返回的格式
class HealthResponse(BaseModel):
    """应用健康检查的响应格式。"""

    status: str
    service: str
    environment: str


class DatabaseHealthResponse(BaseModel):
    """数据库健康检查的响应格式。"""

    status: str
    database: str
    version: str


class StorageHealthResponse(BaseModel):
    """对象存储健康检查的响应格式。"""

    status: str
    bucket: str


class RedisHealthResponse(BaseModel):
    """Redis健康检查的响应格式。"""

    status: str
    service: str