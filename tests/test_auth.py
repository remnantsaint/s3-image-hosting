from fastapi.testclient import TestClient
from backend.api.auth import LOGIN_MAX_FAILED_ATTEMPTS


def test_register_user(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试正常注册用户。"""

    response = client.post(
        "/auth/register",
        json=test_user_data,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["username"] == test_user_data["username"]
    assert data["email"] == test_user_data["email"]
    assert data["is_active"] is True

    # 接口绝不能返回明文密码或密码哈希
    assert "password" not in data
    assert "password_hash" not in data


def test_reject_duplicate_username(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试拒绝重复用户名。"""

    first_response = client.post(
        "/auth/register",
        json=test_user_data,
    )

    assert first_response.status_code == 201

    second_user = {
        **test_user_data,
        "email": f"other_{test_user_data['email']}",
    }

    second_response = client.post(
        "/auth/register",
        json=second_user,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Username is already registered"
    )


def test_reject_duplicate_email(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试拒绝重复邮箱。"""

    first_response = client.post(
        "/auth/register",
        json=test_user_data,
    )

    assert first_response.status_code == 201

    second_user = {
        **test_user_data,
        "username": f"{test_user_data['username']}_other",
    }

    second_response = client.post(
        "/auth/register",
        json=second_user,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Email is already registered"
    )


def test_login_and_read_current_user(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试登录、JWT签发和当前用户接口。"""

    register_response = client.post(
        "/auth/register",
        json=test_user_data,
    )

    assert register_response.status_code == 201

    # 先验证错误密码会被拒绝
    wrong_login_response = client.post(
        "/auth/login",
        json={
            "username": test_user_data["username"],
            "password": "WrongPassword123!",
        },
    )

    assert wrong_login_response.status_code == 401
    assert wrong_login_response.json()["detail"] == (
        "Incorrect username or password"
    )

    # 使用正确密码登录
    login_response = client.post(
        "/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )

    assert login_response.status_code == 200

    token_data = login_response.json()

    assert token_data["access_token"]
    assert token_data["token_type"] == "bearer"

    # 携带JWT访问受保护接口
    me_response = client.get(
        "/users/me",
        headers={
            "Authorization": (
                f"Bearer {token_data['access_token']}"
            ),
        },
    )

    assert me_response.status_code == 200

    current_user = me_response.json()

    assert current_user["username"] == (
        test_user_data["username"]
    )
    assert current_user["email"] == test_user_data["email"]


def test_current_user_requires_token(
    client: TestClient,
) -> None:
    """测试未携带JWT时不能访问当前用户接口。"""

    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_login_rate_limit(
    client: TestClient,
    test_user_data: dict[str, str],
) -> None:
    """测试连续登录失败后触发Redis限流。"""

    # 先注册一个随机测试用户
    register_response = client.post(
        "/auth/register",
        json=test_user_data,
    )

    assert register_response.status_code == 201

    wrong_login_data = {
        "username": test_user_data["username"],
        "password": "WrongPassword123!",
    }

    # 前5次密码错误应正常返回401
    for _ in range(LOGIN_MAX_FAILED_ATTEMPTS):
        response = client.post(
            "/auth/login",
            json=wrong_login_data,
        )

        assert response.status_code == 401
        assert response.json()["detail"] == (
            "Incorrect username or password"
        )

    # 第6次请求在检查密码前就会被Redis限流
    blocked_response = client.post(
        "/auth/login",
        json=wrong_login_data,
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == (
        "Too many failed login attempts"
    )

    # 响应头应告诉客户端还需要等待多少秒
    assert "Retry-After" in blocked_response.headers
    assert int(
        blocked_response.headers["Retry-After"]
    ) > 0

    # 限流期间即使密码正确，也暂时不能继续登录
    correct_but_blocked_response = client.post(
        "/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )

    assert correct_but_blocked_response.status_code == 429