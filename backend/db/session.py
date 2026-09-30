# 创建 SQLAlchemy 数据引擎
# 管理数据库连接池
# 为后续接口提供数据库会话

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker
from backend.core.config import get_settings

settings = get_settings()

# 创建数据库地址，使用URL.create可以正确处理密码中的特殊字符
database_url = URL.create(
    drivername="mysql+pymysql",
    username=settings.mysql_user,
    password=settings.mysql_password,
    host=settings.mysql_host,
    port=settings.mysql_port,
    database=settings.mysql_database,
    query={"charset": "utf8mb4"},
)

# 创建数据库引擎，engine负责维护FastAPI与MySQL之间的连接池
engine = create_engine(
    database_url,
    pool_pre_ping=True,  # 使用连接前检查它是否仍然有效
    pool_recycle=3600,   # 定期回收长时间空闲的MySQL连接
)

# 创建 Session 工厂，后续每次数据库操作都会从这里创建Session
SessionLocal = sessionmaker(
    bind=engine, # 创建的 Session 都使用前面的 engine 连接 MySQL
    autoflush=False, # 执行查询前，不把尚未提交的修改刷新到数据库。
    expire_on_commit=False, # 提交数据后，Python 对象中的数据不会立即失效，可以继续访问其属性。
)

# get_db() 会暂时提供一个 Session
def get_db() -> Generator[Session, None, None]: # 注解表示是一个生成器
    """为一次请求创建数据库会话，并在请求结束后关闭。"""

    db = SessionLocal()

    try:
        yield db # yield 是暂时把 db 交给 FastAPI，然后暂停函数
    finally:
        db.close() # 无论接口怎么样，必须执行，避免数据库连接一直占用。