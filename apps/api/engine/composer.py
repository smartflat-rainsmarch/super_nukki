import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np

from engine.ocr import TextBox
from engine.segmentation import UIElement


@dataclass(frozen=True)
class LayerInfo:
    name: str
    layer_type: str  # text, button, card, icon, image, background
    bbox: tuple[int, int, int, int]  # x, y, w, h
    z_index: int
    image_path: str
    text_content: str | None = None
    font_size: int | None = None
    text_color: tuple[int, int, int] | None = None
    group: str | None = None


@dataclass(frozen=True)
class ComposerResult:
    layers: list[LayerInfo]
    manifest_path: str


def _assign_group(element_type: str, y: int, image_h: int) -> str:
    if y < image_h * 0.12:
        return "Header"
    if y > image_h * 0.88:
        return "Footer"
    if element_type == "card":
        return "Card"
    if element_type == "button":
        return "CTA"
    return "Body"


def _extract_element_png(
    image: np.ndarray,
    mask: np.ndarray,
    bbox: tuple[int, int, int, int],
) -> np.ndarray:
    x, y, w, h = bbox
    img_h, img_w = image.shape[:2]

    x = max(0, x)
    y = max(0, y)
    w = min(w, img_w - x)
    h = min(h, img_h - y)

    roi = image[y:y + h, x:x + w]
    mask_roi = mask[y:y + h, x:x + w]

    rgba = cv2.cvtColor(roi, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = mask_roi

    return rgba


def compose_layers(
    image: np.ndarray,
    background: np.ndarray,
    elements: list[UIElement],
    text_boxes: list[TextBox],
    output_dir: str | Path,
) -> ComposerResult:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    image_h, image_w = image.shape[:2]
    layers: list[LayerInfo] = []

    bg_path = str(output_path / "background.png")
    cv2.imwrite(bg_path, background)
    layers.append(LayerInfo(
        name="Background",
        layer_type="background",
        bbox=(0, 0, image_w, image_h),
        z_index=0,
        image_path=bg_path,
        group="Background",
    ))

    for idx, element in enumerate(elements):
        if element.element_type == "background":
            continue

        png = _extract_element_png(image, element.mask, element.bbox)
        elem_name = f"{element.element_type}_{idx}"
        elem_path = str(output_path / f"{elem_name}.png")
        cv2.imwrite(elem_path, png)

        group = _assign_group(element.element_type, element.bbox[1], image_h)

        layers.append(LayerInfo(
            name=elem_name,
            layer_type=element.element_type,
            bbox=element.bbox,
            z_index=element.z_index + 1,
            image_path=elem_path,
            group=group,
        ))

    for idx, text_box in enumerate(text_boxes):
        x, y, w, h = text_box.bbox
        text_name = f"text_{idx}"
        group = _assign_group("text", y, image_h)

        text_roi = image[y:y + h, x:x + w]
        text_rgba = cv2.cvtColor(text_roi, cv2.COLOR_BGR2BGRA)
        text_path = str(output_path / f"{text_name}.png")
        cv2.imwrite(text_path, text_rgba)

        layers.append(LayerInfo(
            name=text_name,
            layer_type="text",
            bbox=text_box.bbox,
            z_index=len(elements) + idx + 1,
            image_path=text_path,
            text_content=text_box.text,
            font_size=text_box.font_size_estimate,
            text_color=text_box.color_estimate,
            group=group,
        ))

    layers_sorted = sorted(layers, key=lambda l: l.z_index)

    manifest = {
        "canvas_size": {"width": image_w, "height": image_h},
        "layers": [
            {
                "name": l.name,
                "type": l.layer_type,
                "bbox": {"x": l.bbox[0], "y": l.bbox[1], "w": l.bbox[2], "h": l.bbox[3]},
                "z_index": l.z_index,
                "image_path": l.image_path,
                "text_content": l.text_content,
                "font_size": l.font_size,
                "text_color": l.text_color,
                "group": l.group,
            }
            for l in layers_sorted
        ],
    }

    manifest_path = str(output_path / "manifest.json")
    Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    return ComposerResult(layers=layers_sorted, manifest_path=manifest_path)
