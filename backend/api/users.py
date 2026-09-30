from fastapi import APIRouter

from backend.api.dependencies import CurrentUser
from backend.models.user import User
from backend.schemas.user import UserResponse


router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
def read_current_user(
    current_user: CurrentUser,
) -> User:
    """返回当前登录用户的信息。"""

    return current_user