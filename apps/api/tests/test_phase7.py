"""Phase 7 tests: layout detection, quality scoring, adaptive inpainting."""
import numpy as np


class TestLayoutDetection:
    def test_mobile_portrait(self):
        from engine.preprocess import detect_layout_type, LayoutType

        assert detect_layout_type(390, 844) == LayoutType.MOBILE_PORTRAIT

    def test_desktop(self):
        from engine.preprocess import detect_layout_type, LayoutType

        assert detect_layout_type(1920, 1080) == LayoutType.DESKTOP

    def test_tablet(self):
        from engine.preprocess import detect_layout_type, LayoutType

        assert detect_layout_type(1024, 768) == LayoutType.TABLET

    def test_mobile_landscape(self):
        from engine.preprocess import detect_layout_type, LayoutType

        assert detect_layout_type(844, 390) == LayoutType.DESKTOP

    def test_preprocess_includes_layout_type(self):
        import tempfile
        from pathlib import Path
        import cv2

        img = np.ones((844, 390, 3), dtype=np.uint8) * 200
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.png")
            cv2.imwrite(path, img)
            from engine.preprocess import preprocess, LayoutType
            result = preprocess(path)
            assert result.layout_type == LayoutType.MOBILE_PORTRAIT


class TestQualityScore:
    def test_compute_quality_with_data(self):
        from engine.ocr import OcrResult, TextBox
        from engine.segmentation import SegmentationResult, UIElement
        from engine.inpainting import InpaintResult
        from engine.quality_score import compute_quality

        ocr = OcrResult(
            text_boxes=[
                TextBox((10, 10, 100, 20), "Hello", 0.95, 16, (0, 0, 0), "left"),
                TextBox((10, 40, 100, 20), "World", 0.8, 14, (0, 0, 0), "left"),
            ],
            full_text="Hello\nWorld",
        )

        mask = np.zeros((100, 100), dtype=np.uint8)
        seg = SegmentationResult(
            elements=[
                UIElement("button", (10, 10, 50, 20), mask, 0.8, 0),
                UIElement("card", (10, 40, 80, 50), mask, 0.9, 1),
                UIElement("text", (10, 60, 60, 15), mask, 0.7, 2),
            ],
            background_mask=mask,
        )

        inpaint_result = InpaintResult(
            restored_image=np.zeros((100, 100, 3), dtype=np.uint8),
            quality_score=0.85,
            inpaint_mask=mask,
        )

        report = compute_quality(ocr, seg, inpaint_result)
        assert 0 <= report.overall_score <= 100
        assert report.grade in ("A", "B", "C", "D", "F")
        assert isinstance(report.details, list)

    def test_compute_quality_no_text(self):
        from engine.ocr import OcrResult
        from engine.segmentation import SegmentationResult
        from engine.inpainting import InpaintResult
        from engine.quality_score import compute_quality

        mask = np.zeros((100, 100), dtype=np.uint8)
        ocr = OcrResult(text_boxes=[], full_text="")
        seg = SegmentationResult(elements=[], background_mask=mask)
        inpaint_result = InpaintResult(
            restored_image=np.zeros((100, 100, 3), dtype=np.uint8),
            quality_score=0.5,
            inpaint_mask=mask,
        )

        report = compute_quality(ocr, seg, inpaint_result)
        assert report.ocr_score == 50.0
        assert "No text detected" in report.details

    def test_grade_mapping(self):
        from engine.quality_score import _grade_from_score

        assert _grade_from_score(95) == "A"
        assert _grade_from_score(80) == "B"
        assert _grade_from_score(65) == "C"
        assert _grade_from_score(45) == "D"
        assert _grade_from_score(30) == "F"


class TestAdaptiveInpainting:
    def test_adaptive_solid(self):
        from engine.inpainting_advanced import InpaintConfig, InpaintMethod, inpaint_advanced

        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[30:50, 30:50] = 255

        config = InpaintConfig(method=InpaintMethod.ADAPTIVE)
        result, warning = inpaint_advanced(img, mask, config)
        assert result.restored_image is not None

    def test_multipass(self):
        from engine.inpainting_advanced import InpaintConfig, inpaint_advanced

        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[30:50, 30:50] = 255

        config = InpaintConfig(multipass=True)
        result, warning = inpaint_advanced(img, mask, config)
        assert result.restored_image is not None
        assert result.quality_score >= 0


class TestDesktopRegions:
    def test_classify_desktop_header(self):
        from engine.ui_rules import classify_region

        assert classify_region(20, 30, 1080, "desktop") == "header"

    def test_classify_desktop_footer(self):
        from engine.ui_rules import classify_region

        assert classify_region(1000, 50, 1080, "desktop") == "footer"

    def test_classify_desktop_content(self):
        from engine.ui_rules import classify_region

        assert classify_region(400, 50, 1080, "desktop") == "content"
