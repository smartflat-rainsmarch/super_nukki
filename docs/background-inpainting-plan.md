# AI Background Inpainting - 기획서 & 기술 계획서

## 1. 현황 분석

### 현재 상태

| 항목 | 현재 | 문제점 |
|------|------|--------|
| 배경 생성 | OpenCV Telea/NS | 텍스트 제거 수준만 가능, 큰 영역 처리 불가 |
| 요소 제거 | 미구현 | API 엔드포인트 자체가 없음 |
| LaMa 모델 | placeholder만 존재 | `_try_lama_inpaint()` → `return None` |
| 마스크 생성 | OCR 텍스트 전용 | 임의 요소 마스크 생성 불가 |

### 현재 인페인팅 한계

```
OpenCV Telea/NS 인페인팅:
- 원리: 주변 3~10px 픽셀의 색상을 수학적으로 보간
- 적합: 텍스트 제거, 스크래치 제거 (작은 영역)
- 한계: 50px 이상 영역에서 blurry smear 발생
- 결과: 아마추어 수준 (삼성 Object Eraser와 비교 불가)
```

### 목표 품질 기준 (삼성 Object Eraser 수준)

- 주변 텍스처/패턴 자연스러운 연속
- 그라데이션 배경에서 색상 전환 유지
- 복잡한 패턴(체크, 줄무늬 등) 정확한 재현
- 경계선에서 부자연스러운 이음새 없음
- 사람이 봤을 때 제거 흔적 인식 불가

---

## 2. 기술 스택 선정

### 인페인팅 모델 비교

| 모델 | 품질 | 속도 | VRAM | 장점 | 단점 |
|------|------|------|------|------|------|
| **LaMa** | ★★★★ | ~0.5s | ~2GB | 가볍고 빠름, 대형 마스크 특화 | 복잡한 텍스처 한계 |
| **MAT** | ★★★★ | ~1s | ~4GB | Transformer 기반 고품질 | LaMa보다 무거움 |
| **SD Inpainting** | ★★★★★ | ~3-8s | ~6GB | 최고 품질, 텍스트 프롬프트 가이드 가능 | 느리고 무거움 |
| **IoPaint** | ★★★★★ | 가변 | 가변 | LaMa/SD/MAT 통합, WebUI 포함 | 의존성 많음 |
| **MI-GAN** | ★★★★ | ~0.3s | ~2GB | 초고속 | 복잡한 장면 한계 |

### 선정: 3-Tier 하이브리드 전략

```
Tier 1: OpenCV (기존) ──── 작은 영역 (<2000px²), 단색 배경
           │                 응답시간: <100ms
           │
Tier 2: LaMa ────────────── 중간 영역, 그라데이션/단순 패턴
           │                 응답시간: ~500ms (GPU) / ~3s (CPU)
           │
Tier 3: Stable Diffusion ── 대형 영역, 복잡한 패턴/텍스처
         Inpainting          응답시간: ~5s (GPU)
```

**선정 근거:**
- LaMa: 대부분의 UI 요소 제거에 충분한 품질, 빠른 속도
- SD Inpainting: 복잡한 배경(사진, 일러스트)에서 LaMa보다 우수
- 기존 OpenCV: 단순 텍스트 제거에는 여전히 최적 (속도)

### 핵심 라이브러리

```
# 모델 추론
torch>=2.1.0                  # PyTorch (CUDA 지원)
torchvision>=0.16.0           # 이미지 전처리
diffusers>=0.25.0             # Stable Diffusion Inpainting
transformers>=4.36.0          # 모델 로딩
accelerate>=0.25.0            # GPU 최적화

# LaMa 모델
simple-lama-inpainting>=0.1.0 # LaMa 래퍼 (pip install 가능)
# 또는 iopaint>=1.3.0         # IoPaint (LaMa + SD 통합)

# 이미지 처리 (기존)
opencv-python-headless         # 기존 유지
Pillow                         # 기존 유지
numpy                          # 기존 유지

# GPU 관리
nvidia-ml-py3                  # GPU 메모리 모니터링 (선택)
```

---

## 3. 아키텍처 설계

### 전체 흐름

