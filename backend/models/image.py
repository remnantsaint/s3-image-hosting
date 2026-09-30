from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class Image(Base):
    """图片信息表，保存Garage对象与用户之间的对应关系。"""

    __tablename__ = "images"

    # 图片记录的唯一编号
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # 上传这张图片的用户
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # 图片在Garage中的唯一位置，例如：
    # users/3/2026/09/随机文件名.png
    object_key: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        index=True,
        nullable=False,
    )

    # 用户上传时的原始文件名
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 文件类型，例如 image/png、image/jpeg
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # 文件大小，单位是字节
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # 图片记录创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )