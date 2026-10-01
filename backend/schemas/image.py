from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageResponse(BaseModel):
    """图片上传成功后，向前端返回的图片信息。"""

    id: int
    owner_id: int
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    # 允许Pydantic直接读取SQLAlchemy的Image对象
    model_config = ConfigDict(from_attributes=True)

# Pydantic 默认从字典读取数据，model_config = ConfigDict(from_attributes=True) 允许他从对象属性中读取数据
# 前端传来的 JSON 是字典数据，可以直接读取。
# 数据库查出来的是 SQLAlchemy 的 User 或 Image 对象，所以需要设置，通过对象属性访问数据


class ImageUrlResponse(BaseModel):
    """图片临时访问地址的返回格式。"""

    id: int
    url: str
    expires_in_seconds: int


class ImageListItemResponse(BaseModel):
    """图片列表中一张图片的信息。"""

    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    url: str
    # 固定分享链接；为None表示尚未分享
    share_url: str | None = None


class ImageListResponse(BaseModel):
    """带分页信息的图片列表。"""

    total: int
    page: int
    page_size: int
    items: list[ImageListItemResponse]


class ImageShareResponse(BaseModel):
    """创建固定分享链接后的响应格式。"""

    id: int
    share_url: str