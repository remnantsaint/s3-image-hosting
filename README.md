# S3 Image Hosting

一个可自行部署的全栈图片托管系统，面向个人或小范围团队使用。系统提供用户注册登录、图片上传与管理、临时访问链接、固定分享链接、访问限流等功能，并通过 Docker Compose 统一编排前端、后端、数据库、缓存、对象存储和反向代理。

## 功能概览

- Vue 3 前端：注册、登录、退出、图片上传、图库浏览和图片删除
- JWT 身份认证：不同用户只能管理自己的图片
- 图片校验：支持 JPEG、PNG、GIF、WebP，限制文件大小并校验文件真实类型
- 分离存储：MySQL 保存图片元数据，Garage 保存图片文件
- 临时访问：使用 S3 预签名 URL 生成限时访问地址
- 固定分享：可为图片创建、复制和取消固定分享链接
- Redis 限流：限制暴力登录和高频恶意上传
- Alembic 数据库迁移：用版本化脚本维护表结构
- Pytest 自动化测试：覆盖健康检查、认证、限流和图片主要接口
- Docker Compose：统一启动 MySQL、Redis、Garage、FastAPI 和 Nginx
- Nginx：托管生产版前端，并为 API 和公开分享链接提供统一入口

## 系统架构

```text
                         ┌─────────────────────┐
                         │      Browser        │
                         └──────────┬──────────┘
                                    │ :8080
                         ┌──────────▼──────────┐
                         │       Nginx         │
                         │  /      Vue 静态资源 │
                         │  /api/* FastAPI API │
                         │  /s/*   公开分享入口 │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │      FastAPI        │
                         └───┬────────┬────────┘
                             │        │
                    ┌────────▼─┐  ┌───▼─────┐
                    │  MySQL   │  │  Redis  │
                    │ 元数据    │  │  限流    │
                    └──────────┘  └─────────┘
                             │
                    ┌────────▼────────┐
                    │ Garage（S3 API） │
                    │ 图片文件         │
                    └─────────────────┘
```

访问固定分享链接 `/s/{share_token}` 时，后端会生成新的短期 S3 预签名 URL，并通过 HTTP 307 重定向到 Garage。固定分享地址本身保持不变，直到用户主动取消分享或删除图片。

## 技术栈

| 分类 | 技术 |
| --- | --- |
| 后端 | Python、FastAPI、SQLAlchemy、Pydantic、Alembic |
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Axios、Element Plus |
| 数据库 | MySQL 8.4 |
| 缓存与限流 | Redis |
| 对象存储 | Garage、Boto3、S3 兼容 API |
| 认证 | JWT、Argon2 密码哈希 |
| 测试 | Pytest、FastAPI TestClient |
| 部署 | Docker、Docker Compose、Nginx |

## 项目结构

```text
s3-image-hosting/
├── backend/                 # FastAPI 后端
│   ├── api/                 # 认证、用户、图片和分享接口
│   ├── core/                # 配置、安全、限流等基础能力
│   ├── db/                  # 数据库连接与模型基类
│   ├── models/              # SQLAlchemy 数据模型
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 对象存储等业务服务
│   └── main.py              # FastAPI 应用入口
├── frontend/                # Vue 3 前端
│   ├── src/api/             # 前端 API 请求封装
│   ├── src/components/      # 图片上传、图片列表等组件
│   ├── src/router/          # 页面路由
│   ├── src/stores/          # Pinia 状态管理
│   └── src/views/           # 登录、注册和图库页面
├── migrations/              # Alembic 数据库迁移脚本
├── nginx/                   # Nginx 配置和前端生产镜像
├── tests/                   # 自动化接口测试
├── .env.example             # 环境变量模板及部署说明
├── docker-compose.yml       # 全部服务编排配置
├── garage.toml              # Garage 单节点开发配置
├── alembic.ini              # Alembic 配置
├── requirements.txt         # 后端运行依赖
└── requirements-dev.txt     # 测试依赖
```

## 快速启动（推荐）

### 1. 环境要求

- Docker Desktop 或 Docker Engine
- Docker Compose v2
- Git（用于下载代码）

完整 Docker 启动不要求本机安装 Python、MySQL、Redis、Garage 或 Node.js。

### 2. 创建环境变量文件

Linux、macOS 或 Git Bash：

```bash
cp .env.example .env
```

PowerShell：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，至少替换数据库密码、JWT 密钥、Garage RPC 密钥和 S3 访问密钥。`.env.example` 末尾提供了本地与服务器环境的配置说明以及密钥生成命令。

> 不要将 `.env` 提交到 Git 仓库。项目的 `.gitignore` 已忽略该文件。

### 3. 构建并启动全部服务

```bash
docker compose up -d --build
```

查看运行状态：

```bash
docker compose ps
```

首次启动时，系统会自动执行数据库迁移，并初始化 Garage 所需的 bucket 和访问密钥。

### 4. 访问系统

默认地址如下：

| 内容 | 地址 |
| --- | --- |
| Web 页面 | <http://127.0.0.1:8080/> |
| Swagger API 文档 | <http://127.0.0.1:8080/docs> |
| 应用健康检查 | <http://127.0.0.1:8080/api/health> |

如果修改了 `APP_HOST_PORT`，请将地址中的 `8080` 替换为实际端口。

## 基本使用流程

1. 打开 Web 页面并注册账号。
2. 登录后上传 JPEG、PNG、GIF 或 WebP 图片。
3. 在“我的图片”中预览、分页浏览或删除图片。
4. 需要短期访问时复制临时链接。
5. 需要长期对外分享时创建固定分享链接。
6. 不再分享时取消固定链接；删除图片也会同时使其分享链接失效。

默认情况下，图片属于私有资源。其他用户无法查看或修改图片，只有主动创建的固定分享链接可以免登录访问。

## 前端开发

本地开发时，可以让 Docker 中的后端与基础服务继续运行，只单独启动 Vite 开发服务器：

```bash
cd frontend
npm ci
npm run dev
```

开发页面默认位于 <http://127.0.0.1:5173/>。修改 Vue 文件后，Vite 会自动热更新。

需要注意：

- `5173` 显示本地实时开发页面。
- `8080` 显示 Nginx 镜像中最近一次构建的生产页面。
- 修改前端后若希望 `8080` 同步更新，需要重新构建 Nginx：

```bash
docker compose up -d --build nginx
```

前端质量检查：

```bash
npm run lint
npm run build
```

`npm run build` 会执行 TypeScript 类型检查，并在 `frontend/dist/` 生成可部署的静态文件。

## 后端本地开发

如需在 Conda 环境中调试 FastAPI，可只使用 Docker 启动依赖服务：

```bash
docker compose up -d mysql redis garage
```

创建并激活环境后安装依赖：

```bash
conda create -n s3-image-hosting python=3.12
conda activate s3-image-hosting
pip install -r requirements-dev.txt
```

执行数据库迁移并启动后端：

```bash
python -m alembic upgrade head
uvicorn backend.main:app --reload
```

本地后端默认地址为 <http://127.0.0.1:8000/>，API 文档位于 <http://127.0.0.1:8000/docs>。

## 自动化测试

测试前应确保 MySQL、Redis 和 Garage 正常运行，并且它们使用的账号、密码与当前 `.env` 一致：

```bash
docker compose up -d mysql redis garage
python -m pytest -v
```

当前测试覆盖：

- 应用、数据库、Redis 和对象存储健康检查
- 用户注册、登录和 JWT 认证
- 登录与上传限流
- 图片上传、查询、访问和删除等主要流程

## 主要接口

下表使用通过 Nginx 访问时的公开路径：

| 方法 | 路径 | 说明 | 是否需要登录 |
| --- | --- | --- | --- |
| GET | `/api/health` | 应用健康检查 | 否 |
| GET | `/api/health/database` | MySQL 健康检查 | 否 |
| GET | `/api/health/storage` | Garage 健康检查 | 否 |
| GET | `/api/health/redis` | Redis 健康检查 | 否 |
| POST | `/api/auth/register` | 注册用户 | 否 |
| POST | `/api/auth/login` | 登录并获取 JWT | 否 |
| GET | `/api/users/me` | 获取当前用户 | 是 |
| POST | `/api/images` | 上传图片 | 是 |
| GET | `/api/images` | 分页查询个人图片 | 是 |
| GET | `/api/images/{id}/url` | 获取临时访问链接 | 是 |
| DELETE | `/api/images/{id}` | 删除图片 | 是 |
| POST | `/api/images/{id}/share` | 创建或获取固定分享链接 | 是 |
| DELETE | `/api/images/{id}/share` | 取消固定分享链接 | 是 |
| GET | `/s/{share_token}` | 访问公开分享图片 | 否 |

FastAPI 自带文档中显示的是后端内部路径，因此不会带 `/api` 前缀；`/api` 是 Nginx 对外转发时添加的统一入口。

## 环境变量说明