```
[사용자가 레이어 선택하여 제거 요청]
        │
        ▼
┌──────────────────────────┐
│  POST /api/project/{id}/ │
│  layer/{id}/remove       │
│  body: { layer_ids: [] } │
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  1. 마스크 생성           │ ← 제거할 요소의 bbox + alpha 마스크
│     (element_mask_gen)    │    안전 마진(dilation) 추가
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  2. Tier 자동 선택        │ ← 마스크 면적 + 배경 복잡도 분석
│     (tier_selector)       │
└──────────────────────────┘
        │
        ├─── 작은 영역, 단색 ──── OpenCV Telea/NS
        │
        ├─── 중간 영역 ─────────── LaMa
        │
        └─── 대형/복잡 ─────────── SD Inpainting
                                      │
        ┌─────────────────────────────┘
        ▼
┌──────────────────────────┐
│  3. 인페인팅 실행         │
│     + 품질 검증           │ ← quality_score < threshold면 상위 Tier로 재시도
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  4. 후처리                │ ← 경계 블렌딩 (Poisson blending)
│     (post_processing)     │    색상 보정, 노이즈 매칭
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  5. 결과 저장 & 응답      │ ← background.png 업데이트
│     - 레이어 트리 갱신     │    manifest.json 갱신
│     - PSD 재생성          │    DB Layer 상태 변경
└──────────────────────────┘
```

### 파일 구조 (신규/변경)

```
apps/api/engine/
├── inpainting.py              # 기존 유지 (OpenCV 전용)
├── inpainting_advanced.py     # 기존 유지 (어댑티브 로직)
├── inpainting_ai.py           # [신규] AI 인페인팅 통합 모듈
│   ├── InpaintingEngine       #   모델 로딩/캐싱, Tier 선택
│   ├── lama_inpaint()         #   LaMa 인페인팅
│   ├── sd_inpaint()           #   SD Inpainting
│   └── auto_inpaint()         #   자동 Tier 선택 + 실행
├── mask_generator.py          # [신규] 요소 마스크 생성
│   ├── create_element_mask()  #   단일 요소 마스크
│   ├── create_multi_mask()    #   다중 요소 마스크
│   └── refine_mask()          #   마스크 다듬기 (feathering)
├── post_process.py            # [신규] 인페인팅 후처리
│   ├── poisson_blend()        #   포아송 블렌딩
│   ├── color_correct()        #   색상 보정
│   └── noise_match()          #   노이즈 패턴 매칭
└── quality_score.py           # 기존 확장

apps/api/routers/
├── project.py                 # [수정] remove 엔드포인트 추가
└── layer.py                   # [신규 또는 project.py 내] 레이어 제거 API

apps/web/src/
├── app/project/[id]/edit/
│   └── page.tsx               # [수정] 요소 제거 UI 추가
└── components/
    └── LayerRemoveDialog.tsx   # [신규] 제거 확인 + 진행 상태 UI
```

---

## 4. 상세 구현 계획

### Phase 1: 인프라 & LaMa 통합 (핵심 MVP)

**목표:** 버튼/카드 등 UI 요소를 제거하면 배경이 자연스럽게 채워지는 것

#### 1-1. LaMa 모델 설치 및 래퍼 구현

```python
# apps/api/engine/inpainting_ai.py

from dataclasses import dataclass
from enum import Enum
import numpy as np
import torch
from PIL import Image

class InpaintTier(str, Enum):
    OPENCV = "opencv"       # 기존
    LAMA = "lama"           # Phase 1
    SD_INPAINT = "sd"       # Phase 2

@dataclass(frozen=True)
class AIInpaintConfig:
    tier: InpaintTier = InpaintTier.LAMA
    mask_dilation_px: int = 15       # 요소 경계 확장
    mask_feather_px: int = 5         # 마스크 부드러운 경계
    quality_threshold: float = 0.7   # 이 미만이면 상위 Tier 재시도
    auto_tier: bool = True           # 자동 Tier 선택

class InpaintingEngine:
    """싱글턴: 모델 로드 비용이 크므로 앱 시작 시 1회만 로드"""

    _instance = None
    _lama_model = None
    _sd_pipeline = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_lama(self):
        """LaMa 모델 로드 (최초 1회)"""
        if self._lama_model is None:
            from simple_lama_inpainting import SimpleLama
            self._lama_model = SimpleLama()
        return self._lama_model

    def lama_inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        model = self.load_lama()
        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        mask_pil = Image.fromarray(mask)
        result = model(img_pil, mask_pil)
        return cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
```

