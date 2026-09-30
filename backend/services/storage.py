# 根据.env中的地址和密钥创建S3客户端
from functools import lru_cache
import boto3
from botocore.client import BaseClient
from botocore.config import Config
from backend.core.config import get_settings

settings = get_settings()

def create_s3_client(
    endpoint_url: str,
) -> BaseClient:
    """根据指定地址创建S3客户端。"""

    addressing_style = (
        "path" if settings.s3_force_path_style else "virtual"
    )

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=(
            settings.s3_secret_access_key.get_secret_value()
        ),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": addressing_style},
        ),
    )

@lru_cache
def get_s3_client() -> BaseClient:
    """创建后端访问Garage时使用的内部客户端。"""

    return create_s3_client(
        settings.s3_endpoint_url
    )

@lru_cache
def get_s3_public_client() -> BaseClient:
    """创建生成浏览器临时链接时使用的客户端。"""

    return create_s3_client(
        settings.s3_public_endpoint_url
    )