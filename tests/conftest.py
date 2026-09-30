# 创建测试客户端和测试用户数据
from collections.abc import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db.session import SessionLocal
from backend.main import app
from backend.models.user import User


# 调用一次工厂函数，就生成一个随机测试用户数据
UserDataFactory = Callable[[], dict[str, str]]


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """为每个测试提供一个FastAPI测试客户端。"""

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_data_factory() -> Generator[
    UserDataFactory,
    None,
    None,
]:
    """提供测试用户数据工厂，并统一清理创建的用户。"""

    created_usernames: list[str] = []

    def create_user_data() -> dict[str, str]:
        """生成一组唯一的测试用户数据。"""

        suffix = uuid4().hex[:10]

        user_data = {
            "username": f"test_{suffix}",
            "email": f"test_{suffix}@example.com",
            "password": "TestPassword123!",
        }

        created_usernames.append(
            user_data["username"]
        )

        return user_data

    yield create_user_data

    # 测试完成后统一清理工厂生成的所有用户
    if created_usernames:
        with SessionLocal() as db:
            users = db.scalars(
                select(User).where(
                    User.username.in_(created_usernames),
                )
            ).all()

            for user in users:
                db.delete(user)

            db.commit()


@pytest.fixture
def test_user_data(
    user_data_factory: UserDataFactory,
) -> dict[str, str]:
    """为只需要一个用户的测试生成用户数据。"""

    return user_data_factory()