**설치:**
```bash
pip install simple-lama-inpainting
# 또는 GPU 최적화 버전:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install simple-lama-inpainting
```

#### 1-2. 요소 마스크 생성기

```python
# apps/api/engine/mask_generator.py

def create_element_mask(
    image_shape: tuple[int, int],
    element_bbox: tuple[int, int, int, int],
    element_mask: np.ndarray | None = None,
    dilation_px: int = 15,
    feather_px: int = 5,
) -> np.ndarray:
    """
    요소의 정확한 마스크를 생성.
    element_mask가 있으면 정밀 마스크 사용, 없으면 bbox 기반.
    """
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    if element_mask is not None:
        # 세그멘테이션에서 얻은 정밀 마스크 사용
        x, y, bw, bh = element_bbox
        mask[y:y+bh, x:x+bw] = element_mask[y:y+bh, x:x+bw]
    else:
        # bbox 기반 사각형 마스크
        x, y, bw, bh = element_bbox
        mask[y:y+bh, x:x+bw] = 255

    # 안전 마진 확장
    if dilation_px > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (dilation_px * 2 + 1, dilation_px * 2 + 1)
        )
        mask = cv2.dilate(mask, kernel, iterations=1)

    # 부드러운 경계 (feathering)
    if feather_px > 0:
        mask = cv2.GaussianBlur(mask, (0, 0), feather_px)
        mask = (mask > 127).astype(np.uint8) * 255

    return mask
```

#### 1-3. 자동 Tier 선택기

```python
def select_tier(
    mask: np.ndarray,
    image: np.ndarray,
) -> InpaintTier:
    """마스크 면적과 배경 복잡도에 따라 최적 Tier 자동 선택"""
    mask_area = np.count_nonzero(mask)
    total_area = mask.shape[0] * mask.shape[1]
    area_ratio = mask_area / total_area

    # 배경 복잡도 분석
    bg_region = image[mask == 0]
    bg_std = np.std(bg_region) if bg_region.size > 0 else 0

    # 결정 로직
    if area_ratio < 0.01 and bg_std < 15:
        return InpaintTier.OPENCV       # 작은 단색 → OpenCV로 충분
    if area_ratio < 0.15 or bg_std < 40:
        return InpaintTier.LAMA         # 대부분의 UI 요소 제거
    return InpaintTier.SD_INPAINT       # 대형 영역 or 복잡한 패턴
```

#### 1-4. API 엔드포인트

```python
# POST /api/project/{project_id}/remove-elements
# Body: { "layer_ids": ["uuid1", "uuid2"] }
# Response: {
#   "background_url": "/api/layer-image/{project_id}/background_updated.png",
#   "removed_layers": ["uuid1", "uuid2"],
#   "quality_score": 0.87,
#   "tier_used": "lama",
#   "warning": null
# }
```

#### 1-5. 프론트엔드 UI

- 레이어 트리에서 요소 선택 → "요소 제거" 버튼
- 제거 확인 다이얼로그 (선택된 요소 미리보기)
- 진행 상태 표시 (처리 중 → 완료)
- 결과 미리보기 (before/after 비교)

### Phase 2: Stable Diffusion Inpainting (고품질)

**목표:** 사진 배경, 일러스트 등 복잡한 배경에서도 프로 수준 결과

#### 2-1. SD Inpainting 파이프라인

