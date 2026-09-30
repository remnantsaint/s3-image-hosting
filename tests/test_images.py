import base64
from urllib.error import HTTPError
from urllib.request import urlopen
from collections.abc import Callable
from backend.api.images import UPLOAD_MAX_REQUESTS
import pytest
from fastapi.testclient import TestClient


# 一张真实有效的1×1像素PNG图片
TEST_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
    "CAQAAAC1HAwCAAAAC0lEQVR42mNk+A8A"
    "AQUBAScY42YAAAAASUVORK5CYII="
)


def create_auth_headers(
    client: TestClient,
    user_data: dict[str, str],
) -> dict[str, str]:
    """注册并登录测试用户，返回JWT请求头。"""

    register_response = client.post(
        "/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def test_image_lifecycle(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试图片从上传到删除的完整生命周期。"""

    headers = create_auth_headers(
        client,
        test_user_data,
    )

    image_id: int | None = None

    try:
        # 上传一张测试PNG图片
        upload_response = client.post(
            "/images",
            headers=headers,
            files={
                "file": (
                    "test_image.png",
                    TEST_PNG_BYTES,
                    "image/png",
                ),
            },
        )

        assert upload_response.status_code == 201

        uploaded_image = upload_response.json()
        image_id = uploaded_image["id"]

        assert image_id > 0
        assert uploaded_image["original_filename"] == (
            "test_image.png"
        )
        assert uploaded_image["content_type"] == "image/png"
        assert uploaded_image["size_bytes"] == len(
            TEST_PNG_BYTES
        )

        # 查询当前用户的图片列表
        list_response = client.get(
            "/images",
            headers=headers,
        )

        assert list_response.status_code == 200

        image_list = list_response.json()

        assert image_list["total"] == 1
        assert len(image_list["items"]) == 1
        assert image_list["items"][0]["id"] == image_id

        # 获取图片的临时访问地址
        url_response = client.get(
            f"/images/{image_id}/url",
            headers=headers,
        )

        assert url_response.status_code == 200

        url_data = url_response.json()
        image_url = url_data["url"]

        assert url_data["id"] == image_id
        assert url_data["expires_in_seconds"] == 600
        assert image_url.startswith("http")

        # 通过临时地址直接读取Garage中的真实图片
        with urlopen(
            image_url,
            timeout=5,
        ) as storage_response:
            downloaded_content = storage_response.read()

            assert storage_response.status == 200
            assert (
                storage_response.headers.get_content_type()
                == "image/png"
            )
            assert downloaded_content == TEST_PNG_BYTES

        # 删除图片
        delete_response = client.delete(
            f"/images/{image_id}",
            headers=headers,
        )

        assert delete_response.status_code == 204
        assert delete_response.content == b""

        # 删除后，图片列表应该为空
        empty_list_response = client.get(
            "/images",
            headers=headers,
        )

        assert empty_list_response.status_code == 200
        assert empty_list_response.json()["total"] == 0

        # 之前的临时链接也不能再读取Garage文件
        with pytest.raises(HTTPError) as error:
            urlopen(
                image_url,
                timeout=5,
            )

        assert error.value.code in {403, 404}

        # 标记为已经成功删除，finally不需要再次清理
        image_id = None
    finally:
        # 如果测试中途失败，尽量调用接口清理已上传图片
        if image_id is not None:
            client.delete(
                f"/images/{image_id}",
                headers=headers,
            )


def test_reject_fake_image(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试拒绝伪装成PNG的普通文本文件。"""

    headers = create_auth_headers(
        client,
        test_user_data,
    )

    response = client.post(
        "/images",
        headers=headers,
        files={
            "file": (
                "fake.png",
                b"This is not a real PNG image.",
                "image/png",
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "File content does not match its image type"
    )


def test_upload_requires_authentication(
    client: TestClient,
) -> None:
    """测试未登录用户不能上传图片。"""

    response = client.post(
        "/images",
        files={
            "file": (
                "test_image.png",
                TEST_PNG_BYTES,
                "image/png",
            ),
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_upload_rate_limit(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试超过上传请求次数后返回429。"""

    headers = create_auth_headers(
        client,
        test_user_data,
    )

    fake_image = {
        "file": (
            "fake.png",
            b"This is not a real PNG image.",
            "image/png",
        ),
    }

    # 前10次请求通过限流检查，
    # 随后因为图片内容无效而返回400
    for _ in range(UPLOAD_MAX_REQUESTS):
        response = client.post(
            "/images",
            headers=headers,
            files=fake_image,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "File content does not match its image type"
        )

    # 第11次请求会在读取图片前被Redis拦截
    blocked_response = client.post(
        "/images",
        headers=headers,
        files=fake_image,
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == (
        "Too many image upload requests"
    )
    assert "Retry-After" in blocked_response.headers
    assert int(
        blocked_response.headers["Retry-After"]
    ) > 0


def test_users_cannot_access_each_others_images(
    client: TestClient,
    user_data_factory: Callable[
        [],
        dict[str, str],
    ],
) -> None:
    """测试一个用户不能查看或删除另一个用户的图片。"""

    first_user_data = user_data_factory()
    second_user_data = user_data_factory()

    first_headers = create_auth_headers(
        client,
        first_user_data,
    )
    second_headers = create_auth_headers(
        client,
        second_user_data,
    )

    image_id: int | None = None

    try:
        # 用户一上传图片
        upload_response = client.post(
            "/images",
            headers=first_headers,
            files={
                "file": (
                    "private.png",
                    TEST_PNG_BYTES,
                    "image/png",
                ),
            },
        )

        assert upload_response.status_code == 201

        image_id = upload_response.json()["id"]

        # 用户二的图片列表应该仍然为空
        second_list_response = client.get(
            "/images",
            headers=second_headers,
        )

        assert second_list_response.status_code == 200
        assert second_list_response.json()["total"] == 0

        # 用户二不能获取用户一的图片链接
        second_url_response = client.get(
            f"/images/{image_id}/url",
            headers=second_headers,
        )

        assert second_url_response.status_code == 404
        assert second_url_response.json()["detail"] == (
            "Image not found"
        )

        # 用户二也不能删除用户一的图片
        second_delete_response = client.delete(
            f"/images/{image_id}",
            headers=second_headers,
        )

        assert second_delete_response.status_code == 404

        # 用户一仍然可以获取自己的图片
        first_url_response = client.get(
            f"/images/{image_id}/url",
            headers=first_headers,
        )

        assert first_url_response.status_code == 200
    finally:
        # 使用真正的图片所有者清理测试图片
        if image_id is not None:
            client.delete(
                f"/images/{image_id}",
                headers=first_headers,
            )