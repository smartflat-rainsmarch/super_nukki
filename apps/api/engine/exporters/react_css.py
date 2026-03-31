"""Generate React component skeleton + CSS from layer data."""
from dataclasses import dataclass
from pathlib import Path

from engine.composer import LayerInfo


@dataclass(frozen=True)
class ReactExportResult:
    component_path: str
    css_path: str
    component_count: int


def _layer_to_class_name(layer: LayerInfo) -> str:
    name = layer.name.replace(" ", "-").replace("_", "-").lower()
    return f"layer-{name}"


def _layer_to_css(layer: LayerInfo) -> str:
    x, y, w, h = layer.bbox
    cls = _layer_to_class_name(layer)

    rules = [
        f"  position: absolute;",
        f"  left: {x}px;",
        f"  top: {y}px;",
        f"  width: {w}px;",
        f"  height: {h}px;",
    ]

    if layer.layer_type == "text" and layer.font_size:
        rules.append(f"  font-size: {layer.font_size}px;")
        if layer.text_color:
            r, g, b = layer.text_color
            rules.append(f"  color: rgb({r}, {g}, {b});")

    if layer.layer_type == "button":
        rules.extend([
            "  border-radius: 8px;",
            "  cursor: pointer;",
        ])

    if layer.layer_type == "card":
        rules.extend([
            "  border-radius: 12px;",
            "  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);",
        ])

    return f".{cls} {{\n" + "\n".join(rules) + "\n}"


def _layer_to_jsx(layer: LayerInfo) -> str:
    cls = _layer_to_class_name(layer)

    if layer.layer_type == "text" and layer.text_content:
        tag = "p" if layer.font_size and layer.font_size < 20 else "h2"
        return f'      <{tag} className="{cls}">{layer.text_content}</{tag}>'

    if layer.layer_type == "button":
        label = layer.text_content or "Button"
        return f'      <button className="{cls}">{label}</button>'

    if layer.layer_type == "background":
        return f'      <div className="{cls}" />'

    return f'      <div className="{cls}" />'


def export_react(
    layers: list[LayerInfo],
    canvas_width: int,
    canvas_height: int,
    output_dir: str | Path,
) -> ReactExportResult:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    sorted_layers = sorted(layers, key=lambda l: l.z_index)

    # CSS
    css_parts = [
        f".screen {{\n  position: relative;\n  width: {canvas_width}px;\n  height: {canvas_height}px;\n  overflow: hidden;\n}}"
    ]
    for layer in sorted_layers:
        css_parts.append(_layer_to_css(layer))

    css_content = "\n\n".join(css_parts) + "\n"
    css_path = output_path / "Screen.css"
    css_path.write_text(css_content)

    # React Component
    jsx_lines = [_layer_to_jsx(layer) for layer in sorted_layers]

    component = f'''import React from "react";
import "./Screen.css";

export function Screen() {{
  return (
    <div className="screen">
{chr(10).join(jsx_lines)}
    </div>
  );
}}
'''

    component_path = output_path / "Screen.tsx"
    component_path.write_text(component)

    return ReactExportResult(
        component_path=str(component_path),
        css_path=str(css_path),
        component_count=len(sorted_layers),
    )