```python
def load_sd_inpaint(self):
    """Stable Diffusion Inpainting 모델 로드"""
    if self._sd_pipeline is None:
        from diffusers import StableDiffusionInpaintPipeline
        self._sd_pipeline = StableDiffusionInpaintPipeline.from_pretrained(
            "runwayml/stable-diffusion-inpainting",
            torch_dtype=torch.float16,
            safety_checker=None,
        )
        if torch.cuda.is_available():
            self._sd_pipeline = self._sd_pipeline.to("cuda")
            self._sd_pipeline.enable_xformers_memory_efficient_attention()
    return self._sd_pipeline

def sd_inpaint(
    self,
    image: np.ndarray,
    mask: np.ndarray,
    prompt: str = "clean background, seamless texture",
    negative_prompt: str = "text, watermark, logo, artifact, blurry",
    strength: float = 0.75,
    guidance_scale: float = 7.5,
    num_inference_steps: int = 30,
) -> np.ndarray:
    pipe = self.load_sd_inpaint()
    img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    mask_pil = Image.fromarray(mask)

    # 512x512 단위로 리사이즈 (SD 요구사항)
    orig_size = img_pil.size
    img_resized = img_pil.resize((512, 512))
    mask_resized = mask_pil.resize((512, 512))

    result = pipe(
        prompt=prompt,
        image=img_resized,
        mask_image=mask_resized,
        strength=strength,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
    ).images[0]

    # 원본 해상도로 복원
    result_resized = result.resize(orig_size, Image.LANCZOS)
    return cv2.cvtColor(np.array(result_resized), cv2.COLOR_RGB2BGR)
```

#### 2-2. 프롬프트 자동 생성

배경 영역 분석 → 자동 프롬프트:

```python
def generate_inpaint_prompt(image: np.ndarray, mask: np.ndarray) -> str:
    """배경 특성을 분석하여 최적 프롬프트 자동 생성"""
    bg = image[mask == 0]
    mean_color = bg.mean(axis=0)
    std_color = bg.std(axis=0)

    prompts = ["clean seamless background"]

    if std_color.mean() < 10:
        prompts.append(f"solid color background")
    elif std_color.mean() < 30:
        prompts.append("smooth gradient background")
    else:
        prompts.append("natural texture pattern continuation")

    return ", ".join(prompts)
```

### Phase 3: 후처리 & 품질 향상

#### 3-1. 포아송 블렌딩 (경계 자연스러움)

```python
# apps/api/engine/post_process.py

def poisson_blend(
    source: np.ndarray,      # 인페인팅 결과
    target: np.ndarray,      # 원본 이미지
    mask: np.ndarray,        # 인페인팅 마스크
) -> np.ndarray:
    """OpenCV seamlessClone으로 경계 자연스럽게 블렌딩"""
    # 마스크 중심점 계산
    moments = cv2.moments(mask)
    if moments["m00"] == 0:
        return source
    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])

    # Poisson blending
    result = cv2.seamlessClone(
        source, target, mask,
        (cx, cy),
        cv2.NORMAL_CLONE
    )
    return result
```

#### 3-2. 노이즈 매칭

```python
def match_noise(
    inpainted: np.ndarray,
    original: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """원본의 노이즈/그레인 패턴을 인페인팅 영역에 적용"""
    # 원본 배경에서 노이즈 추출
    bg_region = original[mask == 0]
    blur = cv2.GaussianBlur(original, (5, 5), 0)
    noise = original.astype(float) - blur.astype(float)

    # 노이즈 강도 측정
    noise_std = np.std(noise[mask == 0])

    if noise_std < 2.0:
        return inpainted  # 노이즈 없는 이미지

    # 인페인팅 영역에 동일 강도 노이즈 추가
    synthetic_noise = np.random.normal(0, noise_std, inpainted.shape)
    result = inpainted.astype(float)
    noise_mask = (mask > 0).astype(float)[:, :, np.newaxis]
    result = result + synthetic_noise * noise_mask
    return np.clip(result, 0, 255).astype(np.uint8)
```

### Phase 4: GPU / 클라우드 인프라

#### 옵션 A: 자체 GPU 서버

```yaml
# docker-compose.gpu.yml
services:
  api:
    build: ./apps/api
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - INPAINT_MODEL_CACHE=/models
    volumes:
      - model-cache:/models
```

**최소 사양:**
- GPU: NVIDIA RTX 3060 (12GB VRAM) 이상
- RAM: 16GB
- Storage: 50GB (모델 캐시)

#### 옵션 B: 클라우드 GPU (비용 최적화)

```
요청 흐름:
Client → FastAPI → Celery Task → GPU Worker (RunPod/Lambda)
                                       │
                                  결과 반환 (S3/직접)
```

