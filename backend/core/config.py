from functools import lru_cache
from pathlib import Path
from pydantic import SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict


# 找到项目根目录，用于定位根目录下的.env
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """集中管理应用配置和数据库配置。"""

    app_name: str = "S3 Image Hosting"
    app_env: str = "development"
    debug: bool = True

    # MySQL连接信息，对应.env中的环境变量
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "image_hosting"
    mysql_user: str = "image_hosting"
    mysql_password: str

    # JWT身份认证配置
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # 后端访问Garage使用的内部地址
    s3_endpoint_url: str = "http://127.0.0.1:3900"
    # 返回给浏览器的Garage公开地址
    s3_public_endpoint_url: str = "http://127.0.0.1:3900"
    s3_region: str = "garage"
    s3_access_key_id: str
    s3_secret_access_key: SecretStr
    s3_bucket: str = "image-hosting"
    s3_force_path_style: bool = True

    # Redis连接配置，用于缓存和接口限流
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """读取并缓存配置，避免每次请求重复解析.env。"""

    return Settings()