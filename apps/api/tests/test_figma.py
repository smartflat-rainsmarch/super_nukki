"""Figma integration tests: share link creation and data retrieval."""
from models import Billing, FigmaShare, Project, User


def _create_pro_with_project(client):
    from tests.conftest import override_get_db

    reg = client.post("/api/auth/register", json={"email": "figma@example.com", "password": "password123"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]

    db = next(override_get_db())
    user = db.query(User).filter(User.id == user_id).first()
    user.plan_type = "pro"
    billing = db.query(Billing).filter(Billing.user_id == user_id).first()
    if billing:
        billing.plan = "pro"
    db.commit()

    project = Project(user_id=user_id, image_url="/test.png", status="done")
    db.add(project)
    db.commit()
    db.refresh(project)

    return token, str(project.id)


class TestFigmaShare:
    def test_create_share_link(self, client):
        token, project_id = _create_pro_with_project(client)
        res = client.post(
            f"/api/export/{project_id}/figma-share",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "share_code" in data
        assert data["expires_in"] == 3600

    def test_get_shared_data(self, client):
        token, project_id = _create_pro_with_project(client)
        share_res = client.post(
            f"/api/export/{project_id}/figma-share",
            headers={"Authorization": f"Bearer {token}"},
        )
        share_code = share_res.json()["share_code"]

        data_res = client.get(f"/api/share/{share_code}")
        assert data_res.status_code == 200
        data = data_res.json()
        assert "canvas_size" in data
        assert "layers" in data
        assert data["project_id"] == project_id

    def test_invalid_share_code(self, client):
        res = client.get("/api/share/nonexistent-code")
        assert res.status_code == 404

    def test_share_requires_auth(self, client):
        res = client.post("/api/export/fake-id/figma-share")
        assert res.status_code == 401

    def test_formats_include_figma(self, client):
        token, project_id = _create_pro_with_project(client)
        res = client.get(
            f"/api/export/{project_id}/formats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert "figma_share" in res.json()["available_formats"]
