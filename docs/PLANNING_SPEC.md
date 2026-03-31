# UI2PSD Studio - 종합 기획서

> 최종 수정일: 2026-03-31
> 문서 버전: v1.0

---

## 1. 프로젝트 개요

### 1.1 서비스명
**UI2PSD Studio** (가칭: Screen2PSD / PixelSplit AI)

### 1.2 한 줄 정의
> "AI가 만든 한 장의 UI 이미지를, 실무에서 편집 가능한 PSD 레이어 파일로 되돌리는 SaaS"

### 1.3 핵심 가치
| 대상 | 가치 |
|------|------|
| 프론트엔드 개발자 | AI 시안을 컴포넌트 단위로 해석 |
| 디자이너 | PNG/JPG → PSD 레이어 복원 |
| 에이전시/외주업체 | 캡처본을 편집 가능 형태로 즉시 변환 |
| 스타트업 PM/기획자 | 생성형 AI 결과물 → 수정/개발 가능 구조 |
| 마케터/운영자 | 배너/상세페이지에서 구성요소 재활용 |

### 1.4 차별점
기존 배경제거 서비스와 달리 **하나의 파이프라인**으로:
- UI 요소 구조 이해
- 텍스트 OCR + 스타일 추정
- 레이어 재구성
- 빈 공간 인페인팅
- PSD 레이어 패키징

---

## 2. 기술 아키텍처

### 2.1 시스템 구조

```
Frontend (Next.js + TypeScript + Tailwind)
    ↓
API Gateway (Nginx)
    ↓
Backend (FastAPI + Celery + Redis)
    ↓
AI Engine Layer (PyTorch + OpenCV + PaddleOCR + SAM2)
    ↓
Storage (S3/R2 + PostgreSQL)
```

### 2.2 프론트엔드
- **프레임워크**: Next.js + TypeScript
- **스타일**: Tailwind CSS + shadcn/ui
- **상태관리**: Zustand 또는 React Query
- **캔버스 편집**: Konva.js 또는 Fabric.js

### 2.3 백엔드
- **API**: FastAPI (Python)
- **작업 큐**: Celery + Redis
- **DB**: PostgreSQL
- **스토리지**: AWS S3 / Cloudflare R2

### 2.4 AI/CV 엔진

| 모듈 | 기술 | 역할 |
|------|------|------|
| OCR | PaddleOCR + EasyOCR | 텍스트 추출 + 스타일 추정 |
| 세그멘테이션 | SAM 2 + Detectron2 | UI 요소 분리 |
| 인페인팅 | OpenCV (MVP) → LaMa (고급) | 배경 복원 |
| PSD 생성 | psd-tools + 커스텀 빌더 | 레이어 파일 생성 |

### 2.5 인프라
- Docker + Docker Compose
- GitHub Actions (CI/CD)
- GPU 서버 (추론용)
- CDN, Sentry, Prometheus/Grafana

---

## 3. 데이터베이스 스키마

### 3.1 핵심 테이블

```
users          → id, email, password, plan_type, created_at
projects       → id, user_id(FK), image_url, status, created_at
layers         → id, project_id(FK), type, position(json), image_url, text_content, z_index
jobs           → id, project_id, status, started_at, finished_at
billing        → id, user_id, plan, usage_count, reset_date
```

### 3.2 Job 상태 흐름

```
uploaded → queued → preprocessing → analyzing → segmenting
    → inpainting → composing → exporting → completed
                                            ↘ failed
```

---

## 4. API 엔드포인트

### 4.1 공개 API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/upload` | 이미지 업로드 → project_id 반환 |
| GET | `/api/project/{id}` | 처리 상태 조회 (status, progress) |
| GET | `/api/project/{id}/result` | 결과 조회 (psd_url, layers) |
| GET | `/api/download/{id}` | PSD 파일 다운로드 |
| GET | `/api/usage` | 잔여 사용량 조회 |

