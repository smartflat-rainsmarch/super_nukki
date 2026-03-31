from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from engine.inpainting import InpaintResult, inpaint


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
    # LaMa model not yet available - fall back to adaptive OpenCV
    # TODO: integrate LaMa model when GPU inference is set up
    return None
