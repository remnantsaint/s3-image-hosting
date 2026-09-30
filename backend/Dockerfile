# 使用与本地环境一致的Python版本
FROM python:3.12.14-slim

# 不生成.pyc文件，并立即输出日志
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 容器中的项目目录
WORKDIR /app

# 先复制依赖文件，可以利用Docker构建缓存
COPY backend/requirements.txt ./backend/requirements.txt

# 安装正式运行依赖，不安装pytest等开发依赖
RUN python -m pip install \
    --no-cache-dir \
    -r backend/requirements.txt

# 复制后端源码和Alembic配置
COPY backend ./backend
COPY alembic.ini ./alembic.ini

EXPOSE 8000

# 启动前执行数据库迁移，然后启动FastAPI。backend只接受Docker内部Nginx转发的请求，因此可以信任代理请求头
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*"]


# 做一个包含全部本地代码的镜像，修改代码后需要重新构建镜像
# 用 docker compose up -d --build backend 来重新构建镜像，并创建启动容器