from dataclasses import dataclass
from pathlib import Path

from engine.preprocess import preprocess
from engine.ocr import run_ocr
from engine.segmentation import segment
from engine.inpainting import inpaint_text_regions
from engine.composer import compose_layers
from engine.psd_builder import build_psd, PsdBuildResult


@dataclass(frozen=True)
class PipelineResult:
    psd_result: PsdBuildResult
    manifest_path: str
    text_count: int
    element_count: int
    inpaint_quality: float


def run_pipeline(image_path: str, output_dir: str) -> PipelineResult:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    preprocessed = preprocess(image_path)
    image = preprocessed.image

    ocr_result = run_ocr(image)

    seg_result = segment(image)

    text_bboxes = [tb.bbox for tb in ocr_result.text_boxes]
    inpaint_result = inpaint_text_regions(image, text_bboxes)

    layers_dir = output_path / "layers"
    composer_result = compose_layers(
        image=image,
        background=inpaint_result.restored_image,
        elements=seg_result.elements,
        text_boxes=ocr_result.text_boxes,
        output_dir=str(layers_dir),
    )

    psd_path = output_path / "output.psd"
    canvas_w, canvas_h = preprocessed.processed_size
    psd_result = build_psd(
        layers=composer_result.layers,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        output_path=str(psd_path),
    )

    return PipelineResult(
        psd_result=psd_result,
        manifest_path=composer_result.manifest_path,
        text_count=len(ocr_result.text_boxes),
        element_count=len(seg_result.elements),
        inpaint_quality=inpaint_result.quality_score,
    )
