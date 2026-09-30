from fastapi.testclient import TestClient


def test_application_health(
    client: TestClient,
) -> None:
    """检查FastAPI应用本身是否正常。"""

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "S3 Image Hosting"
    assert data["environment"] == "development"


def test_database_health(
    client: TestClient,
) -> None:
    """检查FastAPI是否能够连接MySQL。"""

    response = client.get("/health/database")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["database"] == "image_hosting"
    assert data["version"]


def test_storage_health(
    client: TestClient,
) -> None:
    """检查FastAPI是否能够访问Garage存储桶。"""

    response = client.get("/health/storage")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["bucket"] == "image-hosting"


def test_redis_health(
    client: TestClient,
) -> None:
    """检查FastAPI是否能够连接Redis。"""

    response = client.get("/health/redis")

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "status": "ok",
        "service": "redis",
    }