### 4.2 내부 엔진 API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/internal/preprocess` | 전처리 |
| POST | `/internal/detect-layout` | 레이아웃 감지 |
| POST | `/internal/run-ocr` | OCR 실행 |
| POST | `/internal/segment` | 세그멘테이션 |
| POST | `/internal/inpaint` | 인페인팅 |
| POST | `/internal/build-psd` | PSD 생성 |

---

## 5. AI 파이프라인 상세

### 5.1 처리 흐름

```
[업로드] → [전처리] → [UI 레이아웃 감지] → [텍스트/아이콘/버튼/카드 분리]
    → [OCR + 스타일 추정] → [제거 후 배경 인페인팅]
    → [레이어 후처리/그룹핑] → [PSD 빌더] → [미리보기 + 다운로드]
```

### 5.2 엔진 모듈

| 모듈 | 기능 |
|------|------|
| **A. Preprocess** | 해상도 정규화, 노이즈 제거, 샤프닝, 디바이스 프레임 제거 |
| **B. Layout** | 영역 분리, 컴포넌트 경계 탐지, Z-order 추정, 반복 패턴 감지 |
| **C. OCR** | 텍스트 박스 감지, 추출, 폰트 속성 근사 |
| **D. Segmentation** | 버튼/카드/이미지/아이콘/배경 분리, 마스크 생성 |
| **E. Inpainting** | 텍스트 제거 마스크 생성, 배경 보정, 복원 품질 점수 |
| **F. Layer Composer** | 요소별 PNG 생성, 좌표 기록, 그룹 구조, manifest |
| **G. PSD Builder** | 캔버스 생성, 레이어/그룹 삽입, 텍스트/raster 분기 |

---

## 6. 사용자 플로우

### 6.1 기본 플로우
1. 사용자 로그인
2. PNG/JPG/WebP 업로드 (Drag & Drop / 클립보드 / URL)
3. 시스템 전처리
4. UI 레이아웃 분석 (10~30초)
5. 요소 탐지 및 분리
6. 텍스트 OCR + 영역 제거 + 인페인팅
7. 레이어 구성 + PSD 생성
8. 미리보기 제공
9. PSD 다운로드

### 6.2 프로 플로우
1. 여러 화면 한 번에 업로드
2. 반복 컴포넌트 자동 감지
3. 공통 스타일 추출
4. PSD + 에셋 ZIP + JSON 메타데이터 동시 출력

---

## 7. 핵심 기능 매트릭스

### 7.1 입력
- PNG / JPG / JPEG / WebP 업로드
- Drag & Drop, 클립보드, URL 가져오기
- 다중 이미지 업로드 (프로)
- 해상도 제한/보정

### 7.2 분석
- UI 여부 판별, 디바이스 분류
- 상단바/하단탭/카드/리스트/폼/모달 감지
- 시각적 계층 구조 분석

### 7.3 분리
- 텍스트/아이콘/일러스트/배경색/버튼/카드/입력창 분리
- 섹션별 레이어 그룹화, 반투명 오버레이 분리

### 7.4 텍스트 처리
- OCR 추출 (블록/라인 단위)
- 폰트 크기/굵기/정렬/색상/line-height 추정
- 추출 실패 시 raster fallback

### 7.5 배경 복원
- 텍스트/아이콘 제거 후 인페인팅
- 패턴/그라디언트 배경 보정
- 복원 confidence 표기

### 7.6 PSD 생성
- 레이어 + 그룹 구조 (Header/Hero/Card/CTA/Footer)
- 원본 캔버스 크기 유지
- 텍스트 레이어 or raster fallback
- mask/opacity/blend 정보

### 7.7 결과물
- PSD / 에셋 ZIP / JSON 메타데이터 / 미리보기 다운로드
- 처리 이력 저장

### 7.8 편집 보정
- 자동 탐지 영역 수동 수정
- 텍스트/배경 레이어 병합/분리
- PSD 생성 전 검토 화면

---

## 8. 수익 모델

### 8.1 요금제

