from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class PreprocessResult:
    image: np.ndarray
    original_size: tuple[int, int]
    processed_size: tuple[int, int]
    scale_factor: float


MAX_DIMENSION = 2048
TARGET_MIN_DIMENSION = 640


def load_image(path: str | Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Cannot load image: {path}")
    return img


def normalize_resolution(image: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = image.shape[:2]
    max_dim = max(h, w)

    if max_dim <= MAX_DIMENSION:
        return image, 1.0

    scale = MAX_DIMENSION / max_dim
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    return resized, scale


def denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image, None, 6, 6, 7, 21)


def sharpen(image: np.ndarray) -> np.ndarray:
    kernel = np.array([
        [0, -0.5, 0],
        [-0.5, 3, -0.5],
        [0, -0.5, 0],
    ], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)


def detect_device_frame(image: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    border_top = gray[:int(h * 0.05), :]
    border_bottom = gray[int(h * 0.95):, :]
    border_left = gray[:, :int(w * 0.05)]
    border_right = gray[:, int(w * 0.95):]

    borders = [border_top, border_bottom, border_left, border_right]
    dark_borders = sum(1 for b in borders if np.mean(b) < 30)

    if dark_borders >= 3:
        mask = gray > 30
        coords = np.argwhere(mask)
        if len(coords) > 0:
            y0, x0 = coords.min(axis=0)
            y1, x1 = coords.max(axis=0)
            padding = 2
            y0 = max(0, y0 - padding)
            x0 = max(0, x0 - padding)
            y1 = min(h - 1, y1 + padding)
            x1 = min(w - 1, x1 + padding)
            return image[y0:y1 + 1, x0:x1 + 1]

    return None


def preprocess(image_path: str | Path) -> PreprocessResult:
    image = load_image(image_path)
    original_h, original_w = image.shape[:2]

    cropped = detect_device_frame(image)
    if cropped is not None:
        image = cropped

    image, scale = normalize_resolution(image)
    image = denoise(image)
    image = sharpen(image)

    processed_h, processed_w = image.shape[:2]

    return PreprocessResult(
        image=image,
        original_size=(original_w, original_h),
        processed_size=(processed_w, processed_h),
        scale_factor=scale,
    )
