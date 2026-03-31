def test_get_project(client):
    response = client.get("/api/project/some-id")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "some-id"


def test_get_project_result(client):
    response = client.get("/api/project/some-id/result")
    assert response.status_code == 200
    data = response.json()
    assert "layers" in data
