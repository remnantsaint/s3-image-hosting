# REST API 命名习惯：单个数据实体用单数，资源集合和接口路径用复数
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4
from sqlalchemy import func, select
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from backend.api.dependencies import CurrentUser, DatabaseSession
from backend.core.config import get_settings
from backend.models.image import Image
from backend.schemas.image import (
    ImageListItemResponse,
    ImageListResponse,
    ImageResponse,
    ImageUrlResponse,
)
from backend.services.storage import (
    get_s3_client,
    get_s3_public_client,
)
from redis.exceptions import RedisError
from backend.services.cache import get_redis_client


logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/images",
    tags=["images"],
)

# 单张图片最大允许上传10 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# 临时图片链接有效期为10分钟
PRESIGNED_URL_EXPIRE_SECONDS = 600

# 支持的图片类型，以及保存时使用的扩展名
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# 每个用户60秒内最多发起10次上传请求
UPLOAD_MAX_REQUESTS = 10
UPLOAD_RATE_LIMIT_SECONDS = 60


def check_upload_rate_limit(user_id: int) -> None:
    """检查当前用户是否超过图片上传频率限制。"""

    key = f"rate_limit:upload:user:{user_id}"

    try:
        redis_client = get_redis_client()

        # INCREX会原子地完成以下操作：
        # 1. 计数加一
        # 2. 第一次计数时设置60秒过期时间
        # 3. 计数最高不超过10
        result = redis_client.execute_command(
            "INCREX",
            key,
            "BYINT",
            1,
            "UBOUND",
            UPLOAD_MAX_REQUESTS,
            "EX",
            UPLOAD_RATE_LIMIT_SECONDS,
            "ENX",
        )

        current_count = int(result[0])
        actual_increment = int(result[1])

        # 达到上限后，Redis不会继续增加计数，
        # actual_increment会返回0
        if actual_increment == 0:
            retry_after = redis_client.ttl(key)

            if retry_after <= 0:
                retry_after = UPLOAD_RATE_LIMIT_SECONDS

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many image upload requests",
                headers={
                    "Retry-After": str(retry_after),
                },
            )

        logger.debug(
            "Upload rate limit count: user=%s count=%s",
            user_id,
            current_count,
        )
    except RedisError: 
        # Redis出现故障时仍允许上传，
        # 没有 raise 异常 不会停止
        # 避免Redis故障导致整个上传功能不可用
        logger.exception(
            "Failed to check upload rate limit"
        )


def has_valid_image_signature(
    content_type: str,
    content: bytes,
) -> bool:
    """根据文件开头的特征字节，初步判断是否是真实图片。"""

    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")

    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")

    if content_type == "image/gif":
        return content.startswith((b"GIF87a", b"GIF89a"))

    if content_type == "image/webp":
        return (
            len(content) >= 12
            and content[:4] == b"RIFF"
            and content[8:12] == b"WEBP"
        )

    return False


@router.post(
    "",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_image(
    current_user: CurrentUser,
    db: DatabaseSession,
    file: Annotated[
        UploadFile,
        File(description="需要上传的图片文件"),
    ],
) -> Image:
    """接收图片，上传到Garage，并把图片信息写入MySQL。"""

    # 在读取和处理图片之前先检查上传频率
    check_upload_rate_limit(current_user.id)

    content_type = file.content_type or ""

    # 目前只允许JPEG、PNG、GIF和WebP
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, GIF and WebP images are supported",
        )

    try:
        # 最多读取10 MB再多一个字节，用于判断文件是否超限
        content = file.file.read(MAX_IMAGE_SIZE + 1)
    finally:
        file.file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image size must not exceed 10 MB",
        )

    # 避免有人把非图片文件伪装成图片类型上传
    if not has_valid_image_signature(content_type, content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its image type",
        )

    extension = ALLOWED_IMAGE_TYPES[content_type]
    current_time = datetime.now(timezone.utc)

    # 使用用户ID、年月和随机UUID生成唯一的Garage对象路径
    object_key = (
        f"users/{current_user.id}/"
        f"{current_time:%Y/%m}/"
        f"{uuid4().hex}{extension}"
    )

    # 只保存原始文件名，不使用原始文件名作为Garage路径
    original_filename = Path(
        file.filename or f"unnamed{extension}"
    ).name[:255]

    try:
        # 将图片文件上传到Garage
        get_s3_client().put_object(
            Bucket=settings.s3_bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to upload image to object storage")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable",
        ) from exc

    # 创建MySQL图片记录
    new_image = Image(
        owner_id=current_user.id,
        object_key=object_key,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=len(content),
    )

    db.add(new_image)

    try:
        # 把图片信息正式写入MySQL
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()

        # MySQL保存失败时，删除刚才上传的Garage文件，
        # 避免产生没有数据库记录的孤立文件
        try:
            get_s3_client().delete_object(
                Bucket=settings.s3_bucket,
                Key=object_key,
            )
        except (BotoCoreError, ClientError):
            logger.exception(
                "Failed to clean up object after database error"
            )

        logger.exception("Failed to save image information")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image information",
        ) from exc

    # 读取数据库生成的ID和创建时间
    db.refresh(new_image)

    return new_image


