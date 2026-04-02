# Figma 연동 개발 스택 및 일정 계획서

> 기획서: [FIGMA_INTEGRATION_PRD.md](./FIGMA_INTEGRATION_PRD.md)
> 작성일: 2026-04-02

---

## 1. 개발 스택

### 1.1 백엔드 (UI2PSD 서버)

| 기술 | 버전 | 용도 |
|------|------|------|
| FastAPI | 0.115+ | 공유 링크 API, Figma 데이터 API |
| SQLAlchemy | 2.0+ | FigmaShare 모델 (share_code, expires_at) |
| Python secrets | stdlib | 공유 코드 생성 (url-safe) |
| Pillow | 11.1+ | 이미지 리사이즈 (Figma 4096px 제한 대응) |

### 1.2 Figma Plugin

| 기술 | 버전 | 용도 |
|------|------|------|
| TypeScript | 5.x | Plugin 코드 |
| Figma Plugin API | 1.0 | Canvas 조작 (프레임, 텍스트, 이미지 생성) |
| esbuild / webpack | 최신 | Plugin 번들링 |
| Figma Plugin Typings | `@figma/plugin-typings` | 타입 정의 |

### 1.3 프론트엔드 (UI2PSD 웹)

| 기술 | 버전 | 용도 |
|------|------|------|
| Next.js | 15.x | "Figma로 보내기" UI, 공유 코드 표시 |
| React | 19.x | 모달 컴포넌트 |

### 1.4 인프라

| 기술 | 용도 |
|------|------|
| Figma Community | Plugin 배포 (공개 또는 Organization) |
| CDN / Signed URL | 레이어 이미지 임시 접근 |

---

## 2. 개발 Phase 및 일정

### 총 예상 기간: 3주 (15 영업일)

```
Phase 1: 백엔드 API (3일)
    ↓
Phase 2: Figma Plugin 개발 (5일)
    ↓
Phase 3: 프론트엔드 UI (2일)
    ↓
Phase 4: 통합 테스트 + QA (3일)
    ↓
Phase 5: Plugin 배포 + 문서 (2일)
```

---

### Phase 1: 백엔드 API (3일)

| 일차 | 작업 | 산출물 |
|:----:|------|--------|
| 1일차 | FigmaShare 모델 + 마이그레이션 | `models.py` 수정 |
| 1일차 | `POST /api/export/{id}/figma-share` 엔드포인트 | `routers/export.py` 수정 |
| 2일차 | `GET /api/share/{code}` 공유 데이터 API | `routers/share.py` 신규 |
| 2일차 | 이미지 서명 URL 생성 로직 | 이미지 임시 접근 보안 |
| 3일차 | API 테스트 + 문서 | Swagger 자동 문서 |

**변경 파일:**
- `apps/api/models.py` — FigmaShare 테이블
- `apps/api/routers/export.py` — figma-share 엔드포인트
- `apps/api/routers/share.py` — 신규, 공유 데이터 API
- `apps/api/main.py` — share 라우터 등록

---

### Phase 2: Figma Plugin 개발 (5일)

| 일차 | 작업 | 산출물 |
|:----:|------|--------|
| 1일차 | Plugin 프로젝트 셋업 (TypeScript + esbuild) | `figma-plugin/` 디렉토리 |
| 1일차 | Plugin UI (HTML + CSS) — Share Code 입력 폼 | `ui.html` |
| 2일차 | API fetch → 레이어 JSON 파싱 | `code.ts` |
| 3일차 | Frame 생성 + Rectangle + Image Fill | Canvas 렌더링 |
| 4일차 | Text 레이어 생성 (폰트, 크기, 색상) | 텍스트 렌더링 |
| 5일차 | 그룹 구조 + z-index 정렬 + 에러 처리 | 완성 |

**Plugin 프로젝트 구조:**
```
figma-plugin/
├── manifest.json        # Plugin 메타데이터
├── code.ts             # Main Plugin 로직
├── ui.html             # Plugin UI
├── tsconfig.json
├── package.json
└── esbuild.config.js
```

**주요 Figma API 사용:**
```typescript
// 프레임 생성
const frame = figma.createFrame()
frame.resize(canvas.width, canvas.height)

// 이미지 삽입
const image = figma.createImage(uint8Array)
const rect = figma.createRectangle()
rect.fills = [{ type: 'IMAGE', imageHash: image.hash, scaleMode: 'FILL' }]

// 텍스트 생성
const text = figma.createText()
await figma.loadFontAsync({ family: "Inter", style: "Regular" })
text.characters = "Hello World"
text.fontSize = 16
```

---

### Phase 3: 프론트엔드 UI (2일)

