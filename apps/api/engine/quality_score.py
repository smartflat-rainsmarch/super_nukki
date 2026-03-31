from dataclasses import dataclass

from engine.ocr import OcrResult
from engine.segmentation import SegmentationResult
from engine.inpainting import InpaintResult


@dataclass(frozen=True)
class QualityReport:
    overall_score: float  # 0-100
    ocr_score: float
    segmentation_score: float
    inpainting_score: float
    grade: str  # A, B, C, D, F
    details: list[str]


def _grade_from_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def compute_quality(
    ocr_result: OcrResult,
    seg_result: SegmentationResult,
    inpaint_result: InpaintResult,
) -> QualityReport:
    details: list[str] = []

    # OCR score: average confidence
    if ocr_result.text_boxes:
        avg_conf = sum(t.confidence for t in ocr_result.text_boxes) / len(ocr_result.text_boxes)
        ocr_score = min(avg_conf * 100, 100)
        low_conf = [t for t in ocr_result.text_boxes if t.confidence < 0.5]
        if low_conf:
            details.append(f"{len(low_conf)} text regions with low confidence (<50%)")
    else:
        ocr_score = 50.0
        details.append("No text detected")

    # Segmentation score: element count and diversity
    if seg_result.elements:
        type_set = {e.element_type for e in seg_result.elements}
        diversity_bonus = min(len(type_set) * 15, 40)
        count_score = min(len(seg_result.elements) * 10, 60)
        segmentation_score = min(count_score + diversity_bonus, 100)
    else:
        segmentation_score = 20.0
        details.append("No UI elements detected")

    # Inpainting score
    inpainting_score = inpaint_result.quality_score * 100
    if inpainting_score < 50:
        details.append("Background restoration quality is low")

    # Weighted overall
    overall = (
        ocr_score * 0.3
        + segmentation_score * 0.4
        + inpainting_score * 0.3
    )

    grade = _grade_from_score(overall)

    return QualityReport(
        overall_score=round(overall, 1),
        ocr_score=round(ocr_score, 1),
        segmentation_score=round(segmentation_score, 1),
        inpainting_score=round(inpainting_score, 1),
        grade=grade,
        details=details,
    )
