from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class TextBox:
    bbox: tuple[int, int, int, int]  # x, y, w, h
    text: str
    confidence: float
    font_size_estimate: int
    color_estimate: tuple[int, int, int]  # RGB
    alignment: str  # left, center, right


@dataclass(frozen=True)
class OcrResult:
    text_boxes: list[TextBox]
    full_text: str


def _estimate_font_size(bbox_height: int) -> int:
    return max(8, int(bbox_height * 0.75))


def _estimate_text_color(image: np.ndarray, x: int, y: int, w: int, h: int) -> tuple[int, int, int]:
    roi = image[y:y + h, x:x + w]
    if roi.size == 0:
        return (0, 0, 0)

    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    bg_value = np.median(gray_roi)

    if bg_value > 127:
        mask = gray_roi < (bg_value - 30)
    else:
        mask = gray_roi > (bg_value + 30)

    if not np.any(mask):
        return (0, 0, 0)

    text_pixels = roi[mask]
    mean_color = text_pixels.mean(axis=0).astype(int)
    b, g, r = int(mean_color[0]), int(mean_color[1]), int(mean_color[2])
    return (r, g, b)


def _estimate_alignment(x: int, w: int, image_width: int) -> str:
    center_x = x + w / 2
    relative_center = center_x / image_width

    if relative_center < 0.35:
        return "left"
    elif relative_center > 0.65:
        return "right"
    return "center"


def run_ocr(image: np.ndarray) -> OcrResult:
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return _fallback_ocr(image)

    ocr = PaddleOCR(use_angle_cls=True, lang="korean", show_log=False)
    result = ocr.ocr(image, cls=True)

    if not result or not result[0]:
        return OcrResult(text_boxes=[], full_text="")

    image_h, image_w = image.shape[:2]
    text_boxes: list[TextBox] = []
    texts: list[str] = []

    for line in result[0]:
        points = line[0]
        text = line[1][0]
        confidence = float(line[1][1])

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x = int(min(xs))
        y = int(min(ys))
        w = int(max(xs) - x)
        h = int(max(ys) - y)

        x = max(0, x)
        y = max(0, y)
        w = min(w, image_w - x)
        h = min(h, image_h - y)

        text_boxes.append(TextBox(
            bbox=(x, y, w, h),
            text=text,
            confidence=confidence,
            font_size_estimate=_estimate_font_size(h),
            color_estimate=_estimate_text_color(image, x, y, w, h),
            alignment=_estimate_alignment(x, w, image_w),
        ))
        texts.append(text)

    return OcrResult(
        text_boxes=text_boxes,
        full_text="\n".join(texts),
    )


def _fallback_ocr(image: np.ndarray) -> OcrResult:
    try:
        import easyocr
    except ImportError:
        return OcrResult(text_boxes=[], full_text="")

    reader = easyocr.Reader(["ko", "en"], gpu=False)
    results = reader.readtext(image)

    image_h, image_w = image.shape[:2]
    text_boxes: list[TextBox] = []
    texts: list[str] = []

    for bbox_points, text, confidence in results:
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        x = int(min(xs))
        y = int(min(ys))
        w = int(max(xs) - x)
        h = int(max(ys) - y)

        x = max(0, x)
        y = max(0, y)

        text_boxes.append(TextBox(
            bbox=(x, y, w, h),
            text=text,
            confidence=float(confidence),
            font_size_estimate=_estimate_font_size(h),
            color_estimate=_estimate_text_color(image, x, y, w, h),
            alignment=_estimate_alignment(x, w, image_w),
        ))
        texts.append(text)

    return OcrResult(
        text_boxes=text_boxes,
        full_text="\n".join(texts),
    )
