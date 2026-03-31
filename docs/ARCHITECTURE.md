# System Architecture

## 1. 전체 구조

Frontend (Next.js)
    ↓
API Gateway
    ↓
Backend (FastAPI)
    ↓
AI Engine Layer
    ↓
Storage (S3 + DB)

## 2. 구성 요소

### Frontend
- Next.js
- Tailwind
- Upload UI
- Preview UI

### Backend
- FastAPI
- Celery (비동기 처리)
- Redis (Queue)

### AI Engine

#### 1. Layout 분석
- SAM2 (Meta)
- Detectron2

#### 2. OCR
- PaddleOCR
- Tesseract

#### 3. 이미지 처리
- OpenCV
- Pillow

#### 4. Inpainting
- LaMa
- Stable Diffusion Inpainting

#### 5. PSD 생성
- psd-tools
- custom layer builder

### Storage
- AWS S3: 이미지 저장
- PostgreSQL: 메타데이터

## 3. 처리 흐름

1. 업로드
2. Job 생성
3. Queue 등록
4. Worker 실행
5. 결과 저장
6. 다운로드 제공

## 4. 확장 전략
- Worker 수평 확장
- GPU 서버 분리