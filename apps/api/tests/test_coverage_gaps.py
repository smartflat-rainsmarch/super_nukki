"""Tests to fill coverage gaps in usage, admin, download, error handlers, and inpainting_advanced."""
import numpy as np
import pytest

from models import Billing, Job, Project, User


# === Usage Router ===

class TestUsageRouter:
    def _register_and_get_token(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "usage-test@example.com", "password": "password123"},
        )
        return reg.json()["access_token"]

    def test_usage_shows_correct_limits_free(self, client):
        token = self._register_and_get_token(client)
        res = client.get("/api/usage", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["plan"] == "free"
        assert data["limit"] == 3
        assert data["remaining"] == 3
        assert data["usage_count"] == 0

    def test_check_usage_limit_under_limit(self, client):
        from routers.usage import check_usage_limit
        from tests.conftest import override_get_db

        token = self._register_and_get_token(client)
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "usage-test@example.com").first()
        assert check_usage_limit(user, db) is True

    def test_check_usage_limit_over_limit(self, client):
        from routers.usage import check_usage_limit
        from tests.conftest import override_get_db

        token = self._register_and_get_token(client)
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "usage-test@example.com").first()

        billing = db.query(Billing).filter(Billing.user_id == user.id).first()
        billing.usage_count = 5  # exceeds free limit of 3
        db.commit()

        assert check_usage_limit(user, db) is False

    def test_increment_usage(self, client):
        from routers.usage import increment_usage
        from tests.conftest import override_get_db

        token = self._register_and_get_token(client)
        db = next(override_get_db())
        user = db.query(User).filter(User.email == "usage-test@example.com").first()

        billing_before = db.query(Billing).filter(Billing.user_id == user.id).first()
        count_before = billing_before.usage_count

        increment_usage(user, db)

        db.refresh(billing_before)
        assert billing_before.usage_count == count_before + 1


# === Admin Router ===

class TestAdminStats:
    def _create_pro_user(self, client):
        from tests.conftest import override_get_db

        reg = client.post(
            "/api/auth/register",
            json={"email": "admin-pro@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]

        db = next(override_get_db())
        user = db.query(User).filter(User.email == "admin-pro@example.com").first()
        user.plan_type = "pro"
        billing = db.query(Billing).filter(Billing.user_id == user.id).first()
        if billing:
            billing.plan = "pro"
        db.commit()

        return token

    def test_admin_stats_success(self, client):
        token = self._create_pro_user(client)
        res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "users" in data
        assert "projects" in data
        assert "jobs" in data
        assert data["users"]["total"] >= 1

    def test_admin_users_list(self, client):
        token = self._create_pro_user(client)
        res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "users" in data
        assert len(data["users"]) >= 1

    def test_admin_jobs_list(self, client):
        token = self._create_pro_user(client)
        res = client.get("/api/admin/jobs", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "jobs" in data


# === Download Router ===

class TestDownloadRouter:
    def test_download_invalid_uuid(self, client):
        res = client.get("/api/download/not-a-uuid")
        assert res.status_code == 400

    def test_download_not_found(self, client):
        res = client.get("/api/download/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404


# === Error Handlers ===

class TestErrorHandlers:
    def test_404_still_returns(self, client):
        res = client.get("/nonexistent-endpoint")
        assert res.status_code == 404


# === Inpainting Advanced ===

class TestInpaintingAdvancedCoverage:
    def test_inpaint_advanced_default_config(self):
        from engine.inpainting_advanced import InpaintConfig, inpaint_advanced

        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[30:50, 30:50] = 255

        result, warning = inpaint_advanced(img, mask)
        assert result.restored_image is not None
        assert result.quality_score >= 0

    def test_inpaint_advanced_ns_method(self):
        from engine.inpainting_advanced import InpaintConfig, InpaintMethod, inpaint_advanced

        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[30:50, 30:50] = 255

        config = InpaintConfig(method=InpaintMethod.OPENCV_NS)
        result, warning = inpaint_advanced(img, mask, config)
        assert result.restored_image is not None

    def test_inpaint_advanced_lama_fallback(self):
        from engine.inpainting_advanced import InpaintConfig, InpaintMethod, inpaint_advanced

        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[30:50, 30:50] = 255

        config = InpaintConfig(method=InpaintMethod.LAMA)
        result, warning = inpaint_advanced(img, mask, config)
        # LaMa not available, falls back to OpenCV
        assert result.restored_image is not None

    def test_detect_gradient_background(self):
        from engine.inpainting_advanced import _detect_background_type

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            img[i, :] = [i * 2, i * 2, i * 2]  # gradient
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[40:60, 40:60] = 255

        bg_type = _detect_background_type(img, mask)
        assert bg_type in ("gradient", "pattern")

    def test_quality_warning_pattern(self):
        from engine.inpainting_advanced import _quality_warning

        warning = _quality_warning(0.6, "pattern")
        assert warning is not None
        assert "Pattern" in warning


# === Project Router - result with layers ===

class TestProjectResult:
    def test_project_result_with_done_status(self, client):
        from tests.conftest import override_get_db

        db = next(override_get_db())
        project = Project(image_url="/storage/uploads/test.png", status="done")
        db.add(project)
        db.commit()
        db.refresh(project)

        res = client.get(f"/api/project/{project.id}/result")
        assert res.status_code == 200
        data = res.json()
        assert data["psd_url"] is not None
        assert "notice" in data
        assert data["status"] == "done"


# === Auth edge cases ===

class TestAuthEdgeCases:
    def test_invalid_token(self, client):
        res = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert res.status_code == 401

    def test_register_invalid_email(self, client):
        res = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert res.status_code == 422
