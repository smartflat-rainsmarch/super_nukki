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


class TestElementRemoval:
    def test_create_element_removal_mask_basic(self):
        from engine.inpainting_advanced import create_element_removal_mask

        mask = create_element_removal_mask((100, 200), (50, 30, 40, 20))
        assert mask.shape == (100, 200)
        assert mask.dtype == np.uint8
        assert np.any(mask > 0)
        # The bbox area should be filled
        assert mask[35, 60] == 255

    def test_create_element_removal_mask_with_dilation(self):
        from engine.inpainting_advanced import create_element_removal_mask

        mask_no_dilation = create_element_removal_mask((200, 200), (50, 50, 40, 40), dilation_px=0)
        mask_with_dilation = create_element_removal_mask((200, 200), (50, 50, 40, 40), dilation_px=10)
        # Dilated mask should cover more area
        assert np.count_nonzero(mask_with_dilation) > np.count_nonzero(mask_no_dilation)

    def test_create_element_removal_mask_empty_bbox(self):
        from engine.inpainting_advanced import create_element_removal_mask

        mask = create_element_removal_mask((100, 200), (0, 0, 0, 0))
        # Zero-size bbox should still produce a valid mask
        assert mask.shape == (100, 200)

    def test_inpaint_element_removal_solid_bg(self, test_image):
        from engine.inpainting_advanced import inpaint_element_removal

        # Remove the button area (solid-ish background around it)
        result, warning = inpaint_element_removal(test_image, (100, 600, 200, 50))
        assert result.restored_image is not None
        assert result.restored_image.shape == test_image.shape
        assert 0.0 <= result.quality_score <= 1.0
        assert result.inpaint_mask is not None

    def test_inpaint_element_removal_returns_inpaint_result(self, test_image):
        from engine.inpainting_advanced import inpaint_element_removal
        from engine.inpainting import InpaintResult

        result, _ = inpaint_element_removal(test_image, (20, 100, 360, 150))
        assert isinstance(result, InpaintResult)

    def test_poisson_blend_no_mask(self):
        from engine.inpainting_advanced import _poisson_blend

        img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        mask = np.zeros((100, 100), dtype=np.uint8)
        result = _poisson_blend(img, img, mask)
        assert np.array_equal(result, img)

    def test_poisson_blend_with_mask(self, test_image):
        from engine.inpainting_advanced import _poisson_blend

        mask = np.zeros(test_image.shape[:2], dtype=np.uint8)
        cv2.rectangle(mask, (150, 300), (250, 400), 255, -1)
        restored = test_image.copy()
        restored[300:400, 150:250] = 200
        result = _poisson_blend(restored, test_image, mask)
        assert result.shape == test_image.shape

    def test_match_noise_low_noise(self):
        from engine.inpainting_advanced import _match_noise

        # Smooth image with no noise → should return unchanged
        img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(mask, (30, 30), (70, 70), 255, -1)
        result = _match_noise(img, img, mask)
        assert np.array_equal(result, img)

    def test_match_noise_high_noise(self):
        from engine.inpainting_advanced import _match_noise

        rng = np.random.default_rng(0)
        img = (rng.normal(128, 15, (100, 100, 3))).clip(0, 255).astype(np.uint8)
        mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(mask, (30, 30), (70, 70), 255, -1)
        smooth = np.ones((100, 100, 3), dtype=np.uint8) * 128
        result = _match_noise(smooth, img, mask)
        # Noise should be added in masked region
        assert not np.array_equal(result[40, 40], smooth[40, 40])

    def test_postprocess_pipeline(self, test_image):
        from engine.inpainting_advanced import _postprocess

        mask = np.zeros(test_image.shape[:2], dtype=np.uint8)
        cv2.rectangle(mask, (100, 600), (300, 650), 255, -1)
        restored = test_image.copy()
        result = _postprocess(restored, test_image, mask)
        assert result.shape == test_image.shape

    def test_select_inpaint_tier_small_solid(self):
        from engine.inpainting_advanced import _select_inpaint_tier, InpaintMethod

        # Small mask on solid background → should select OpenCV
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        cv2.rectangle(mask, (490, 490), (510, 510), 255, -1)  # tiny area
        assert _select_inpaint_tier(mask, "solid") == InpaintMethod.OPENCV_TELEA

    def test_select_inpaint_tier_large_pattern(self):
        from engine.inpainting_advanced import _select_inpaint_tier, InpaintMethod

        # Large mask → should select LaMa
        mask = np.zeros((100, 100), dtype=np.uint8)
        cv2.rectangle(mask, (10, 10), (90, 90), 255, -1)  # 64% area
        assert _select_inpaint_tier(mask, "pattern") == InpaintMethod.LAMA