@router.get(
    "",
    response_model=ImageListResponse,
)
def list_my_images(
    current_user: CurrentUser,
    db: DatabaseSession,
    page: Annotated[
        int,
        Query(ge=1, description="页码，从1开始"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="每页图片数量"),
    ] = 20,
) -> ImageListResponse:
    """分页返回当前登录用户上传的图片。"""

    # 统计当前用户一共上传了多少张图片
    total = db.scalar(
        select(func.count(Image.id)).where(
            Image.owner_id == current_user.id,
        )
    ) or 0

    # 计算当前页需要跳过多少条记录
    offset = (page - 1) * page_size

    # 按上传时间倒序查询，最新上传的图片排在前面
    image_records = db.scalars(
        select(Image)
        .where(Image.owner_id == current_user.id)
        .order_by(
            Image.created_at.desc(),
            Image.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    ).all()

    items: list[ImageListItemResponse] = []

    try:
        for image_record in image_records:
            # 为列表中的每张图片生成临时浏览地址
            url = get_s3_public_client().generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.s3_bucket,
                    "Key": image_record.object_key,
                },
                ExpiresIn=PRESIGNED_URL_EXPIRE_SECONDS,
            )

            items.append(
                ImageListItemResponse(
                    id=image_record.id,
                    original_filename=image_record.original_filename,
                    content_type=image_record.content_type,
                    size_bytes=image_record.size_bytes,
                    created_at=image_record.created_at,
                    url=url,
                )
            )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to generate image list URLs")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable",
        ) from exc

    return ImageListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


#预签名 URL 可以让没有 Garage 密钥的浏览器临时访问私有对象，有效时间由 ExpiresIn 指定
@router.get(
    "/{image_id}/url",
    response_model=ImageUrlResponse,
)
def get_image_url(
    image_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> ImageUrlResponse:
    """返回当前用户指定图片的临时访问地址。"""

    # 同时按图片ID和用户ID查询，
    # 确保用户只能访问自己上传的图片
    image_record = db.scalar(
        select(Image).where(
            Image.id == image_id,
            Image.owner_id == current_user.id,
        )
    )

    if image_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    try:
        # 生成可以临时访问Garage私有对象的URL
        url = get_s3_public_client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": image_record.object_key,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRE_SECONDS,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to generate image access URL")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable",
        ) from exc

    return ImageUrlResponse(
        id=image_record.id,
        url=url,
        expires_in_seconds=PRESIGNED_URL_EXPIRE_SECONDS,
    )

# 先删除 Garage、再删除数据库。
# 因为 S3 的删除操作可以重复调用：即使图片文件已经不存在，再次删除也不会造成问题。
# 因此如果数据库提交暂时失败，可以重新调用接口完成删除。
# REST 风格：路径表示操作哪个资源、HTTP 方法表示做什么操作
@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_image(
    image_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Response:
    """删除当前用户指定的图片。"""

    # 同时按照图片ID和用户ID查询，
    # 防止一个用户删除另一个用户的图片
    image_record = db.scalar(
        select(Image).where(
            Image.id == image_id,
            Image.owner_id == current_user.id,
        )
    )

    if image_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    try:
        # 先删除Garage中的真实图片文件
        get_s3_client().delete_object(
            Bucket=settings.s3_bucket,
            Key=image_record.object_key,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Failed to delete image from object storage")

        # Garage删除失败时保留数据库记录，方便稍后重试
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable",
        ) from exc

    # Garage删除成功后，再删除MySQL记录
    db.delete(image_record)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to delete image information")

        # 此时Garage文件已经删除，但数据库记录仍然存在。
        # 再次调用删除接口即可继续完成删除。
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image information",
        ) from exc

    # 204响应没有响应正文
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )