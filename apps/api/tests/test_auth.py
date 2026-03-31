def test_register_success(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "test@example.com"
    assert data["plan_type"] == "free"


def test_register_duplicate(client):
    client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password456"},
    )
    assert response.status_code == 409


def test_register_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 400


def test_login_success(client):
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrong@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_me_authenticated(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "me@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_get_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_usage_requires_auth(client):
    response = client.get("/api/usage")
    assert response.status_code == 401


def test_usage_with_auth(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "usage@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    response = client.get(
        "/api/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "free"
    assert data["limit"] == 3
    assert data["remaining"] == 3
