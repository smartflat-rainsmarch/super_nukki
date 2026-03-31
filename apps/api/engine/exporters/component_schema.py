"""Generate structured UI component JSON schema from layer data."""
import json
from dataclasses import dataclass
from pathlib import Path

from engine.composer import LayerInfo


@dataclass(frozen=True)
class ComponentSchemaResult:
    json_path: str
    component_count: int


def _layer_to_component(layer: LayerInfo) -> dict:
    x, y, w, h = layer.bbox

    component: dict = {
        "type": _map_component_type(layer.layer_type),
        "name": layer.name,
        "bounds": {"x": x, "y": y, "width": w, "height": h},
        "zIndex": layer.z_index,
    }

    if layer.text_content:
        component["text"] = {
            "content": layer.text_content,
            "fontSize": layer.font_size,
            "color": _format_color(layer.text_color),
        }

    if layer.image_path:
        component["asset"] = {"src": layer.image_path}

    return component


def _map_component_type(layer_type: str) -> str:
    mapping = {
        "text": "Text",
        "button": "Button",
        "card": "Card",
        "icon": "Icon",
        "image": "Image",
        "background": "Container",
    }
    return mapping.get(layer_type, "Box")


def _format_color(color: tuple[int, int, int] | None) -> str | None:
    if color is None:
        return None
    return f"rgb({color[0]}, {color[1]}, {color[2]})"


def _build_component_tree(layers: list[LayerInfo]) -> list[dict]:
    sorted_layers = sorted(layers, key=lambda l: l.z_index)

    groups: dict[str, list[dict]] = {}
    for layer in sorted_layers:
        group = layer.group or "root"
        component = _layer_to_component(layer)
        groups.setdefault(group, []).append(component)

    if len(groups) == 1:
        return list(groups.values())[0]

    tree: list[dict] = []
    for group_name, children in groups.items():
        tree.append({
            "type": "Section",
            "name": group_name,
            "children": children,
        })

    return tree


def export_component_schema(
    layers: list[LayerInfo],
    canvas_width: int,
    canvas_height: int,
    output_path: str | Path,
) -> ComponentSchemaResult:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tree = _build_component_tree(layers)

    schema = {
        "$schema": "https://ui2psd.com/component-schema/v1",
        "canvas": {"width": canvas_width, "height": canvas_height},
        "components": tree,
        "metadata": {
            "generator": "UI2PSD Studio",
            "version": "0.1.0",
            "totalComponents": len(layers),
        },
    }

    output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2))

    return ComponentSchemaResult(
        json_path=str(output_path),
        component_count=len(layers),
    )
