"""Phase 9 tests: Figma, React/CSS, design tokens, component schema exports."""
import json
import tempfile
from pathlib import Path

from engine.composer import LayerInfo


def _sample_layers():
    return [
        LayerInfo("Background", "background", (0, 0, 400, 700), 0, "/bg.png", group="Background"),
        LayerInfo("title", "text", (20, 80, 200, 30), 1, "/title.png",
                  text_content="Hello World", font_size=24, text_color=(30, 30, 30), group="Header"),
        LayerInfo("subtitle", "text", (20, 120, 250, 20), 2, "/sub.png",
                  text_content="Description", font_size=14, text_color=(100, 100, 100), group="Header"),
        LayerInfo("card_0", "card", (20, 200, 360, 150), 3, "/card.png", group="Body"),
        LayerInfo("cta_btn", "button", (100, 600, 200, 50), 4, "/btn.png",
                  text_content="Sign Up", font_size=16, text_color=(255, 255, 255), group="CTA"),
    ]


class TestFigmaExport:
    def test_export_creates_json(self):
        from engine.exporters.figma import export_figma

        layers = _sample_layers()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "figma.json")
            result = export_figma(layers, 400, 700, path)

            assert Path(result.json_path).exists()
            assert result.node_count == 5

            data = json.loads(Path(path).read_text())
            assert data["name"] == "UI2PSD Export"
            assert "document" in data
            frame = data["document"]["children"][0]["children"][0]
            assert frame["type"] == "FRAME"

    def test_text_node_has_style(self):
        from engine.exporters.figma import _layer_to_figma_node

        layer = LayerInfo("txt", "text", (10, 10, 100, 20), 0, "/t.png",
                          text_content="Hello", font_size=16, text_color=(0, 0, 0))
        node = _layer_to_figma_node(layer, 0)
        assert node["type"] == "TEXT"
        assert node["characters"] == "Hello"
        assert node["style"]["fontSize"] == 16


class TestReactExport:
    def test_export_creates_files(self):
        from engine.exporters.react_css import export_react

        layers = _sample_layers()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_react(layers, 400, 700, tmpdir)

            assert Path(result.component_path).exists()
            assert Path(result.css_path).exists()
            assert result.component_count == 5

            tsx = Path(result.component_path).read_text()
            assert "Screen" in tsx
            assert "Hello World" in tsx
            assert "Sign Up" in tsx

            css = Path(result.css_path).read_text()
            assert ".screen" in css
            assert "font-size:" in css

    def test_button_has_border_radius(self):
        from engine.exporters.react_css import _layer_to_css

        layer = LayerInfo("btn", "button", (10, 10, 100, 40), 0, "/b.png")
        css = _layer_to_css(layer)
        assert "border-radius: 8px" in css


class TestDesignTokens:
    def test_extract_tokens(self):
        from engine.exporters.design_tokens import extract_design_tokens

        layers = _sample_layers()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "tokens.json")
            result = extract_design_tokens(layers, path)

            assert Path(result.json_path).exists()
            assert result.color_count >= 1
            assert result.font_size_count >= 1

            data = json.loads(Path(path).read_text())
            assert "colors" in data
            assert "typography" in data
            assert "spacing" in data

    def test_rgb_to_hex(self):
        from engine.exporters.design_tokens import _rgb_to_hex

        assert _rgb_to_hex(255, 0, 0) == "#ff0000"
        assert _rgb_to_hex(0, 0, 0) == "#000000"


class TestComponentSchema:
    def test_export_schema(self):
        from engine.exporters.component_schema import export_component_schema

        layers = _sample_layers()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "schema.json")
            result = export_component_schema(layers, 400, 700, path)

            assert Path(result.json_path).exists()
            assert result.component_count == 5

            data = json.loads(Path(path).read_text())
            assert data["$schema"].startswith("https://")
            assert data["canvas"]["width"] == 400
            assert len(data["components"]) > 0

    def test_component_type_mapping(self):
        from engine.exporters.component_schema import _map_component_type

        assert _map_component_type("button") == "Button"
        assert _map_component_type("text") == "Text"
        assert _map_component_type("card") == "Card"
        assert _map_component_type("unknown") == "Box"


class TestExportAPI:
    def test_export_formats_free(self, client):
        from tests.conftest import override_get_db
        from models import Project

        reg = client.post(
            "/api/auth/register",
            json={"email": "export-free@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]

        db = next(override_get_db())
        project = Project(user_id=user_id, image_url="/test.png", status="done")
        db.add(project)
        db.commit()
        db.refresh(project)

        res = client.get(
            f"/api/export/{project.id}/formats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "psd" in data["available_formats"]
        assert "react" not in data["available_formats"]

    def test_export_formats_pro(self, client):
        from tests.conftest import override_get_db
        from models import Billing, Project, User

        reg = client.post(
            "/api/auth/register",
            json={"email": "export-pro@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        user_id = reg.json()["user_id"]

        db = next(override_get_db())
        user = db.query(User).filter(User.id == user_id).first()
        user.plan_type = "pro"
        db.commit()

        project = Project(user_id=user_id, image_url="/test.png", status="done")
        db.add(project)
        db.commit()
        db.refresh(project)

        res = client.get(
            f"/api/export/{project.id}/formats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "react" in data["available_formats"]
        assert "design_tokens" in data["available_formats"]
        assert "component_schema" in data["available_formats"]
