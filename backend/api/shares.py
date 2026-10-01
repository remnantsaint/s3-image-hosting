import logging

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from backend.api.dependencies import DatabaseSession
from backend.core.config import get_settings
from backend.models.image import Image
from backend.services.storage import get_s3_public_client


logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["shares"])

# 跳转到Garage的临时地址仍然只允许使用10分钟
PRESIGNED_URL_EXPIRE_SECONDS = 600


@router.get(
    "/s/{share_token}",
    response_class=RedirectResponse,
)
def open_shared_image(
    share_token: str,
    db: DatabaseSession,
) -> RedirectResponse:
    """通过固定分享码公开访问图片，不要求用户登录。"""

    image_record = db.scalar(
        select(Image).where(
            Image.share_token == share_token,
        )
    )

    if image_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared image not found",
        )

    try:
        # 固定分享链接本身不会变化，
        # 每次访问时再生成短期Garage访问地址。
        temporary_url = (
            get_s3_public_client().generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.s3_bucket,
                    "Key": image_record.object_key,
                },
                ExpiresIn=PRESIGNED_URL_EXPIRE_SECONDS,
            )
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception(
            "Failed to generate shared image URL"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is unavailable",
        ) from exc

    return RedirectResponse(
        url=temporary_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        # 避免浏览器长期缓存临时跳转结果
        headers={"Cache-Control": "no-store"},
    )