### S3 Image Hosting

一个基于 FastAPI 和 S3 兼容对象存储实现的后端图片存储服务。项目提供用户注册与登录、JWT 身份认证、图片上传与管理、临时访问链接、Redis 接口限流、自动化测试以及 Docker Compose 一键启动能力。

项目当前以后端为主，不包含前端页面

#### 主要功能

- 用户注册、登录和 JWT 身份认证
- JPEG、PNG、GIF、WebP 图片上传
- 10 MB 单文件大小限制和图片文件头校验
- 使用 Garage 保存图片文件，使用 MySQL 保存用户及图片元数据
- 分页查询当前用户的图片
- 生成有效期为 10 分钟的 S3 预签名访问链接
- 删除图片及其数据库记录
- 用户数据隔离，用户只能查看和删除自己的图片
- 基于 Redis 的登录失败限流和图片上传限流
- Alembic 数据库结构迁移
- Nginx 反向代理和请求大小限制
- Pytest 接口与集成测试

#### 技术栈

- Python 
- FastAPI、Uvicorn、Pydantic
- SQLAlchemy、Alembic、PyMySQL
- MySQL 
- Redis 
- Garage 
- Boto3
- Nginx
- Docker、Docker Compose
- Pytest

#### 系统架构

```text
                         ┌──────────────┐
浏览器 ── HTTP :8080 ──>│    Nginx     │
                         └──────┬───────┘
                                │ Docker内部网络
                         ┌──────▼───────┐
                         │   FastAPI    │
                         │ backend:8000 │
                         └───┬───┬───┬──┘
                             │   │   │
                    ┌────────┘   │   └─────────┐
                    ▼            ▼             ▼
                 MySQL         Redis         Garage
               业务元数据      接口限流       图片文件

浏览器也会使用预签名 URL，通过本机 3900 端口临时读取 Garage 中的图片。
```

在完整 Docker 模式下，FastAPI 不直接向宿主机暴露端口，外部请求统一经过 Nginx 转发。

#### 项目结构

```text
s3-image-hosting/
├── backend/
│   ├── api/                 # HTTP接口和依赖项
│   ├── core/                # 配置与安全工具
│   ├── db/                  # SQLAlchemy连接与模型基类
│   ├── migrations/          # Alembic数据库迁移
│   ├── models/              # SQLAlchemy数据模型
│   ├── schemas/             # Pydantic请求与响应模型
│   ├── services/            # Redis和S3客户端
│   ├── Dockerfile           # FastAPI镜像构建文件
│   ├── main.py              # FastAPI应用入口
│   ├── requirements.txt     # 正式运行依赖
│   └── requirements-dev.txt # 开发与测试依赖
├── nginx/
│   └── nginx.conf           # Nginx反向代理配置
├── tests/                   # 自动化测试
├── .env.example             # 环境变量示例
├── alembic.ini              # Alembic配置
├── docker-compose.yml       # 容器编排配置
└── garage.toml              # Garage单机开发配置
```

#### 快速启动

##### 1. 环境要求

- Docker Desktop
- Docker Compose

如果只使用完整 Docker 模式，不需要在宿主机另外安装 Python、MySQL、Redis 或 Garage。

##### 2. 创建环境变量文件

在项目根目录执行：

```bash
cp .env.example .env
```

打开 `.env`，将所有 `replace_...` 占位值替换成自己的随机密钥或密码。可以使用以下命令生成随机值：

```bash
# JWT密钥
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 普通随机密码
python -c "import secrets; print(secrets.token_urlsafe(24))"

# Garage要求的64位十六进制RPC密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

##### 3. 构建并启动全部服务

```bash
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

所有服务显示为 `healthy` 后，访问：

- Swagger API 文档：<http://127.0.0.1:8080/docs>
- 应用健康检查：<http://127.0.0.1:8080/health>

FastAPI 容器没有映射宿主机端口，`127.0.0.1:8080` 是项目的统一访问入口。

##### 4. 查看日志

```bash
# 查看全部服务日志
docker compose logs -f

# 只查看FastAPI日志
docker compose logs -f backend

# 只查看Nginx日志
docker compose logs -f nginx
```

按 `Ctrl+C` 只会退出日志查看，不会停止容器。

##### 5. 停止服务

```bash
docker compose down
```

该命令会删除容器和项目网络，但保留 MySQL、Redis 和 Garage 的命名数据卷。  

不要随意添加 `-v`，否则会同时删除数据库记录和已经上传的图片。

#### 本地开发

日常修改 Python 代码时，可以只用 Docker 运行基础设施，并在 Conda 环境中运行 FastAPI，以便使用自动重载。

##### 1. 启动基础设施

```bash
docker compose up -d mysql redis garage
```

此时根目录 `.env` 中的连接地址应保持为宿主机地址：

```text
MYSQL_HOST=127.0.0.1
REDIS_HOST=127.0.0.1
S3_ENDPOINT_URL=http://127.0.0.1:3900
S3_PUBLIC_ENDPOINT_URL=http://127.0.0.1:3900
```

完整 Docker 模式会通过 `docker-compose.yml` 覆盖内部连接地址，使 FastAPI 使用 `mysql`、`redis` 和 `garage` 等 Compose 服务名通信。

##### 2. 创建并安装开发环境

```bash
conda create -n s3-image-hosting python=3.12
conda activate s3-image-hosting
pip install -r backend/requirements-dev.txt
```

##### 3. 应用数据库迁移

```bash
python -m alembic upgrade head
```

##### 4. 启动 FastAPI

```bash
uvicorn backend.main:app --reload
```

本地开发模式的 API 文档地址为：<http://127.0.0.1:8000/docs>。

#### 自动化测试

测试会连接本地运行的 MySQL、Redis 和 Garage，因此需要先启动三个基础设施容器：

```bash
docker compose up -d mysql redis garage
python -m pytest -v
```

当前测试覆盖：

- 用户注册与重复信息校验
- 用户登录、JWT 签发和受保护接口
- 登录失败限流
- 四类健康检查
- 图片上传、列表、预签名访问和删除的完整生命周期
- 伪造图片拒绝
- 上传身份认证和请求限流
- 不同用户之间的图片访问隔离

测试使用随机用户名，并在结束后清理创建的测试用户和图片记录。

#### 主要接口

| 方法 | 路径 | 说明 | 是否需要登录 |
| --- | --- | --- | --- |
| `GET` | `/health` | 检查 FastAPI 状态 | 否 |
| `GET` | `/health/database` | 检查 MySQL 连接 | 否 |
| `GET` | `/health/storage` | 检查 Garage 连接 | 否 |
| `GET` | `/health/redis` | 检查 Redis 连接 | 否 |
| `POST` | `/auth/register` | 注册用户 | 否 |
| `POST` | `/auth/login` | 登录并获取 JWT | 否 |
| `GET` | `/users/me` | 获取当前用户信息 | 是 |
| `POST` | `/images` | 上传图片 | 是 |
| `GET` | `/images` | 分页查询当前用户图片 | 是 |
| `GET` | `/images/{image_id}/url` | 获取临时访问链接 | 是 |
| `DELETE` | `/images/{image_id}` | 删除图片 | 是 |

受保护接口需要携带请求头：

```text
Authorization: Bearer <access_token>
```

#### 数据存储说明

- MySQL 保存用户、密码哈希和图片元数据。
- Garage 保存真实图片文件，并提供 S3 兼容 API。
- Redis 保存短期登录失败计数和上传请求计数。
- Docker 命名数据卷保证容器重建后数据仍然保留。
- 图片默认是私有对象，只能通过有时效的预签名 URL 访问。

#### 常用命令

```bash
# 重新构建并启动FastAPI和Nginx
docker compose up -d --build backend nginx

# 查看所有容器状态
docker compose ps

# 停止某个服务
docker compose stop mysql

# 重新启动某个服务
docker compose start mysql

# 查看当前数据库迁移版本
python -m alembic current

# 根据模型变化生成新的迁移文件
python -m alembic revision --autogenerate -m "describe schema change"

# 将数据库升级到最新迁移
python -m alembic upgrade head
```

#### 当前限制

- 当前使用 Garage 单节点模式，适合本地开发和项目演示。
- 项目尚未配置前端页面、HTTPS、域名和 CDN。
- 预签名图片地址默认只在 10 分钟内有效。
- 自动化测试目前使用本地开发基础设施，而不是独立测试集群。
- 如果部署到公网，还需要增加用户存储配额、注册限流、日志轮转、备份和监控等能力。
