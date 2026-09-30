from logging.config import fileConfig

from alembic import context

# 导入所有模型，确保 Alembic 能发现 User 等数据库表
import backend.models
from backend.db.base import Base
from backend.db.session import database_url, engine


# Alembic 当前使用的配置对象
config = context.config

# 使用 alembic.ini 中的日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic 会将这些模型描述的表结构与数据库进行比较
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线生成迁移 SQL，不直接连接数据库。"""

    context.configure(
        url=database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """连接 MySQL，并执行或生成数据库迁移。"""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据执行模式选择迁移方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()