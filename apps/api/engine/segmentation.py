from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class UIElement:
    element_type: str  # button, card, icon, image, background, text_block
    bbox: tuple[int, int, int, int]  # x, y, w, h
    mask: np.ndarray
    confidence: float
    z_index: int


@dataclass(frozen=True)
class SegmentationResult:
    elements: list[UIElement]
    background_mask: np.ndarray


MIN_ELEMENT_AREA = 200
BUTTON_ASPECT_RATIO_RANGE = (1.5, 8.0)
CARD_MIN_AREA_RATIO = 0.02
ICON_MAX_SIZE = 80


def _classify_element(
    w: int, h: int, image_w: int, image_h: int, aspect_ratio: float, area_ratio: float
) -> str:
    if max(w, h) <= ICON_MAX_SIZE:
        return "icon"

    if (BUTTON_ASPECT_RATIO_RANGE[0] <= aspect_ratio <= BUTTON_ASPECT_RATIO_RANGE[1]
            and h < image_h * 0.1 and area_ratio < 0.05):
        return "button"

    if area_ratio >= CARD_MIN_AREA_RATIO and aspect_ratio < 3.0:
        return "card"

    if area_ratio > 0.5:
        return "background"

    return "image"


def _find_contour_elements(image: np.ndarray) -> list[tuple[int, int, int, int, np.ndarray]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 30, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    results: list[tuple[int, int, int, int, np.ndarray]] = []
    h, w = image.shape[:2]

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_ELEMENT_AREA:
            continue

        x, y, cw, ch = cv2.boundingRect(contour)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        results.append((x, y, cw, ch, mask))

    return results


def _color_based_segmentation(image: np.ndarray) -> list[tuple[int, int, int, int, np.ndarray]]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, w = image.shape[:2]

    results: list[tuple[int, int, int, int, np.ndarray]] = []

    colors = [
        ((0, 50, 50), (10, 255, 255)),     # red
        ((100, 50, 50), (130, 255, 255)),   # blue
        ((35, 50, 50), (85, 255, 255)),     # green
        ((20, 100, 100), (35, 255, 255)),   # yellow/orange
    ]

    for lower, upper in colors:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_ELEMENT_AREA:
                continue
            x, y, cw, ch = cv2.boundingRect(contour)
            elem_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(elem_mask, [contour], -1, 255, -1)
            results.append((x, y, cw, ch, elem_mask))

    return results


def _merge_overlapping(
    elements: list[tuple[int, int, int, int, np.ndarray]],
    iou_threshold: float = 0.5,
) -> list[tuple[int, int, int, int, np.ndarray]]:
    if not elements:
        return []

    kept: list[tuple[int, int, int, int, np.ndarray]] = []

    sorted_elems = sorted(elements, key=lambda e: e[2] * e[3], reverse=True)

    for elem in sorted_elems:
        x1, y1, w1, h1, mask1 = elem
        is_duplicate = False

        for kx, ky, kw, kh, kmask in kept:
            inter_x = max(x1, kx)
            inter_y = max(y1, ky)
            inter_x2 = min(x1 + w1, kx + kw)
            inter_y2 = min(y1 + h1, ky + kh)

            if inter_x2 <= inter_x or inter_y2 <= inter_y:
                continue

            inter_area = (inter_x2 - inter_x) * (inter_y2 - inter_y)
            area1 = w1 * h1
            area2 = kw * kh
            union_area = area1 + area2 - inter_area
            iou = inter_area / union_area if union_area > 0 else 0

            if iou > iou_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(elem)

    return kept


def segment(image: np.ndarray) -> SegmentationResult:
    image_h, image_w = image.shape[:2]
    total_area = image_h * image_w

    contour_elements = _find_contour_elements(image)
    color_elements = _color_based_segmentation(image)

    all_elements = _merge_overlapping(contour_elements + color_elements)

    ui_elements: list[UIElement] = []
    combined_mask = np.zeros((image_h, image_w), dtype=np.uint8)

    for idx, (x, y, w, h, mask) in enumerate(all_elements):
        area_ratio = (w * h) / total_area
        aspect_ratio = w / max(h, 1)

        element_type = _classify_element(w, h, image_w, image_h, aspect_ratio, area_ratio)

        confidence = min(0.9, 0.5 + area_ratio * 2)

        ui_elements.append(UIElement(
            element_type=element_type,
            bbox=(x, y, w, h),
            mask=mask,
            confidence=confidence,
            z_index=idx + 1,
        ))

        combined_mask = cv2.bitwise_or(combined_mask, mask)

    background_mask = cv2.bitwise_not(combined_mask)

    ui_elements_sorted = sorted(
        ui_elements,
        key=lambda e: e.bbox[2] * e.bbox[3],
        reverse=True,
    )
    final_elements = [
        UIElement(
            element_type=e.element_type,
            bbox=e.bbox,
            mask=e.mask,
            confidence=e.confidence,
            z_index=idx,
        )
        for idx, e in enumerate(ui_elements_sorted)
    ]

    return SegmentationResult(
        elements=final_elements,
        background_mask=background_mask,
    )
