"""Phase 8 tests: batch, projects list, teams, assets."""
import io

from PIL import Image

from models import Project


def _create_test_image(fmt="PNG") -> bytes:
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


def _register_pro_user(client, email="pro8@example.com"):
    from tests.conftest import override_get_db
    from models import Billing, User

    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = reg.json()["access_token"]
    db = next(override_get_db())
    user = db.query(User).filter(User.email == email).first()
    user.plan_type = "pro"
    billing = db.query(Billing).filter(Billing.user_id == user.id).first()
    if billing:
        billing.plan = "pro"
    db.commit()
    return token


class TestBatch:
    def test_batch_requires_auth(self, client):
        res = client.post("/api/batch/upload")
        assert res.status_code == 401

    def test_batch_free_user_blocked(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "free8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        content = _create_test_image()
        res = client.post(
            "/api/batch/upload",
            headers={"Authorization": f"Bearer {token}"},
            files=[("files", ("a.png", content, "image/png"))],
        )
        assert res.status_code == 403

    def test_batch_pro_user_succeeds(self, client):
        token = _register_pro_user(client, "batch-pro@example.com")
        content = _create_test_image()
        res = client.post(
            "/api/batch/upload",
            headers={"Authorization": f"Bearer {token}"},
            files=[
                ("files", ("a.png", content, "image/png")),
                ("files", ("b.png", content, "image/png")),
            ],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["succeeded"] == 2
        assert len(data["project_ids"]) == 2


class TestProjectsList:
    def test_list_requires_auth(self, client):
        res = client.get("/api/projects")
        assert res.status_code == 401

    def test_list_empty(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "list8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        res = client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_delete_project(self, client):
        from tests.conftest import override_get_db

        reg = client.post(
            "/api/auth/register",
            json={"email": "del8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]

        db = next(override_get_db())
        project = Project(user_id=user_id, image_url="/test.png", status="done")
        db.add(project)
        db.commit()
        db.refresh(project)

        res = client.delete(
            f"/api/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"


class TestTeams:
    def test_create_team(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "team8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]

        res = client.post(
            "/api/teams",
            json={"name": "My Team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["name"] == "My Team"

    def test_list_teams(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "teamlist@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]

        client.post(
            "/api/teams",
            json={"name": "Team A"},
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.get("/api/teams", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert len(res.json()["teams"]) == 1

    def test_invite_nonexistent_user(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "owner8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]

        team_res = client.post(
            "/api/teams",
            json={"name": "Invite Team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        team_id = team_res.json()["id"]

        res = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "nobody@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


class TestAssets:
    def test_assets_requires_auth(self, client):
        res = client.get("/api/assets")
        assert res.status_code == 401

    def test_assets_empty(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "asset8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        res = client.get("/api/assets", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_asset_stats(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "stats8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        res = client.get("/api/assets/stats", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert "by_type" in res.json()

    def test_asset_search(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "search8@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        res = client.get(
            "/api/assets/search?q=hello",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["query"] == "hello"
