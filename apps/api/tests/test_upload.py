import io

from PIL import Image


def _create_test_image(format_: str = "PNG") -> bytes:
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format=format_)
    buf.seek(0)
    return buf.read()


def test_upload_valid_png(client):
    content = _create_test_image("PNG")
    response = client.post(
        "/api/upload",
        files={"file": ("test.png", content, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert data["status"] == "pending"
    assert data["image_url"].endswith(".png")


def test_upload_valid_jpeg(client):
    content = _create_test_image("JPEG")
    response = client.post(
        "/api/upload",
        files={"file": ("test.jpg", content, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_upload_invalid_extension(client):
    response = client.post(
        "/api/upload",
        files={"file": ("test.exe", b"not an image", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_fake_image(client):
    response = client.post(
        "/api/upload",
        files={"file": ("fake.png", b"not actually a png", "image/png")},
    )
    assert response.status_code == 400
    assert "Invalid image" in response.json()["detail"]


def test_upload_empty_file(client):
    response = client.post(
        "/api/upload",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400


def test_upload_no_file(client):
    response = client.post("/api/upload")
    assert response.status_code == 422