| 서비스 | GPU | 비용 (시간당) | 콜드스타트 |
|--------|-----|-------------|-----------|
| RunPod Serverless | A40 | ~$0.38 | 5-15s |
| Modal | A10G | ~$0.36 | 3-5s |
| Replicate | A40 | ~$0.00115/s | 10-20s |
| AWS Lambda (GPU) | - | 없음 | - |

**추천:** 초기에는 **Replicate API** 사용 (인프라 관리 불필요)

```python
# Replicate 활용 시 (가장 빠른 MVP)
import replicate

def replicate_inpaint(image_url: str, mask_url: str) -> str:
    output = replicate.run(
        "stability-ai/stable-diffusion-inpainting",
        input={
            "image": image_url,
            "mask": mask_url,
            "prompt": "clean background",
        }
    )
    return output[0]  # 결과 이미지 URL
```

#### 옵션 C: CPU-only 모드 (개발/테스트용)

```python
# LaMa는 CPU에서도 동작 (느리지만 가능)
# 처리 시간: GPU ~0.5s vs CPU ~3-5s
# 개발 시 GPU 없이도 테스트 가능
```

---

## 5. 구현 로드맵

### Phase 1: LaMa MVP (1주)

```
Day 1-2: 환경 설정
  ├── simple-lama-inpainting 설치 및 테스트
  ├── mask_generator.py 구현
  └── inpainting_ai.py (LaMa 래퍼) 구현

Day 3-4: API & 통합
  ├── POST /api/project/{id}/remove-elements 엔드포인트
  ├── composer.py 수정 (배경 이미지 갱신 로직)
  ├── 자동 Tier 선택기 구현
  └── 품질 검증 로직

Day 5: 프론트엔드
  ├── 레이어 트리에 "제거" 버튼 추가
  ├── 제거 확인 다이얼로그
  └── 결과 미리보기 (before/after)

Day 6-7: 테스트 & 튜닝
  ├── 다양한 배경 유형 테스트
  ├── 품질 임계값 조정
  └── 에러 핸들링
```

### Phase 2: SD Inpainting + 후처리 (1주)

```
Day 1-2: SD Inpainting 통합
  ├── diffusers 설치 및 파이프라인 구현
  ├── 자동 프롬프트 생성
  └── Tier 자동 전환 로직

Day 3-4: 후처리 파이프라인
  ├── 포아송 블렌딩
  ├── 색상 보정
  └── 노이즈 매칭

Day 5-7: 통합 테스트 & 최적화
  ├── Tier 1/2/3 전환 테스트
  ├── 성능 벤치마크
  └── 메모리 최적화
```

### Phase 3: 프로덕션 최적화 (1주)

```
Day 1-3: 인프라
  ├── GPU Docker 설정 또는 Replicate 연동
  ├── 모델 캐싱 전략
  └── 비동기 처리 (Celery 큐)

Day 4-5: UX 개선
  ├── 처리 중 실시간 진행률
  ├── 결과 비교 UI (슬라이더)
  ├── 수동 마스크 편집 (선택)

Day 6-7: 품질 보증
  ├── edge case 테스트
  ├── 다양한 디바이스 스크린샷 테스트
  └── 성능 모니터링
```

---

## 6. 비용 분석

### 모델별 처리 비용 (이미지 1장 기준)

| Tier | 자체 GPU | Replicate | Modal |
|------|----------|-----------|-------|
| OpenCV | ~$0 | - | - |
| LaMa | ~$0.001 | ~$0.005 | ~$0.003 |
| SD Inpaint | ~$0.003 | ~$0.015 | ~$0.010 |

### 월간 예상 비용 (1000장/월 기준)

| 항목 | 자체 GPU | 클라우드 GPU |
|------|----------|------------|
| 서버 | ~$150/월 (RTX 3060) | $0 (사용량 과금) |
| 처리비 | ~$0 | ~$5-15/월 |
| 합계 | ~$150/월 | ~$5-15/월 |

**결론:** 초기에는 클라우드 GPU (Replicate), 사용량 증가 시 자체 GPU로 전환

---

## 7. 품질 보장 전략

### 자동 품질 검증 파이프라인

