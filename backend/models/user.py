from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class User(Base):
    """用户表，保存登录账户的基本信息。"""

    # 对应 MySQL 中的表名
    __tablename__ = "users"

    # 用户唯一编号，由数据库自动递增
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # 用户名和邮箱都不允许重复
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # 只保存加密后的密码，绝不能保存明文密码
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 用于控制账户是否允许登录
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("1"),
        nullable=False,
    )

    # 创建用户时，由数据库自动写入时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    # 修改用户信息时，自动更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )