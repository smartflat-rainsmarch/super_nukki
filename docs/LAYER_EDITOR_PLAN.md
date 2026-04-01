# 레이어 편집기 구현 계획서

> 작성일: 2026-04-01
> 상태: 계획 확정 대기

---

## 1. 현재 문제

| 문제 | 원인 |
|------|------|
| 캔버스 미리보기가 빈 상태 | 레이어 PNG 파일을 서빙하는 라우트 없음 |
| 레이어 목록이 비어있음 | 파이프라인이 Layer DB 레코드를 생성하지 않음 |
| 편집 기능 미동작 | placeholder DOM만 존재, 실제 이미지 미렌더링 |

---

## 2. 데이터 흐름 (현재 vs 수정 후)

### 현재 (끊어진 상태)
```
파이프라인 → manifest.json + PNG 파일 생성
                    ↓
              DB Layer 테이블 = 비어있음 ❌
                    ↓
          API /project/{id}/result → layers: [] (빈 배열)
                    ↓
          편집 페이지 → 아무것도 표시 안 됨
```

### 수정 후
```
파이프라인 → manifest.json + PNG 파일 생성
                    ↓
          manifest.json 파싱 → DB Layer 테이블에 삽입 ✅
                    ↓
          StaticFiles 마운트 → /storage/outputs/.../layers/*.png 서빙 ✅
                    ↓
          API /project/{id}/result → layers: [{image_url, position, ...}]
                    ↓
          편집 페이지 → 캔버스에 레이어 PNG 렌더링 ✅
```

---

## 3. 구현 단계

### Step 1: 레이어 이미지 HTTP 서빙
**파일**: `apps/api/main.py`
```
- FastAPI StaticFiles 마운트: /storage → settings.storage_path
- 이후 /storage/outputs/{project_id}/layers/background.png 등 직접 접근 가능
```

### Step 2: 파이프라인 결과 → Layer DB 삽입
**파일**: `apps/api/routers/upload.py` (`_run_pipeline_sync` 함수)
```
파이프라인 완료 후:
1. storage/outputs/{project_id}/layers/manifest.json 읽기
2. manifest의 canvas_size, layers 정보 추출
3. 각 레이어를 models.Layer 테이블에 INSERT:
   - type: manifest의 type
   - position: {"x", "y", "w", "h"} JSON
   - image_url: /storage/outputs/{project_id}/layers/{filename}
   - text_content: manifest의 text_content
   - z_index: manifest의 z_index
```

### Step 3: Result API 확장
**파일**: `apps/api/routers/project.py`
```
GET /api/project/{id}/result 응답에 추가:
- canvas_size: {width, height} (manifest.json에서)
- layers[].image_url: 레이어 PNG HTTP URL
```

### Step 4: 캔버스 미리보기 UI
**파일**: `apps/web/src/app/project/[id]/edit/page.tsx`

```
┌─────────────────────────────────────────────────────┐
│  레이어 편집                    [PSD 재생성] [완료]  │
├──────────────────────────────┬──────────────────────┤
│                              │ 레이어 목록           │
│   ┌──────────────────────┐   │                      │
│   │                      │   │ 👁 background  [bg]  │
│   │  캔버스 미리보기      │   │ 👁 card_0     [card] │
│   │  (레이어 PNG 겹침)    │   │ 👁 text_0     [text] │
│   │                      │   │ 👁 button_0   [btn]  │
│   │  클릭 → 선택(파란)    │   │                      │
│   │                      │   │ ──────────────────── │
│   └──────────────────────┘   │ 위치 조정 (선택 시)   │
│                              │ X [  ] Y [  ]        │
│                              │ W [  ] H [  ]        │
│                              │ [적용]                │
└──────────────────────────────┴──────────────────────┘
```

#### 캔버스 구현 방식
- HTML div + absolute position (Konva.js 불필요)
- 컨테이너: `position: relative`, canvas_size 비율 유지 (fit to viewport)
- 각 레이어: `<img src={image_url}>`, `position: absolute`, `left/top/width/height` 비율 계산
- `visible: false` → `opacity: 0` + `pointer-events: none`
- 선택된 레이어 → `outline: 2px solid blue`

#### 레이어 목록 기능
- z_index 역순 (위 레이어가 목록 상단)
- 각 항목: 👁 토글 | 레이어 이름 | 타입 배지 | z_index
- 클릭 → 캔버스에서 하이라이트
- editable 레이어: 텍스트 인라인 편집 가능

### Step 5: 테스트
**파일**: `apps/api/tests/test_layer_edit.py` (신규)
```
- 업로드 후 Layer DB 레코드 존재 확인
- /project/{id}/result에 layers 배열 비어있지 않은지 확인
- canvas_size 포함 확인
- layer image_url 접근 가능 확인
```

---

## 4. 변경 파일 목록

| # | 파일 | 변경 유형 |
|---|------|----------|
| 1 | `apps/api/main.py` | 수정 - StaticFiles 마운트 추가 |
| 2 | `apps/api/routers/upload.py` | 수정 - manifest → Layer DB 삽입 |
| 3 | `apps/api/routers/project.py` | 수정 - canvas_size + image_url 추가 |
| 4 | `apps/web/src/app/project/[id]/edit/page.tsx` | 수정 - 캔버스 미리보기 전체 재구현 |
| 5 | `apps/api/tests/test_layer_edit.py` | 신규 |

---

## 5. 의존성

```
Step 1 (StaticFiles) ──→ Step 4 (캔버스에서 이미지 로드)
Step 2 (Layer DB)    ──→ Step 3 (API 응답) ──→ Step 4 (캔버스)
Step 1~4 완료        ──→ Step 5 (테스트)
```

---

## 6. 검증 체크리스트

- [ ] 이미지 업로드 → "변환 완료" 도달
- [ ] "레이어 편집" 클릭 → 편집 페이지 로드
- [ ] 캔버스에 원본과 유사한 미리보기 표시
- [ ] 레이어 목록에 5개 이상 레이어 표시
- [ ] 👁 토글 클릭 → 캔버스에서 레이어 숨김/표시
- [ ] 레이어 클릭 → 캔버스에 파란 테두리 하이라이트
- [ ] 전체 테스트 통과