```python
def validate_inpaint_quality(
    original: np.ndarray,
    result: np.ndarray,
    mask: np.ndarray,
) -> dict:
    """인페인팅 결과 다각적 품질 검증"""
    scores = {}

    # 1. 경계 연속성 (border continuity)
    scores["border"] = check_border_continuity(original, result, mask)

    # 2. 텍스처 일관성 (SSIM-based)
    scores["texture"] = check_texture_consistency(original, result, mask)

    # 3. 색상 일관성
    scores["color"] = check_color_consistency(original, result, mask)

    # 4. 아티팩트 감지
    scores["artifact"] = detect_artifacts(result, mask)

    # 종합 점수
    scores["overall"] = (
        scores["border"] * 0.3 +
        scores["texture"] * 0.3 +
        scores["color"] * 0.2 +
        scores["artifact"] * 0.2
    )

    return scores
```

### 품질 미달 시 자동 재시도

```
quality_score < 0.7 → 상위 Tier로 재시도
  OpenCV → LaMa → SD Inpainting

quality_score < 0.5 (모든 Tier 실패) → 사용자에게 수동 확인 요청
```

---

## 8. 리스크 & 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| GPU 없는 환경 | LaMa/SD 사용 불가 | CPU 모드 + Replicate 폴백 |
| 모델 로딩 시간 | 첫 요청 10-30초 지연 | 앱 시작 시 사전 로딩 |
| VRAM 부족 | OOM 크래시 | float16 + 해상도 제한 + 타일 처리 |
| 복잡한 배경 품질 | 아티팩트 발생 | SD Inpainting + 후처리 |
| 비용 증가 | GPU 요금 | 사용량 모니터링 + Tier별 과금 |

---

## 9. MVP 구현 우선순위

```
[즉시 시작 가능 - Phase 1 MVP]

1. simple-lama-inpainting 설치 ← pip install 한 줄
2. mask_generator.py 작성 ← 요소 bbox에서 마스크 생성
3. inpainting_ai.py 작성 ← LaMa 래퍼 + 자동 Tier 선택
4. POST /remove-elements 엔드포인트 ← 라우터에 추가
5. 프론트엔드 "제거" 버튼 ← 레이어 트리에 추가
6. 통합 테스트 ← 실제 UI 이미지로 검증

[결과물]
- 버튼/카드/아이콘 제거 시 배경 자연스럽게 채워짐
- 단색~그라데이션 배경: 거의 완벽
- 복잡한 패턴 배경: 양호 (Phase 2에서 개선)
```

---

## 10. 테스트 시나리오

| # | 시나리오 | 입력 | 기대 결과 |
|---|---------|------|----------|
| 1 | 단색 배경에서 버튼 제거 | 흰 배경 + 파란 버튼 | 흰 배경으로 완전 채움 |
| 2 | 그라데이션에서 카드 제거 | 파랑→보라 그라데이션 + 카드 | 그라데이션 자연스럽게 연속 |
| 3 | 패턴 배경에서 아이콘 제거 | 체크무늬 + 아이콘 | 체크무늬 패턴 유지 |
| 4 | 사진 배경에서 요소 제거 | 풍경 사진 위 UI 요소 | 풍경이 자연스럽게 이어짐 |
| 5 | 다중 요소 동시 제거 | 버튼 3개 선택 제거 | 모든 영역 자연스럽게 채움 |
| 6 | 인접 요소 제거 | 겹치거나 가까운 요소 | 마스크 병합 후 한번에 처리 |
| 7 | 화면 50% 이상 요소 | 큰 모달/카드 | SD Inpainting 자동 선택 |

---

## 부록: 참고 모델/논문

- **LaMa**: Resolution-robust Large Mask Inpainting with Fourier Convolutions (WACV 2022)
- **MAT**: Mask-Aware Transformer for Large Hole Image Inpainting (CVPR 2022)
- **Stable Diffusion Inpainting**: RunwayML, Stability AI
- **IoPaint (lama-cleaner)**: https://github.com/Sanster/IOPaint
- **simple-lama-inpainting**: https://github.com/enesmsahin/simple-lama-inpainting
- **Samsung Object Eraser**: Galaxy AI, on-device LaMa variant
