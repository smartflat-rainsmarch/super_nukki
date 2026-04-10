from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from engine.inpainting import InpaintResult, _compute_quality_score, inpaint


class InpaintMethod(str, Enum):
    OPENCV_TELEA = "telea"
    OPENCV_NS = "ns"
    LAMA = "lama"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True)
class InpaintConfig:
    method: InpaintMethod = InpaintMethod.OPENCV_TELEA
    radius: int = 5
    dilation_px: int = 5
    multipass: bool = False


def _detect_background_type(image: np.ndarray, mask: np.ndarray) -> str:
    bg_region = image[mask == 0]
    if bg_region.size == 0:
        return "solid"

    gray_bg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bg_gray = gray_bg[mask == 0]

    std = np.std(bg_gray)
    if std < 10:
        return "solid"
    elif std < 30:
        return "gradient"
    return "pattern"


def _quality_warning(quality_score: float, bg_type: str) -> str | None:
    if quality_score < 0.5:
        return f"Low restoration quality ({quality_score:.0%}). Background type: {bg_type}. Manual review recommended."
    if bg_type == "pattern" and quality_score < 0.7:
        return f"Pattern background detected with moderate quality ({quality_score:.0%}). Results may need manual adjustment."
    return None


def _multipass_inpaint(image: np.ndarray, mask: np.ndarray, radius: int = 5) -> InpaintResult:
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    inner_mask = cv2.erode(mask, kernel_small, iterations=2)
    outer_mask = cv2.subtract(mask, inner_mask)

    result1 = inpaint(image, outer_mask, radius=radius, method="telea")
    result2 = inpaint(result1.restored_image, inner_mask, radius=radius + 2, method="ns")

    combined_quality = (result1.quality_score + result2.quality_score) / 2

    return InpaintResult(
        restored_image=result2.restored_image,
        quality_score=combined_quality,
        inpaint_mask=mask,
    )


def _adaptive_inpaint(image: np.ndarray, mask: np.ndarray, radius: int = 5) -> InpaintResult:
    bg_type = _detect_background_type(image, mask)

    if bg_type == "solid":
        return inpaint(image, mask, radius=radius, method="telea")

    if bg_type == "gradient":
        return inpaint(image, mask, radius=radius + 3, method="ns")

    return _multipass_inpaint(image, mask, radius=radius)


def inpaint_advanced(
    image: np.ndarray,
    mask: np.ndarray,
    config: InpaintConfig = InpaintConfig(),
) -> tuple[InpaintResult, str | None]:
    bg_type = _detect_background_type(image, mask)

    if config.method == InpaintMethod.LAMA:
        result = _try_lama_inpaint(image, mask)
        if result is not None:
            warning = _quality_warning(result.quality_score, bg_type)
            return result, warning

    if config.method == InpaintMethod.ADAPTIVE:
        result = _adaptive_inpaint(image, mask, radius=config.radius)
        warning = _quality_warning(result.quality_score, bg_type)
        return result, warning

    if config.multipass:
        result = _multipass_inpaint(image, mask, radius=config.radius)
        warning = _quality_warning(result.quality_score, bg_type)
        return result, warning

    method = "telea" if config.method == InpaintMethod.OPENCV_TELEA else "ns"
    result = inpaint(image, mask, radius=config.radius, method=method)

    warning = _quality_warning(result.quality_score, bg_type)
    return result, warning


def _try_lama_inpaint(image: np.ndarray, mask: np.ndarray) -> InpaintResult | None:
    try:
        from engine.lama_inpainter import LamaInpainter, LamaConfig
        from config import settings

        config = LamaConfig(device=settings.lama_device)
        inpainter = LamaInpainter.get_instance(config)
        if not inpainter.is_available():
            return None
        result_image = inpainter.inpaint(image, mask)
        if result_image is None:
            return None
        quality = _compute_quality_score(image, result_image, mask)
        return InpaintResult(
            restored_image=result_image,
            quality_score=quality,
            inpaint_mask=mask,
        )
    except ImportError:
        return None


def create_element_removal_mask(
    image_shape: tuple[int, int],
    bbox: tuple[int, int, int, int],
    dilation_px: int = 8,
) -> np.ndarray:
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    x, y, bw, bh = bbox
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(w, x + bw)
    y1 = min(h, y + bh)
    cv2.rectangle(mask, (x0, y0), (x1, y1), 255, -1)

    if dilation_px > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (dilation_px * 2 + 1, dilation_px * 2 + 1),
        )
        mask = cv2.dilate(mask, kernel, iterations=1)

    return mask


def _poisson_blend(
    restored: np.ndarray,
    original: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    if not np.any(mask > 0):
        return restored

    moments = cv2.moments(mask)
    if moments["m00"] == 0:
        return restored

    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])

    h, w = original.shape[:2]
    cx = max(1, min(w - 2, cx))
    cy = max(1, min(h - 2, cy))

    try:
        result = cv2.seamlessClone(
            restored, original, mask,
            (cx, cy),
            cv2.NORMAL_CLONE,
        )
        return result
    except cv2.error:
        return restored


def _match_noise(
    restored: np.ndarray,
    original: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    border_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    dilated = cv2.dilate(mask, border_kernel)
    border_ring = cv2.bitwise_and(dilated, cv2.bitwise_not(mask))
    border_bool = border_ring > 0

    if not np.any(border_bool):
        return restored

    blur = cv2.GaussianBlur(original, (5, 5), 0)
    noise = original.astype(np.float64) - blur.astype(np.float64)

    noise_std = np.std(noise[border_bool])
    if noise_std < 2.0:
        return restored

    rng = np.random.default_rng()
    synthetic_noise = rng.normal(0, noise_std, restored.shape)
    mask_float = (mask > 0).astype(np.float64)
    if restored.ndim == 3:
        mask_float = mask_float[:, :, np.newaxis]

    result = restored.astype(np.float64) + synthetic_noise * mask_float
    return np.clip(result, 0, 255).astype(np.uint8)


def _postprocess(
    restored: np.ndarray,
    original: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    result = _poisson_blend(restored, original, mask)
    result = _match_noise(result, original, mask)
    return result


def _select_inpaint_tier(
    mask: np.ndarray,
    bg_type: str,
) -> InpaintMethod:
    mask_area = np.count_nonzero(mask)
    total_area = mask.shape[0] * mask.shape[1]
    if total_area == 0:
        return InpaintMethod.OPENCV_TELEA
    area_ratio = mask_area / total_area

    if area_ratio < 0.02 and bg_type == "solid":
        return InpaintMethod.OPENCV_TELEA

    return InpaintMethod.LAMA


def inpaint_element_removal(
    image: np.ndarray,
    bbox: tuple[int, int, int, int],
    config: InpaintConfig = InpaintConfig(method=InpaintMethod.ADAPTIVE),
) -> tuple[InpaintResult, str | None]:
    mask = create_element_removal_mask(image.shape, bbox)
    bg_type = _detect_background_type(image, mask)
    tier = _select_inpaint_tier(mask, bg_type)

    result: InpaintResult | None = None

    if tier == InpaintMethod.LAMA:
        result = _try_lama_inpaint(image, mask)

    if result is None:
        adaptive_result, _ = inpaint_advanced(
            image, mask,
            InpaintConfig(method=InpaintMethod.ADAPTIVE, radius=config.radius),
        )
        result = adaptive_result

    postprocessed = _postprocess(result.restored_image, image, mask)

    final_result = InpaintResult(
        restored_image=postprocessed,
        quality_score=result.quality_score,
        inpaint_mask=mask,
    )

    warning = _quality_warning(result.quality_score, bg_type)
    return final_result, warning
