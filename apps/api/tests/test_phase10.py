"""Phase 10 tests: SSO, RBAC, model config, API keys, SLA."""
from models import Billing, Team, TeamMember, User


def _register_pro(client, email="pro10@example.com"):
    from tests.conftest import override_get_db

    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]

    db = next(override_get_db())
    user = db.query(User).filter(User.id == user_id).first()
    user.plan_type = "pro"
    billing = db.query(Billing).filter(Billing.user_id == user_id).first()
    if billing:
        billing.plan = "pro"
    db.commit()

    return token, user_id


class TestRBAC:
    def test_role_hierarchy(self):
        from rbac import ROLE_HIERARCHY

        assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["admin"]
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["member"]

    def test_check_permission(self, client):
        from rbac import check_permission
        from tests.conftest import override_get_db

        token, user_id = _register_pro(client, "rbac@example.com")

        db = next(override_get_db())
        team = Team(name="RBAC Team", owner_id=user_id)
        db.add(team)
        db.commit()
        db.refresh(team)

        member = TeamMember(team_id=team.id, user_id=user_id, role="owner")
        db.add(member)
        db.commit()

        assert check_permission(user_id, str(team.id), "owner", db) is True
        assert check_permission(user_id, str(team.id), "member", db) is True
        assert check_permission("nonexistent", str(team.id), "member", db) is False


class TestSSO:
    def test_sso_callback_creates_user(self, client):
        from tests.conftest import override_get_db

        token, user_id = _register_pro(client, "sso-owner@example.com")

        db = next(override_get_db())
        team = Team(name="SSO Team", owner_id=user_id)
        db.add(team)
        db.commit()
        db.refresh(team)

        res = client.post("/api/sso/callback", json={
            "email": "sso-user@corp.com",
            "name": "SSO User",
            "provider": "oidc",
            "team_id": str(team.id),
        })
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_sso_configure_requires_auth(self, client):
        res = client.post("/api/sso/configure", json={
            "provider": "saml",
            "team_id": "fake",
        })
        assert res.status_code == 401


class TestModelConfig:
    def test_get_defaults(self, client):
        token, _ = _register_pro(client, "config-def@example.com")
        res = client.get(
            "/api/model-config/defaults",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert "ocr_engine" in res.json()["config"]

    def test_update_config(self, client):
        token, _ = _register_pro(client, "config-upd@example.com")
        res = client.put(
            "/api/model-config/team-123",
            json={"inpainting_radius": 10, "enable_ensemble_ocr": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["config"]["inpainting_radius"] == 10
        assert data["config"]["enable_ensemble_ocr"] is True

    def test_update_config_validation(self, client):
        token, _ = _register_pro(client, "config-val@example.com")
        res = client.put(
            "/api/model-config/team-123",
            json={"inpainting_radius": 50},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400

    def test_list_versions(self, client):
        token, _ = _register_pro(client, "config-ver@example.com")
        res = client.get(
            "/api/model-config/team-123/versions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert len(res.json()["versions"]) >= 1


class TestAPIKeys:
    def test_create_requires_pro(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "key-free@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        res = client.post(
            "/api/keys",
            json={"name": "test-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403

    def test_create_and_list_key(self, client):
        token, _ = _register_pro(client, "key-pro@example.com")

        create_res = client.post(
            "/api/keys",
            json={"name": "my-key", "rate_limit_per_minute": 120},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_res.status_code == 200
        key_data = create_res.json()
        assert key_data["api_key"].startswith("ui2psd_")
        assert key_data["name"] == "my-key"

        list_res = client.get("/api/keys", headers={"Authorization": f"Bearer {token}"})
        assert list_res.status_code == 200
        assert len(list_res.json()["keys"]) == 1

    def test_revoke_key(self, client):
        token, _ = _register_pro(client, "key-rev@example.com")

        create_res = client.post(
            "/api/keys",
            json={"name": "temp-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        key_id = create_res.json()["key_id"]

        del_res = client.delete(
            f"/api/keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "revoked"


class TestSLA:
    def test_health_no_auth(self, client):
        res = client.get("/api/sla/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
        assert "uptime_seconds" in res.json()

    def test_metrics_with_auth(self, client):
        token, _ = _register_pro(client, "sla@example.com")
        res = client.get("/api/sla/metrics", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "jobs" in data
        assert "sla" in data
        assert data["sla"]["target_success_rate"] == 99.5
