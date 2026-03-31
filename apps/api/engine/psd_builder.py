import struct
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from engine.composer import LayerInfo


@dataclass(frozen=True)
class PsdBuildResult:
    psd_path: str
    layer_count: int
    file_size_bytes: int


def _write_psd_header(f, width: int, height: int, num_channels: int, num_layers: int):
    f.write(b"8BPS")         # signature
    f.write(struct.pack(">H", 1))  # version
    f.write(b"\x00" * 6)    # reserved
    f.write(struct.pack(">H", num_channels))  # channels (RGBA=4)
    f.write(struct.pack(">I", height))
    f.write(struct.pack(">I", width))
    f.write(struct.pack(">H", 8))   # bits per channel
    f.write(struct.pack(">H", 3))   # color mode: RGB


def _write_color_mode_data(f):
    f.write(struct.pack(">I", 0))


def _write_image_resources(f):
    f.write(struct.pack(">I", 0))


def _load_layer_rgba(layer: LayerInfo, canvas_w: int, canvas_h: int) -> np.ndarray:
    img = cv2.imread(layer.image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        rgba = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        return rgba

    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

    x, y, w, h = layer.bbox
    layer_h, layer_w = img.shape[:2]

    canvas = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)

    src_h = min(layer_h, h, canvas_h - y)
    src_w = min(layer_w, w, canvas_w - x)

    if src_h > 0 and src_w > 0 and y >= 0 and x >= 0:
        canvas[y:y + src_h, x:x + src_w] = img[:src_h, :src_w]

    bgra = canvas
    rgba = np.empty_like(bgra)
    rgba[:, :, 0] = bgra[:, :, 2]  # R
    rgba[:, :, 1] = bgra[:, :, 1]  # G
    rgba[:, :, 2] = bgra[:, :, 0]  # B
    rgba[:, :, 3] = bgra[:, :, 3]  # A

    return rgba


def _write_channel_data(f, channel_data: np.ndarray):
    f.write(struct.pack(">H", 0))  # raw compression
    f.write(channel_data.tobytes())


def _encode_pascal_string(name: str) -> bytes:
    encoded = name.encode("ascii", errors="replace")[:255]
    length = len(encoded)
    result = struct.pack("B", length) + encoded
    if len(result) % 2 != 0:
        result += b"\x00"
    return result


def build_psd(
    layers: list[LayerInfo],
    canvas_width: int,
    canvas_height: int,
    output_path: str | Path,
) -> PsdBuildResult:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sorted_layers = sorted(layers, key=lambda l: l.z_index)

    with open(output_path, "wb") as f:
        _write_psd_header(f, canvas_width, canvas_height, 4, len(sorted_layers))
        _write_color_mode_data(f)
        _write_image_resources(f)

        layer_section_start = f.tell()
        f.write(struct.pack(">I", 0))  # placeholder for layer section length

        layer_info_start = f.tell()
        f.write(struct.pack(">I", 0))  # placeholder for layer info length

        f.write(struct.pack(">h", len(sorted_layers)))

        layer_images: list[np.ndarray] = []

        for layer in sorted_layers:
            rgba = _load_layer_rgba(layer, canvas_width, canvas_height)
            layer_images.append(rgba)

            x, y, w, h = layer.bbox
            top = max(0, y)
            left = max(0, x)
            bottom = min(canvas_height, y + h)
            right = min(canvas_width, x + w)

            f.write(struct.pack(">I", top))
            f.write(struct.pack(">I", left))
            f.write(struct.pack(">I", bottom))
            f.write(struct.pack(">I", right))

            num_channels = 4
            f.write(struct.pack(">H", num_channels))

            ch_h = bottom - top
            ch_w = right - left
            channel_data_len = 2 + ch_h * ch_w

            for ch_id in [0, 1, 2, -1]:
                f.write(struct.pack(">h", ch_id))
                f.write(struct.pack(">I", channel_data_len))

            f.write(b"8BIM")
            f.write(b"norm")
            f.write(struct.pack("B", 255))  # opacity
            f.write(struct.pack("B", 0))    # clipping
            f.write(struct.pack("B", 8))    # flags (visible)
            f.write(b"\x00")               # filler

            extra_data_start = f.tell()
            f.write(struct.pack(">I", 0))  # placeholder

            f.write(struct.pack(">I", 0))  # layer mask data

            f.write(struct.pack(">I", 0))  # blending ranges

            pascal = _encode_pascal_string(layer.name)
            padded_len = len(pascal)
            while padded_len % 4 != 0:
                padded_len += 1
            f.write(pascal)
            f.write(b"\x00" * (padded_len - len(pascal)))

            extra_data_end = f.tell()
            extra_len = extra_data_end - extra_data_start - 4
            f.seek(extra_data_start)
            f.write(struct.pack(">I", extra_len))
            f.seek(extra_data_end)

        for idx, layer in enumerate(sorted_layers):
            rgba = layer_images[idx]
            x, y, w, h = layer.bbox
            top = max(0, y)
            left = max(0, x)
            bottom = min(canvas_height, y + h)
            right = min(canvas_width, x + w)

            roi = rgba[top:bottom, left:right]

            for ch_idx in [0, 1, 2, 3]:
                channel = roi[:, :, ch_idx]
                _write_channel_data(f, channel)

        layer_info_end = f.tell()
        layer_info_len = layer_info_end - layer_info_start - 4
        f.seek(layer_info_start)
        f.write(struct.pack(">I", layer_info_len))
        f.seek(layer_info_end)

        if (layer_info_len + 4) % 2 != 0:
            f.write(b"\x00")

        layer_section_end = f.tell()
        layer_section_len = layer_section_end - layer_section_start - 4
        f.seek(layer_section_start)
        f.write(struct.pack(">I", layer_section_len))
        f.seek(layer_section_end)

        composite = np.zeros((canvas_height, canvas_width, 4), dtype=np.uint8)
        for rgba in layer_images:
            alpha = rgba[:, :, 3:4].astype(float) / 255.0
            for c in range(3):
                composite[:, :, c] = (
                    composite[:, :, c].astype(float) * (1 - alpha[:, :, 0])
                    + rgba[:, :, c].astype(float) * alpha[:, :, 0]
                ).astype(np.uint8)
            composite[:, :, 3] = np.maximum(composite[:, :, 3], rgba[:, :, 3])

        f.write(struct.pack(">H", 0))  # raw compression
        for ch in range(3):
            f.write(composite[:, :, ch].tobytes())

    file_size = output_path.stat().st_size

    return PsdBuildResult(
        psd_path=str(output_path),
        layer_count=len(sorted_layers),
        file_size_bytes=file_size,
    )
