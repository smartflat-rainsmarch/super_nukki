from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class InpaintResult:
    restored_image: np.ndarray
    quality_score: float  # 0.0 ~ 1.0
    inpaint_mask: np.ndarray


def create_text_mask(
    image_shape: tuple[int, int],
    text_bboxes: list[tuple[int, int, int, int]],
    dilation_px: int = 5,
) -> np.ndarray:
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    for x, y, bw, bh in text_bboxes:
        x0 = max(0, x - dilation_px)
        y0 = max(0, y - dilation_px)
        x1 = min(w, x + bw + dilation_px)
        y1 = min(h, y + bh + dilation_px)
        cv2.rectangle(mask, (x0, y0), (x1, y1), 255, -1)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=2)

    return mask


def _compute_quality_score(
    original: np.ndarray,
    restored: np.ndarray,
    mask: np.ndarray,
) -> float:
    mask_bool = mask > 0
    if not np.any(mask_bool):
        return 1.0

    border_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    dilated = cv2.dilate(mask, border_kernel)
    border = cv2.bitwise_and(dilated, cv2.bitwise_not(mask))
    border_bool = border > 0

    if not np.any(border_bool):
        return 0.5

    original_border = original[border_bool].astype(float)
    restored_border = restored[border_bool].astype(float)

    diff = np.abs(original_border - restored_border)
    mean_diff = diff.mean()

    score = max(0.0, min(1.0, 1.0 - (mean_diff / 128.0)))
    return round(score, 3)


def inpaint(
    image: np.ndarray,
    mask: np.ndarray,
    radius: int = 5,
    method: str = "telea",
) -> InpaintResult:
    if not np.any(mask > 0):
        return InpaintResult(
            restored_image=image.copy(),
            quality_score=1.0,
            inpaint_mask=mask,
        )

    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    restored = cv2.inpaint(image, mask, radius, flag)

    quality = _compute_quality_score(image, restored, mask)

    return InpaintResult(
        restored_image=restored,
        quality_score=quality,
        inpaint_mask=mask,
    )


def inpaint_text_regions(
    image: np.ndarray,
    text_bboxes: list[tuple[int, int, int, int]],
    dilation_px: int = 5,
) -> InpaintResult:
    mask = create_text_mask(image.shape, text_bboxes, dilation_px)
    return inpaint(image, mask)
