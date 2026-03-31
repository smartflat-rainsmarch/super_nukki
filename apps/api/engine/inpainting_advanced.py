from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from engine.inpainting import InpaintResult, inpaint


class InpaintMethod(str, Enum):
    OPENCV_TELEA = "telea"
    OPENCV_NS = "ns"
    LAMA = "lama"


@dataclass(frozen=True)
class InpaintConfig:
    method: InpaintMethod = InpaintMethod.OPENCV_TELEA
    radius: int = 5
    dilation_px: int = 5


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

    method = "telea" if config.method == InpaintMethod.OPENCV_TELEA else "ns"
    result = inpaint(image, mask, radius=config.radius, method=method)

    warning = _quality_warning(result.quality_score, bg_type)
    return result, warning


def _try_lama_inpaint(image: np.ndarray, mask: np.ndarray) -> InpaintResult | None:
    # LaMa integration placeholder
    # In production, this would load the LaMa model and run inference
    # For now, fall back to None to use OpenCV
    return None