完整配置和部署示例见 `.env.example`。几个容易混淆的配置如下：

| 变量 | 用途 |
| --- | --- |
| `APP_BIND_HOST` | Nginx 在宿主机监听的地址，本地通常为 `127.0.0.1`，服务器需按访问范围设置 |
| `APP_HOST_PORT` | 用户访问 Web 系统的宿主机端口 |
| `PUBLIC_BASE_URL` | 生成固定分享链接时使用的外部基础地址 |
| `MYSQL_HOST` / `MYSQL_PORT` | 本机运行 FastAPI 时连接 MySQL 使用的地址和端口 |
| `MYSQL_BIND_HOST` / `MYSQL_HOST_PORT` | Docker 将 MySQL 暴露到宿主机时使用的监听地址和端口 |
| `S3_ENDPOINT_URL` | 本机运行 FastAPI 时连接 Garage 的内部操作地址 |
| `S3_PUBLIC_ENDPOINT_URL` | 浏览器最终访问临时预签名 URL 时使用的外部 Garage 地址 |
| `REDIS_HOST` / `REDIS_PORT` | 本机运行 FastAPI 时连接 Redis 使用的地址和端口 |
| `REDIS_BIND_HOST` / `REDIS_HOST_PORT` | Docker 将 Redis 暴露到宿主机时使用的监听地址和端口 |

容器内的后端会通过 Compose 服务名 `mysql`、`redis`、`garage` 连接其他容器；这些值已在 `docker-compose.yml` 中覆盖，不需要手动写进镜像。

## 部署到 Linux 服务器

服务器只需要安装 Docker 与 Docker Compose，Git 仅用于下载和更新代码。详细部署检查清单已经写在 `.env.example` 末尾。

基本流程如下：

```bash
git clone <repository-url>
cd s3-image-hosting
cp .env.example .env
# 编辑 .env，填写生产环境地址、端口和随机密钥

docker compose up -d mysql redis garage
docker compose build backend nginx
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

如果服务器还运行其他项目，应在 `.env` 中选择未被占用的宿主机端口。例如将 `APP_HOST_PORT` 设置为 `18080` 后，可通过 `http://服务器公网IP:18080/` 访问。

还需要在云平台安全组或服务器防火墙中开放实际使用的 Web 端口，以及当前架构下浏览器访问 Garage 所需的 S3 公网端口。MySQL 和 Redis 端口不应向公网开放。

当前项目尚未配置域名和 HTTPS。若面向互联网长期使用，建议在外层增加 HTTPS 反向代理，并进一步收紧 Garage 端口的访问范围。

## 数据持久化

Docker Compose 使用命名卷保存数据：

- `mysql_data`：用户、图片元数据和分享令牌
- `redis_data`：Redis 持久化数据
- `garage_meta`：Garage 元数据
- `garage_data`：图片对象数据

停止或重新创建容器不会自动删除这些数据：

```bash
docker compose down
```

以下命令会删除容器和数据卷，数据库记录及图片都可能丢失，请谨慎执行：

```bash
docker compose down -v
```

## 常用命令

```bash
# 启动全部服务
docker compose up -d

# 重新构建后端与前端/Nginx
docker compose up -d --build backend nginx

# 查看容器状态
docker compose ps

# 查看全部服务日志
docker compose logs -f

# 查看后端日志
docker compose logs -f backend

# 执行数据库迁移
docker compose run --rm backend alembic upgrade head

# 停止服务但保留数据
docker compose down
```

## 安全说明与当前限制

- 用户密码使用 Argon2 哈希后保存，JWT 密钥和各服务密码必须使用随机强密钥。
- 图片默认私有，固定分享链接一旦创建，获得链接的人无需登录即可查看图片。
- 临时 S3 链接有效期较短；固定分享链接不会直接暴露永久 S3 权限。
- 当前允许公开注册，尚未实现管理员后台、注册审批、用户配额和存储用量统计。
- Garage 当前采用单节点、单副本配置，适合个人项目和小范围试用，不等同于高可用生产集群。
- 当前未包含 HTTPS、CDN、自动备份、监控告警和恶意内容审核。
- 在非 HTTPS 页面中，浏览器可能限制剪贴板 API；前端会直接显示固定分享地址，便于手动复制。

## 后续计划

- 管理员与用户管理功能
- 用户存储配额和图片用量统计
- 图片搜索、标签和批量操作
- 缩略图与图片压缩
- HTTPS、域名和 CDN 接入
- 数据备份、监控与日志完善
- 为固定分享流程补充更完整的自动化测试
