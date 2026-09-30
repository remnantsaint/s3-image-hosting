from fastapi import FastAPI
from backend.api.health import router as health_router
from backend.api.auth import router as auth_router
from backend.api.users import router as users_router
from backend.api.images import router as images_router
from backend.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name, # docs 显示名称
    version="0.3.0", # docs 显示版本号
    debug=settings.debug,
)

# 将健康检查路由注册到 FastAPI 应用
app.include_router(health_router)

# 将注册、登录等身份认证路由注册到 FastAPI 应用
app.include_router(auth_router)

# 将用户相关路由注册到 FastAPI 应用
app.include_router(users_router)

# 将图片上传和管理接口注册到FastAPI应用
app.include_router(images_router)