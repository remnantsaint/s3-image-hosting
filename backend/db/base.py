# 提供所有数据库模型共同继承的基类

from sqlalchemy.orm import DeclarativeBase

# 所有数据库模型都要继承这个 Base
# Alembic 也会通过 Base 找到项目中的表结构
class Base(DeclarativeBase):
    pass