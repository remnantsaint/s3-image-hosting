# 在这里统一导出数据库模型，方便其他模块和Alembic加载
from backend.models.image import Image
from backend.models.user import User

__all__ = ["User", "Image"]


# 统一导出的作用：
# 用 from backend.models import User, Image 代替 from backend.models.image import Image 等等