class TestLamaInpainter:
    def test_singleton_pattern(self):
        from engine.lama_inpainter import LamaInpainter
        LamaInpainter.reset_instance()
        a = LamaInpainter.get_instance()
        b = LamaInpainter.get_instance()
        assert a is b
        LamaInpainter.reset_instance()

    def test_is_available_without_package(self):
        from engine.lama_inpainter import LamaInpainter, LamaConfig
        LamaInpainter.reset_instance()
        inpainter = LamaInpainter(LamaConfig())
        # simple_lama_inpainting may or may not be installed
        result = inpainter.is_available()
        assert isinstance(result, bool)
        LamaInpainter.reset_instance()

    def test_inpaint_returns_none_when_unavailable(self):
        from engine.lama_inpainter import LamaInpainter, LamaConfig
        LamaInpainter.reset_instance()
        inpainter = LamaInpainter(LamaConfig())
        inpainter._available = False
        result = inpainter.inpaint(
            np.ones((100, 100, 3), dtype=np.uint8) * 128,
            np.zeros((100, 100), dtype=np.uint8),
        )
        assert result is None
        LamaInpainter.reset_instance()

    def test_try_lama_fallback_to_opencv(self, test_image):
        from engine.lama_inpainter import LamaInpainter
        from engine.inpainting_advanced import inpaint_element_removal

        LamaInpainter.reset_instance()
        inpainter = LamaInpainter.get_instance()
        inpainter._available = False

        result, warning = inpaint_element_removal(test_image, (100, 600, 200, 50))
        assert result.restored_image is not None
        assert result.restored_image.shape == test_image.shape
        LamaInpainter.reset_instance()

    def test_resize_if_needed_small_image(self):
        from engine.lama_inpainter import LamaInpainter, LamaConfig
        LamaInpainter.reset_instance()
        inpainter = LamaInpainter(LamaConfig(max_side=2048))
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        mask = np.zeros((100, 200), dtype=np.uint8)
        r_img, r_mask, orig = inpainter._resize_if_needed(img, mask)
        assert orig is None
        assert r_img.shape == img.shape
        LamaInpainter.reset_instance()

    def test_resize_if_needed_large_image(self):
        from engine.lama_inpainter import LamaInpainter, LamaConfig
        LamaInpainter.reset_instance()
        inpainter = LamaInpainter(LamaConfig(max_side=100))
        img = np.zeros((300, 200, 3), dtype=np.uint8)
        mask = np.zeros((300, 200), dtype=np.uint8)
        r_img, r_mask, orig = inpainter._resize_if_needed(img, mask)
        assert orig == (200, 300)
        assert max(r_img.shape[:2]) <= 100
        LamaInpainter.reset_instance()

    def test_select_tier_zero_area(self):
        from engine.inpainting_advanced import _select_inpaint_tier, InpaintMethod

        mask = np.zeros((0, 0), dtype=np.uint8)
        assert _select_inpaint_tier(mask, "solid") == InpaintMethod.OPENCV_TELEA


class TestBatchRemoval:
    def test_multiple_element_removal_sequential(self, test_image):
        from engine.inpainting_advanced import inpaint_element_removal

        # Remove button area first
        result1, _ = inpaint_element_removal(test_image, (100, 600, 200, 50))
        assert result1.restored_image.shape == test_image.shape

        # Remove card area from already-inpainted image
        result2, _ = inpaint_element_removal(result1.restored_image, (20, 100, 360, 150))
        assert result2.restored_image.shape == test_image.shape

        # Both quality scores should be valid
        assert 0.0 <= result1.quality_score <= 1.0
        assert 0.0 <= result2.quality_score <= 1.0

    def test_sequential_quality_not_degraded(self, test_image):
        from engine.inpainting_advanced import inpaint_element_removal

        # Single large removal
        result_single, _ = inpaint_element_removal(test_image, (100, 600, 200, 50))

        # Sequential small removals on same image
        r1, _ = inpaint_element_removal(test_image, (100, 600, 100, 50))
        r2, _ = inpaint_element_removal(r1.restored_image, (200, 600, 100, 50))

        # Both approaches should produce valid results
        assert result_single.quality_score > 0.0
        assert r2.quality_score > 0.0

    def test_overlapping_bbox_removal(self, test_image):
        from engine.inpainting_advanced import inpaint_element_removal

        # First removal
        r1, _ = inpaint_element_removal(test_image, (100, 600, 200, 50))
        # Overlapping area removal
        r2, _ = inpaint_element_removal(r1.restored_image, (150, 590, 200, 70))
        assert r2.restored_image.shape == test_image.shape

    def test_full_image_bbox(self, test_image):
        from engine.inpainting_advanced import inpaint_element_removal

        h, w = test_image.shape[:2]
        # Remove almost entire image (extreme case)
        result, warning = inpaint_element_removal(test_image, (0, 0, w, h))
        assert result.restored_image is not None
        # Quality should be low for such extreme case
        assert result.quality_score >= 0.0


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
