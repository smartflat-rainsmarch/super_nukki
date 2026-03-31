import numpy as np
import cv2


class TestUIRules:
    def test_classify_region(self):
        from engine.ui_rules import classify_region

        assert classify_region(10, 30, 700) == "status_bar"
        assert classify_region(70, 40, 700) == "header"
        assert classify_region(350, 50, 700) == "content"
        assert classify_region(630, 50, 700) == "bottom_nav"

    def test_detect_repeated_components(self):
        from engine.segmentation import UIElement
        from engine.ui_rules import detect_repeated_components

        mask = np.zeros((100, 100), dtype=np.uint8)
        elements = [
            UIElement("card", (10, 10, 80, 40), mask, 0.8, 0),
            UIElement("card", (10, 60, 82, 41), mask, 0.8, 1),
            UIElement("button", (10, 110, 30, 15), mask, 0.8, 2),
        ]

        groups = detect_repeated_components(elements)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_refine_element_types(self):
        from engine.segmentation import UIElement
        from engine.ui_rules import refine_element_types

        image = np.random.randint(50, 200, (700, 400, 3), dtype=np.uint8)
        mask = np.ones((700, 400), dtype=np.uint8) * 255

        elements = [
            UIElement("card", (10, 5, 20, 15), mask, 0.8, 0),  # status bar area -> icon
        ]

        refined = refine_element_types(elements, image)
        assert refined[0].element_type == "icon"


class TestOcrEnsemble:
    def test_iou_calculation(self):
        from engine.ocr_ensemble import _iou

        assert _iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
        assert _iou((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0
        assert 0 < _iou((0, 0, 10, 10), (5, 5, 10, 10)) < 1.0


class TestInpaintingAdvanced:
    def test_detect_background_type_solid(self):
        from engine.inpainting_advanced import _detect_background_type

        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:40, 20:40] = 255

        assert _detect_background_type(img, mask) == "solid"

    def test_quality_warning_low(self):
        from engine.inpainting_advanced import _quality_warning

        warning = _quality_warning(0.3, "solid")
        assert warning is not None
        assert "Low" in warning

    def test_quality_warning_none(self):
        from engine.inpainting_advanced import _quality_warning

        assert _quality_warning(0.9, "solid") is None


class TestPipelineEnhanced:
    def test_pipeline_with_warnings(self):
        import tempfile
        from pathlib import Path

        img = np.ones((700, 400, 3), dtype=np.uint8) * 245
        cv2.rectangle(img, (0, 0), (400, 60), (50, 50, 200), -1)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            cv2.imwrite(f.name, img)
            img_path = f.name

        with tempfile.TemporaryDirectory() as tmpdir:
            from engine.pipeline import run_pipeline
            result = run_pipeline(img_path, tmpdir)

            assert result.psd_result.psd_path is not None
            assert isinstance(result.warnings, list)
            assert isinstance(result.repeated_groups, int)

        Path(img_path).unlink(missing_ok=True)


class TestAdmin:
    def test_admin_requires_auth(self, client):
        response = client.get("/api/admin/stats")
        assert response.status_code == 401

    def test_admin_requires_pro(self, client):
        reg = client.post(
            "/api/auth/register",
            json={"email": "free@example.com", "password": "password123"},
        )
        token = reg.json()["access_token"]
        response = client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403


class TestErrorHandlers:
    def test_health_still_works(self, client):
        response = client.get("/health")
        assert response.status_code == 200
