from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LamaConfig:
    device: str = "cpu"
    max_side: int = 2048


class LamaInpainter:
    _instance: LamaInpainter | None = None
    _lock = threading.Lock()

    def __init__(self, config: LamaConfig = LamaConfig()) -> None:
        self._config = config
        self._model: object | None = None
        self._available: bool | None = None

    @classmethod
    def get_instance(cls, config: LamaConfig | None = None) -> LamaInpainter:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config or LamaConfig())
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            if cls._instance is not None:
                cls._instance._release_model()
            cls._instance = None

    def _release_model(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            from simple_lama_inpainting import SimpleLama  # noqa: F401
            self._available = True
        except ImportError:
            logger.info("simple-lama-inpainting not installed, LaMa unavailable")
            self._available = False

        return self._available

    def _load_model(self) -> object:
        if self._model is not None:
            return self._model

        from simple_lama_inpainting import SimpleLama
        self._model = SimpleLama()
        logger.info("LaMa model loaded (device: %s)", self._config.device)
        return self._model

    def _resize_if_needed(
        self,
        image: np.ndarray,
        mask: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, tuple[int, int] | None]:
        h, w = image.shape[:2]
        max_side = max(h, w)

        if max_side <= self._config.max_side:
            return image, mask, None

        scale = self._config.max_side / max_side
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        resized_mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

        return resized_img, resized_mask, (w, h)

    def inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray | None:
        if not self.is_available():
            return None

        try:
            from PIL import Image as PILImage

            model = self._load_model()

            resized_img, resized_mask, original_size = self._resize_if_needed(image, mask)

            img_rgb = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            img_pil = PILImage.fromarray(img_rgb)
            mask_pil = PILImage.fromarray(resized_mask)

            result_pil = model(img_pil, mask_pil)
            result_rgb = np.array(result_pil)
            result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

            if original_size is not None:
                result_bgr = cv2.resize(
                    result_bgr, original_size, interpolation=cv2.INTER_LANCZOS4,
                )

            return result_bgr
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                logger.error("GPU OOM during LaMa inpainting, releasing model")
                self._release_model()
            else:
                logger.exception("LaMa runtime error")
            return None
        except Exception:
            logger.exception("LaMa inpainting failed")
            return None
