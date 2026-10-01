# 第一阶段：使用Node构建Vue生产文件
FROM node:22-alpine AS frontend-build

WORKDIR /app

# 先复制依赖清单，依赖没有变化时可以复用Docker缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 复制前端源码并生成dist目录
COPY frontend/ ./
RUN npm run build


# 第二阶段：使用Nginx提供前端页面并代理后端接口
FROM nginx:1.28-alpine

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html
