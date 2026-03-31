"""Extract design tokens (colors, fonts, spacing) from layer data."""
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from engine.composer import LayerInfo


@dataclass(frozen=True)
class DesignTokensResult:
    json_path: str
    color_count: int
    font_size_count: int


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _extract_colors(layers: list[LayerInfo]) -> list[dict]:
    color_counter: Counter[str] = Counter()

    for layer in layers:
        if layer.text_color:
            hex_color = _rgb_to_hex(*layer.text_color)
            color_counter[hex_color] += 1

    sorted_colors = color_counter.most_common(20)
    tokens = []
    for i, (hex_val, count) in enumerate(sorted_colors):
        name = f"color-{i + 1}" if i > 0 else "color-primary"
        tokens.append({
            "name": name,
            "value": hex_val,
            "usage_count": count,
        })

    return tokens


def _extract_font_sizes(layers: list[LayerInfo]) -> list[dict]:
    size_counter: Counter[int] = Counter()

    for layer in layers:
        if layer.font_size and layer.layer_type == "text":
            size_counter[layer.font_size] += 1

    sorted_sizes = sorted(size_counter.items(), reverse=True)
    scale_names = ["display", "heading-1", "heading-2", "heading-3", "body-lg", "body", "caption", "small"]
    tokens = []
    for i, (size, count) in enumerate(sorted_sizes):
        name = scale_names[i] if i < len(scale_names) else f"size-{size}"
        tokens.append({
            "name": name,
            "value": f"{size}px",
            "raw": size,
            "usage_count": count,
        })

    return tokens


def _extract_spacing(layers: list[LayerInfo]) -> list[dict]:
    gaps: Counter[int] = Counter()

    sorted_layers = sorted(layers, key=lambda l: l.bbox[1])
    for i in range(len(sorted_layers) - 1):
        _, y1, _, h1 = sorted_layers[i].bbox
        _, y2, _, _ = sorted_layers[i + 1].bbox
        gap = y2 - (y1 + h1)
        if 0 < gap < 200:
            rounded = round(gap / 4) * 4
            gaps[rounded] += 1

    sorted_gaps = sorted(gaps.items())
    return [
        {"name": f"space-{v}", "value": f"{v}px", "usage_count": c}
        for v, c in sorted_gaps
    ]


def extract_design_tokens(
    layers: list[LayerInfo],
    output_path: str | Path,
) -> DesignTokensResult:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    colors = _extract_colors(layers)
    font_sizes = _extract_font_sizes(layers)
    spacing = _extract_spacing(layers)

    tokens = {
        "version": "1.0",
        "colors": colors,
        "typography": {
            "fontFamily": "Inter, sans-serif",
            "sizes": font_sizes,
        },
        "spacing": spacing,
    }

    output_path.write_text(json.dumps(tokens, ensure_ascii=False, indent=2))

    return DesignTokensResult(
        json_path=str(output_path),
        color_count=len(colors),
        font_size_count=len(font_sizes),
    )
