from dataclasses import dataclass

import cv2
import numpy as np

from engine.segmentation import UIElement


@dataclass(frozen=True)
class UIRegion:
    name: str
    y_start_ratio: float
    y_end_ratio: float


UI_REGIONS = [
    UIRegion("status_bar", 0.0, 0.05),
    UIRegion("header", 0.05, 0.15),
    UIRegion("content", 0.15, 0.85),
    UIRegion("bottom_nav", 0.85, 1.0),
]


def classify_region(y: int, h: int, image_h: int) -> str:
    center_y = (y + h / 2) / image_h
    for region in UI_REGIONS:
        if region.y_start_ratio <= center_y <= region.y_end_ratio:
            return region.name
    return "content"


def detect_repeated_components(elements: list[UIElement], tolerance: float = 0.15) -> list[list[int]]:
    groups: list[list[int]] = []

    for i, elem_a in enumerate(elements):
        _, _, wa, ha = elem_a.bbox
        found_group = False

        for group in groups:
            ref_idx = group[0]
            _, _, wr, hr = elements[ref_idx].bbox
            w_ratio = abs(wa - wr) / max(wr, 1)
            h_ratio = abs(ha - hr) / max(hr, 1)

            if w_ratio < tolerance and h_ratio < tolerance and elem_a.element_type == elements[ref_idx].element_type:
                group.append(i)
                found_group = True
                break

        if not found_group:
            groups.append([i])

    return [g for g in groups if len(g) >= 2]


def refine_element_types(elements: list[UIElement], image: np.ndarray) -> list[UIElement]:
    image_h, image_w = image.shape[:2]
    refined: list[UIElement] = []

    for elem in elements:
        x, y, w, h = elem.bbox
        region = classify_region(y, h, image_h)
        element_type = elem.element_type

        if region == "status_bar" and h < image_h * 0.05:
            element_type = "icon"

        if region == "bottom_nav" and w > image_w * 0.8:
            element_type = "card"

        aspect = w / max(h, 1)
        if element_type == "card" and aspect > 5 and h < image_h * 0.08:
            element_type = "button"

        roi = image[y:y + h, x:x + w]
        if roi.size > 0:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            std = np.std(gray)
            if std < 15 and elem.element_type not in ("text", "background"):
                element_type = "background"

        refined.append(UIElement(
            element_type=element_type,
            bbox=elem.bbox,
            mask=elem.mask,
            confidence=elem.confidence,
            z_index=elem.z_index,
        ))

    return refined
