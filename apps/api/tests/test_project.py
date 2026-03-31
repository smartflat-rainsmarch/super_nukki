from models import Project


def test_get_project_not_found(client):
    response = client.get("/api/project/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_project_invalid_id(client):
    response = client.get("/api/project/not-a-uuid")
    assert response.status_code == 400


def test_get_project_exists(client):
    from tests.conftest import override_get_db

    db = next(override_get_db())
    project = Project(image_url="/storage/uploads/test.png", status="pending")
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.get(f"/api/project/{project.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["progress"] == 0


def test_get_project_result_not_found(client):
    response = client.get("/api/project/00000000-0000-0000-0000-000000000000/result")
    assert response.status_code == 404


def test_download_not_complete(client):
    from tests.conftest import override_get_db

    db = next(override_get_db())
    project = Project(image_url="/storage/uploads/test.png", status="pending")
    db.add(project)
    db.commit()
    db.refresh(project)

    response = client.get(f"/api/download/{project.id}")
    assert response.status_code == 400
    assert "not complete" in response.json()["detail"]
