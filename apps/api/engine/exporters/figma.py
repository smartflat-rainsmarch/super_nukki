"""Figma-compatible JSON export from layer data."""
import json
from dataclasses import dataclass
from pathlib import Path

from engine.composer import LayerInfo


@dataclass(frozen=True)
class FigmaExportResult:
    json_path: str
    node_count: int


def _layer_to_figma_node(layer: LayerInfo, index: int) -> dict:
    x, y, w, h = layer.bbox

    base = {
        "id": f"node_{index}",
        "name": layer.name,
        "visible": True,
        "locked": False,
        "opacity": 1.0,
        "absoluteBoundingBox": {"x": x, "y": y, "width": w, "height": h},
        "constraints": {"vertical": "TOP", "horizontal": "LEFT"},
    }

    if layer.layer_type == "text" and layer.text_content:
        return {
            **base,
            "type": "TEXT",
            "characters": layer.text_content,
            "style": {
                "fontFamily": "Inter",
                "fontSize": layer.font_size or 14,
                "fontWeight": 400,
                "textAlignHorizontal": "LEFT",
                "textAlignVertical": "TOP",
                "lineHeightPx": (layer.font_size or 14) * 1.5,
            },
            "fills": [
                {
                    "type": "SOLID",
                    "color": _rgb_to_figma(layer.text_color or (0, 0, 0)),
                }
            ],
        }

    if layer.layer_type == "background":
        return {
            **base,
            "type": "RECTANGLE",
            "fills": [{"type": "IMAGE", "imageRef": layer.image_path}],
            "cornerRadius": 0,
        }

    return {
        **base,
        "type": "FRAME",
        "fills": [{"type": "IMAGE", "imageRef": layer.image_path}],
        "cornerRadius": _guess_corner_radius(layer.layer_type),
    }


def _rgb_to_figma(rgb: tuple[int, int, int]) -> dict:
    return {
        "r": rgb[0] / 255.0,
        "g": rgb[1] / 255.0,
        "b": rgb[2] / 255.0,
        "a": 1.0,
    }


def _guess_corner_radius(layer_type: str) -> int:
    radii = {"button": 8, "card": 12, "icon": 0, "image": 0}
    return radii.get(layer_type, 0)


def _group_layers(layers: list[LayerInfo]) -> dict[str, list[LayerInfo]]:
    groups: dict[str, list[LayerInfo]] = {}
    for layer in layers:
        group = layer.group or "Ungrouped"
        groups.setdefault(group, []).append(layer)
    return groups


def export_figma(
    layers: list[LayerInfo],
    canvas_width: int,
    canvas_height: int,
    output_path: str | Path,
) -> FigmaExportResult:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    grouped = _group_layers(layers)
    children: list[dict] = []
    node_index = 0

    for group_name, group_layers in grouped.items():
        group_children = []
        for layer in sorted(group_layers, key=lambda l: l.z_index):
            group_children.append(_layer_to_figma_node(layer, node_index))
            node_index += 1

        children.append({
            "id": f"group_{group_name}",
            "name": group_name,
            "type": "GROUP",
            "visible": True,
            "children": group_children,
        })

    figma_doc = {
        "name": "UI2PSD Export",
        "document": {
            "id": "doc",
            "name": "Document",
            "type": "DOCUMENT",
            "children": [
                {
                    "id": "page_0",
                    "name": "Page 1",
                    "type": "CANVAS",
                    "children": [
                        {
                            "id": "frame_0",
                            "name": "Screen",
                            "type": "FRAME",
                            "absoluteBoundingBox": {
                                "x": 0,
                                "y": 0,
                                "width": canvas_width,
                                "height": canvas_height,
                            },
                            "children": children,
                        }
                    ],
                }
            ],
        },
    }

    output_path.write_text(json.dumps(figma_doc, ensure_ascii=False, indent=2))

    return FigmaExportResult(
        json_path=str(output_path),
        node_count=node_index,
    )
