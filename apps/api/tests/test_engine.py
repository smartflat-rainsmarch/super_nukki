import io
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image


def _create_test_ui_image(width=400, height=700) -> np.ndarray:
    img = np.ones((height, width, 3), dtype=np.uint8) * 245

    cv2.rectangle(img, (0, 0), (width, 60), (50, 50, 200), -1)
    cv2.putText(img, "Header", (140, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    cv2.rectangle(img, (20, 100), (380, 250), (255, 255, 255), -1)
    cv2.rectangle(img, (20, 100), (380, 250), (200, 200, 200), 2)
    cv2.putText(img, "Card Title", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(img, "Description text here", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    cv2.rectangle(img, (100, 600), (300, 650), (200, 100, 50), -1)
    cv2.putText(img, "Button", (155, 635), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return img


@pytest.fixture()
def test_image_path():
    img = _create_test_ui_image()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        cv2.imwrite(f.name, img)
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture()
def test_image():
    return _create_test_ui_image()


class TestPreprocess:
    def test_preprocess_loads_image(self, test_image_path):
        from engine.preprocess import preprocess

        result = preprocess(test_image_path)
        assert result.image is not None
        assert result.image.shape[2] == 3
        assert result.original_size == (400, 700)

    def test_preprocess_invalid_path(self):
        from engine.preprocess import preprocess

        with pytest.raises(ValueError, match="Cannot load image"):
            preprocess("/nonexistent/image.png")

    def test_normalize_resolution_large_image(self):
        from engine.preprocess import normalize_resolution

        large = np.zeros((4000, 3000, 3), dtype=np.uint8)
        result, scale = normalize_resolution(large)
        assert max(result.shape[:2]) <= 2048
        assert scale < 1.0

    def test_normalize_resolution_small_image(self):
        from engine.preprocess import normalize_resolution

        small = np.zeros((500, 300, 3), dtype=np.uint8)
        result, scale = normalize_resolution(small)
        assert scale == 1.0
        assert result.shape == small.shape


class TestSegmentation:
    def test_segment_finds_elements(self, test_image):
        from engine.segmentation import segment

        result = segment(test_image)
        assert len(result.elements) > 0
        assert result.background_mask is not None
        assert result.background_mask.shape == test_image.shape[:2]

    def test_segment_returns_bboxes(self, test_image):
        from engine.segmentation import segment

        result = segment(test_image)
        for elem in result.elements:
            x, y, w, h = elem.bbox
            assert w > 0
            assert h > 0


class TestInpainting:
    def test_inpaint_with_no_text(self, test_image):
        from engine.inpainting import inpaint_text_regions

        result = inpaint_text_regions(test_image, [])
        assert result.quality_score == 1.0
        assert np.array_equal(result.restored_image, test_image)

    def test_inpaint_with_text_regions(self, test_image):
        from engine.inpainting import inpaint_text_regions

        bboxes = [(40, 130, 200, 30), (40, 180, 250, 25)]
        result = inpaint_text_regions(test_image, bboxes)
        assert result.restored_image is not None
        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0
        assert np.any(result.inpaint_mask > 0)

    def test_create_text_mask(self):
        from engine.inpainting import create_text_mask

        mask = create_text_mask((100, 200), [(10, 10, 50, 20)], dilation_px=3)
        assert mask.shape == (100, 200)
        assert np.any(mask > 0)


class TestComposer:
    def test_compose_layers(self, test_image):
        from engine.segmentation import segment, UIElement
        from engine.ocr import TextBox
        from engine.composer import compose_layers

        elements = [UIElement(
            element_type="card",
            bbox=(20, 100, 360, 150),
            mask=np.ones(test_image.shape[:2], dtype=np.uint8) * 255,
            confidence=0.8,
            z_index=1,
        )]
        text_boxes = [TextBox(
            bbox=(40, 130, 200, 30),
            text="Card Title",
            confidence=0.95,
            font_size_estimate=18,
            color_estimate=(30, 30, 30),
            alignment="left",
        )]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = compose_layers(
                image=test_image,
                background=test_image,
                elements=elements,
                text_boxes=text_boxes,
                output_dir=tmpdir,
            )
            assert len(result.layers) >= 2  # background + at least one element
            assert Path(result.manifest_path).exists()


class TestPsdBuilder:
    def test_build_simple_psd(self):
        from engine.composer import LayerInfo
        from engine.psd_builder import build_psd

        with tempfile.TemporaryDirectory() as tmpdir:
            bg = np.ones((100, 200, 3), dtype=np.uint8) * 200
            bg_path = str(Path(tmpdir) / "bg.png")
            cv2.imwrite(bg_path, bg)

            layers = [LayerInfo(
                name="Background",
                layer_type="background",
                bbox=(0, 0, 200, 100),
                z_index=0,
                image_path=bg_path,
                group="Background",
            )]

            psd_path = str(Path(tmpdir) / "test.psd")
            result = build_psd(layers, 200, 100, psd_path)

            assert Path(result.psd_path).exists()
            assert result.layer_count == 1
            assert result.file_size_bytes > 0

            with open(psd_path, "rb") as f:
                sig = f.read(4)
                assert sig == b"8BPS"
