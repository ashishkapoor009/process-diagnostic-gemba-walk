"""OCR utilities for scanned process maps, swimlanes and screenshots.

Uses OpenCV for light pre-processing (grayscale + adaptive threshold) to
improve Tesseract accuracy on low-quality scans/screenshots, per the spec's
"extract process steps automatically using OCR + LLM" requirement.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

try:
    import cv2

    _HAS_CV2 = True
except ImportError:  # pragma: no cover - optional dependency
    _HAS_CV2 = False


def _configure_tesseract() -> None:
    settings = get_settings()
    if settings.tesseract_cmd and settings.tesseract_cmd != "tesseract":
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def preprocess_image(image: Image.Image) -> Image.Image:
    """Grayscale + adaptive threshold + denoise to boost OCR accuracy on
    process-map screenshots and low-DPI scans. Falls back to a plain
    grayscale conversion when OpenCV isn't available.
    """
    if not _HAS_CV2:
        return image.convert("L")

    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    return Image.fromarray(thresh)


def ocr_image(image_path: str | Path) -> str:
    """Run OCR on a single image file and return extracted text."""
    _configure_tesseract()
    try:
        image = Image.open(image_path)
        processed = preprocess_image(image)
        text = pytesseract.image_to_string(processed)
        return text.strip()
    except Exception as exc:  # pragma: no cover - depends on system tesseract install
        logger.warning(f"OCR failed for {image_path}: {exc}")
        return ""


def ocr_pil_image(image: Image.Image) -> str:
    _configure_tesseract()
    try:
        processed = preprocess_image(image)
        return pytesseract.image_to_string(processed).strip()
    except Exception as exc:  # pragma: no cover
        logger.warning(f"OCR failed for in-memory image: {exc}")
        return ""
