from dataclasses import dataclass

import cv2
import numpy as np

from engine.ocr import OcrResult, TextBox, run_ocr, _fallback_ocr, _estimate_font_size, _estimate_text_color, _estimate_alignment


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b

    ix = max(ax, bx)
    iy = max(ay, by)
    ix2 = min(ax + aw, bx + bw)
    iy2 = min(ay + ah, by + bh)

    if ix2 <= ix or iy2 <= iy:
        return 0.0

    inter = (ix2 - ix) * (iy2 - iy)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _merge_results(primary: OcrResult, secondary: OcrResult, iou_threshold: float = 0.5) -> OcrResult:
    merged: list[TextBox] = list(primary.text_boxes)

    for s_box in secondary.text_boxes:
        is_duplicate = False
        for p_box in primary.text_boxes:
            if _iou(s_box.bbox, p_box.bbox) > iou_threshold:
                is_duplicate = True
                break

        if not is_duplicate and s_box.confidence > 0.3:
            merged.append(s_box)

    merged_sorted = sorted(merged, key=lambda b: (b.bbox[1], b.bbox[0]))
    full_text = "\n".join(b.text for b in merged_sorted)

    return OcrResult(text_boxes=merged_sorted, full_text=full_text)


def run_ocr_ensemble(image: np.ndarray) -> OcrResult:
    primary = run_ocr(image)
    secondary = _fallback_ocr(image)

    if not primary.text_boxes and not secondary.text_boxes:
        return OcrResult(text_boxes=[], full_text="")

    if not primary.text_boxes:
        return secondary
    if not secondary.text_boxes:
        return primary

    return _merge_results(primary, secondary)