| 항목 | 무료 | 일반 ($39/mo) | 프로 ($129/mo) |
|------|:----:|:-----:|:-----:|
| 월 처리 횟수 | 3회 | 100회 | 500회 |
| 최대 해상도 | 1024px 제한 | HD | 4K |
| 기본 OCR | O | O | O |
| 고급 OCR 앙상블 | X | 부분 | O |
| PSD 그룹 구조 | 기본 | 고급 | 고급 |
| PNG ZIP | X | O | O |
| JSON 메타데이터 | X | X | O |
| 고급 인페인팅 | X | 부분 | O |
| 배치 처리 | X | 제한 | O |
| 수동 보정 UI | X | 기본 | 고급 |
| API access | X | X | 제한형 |
| 우선 처리 | X | O | 최고 |

### 8.2 추가 크레딧
- 20회 추가: $12
- 100회 추가: $39
- 고급 인페인팅 팩: $19

### 8.3 연간 결제
- 일반: $390/yr (2개월 할인)
- 프로: $1,290/yr (2개월 할인)

---

## 9. 핵심 기술 난제

| 난제 | 설명 | 대응 |
|------|------|------|
| UI 화면 이해 | 일반 객체탐지로 부족, UI 특화 후처리 필요 | SAM2 + UI 규칙엔진 조합 |
| 배경 복원 | 이미지/그라디언트 배경은 난이도 높음 | 무료: OpenCV, 프로: LaMa/Diffusion |
| PSD 품질 | 정리된 레이어명, 그룹, 편집 가능 텍스트 필요 | psd-tools + 커스텀 빌더 |
| AI 이미지 비정형성 | 비일관적 모서리/폰트/그림자 | 자동 + 수동 보정 UX |

---

## 10. 품질 평가 기준

### 10.1 자동 지표
- OCR 문자 정확도
- 레이어 수 분리 정확도
- 마스크 IoU
- 인페인팅 품질 점수
- PSD 열림 성공률
- 평균 처리 시간

### 10.2 서비스 KPI
- 업로드 → 다운로드 전환율
- 무료 → 유료 전환율 (목표: 5%+)
- 변환 성공률 (목표: 90%)
- 평균 처리시간 (목표: 20초 이하)
- 재방문율, 환불률

---

## 11. 리스크 및 대응

### 11.1 기술 리스크
| 리스크 | 대응 |
|--------|------|
| PSD 완성도 기대 이하 | "실무용 초안 생성기" 포지셔닝 |
| OCR/세그멘테이션 품질 편차 | 복수 엔진 앙상블 + confidence 표시 |
| 고급 인페인팅 비용 | 무료/일반은 빠른 엔진, 프로만 고급 |

### 11.2 사업 리스크
| 리스크 | 대응 |
|--------|------|
| "완벽 복원" 기대 | 결과 미리보기 후 다운로드 UX |
| 낮은 가격 → 비용 구조 붕괴 | 전략 B (일반 $39, 프로 $129) |
| 과도한 자동화 약속 → CS 폭증 | 품질 점수 + 수동 보정 기능 |

---

## 12. 핵심 화면 구성

1. **랜딩페이지** - 서비스 소개, Before/After 비교
2. **업로드 페이지** - Drag & Drop, 클립보드, URL
3. **처리 대기 페이지** - 단계별 진행률, 예상 시간
4. **결과 미리보기** - 원본 vs 분리 결과, 레이어 목록
5. **가격 페이지** - 플랜 비교표
6. **마이페이지** - 작업 이력, 재다운로드
7. **관리자 페이지** - 모니터링, 사용자 관리

---

## 13. 타겟 시장 우선순위

1. AI 생성 UI를 사용하는 개발자
2. 외주 디자이너
3. 스타트업 프로토타이핑 팀
4. 마케팅 크리에이티브 팀

---

## 14. 장기 비전

단순 PSD 복원기를 넘어:
- Figma export
- HTML/CSS 초안 생성
- React/Vue 컴포넌트 스켈레톤
- 디자인 토큰 추출
- UI 컴포넌트 라이브러리 자동 생성