| 일차 | 작업 | 산출물 |
|:----:|------|--------|
| 1일차 | "Figma로 보내기" 버튼 + 공유 코드 모달 | 결과 페이지 수정 |
| 2일차 | Plugin 설치 가이드 UI + 번역 키 | i18n 추가 |

**변경 파일:**
- `apps/web/src/app/project/[id]/page.tsx` — "Figma로 보내기" 버튼
- `apps/web/src/components/figma-share-modal.tsx` — 신규 모달
- `apps/web/src/lib/locales/ko.json` — 번역 키
- `apps/web/src/lib/locales/en.json` — 영어 번역

---

### Phase 4: 통합 테스트 + QA (3일)

| 일차 | 작업 |
|:----:|------|
| 1일차 | 백엔드 API 단위 테스트 (share 생성, 만료, 데이터 조회) |
| 2일차 | Plugin ↔ API 연동 E2E 테스트 |
| 3일차 | 다양한 레이어 유형 테스트 (텍스트, 이미지, 복잡한 그룹) |

**테스트 체크리스트:**
- [ ] 공유 링크 생성 → 1시간 후 만료 확인
- [ ] Plugin에서 Share Code 입력 → 데이터 fetch 성공
- [ ] Figma Canvas에 프레임 생성 확인
- [ ] 이미지 레이어 정상 표시
- [ ] 텍스트 레이어 폰트/크기/색상 일치
- [ ] 그룹 구조 (Header, Body 등) 정상 반영
- [ ] 50개 이상 레이어 성능 테스트
- [ ] 4096px 초과 이미지 자동 리사이즈

---

### Phase 5: Plugin 배포 + 문서 (2일)

| 일차 | 작업 |
|:----:|------|
| 1일차 | Figma Community에 Plugin 배포 (또는 Organization 배포) |
| 2일차 | 사용자 가이드 작성 + 랜딩페이지에 Figma 연동 소개 추가 |

---

## 3. 의존성

```
Phase 1 (백엔드) ──→ Phase 2 (Plugin: API 호출)
                ──→ Phase 3 (프론트: 공유 코드 UI)
Phase 2 + 3 완료 ──→ Phase 4 (통합 테스트)
Phase 4 완료     ──→ Phase 5 (배포)
```

---

## 4. 리스크

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|:----:|------|
| Figma Plugin API 제한 | 일부 레이어 속성 미지원 | 중 | 지원 가능한 속성만 처리, 나머지는 래스터 이미지 |
| 폰트 로딩 실패 | 텍스트 렌더링 불가 | 중 | Inter 폰트 fallback 사용 |
| 이미지 용량 | Plugin 메모리 초과 | 낮 | 이미지 리사이즈 + 배치 로딩 |
| Figma Community 심사 | 배포 지연 | 낮 | Organization 배포로 우회 가능 |
| CORS 차단 | Plugin에서 API 호출 실패 | 중 | `figma.com` origin CORS 허용 |

---

## 5. 예상 변경 파일 요약

### 백엔드 (4개)
| 파일 | 작업 |
|------|------|
| `apps/api/models.py` | FigmaShare 모델 추가 |
| `apps/api/routers/export.py` | figma-share 엔드포인트 추가 |
| `apps/api/routers/share.py` | 신규 — 공유 데이터 API |
| `apps/api/main.py` | share 라우터 등록 |

### Figma Plugin (5개, 신규 디렉토리)
| 파일 | 작업 |
|------|------|
| `figma-plugin/manifest.json` | Plugin 메타데이터 |
| `figma-plugin/code.ts` | Plugin 메인 로직 |
| `figma-plugin/ui.html` | Plugin UI |
| `figma-plugin/package.json` | 의존성 |
| `figma-plugin/tsconfig.json` | TypeScript 설정 |

### 프론트엔드 (4개)
| 파일 | 작업 |
|------|------|
| `apps/web/src/app/project/[id]/page.tsx` | "Figma로 보내기" 버튼 |
| `apps/web/src/components/figma-share-modal.tsx` | 신규 — 공유 모달 |
| `apps/web/src/lib/locales/ko.json` | 번역 키 추가 |
| `apps/web/src/lib/locales/en.json` | 영어 번역 |

---

## 6. 마일스톤

| 주차 | 마일스톤 | 검증 기준 |
|:----:|---------|----------|
| 1주차 | 백엔드 API + Plugin 프로토타입 | Share Code로 데이터 fetch 성공 |
| 2주차 | Plugin Canvas 렌더링 + 프론트 UI | Figma에서 레이어 확인 가능 |
| 3주차 | QA + 배포 | Plugin 배포 완료, E2E 통과 |
