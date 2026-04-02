# Figma 연동 기획서 (PRD)

> 작성일: 2026-04-02
> 버전: v1.0

---

## 1. 개요

### 1.1 목적
UI2PSD Studio에서 변환한 결과물을 **Figma에서 바로 열어볼 수 있는** 연동 기능을 추가한다. PSD 다운로드 외에 "Figma로 보내기" 옵션을 제공하여, 디자이너가 Figma 워크스페이스에서 바로 편집할 수 있게 한다.

### 1.2 핵심 가치
| 대상 | 가치 |
|------|------|
| 디자이너 | PSD 다운로드 없이 Figma에서 바로 레이어 확인 |
| 프론트엔드 개발자 | Figma inspect으로 CSS 값 바로 추출 |
| 팀 협업 | Figma 링크 공유로 실시간 리뷰 가능 |

---

## 2. 사용자 플로우

### 2.1 기본 플로우
```
[1] 이미지 업로드 → PSD 변환 완료
    ↓
[2] 결과 페이지에서 "Figma로 보내기" 버튼 클릭
    ↓
[3] Figma OAuth 인증 (최초 1회)
    ↓
[4] Figma 팀/프로젝트 선택 (또는 새 파일 생성)
    ↓
[5] 레이어 데이터가 Figma 파일로 생성됨
    ↓
[6] "Figma에서 열기" 링크 제공 → Figma 앱에서 편집
```

### 2.2 재연동 플로우
```
- 이미 Figma 인증된 사용자 → [2]에서 바로 [4]로
- 이전에 보낸 프로젝트 재전송 → 기존 Figma 파일 업데이트 또는 새 파일 생성 선택
```

---

## 3. 연동 방식 비교

### 3.1 방식 A: Figma REST API (권장)

| 항목 | 내용 |
|------|------|
| 방식 | 서버에서 Figma REST API로 파일 생성 |
| 인증 | OAuth 2.0 (Figma Personal Access Token 또는 OAuth App) |
| 장점 | 서버 사이드 처리, 사용자 행동 불필요, 자동화 가능 |
| 단점 | REST API로는 파일 **읽기**만 가능, **쓰기(생성)**는 Plugin API 필요 |
| 결론 | **읽기 + 메타데이터만 가능, 파일 생성 불가** |

### 3.2 방식 B: Figma Plugin (권장 — 실제 파일 생성 가능)

| 항목 | 내용 |
|------|------|
| 방식 | Figma Plugin을 제작하여 Figma 앱 내에서 import |
| 인증 | Plugin 내에서 UI2PSD API 호출 (API Key 사용) |
| 장점 | 완전한 Figma 파일 생성/편집 가능, 프레임/텍스트/이미지 모두 지원 |
| 단점 | 사용자가 Figma Plugin 설치 필요, Figma 앱에서만 동작 |
| 결론 | **파일 생성이 가능한 유일한 방식** |

### 3.3 방식 C: 하이브리드 (최종 권장)

```
[UI2PSD 웹] → "Figma로 보내기" 클릭
    → Figma Plugin 설치 안내 (최초 1회)
    → Figma 앱에서 Plugin 실행
    → Plugin이 UI2PSD API에서 레이어 데이터 fetch
    → Figma Canvas에 프레임/레이어/텍스트 자동 생성
```

| 단계 | 위치 | 역할 |
|------|------|------|
| 1. 데이터 준비 | UI2PSD 서버 | Figma 호환 JSON 생성 (기존 figma.py) |
| 2. 공유 링크 생성 | UI2PSD 서버 | `/api/export/{id}/figma` → 임시 공유 URL |
| 3. 데이터 import | Figma Plugin | 공유 URL에서 JSON fetch → Canvas에 렌더링 |

---

## 4. Figma Plugin 기능 명세

