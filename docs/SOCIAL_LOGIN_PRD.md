# 소셜 로그인 기획서 (PRD)

> 작성일: 2026-03-31
> 버전: v1.0

---

## 1. 개요

### 1.1 목적
기존 이메일/비밀번호 로그인 외에 **Google**, **카카오** 소셜 로그인을 추가하여 가입/로그인 전환율을 높인다.

### 1.2 로그인 옵션 (3가지)
| 순서 | 옵션 | 프로바이더 | 프로토콜 |
|:---:|------|-----------|---------|
| 1 | Google로 계속하기 | Google OAuth 2.0 | OpenID Connect |
| 2 | 카카오로 계속하기 | Kakao OAuth 2.0 | OAuth 2.0 + REST API |
| 3 | 이메일로 계속하기 | 자체 (기존) | 이메일 + 비밀번호 |

---

## 2. 현재 상태 분석

### 2.1 기존 인증 구조
- **백엔드**: FastAPI + JWT (python-jose) + bcrypt
- **프론트**: Next.js + localStorage 토큰 저장
- **DB**: `users` 테이블 — email, password, plan_type
- **엔드포인트**: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

### 2.2 변경이 필요한 파일
| 계층 | 파일 | 변경 내용 |
|------|------|----------|
| DB | `models.py` | User에 `auth_provider`, `provider_id` 컬럼 추가 |
| Backend | `auth.py` | OAuth 토큰 검증 함수 추가 |
| Backend | `routers/auth.py` | `/auth/google/callback`, `/auth/kakao/callback` 추가 |
| Backend | `config.py` | Google/Kakao OAuth 환경변수 추가 |
| Frontend | `lib/auth.ts` | `loginWithGoogle()`, `loginWithKakao()` 함수 추가 |
| Frontend | `app/login/page.tsx` | 소셜 로그인 버튼 3개 UI |
| Frontend | `app/register/page.tsx` | 소셜 가입 버튼 통합 |
| Frontend | `app/auth/callback/page.tsx` | OAuth 콜백 처리 페이지 (신규) |
| Config | `.env.example` | OAuth 키 추가 |

---

## 3. OAuth 플로우

### 3.1 Google OAuth 플로우
```
[사용자] → "Google로 계속하기" 클릭
    → [프론트] Google OAuth URL로 리다이렉트
    → [Google] 로그인/동의
    → [Google] /auth/callback?code=xxx 로 리다이렉트
    → [프론트] code를 백엔드로 전송
    → [백엔드] POST /api/auth/google/callback { code }
        → Google에 code → access_token 교환
        → access_token으로 사용자 정보 조회 (email, name, picture)
        → DB에서 email 조회:
            - 있으면: 기존 유저로 로그인
            - 없으면: 새 유저 자동 생성 (password 없이)
        → JWT 발급 → 프론트에 반환
    → [프론트] 토큰 저장 → /upload 이동
```

### 3.2 카카오 OAuth 플로우
```
[사용자] → "카카오로 계속하기" 클릭
    → [프론트] Kakao OAuth URL로 리다이렉트
    → [Kakao] 로그인/동의
    → [Kakao] /auth/callback?code=xxx&provider=kakao 로 리다이렉트
    → [프론트] code를 백엔드로 전송
    → [백엔드] POST /api/auth/kakao/callback { code }
        → Kakao에 code → access_token 교환
        → access_token으로 사용자 정보 조회 (email, nickname, profile_image)
        → DB에서 email 조회:
            - 있으면: 기존 유저로 로그인
            - 없으면: 새 유저 자동 생성
        → JWT 발급 → 프론트에 반환
    → [프론트] 토큰 저장 → /upload 이동
```

### 3.3 이메일 로그인 (기존)
```
[사용자] → "이메일로 계속하기" 클릭
    → 이메일/비밀번호 폼 표시
    → 기존 로직 동일
```

---

## 4. UI 설계

### 4.1 로그인 페이지 레이아웃
```
┌─────────────────────────────┐
│         로그인               │
│                             │
│  ┌───────────────────────┐  │
│  │  G  Google로 계속하기   │  │  ← 흰 배경 + 구글 로고
│  └───────────────────────┘  │
│                             │
│  ┌───────────────────────┐  │
│  │  💬 카카오로 계속하기   │  │  ← 노란 배경 (#FEE500)
│  └───────────────────────┘  │
│                             │
│  ────── 또는 ──────         │
│                             │
│  ┌───────────────────────┐  │
│  │  ✉  이메일로 계속하기   │  │  ← 회색 배경
│  └───────────────────────┘  │
│                             │
│  계정이 없으신가요? 회원가입  │
└─────────────────────────────┘
```

### 4.2 이메일 선택 시
"이메일로 계속하기" 클릭 → 이메일/비밀번호 입력 폼이 슬라이드 다운으로 표시

### 4.3 회원가입 페이지
로그인 페이지와 동일한 소셜 버튼 + 이메일 가입 폼

---

## 5. DB 스키마 변경

### 5.1 users 테이블 변경
```sql
ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'email';
ALTER TABLE users ADD COLUMN provider_id VARCHAR(255);
ALTER TABLE users ADD COLUMN name VARCHAR(100);
ALTER TABLE users ADD COLUMN profile_image TEXT;
ALTER TABLE users ALTER COLUMN password DROP NOT NULL;
```

### 5.2 auth_provider 값
| 값 | 설명 |
|----|------|
| `email` | 이메일/비밀번호 가입 (기존) |
| `google` | Google OAuth 가입 |
| `kakao` | 카카오 OAuth 가입 |

---

## 6. 환경변수

```env
# Google OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback?provider=google

# Kakao OAuth
KAKAO_CLIENT_ID=xxx
KAKAO_CLIENT_SECRET=xxx
KAKAO_REDIRECT_URI=http://localhost:3000/auth/callback?provider=kakao
```

---

## 7. 보안 고려사항

| 항목 | 대응 |
|------|------|
| CSRF | OAuth state 파라미터로 방어 |
| 토큰 노출 | 백엔드에서만 provider token 처리, 프론트에는 JWT만 전달 |
| 이메일 중복 | 같은 이메일로 소셜+이메일 가입 시 기존 계정에 연결 |
| 계정 연결 | 소셜 로그인 시 기존 이메일 계정이 있으면 자동 연결 (password 유지) |

---

## 8. 에지 케이스

| 시나리오 | 동작 |
|----------|------|
| 이메일 가입 후 Google로 같은 이메일 로그인 | 기존 계정에 google provider 연결, 로그인 성공 |
| Google 가입 후 이메일 로그인 시도 | 비밀번호 없으므로 "소셜 로그인으로 가입된 계정입니다" 안내 |
| 카카오에 이메일 동의 거부 | 에러 표시: "이메일 동의가 필요합니다" |
| 소셜 로그인 취소 | 로그인 페이지로 돌아감 |
