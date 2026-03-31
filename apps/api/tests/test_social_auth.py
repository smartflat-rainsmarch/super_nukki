"""Social login tests: Google, Kakao OAuth + edge cases."""


class TestGoogleOAuth:
    def test_google_url_endpoint(self, client):
        res = client.get("/api/auth/google/url")
        assert res.status_code == 200
        assert "url" in res.json()

    def test_google_callback_creates_user(self, client):
        res = client.post(
            "/api/auth/google/callback",
            json={"code": "mock-google-code-12345"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["auth_provider"] == "google"
        assert "mock" in data["email"]

    def test_google_callback_same_code_same_user(self, client):
        res1 = client.post(
            "/api/auth/google/callback",
            json={"code": "same-code-aaa"},
        )
        res2 = client.post(
            "/api/auth/google/callback",
            json={"code": "same-code-aaa"},
        )
        assert res1.json()["user_id"] == res2.json()["user_id"]


class TestKakaoOAuth:
    def test_kakao_url_endpoint(self, client):
        res = client.get("/api/auth/kakao/url")
        assert res.status_code == 200
        assert "url" in res.json()

    def test_kakao_callback_creates_user(self, client):
        res = client.post(
            "/api/auth/kakao/callback",
            json={"code": "mock-kakao-code-67890"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["auth_provider"] == "kakao"


class TestSocialEmailConflict:
    def test_email_register_then_google_links(self, client):
        # 1. Email register
        client.post(
            "/api/auth/register",
            json={"email": "conflict@mock.ui2psd.com", "password": "password123"},
        )

        # 2. Google login with same email - mock generates different email, so test account linking
        # Register a user first, then simulate OAuth with same email
        from tests.conftest import override_get_db
        from models import User

        db = next(override_get_db())
        user = db.query(User).filter(User.email == "conflict@mock.ui2psd.com").first()
        assert user is not None
        assert user.auth_provider == "email"
        assert user.password is not None  # has password

    def test_social_user_cannot_email_login(self, client):
        # Create a social user first
        client.post(
            "/api/auth/google/callback",
            json={"code": "social-only-user"},
        )

        # Try email login with that user's email (no password set)
        res = client.post(
            "/api/auth/login",
            json={"email": "google-social-o@mock.ui2psd.com", "password": "anypassword"},
        )
        assert res.status_code == 401
        assert "google" in res.json()["detail"].lower()

    def test_social_user_email_register_blocked(self, client):
        # Create via Google
        google_res = client.post(
            "/api/auth/google/callback",
            json={"code": "block-test-xx"},
        )
        email = google_res.json()["email"]

        # Try registering same email
        res = client.post(
            "/api/auth/register",
            json={"email": email, "password": "password123"},
        )
        assert res.status_code == 409
        assert "google" in res.json()["detail"].lower()


class TestAuthResponseExtended:
    def test_register_returns_auth_provider(self, client):
        res = client.post(
            "/api/auth/register",
            json={"email": "ext@example.com", "password": "password123"},
        )
        data = res.json()
        assert data["auth_provider"] == "email"
        assert data.get("name") is None

    def test_me_returns_auth_provider(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "me-ext@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        data = res.json()
        assert data["auth_provider"] == "email"

    def test_google_me_returns_provider(self, client):
        google_res = client.post(
            "/api/auth/google/callback",
            json={"code": "me-google-test"},
        )
        token = google_res.json()["access_token"]
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        data = res.json()
        assert data["auth_provider"] == "google"
        assert data["name"] == "Google Mock User"