### 4.1 Plugin UI
```
┌─────────────────────────────────┐
│  UI2PSD → Figma Import          │
│                                 │
│  Project URL 또는 Share Code:   │
│  ┌───────────────────────────┐  │
│  │ https://ui2psd.com/s/abc  │  │
│  └───────────────────────────┘  │
│                                 │
│  [Import to Figma]              │
│                                 │
│  ─── 또는 ───                   │
│                                 │
│  API Key:                       │
│  ┌───────────────────────────┐  │
│  │ ui2psd_xxxxx              │  │
│  └───────────────────────────┘  │
│  [내 프로젝트 목록 불러오기]     │
└─────────────────────────────────┘
```

### 4.2 Import 동작
| Figma 요소 | UI2PSD 소스 |
|------------|-------------|
| Frame | canvas_size 기반 메인 프레임 |
| Group | 레이어 그룹 (Header, Body, CTA 등) |
| Rectangle + Image Fill | 래스터 레이어 (버튼, 카드, 아이콘, 배경) |
| Text | 텍스트 레이어 (OCR 추출 텍스트, 폰트 크기/색상) |
| Frame Position | 각 레이어의 x, y, w, h 좌표 |

### 4.3 Plugin 기술 스택
| 기술 | 용도 |
|------|------|
| TypeScript | Plugin 코드 |
| Figma Plugin API | Canvas 조작 (createFrame, createText, createRectangle) |
| fetch API | UI2PSD 서버에서 레이어 데이터 가져오기 |

---

## 5. 백엔드 API 추가

### 5.1 공유 링크 생성
```
POST /api/export/{project_id}/figma-share
→ { "share_url": "https://api.ui2psd.com/s/{share_code}", "expires_in": 3600 }
```
- 1시간 유효 임시 링크
- 인증 없이 접근 가능 (Plugin에서 호출)

### 5.2 공유 데이터 조회 (Plugin에서 호출)
```
GET /api/share/{share_code}
→ { "canvas_size": {...}, "layers": [...], "images": {...} }
```
- 레이어 JSON + 이미지 URL 포함
- Plugin이 이미지를 fetch하여 Figma에 삽입

---

## 6. UI 변경사항

### 6.1 결과 페이지
```
[PSD로 받기]  [Figma로 보내기]  [레이어 편집]
```

### 6.2 "Figma로 보내기" 클릭 시
```
┌─────────────────────────────────────┐
│  Figma로 보내기                      │
│                                     │
│  1. Figma에서 UI2PSD Plugin 설치     │
│     [Plugin 설치하기 →]              │
│                                     │
│  2. Plugin에서 아래 코드 입력:       │
│     ┌─────────────────────────┐     │
│     │  ABC-DEF-123  📋 복사   │     │
│     └─────────────────────────┘     │
│                                     │
│  또는 링크 복사:                     │
│  [링크 복사] [QR 코드]              │
└─────────────────────────────────────┘
```

---

## 7. 요금제별 제한

| 기능 | 무료 | 일반 ($39) | 프로 ($129) |
|------|:----:|:-----:|:-----:|
| Figma Export JSON 다운로드 | X | O | O |
| Figma 공유 링크 생성 | X | O | O |
| Figma Plugin Import | X | O | O |
| API Key로 자동 연동 | X | X | O |

---

## 8. 보안 고려사항

| 항목 | 대응 |
|------|------|
| 공유 링크 노출 | 1시간 만료, 1회 사용 후 폐기 옵션 |
| 이미지 URL 보호 | 임시 서명 URL (signed URL) 사용 |
| Plugin 인증 | API Key 또는 Share Code 기반 |
| CORS | Plugin origin 허용 (`https://www.figma.com`) |

---

## 9. 에지 케이스

| 상황 | 동작 |
|------|------|
| 레이어 50개 이상 | 그룹별 배치 처리, 진행률 표시 |
| 이미지 용량 큰 경우 | 자동 리사이즈 (Figma 제한: 4096px) |
| 텍스트 폰트 없음 | Inter 폰트 fallback |
| Plugin 미설치 | 설치 가이드 + Figma Community 링크 |
| 공유 링크 만료 | "링크가 만료되었습니다. 다시 생성하세요" |
