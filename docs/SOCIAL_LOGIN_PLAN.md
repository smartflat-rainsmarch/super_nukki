# 소셜 로그인 구현 계획서

> 작성일: 2026-03-31
> 기획서: [SOCIAL_LOGIN_PRD.md](./SOCIAL_LOGIN_PRD.md)
> 예상 변경 파일: 12개

---

## 구현 순서

```
Phase A: DB + 백엔드 기반
    ↓
Phase B: OAuth 프로바이더 연동
    ↓
Phase C: 프론트엔드 UI
    ↓
Phase D: 테스트 + 검증
```

---

## Phase A: DB + 백엔드 기반 (의존성 없음)

### A-1. User 모델 확장
**파일**: `apps/api/models.py`
```
변경 내용:
- auth_provider 컬럼 추가 (VARCHAR(20), default='email')
- provider_id 컬럼 추가 (VARCHAR(255), nullable)
- name 컬럼 추가 (VARCHAR(100), nullable)
- profile_image 컬럼 추가 (TEXT, nullable)
- password 컬럼을 nullable로 변경 (소셜 로그인은 password 불필요)
```

### A-2. 환경변수 설정
**파일**: `apps/api/config.py`, `.env.example`
```
변경 내용:
- google_client_id, google_client_secret, google_redirect_uri
- kakao_client_id, kakao_client_secret, kakao_redirect_uri
- Settings 클래스에 필드 추가
```

### A-3. OAuth 유틸리티
**파일**: `apps/api/oauth.py` (신규)
```
구현 내용:
- get_google_auth_url(state) → Google 인증 URL 생성
- get_kakao_auth_url(state) → Kakao 인증 URL 생성
- exchange_google_code(code) → Google에 code 교환 → 사용자 정보 반환
- exchange_kakao_code(code) → Kakao에 code 교환 → 사용자 정보 반환
- OAuthUserInfo dataclass: email, name, profile_image, provider, provider_id
```

### A-4. Auth 라우터 확장
**파일**: `apps/api/routers/auth.py`
```
새 엔드포인트:
- GET  /api/auth/google/url      → Google 인증 URL 반환
- POST /api/auth/google/callback → code로 로그인/가입 처리
- GET  /api/auth/kakao/url       → Kakao 인증 URL 반환
- POST /api/auth/kakao/callback  → code로 로그인/가입 처리

공통 로직 (find_or_create_oauth_user):
1. email로 기존 유저 조회
2. 있으면: auth_provider/provider_id 업데이트 → JWT 반환
3. 없으면: 새 User 생성 (password=None) → Billing 생성 → JWT 반환
```

---

## Phase B: 기존 로그인 로직 보강

### B-1. 이메일 로그인 시 소셜 계정 체크
**파일**: `apps/api/routers/auth.py`
```
변경 내용:
- login() 에서 user.auth_provider != 'email'이고 password가 없으면:
  → "Google/카카오로 가입된 계정입니다" 에러 반환
- register() 에서 기존 소셜 유저가 있으면:
  → 409 에러에 provider 정보 포함
```

### B-2. AuthResponse 확장
**파일**: `apps/api/routers/auth.py`, `apps/api/schemas.py`
```
변경 내용:
- AuthResponse에 name, profile_image 필드 추가
- UserResponse에 auth_provider, name, profile_image 추가
```

---

## Phase C: 프론트엔드 UI

### C-1. auth.ts OAuth 함수
**파일**: `apps/web/src/lib/auth.ts`
```
새 함수:
- getGoogleLoginUrl() → API에서 Google 인증 URL 가져오기
- getKakaoLoginUrl() → API에서 Kakao 인증 URL 가져오기
- handleOAuthCallback(code, provider) → 백엔드에 code 전달 → 토큰 저장
```

### C-2. 로그인 페이지 리디자인
**파일**: `apps/web/src/app/login/page.tsx`
```
변경 내용:
- 기존 이메일 폼 → 3버튼 + 이메일 폼 확장형으로 변경
- Google 버튼: 흰 배경, 구글 로고, 테두리
- 카카오 버튼: #FEE500 배경, 카카오 로고
- 이메일 버튼: 회색, 클릭 시 폼 확장
- "또는" 구분선
```

### C-3. 회원가입 페이지 통합
**파일**: `apps/web/src/app/register/page.tsx`
```
변경 내용:
- 로그인과 동일한 소셜 버튼 상단 배치
- 이메일 가입 폼은 "이메일로 계속하기" 클릭 시 표시
```

### C-4. OAuth 콜백 페이지
**파일**: `apps/web/src/app/auth/callback/page.tsx` (신규)
```
구현 내용:
- URL에서 code, provider 파라미터 추출
- 백엔드 /api/auth/{provider}/callback 호출
- 성공: 토큰 저장 → /upload 이동
- 실패: 에러 표시 → /login 이동
```

---

## Phase D: 테스트

### D-1. 백엔드 테스트
**파일**: `apps/api/tests/test_social_auth.py` (신규)
```
테스트 케이스:
- Google OAuth URL 생성 확인
- Kakao OAuth URL 생성 확인
- Google callback으로 신규 유저 생성
- Google callback으로 기존 유저 로그인
- 소셜 유저의 이메일 로그인 차단
- 이메일 유저의 소셜 로그인 시 계정 연결
- 카카오 이메일 미동의 에러 처리
```

### D-2. 기존 테스트 수정
**파일**: `apps/api/tests/test_auth.py`
```
변경 내용:
- User 모델 변경에 따른 기존 테스트 호환성 확인
- password nullable 변경 후에도 이메일 가입/로그인 정상 동작 확인
```

---

## 변경 파일 목록 (총 12개)

| # | 파일 | 작업 |
|---|------|------|
| 1 | `apps/api/models.py` | User 모델 컬럼 추가 |
| 2 | `apps/api/config.py` | OAuth 환경변수 추가 |
| 3 | `apps/api/oauth.py` | **신규** - OAuth 유틸리티 |
| 4 | `apps/api/routers/auth.py` | OAuth 콜백 엔드포인트 추가 |
| 5 | `apps/api/schemas.py` | AuthResponse 확장 |
| 6 | `apps/web/src/lib/auth.ts` | OAuth 함수 추가 |
| 7 | `apps/web/src/app/login/page.tsx` | 소셜 버튼 UI |
| 8 | `apps/web/src/app/register/page.tsx` | 소셜 버튼 통합 |
| 9 | `apps/web/src/app/auth/callback/page.tsx` | **신규** - 콜백 처리 |
| 10 | `apps/api/tests/test_social_auth.py` | **신규** - 소셜 인증 테스트 |
| 11 | `apps/api/tests/test_auth.py` | 기존 테스트 호환성 수정 |
| 12 | `.env.example` | OAuth 키 추가 |

---

## 의존성

```
A-1 (모델) ──→ A-3 (OAuth 유틸) ──→ A-4 (라우터)
A-2 (환경변수) ─┘                      ↓
                               B-1 (로그인 보강) ──→ D-1 (테스트)
                                       ↓
                               C-1 (auth.ts) ──→ C-2 (로그인 UI)
                                               ──→ C-3 (가입 UI)
                                               ──→ C-4 (콜백 페이지)
```

---

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Google/Kakao OAuth 키 미발급 | 소셜 로그인 테스트 불가 | 목업 응답으로 개발, 키 발급 후 통합 테스트 |
| 카카오 이메일 미동의 | 유저 생성 불가 | 필수 동의 항목으로 설정 + 에러 안내 |
| 기존 password NOT NULL | 소셜 유저 생성 실패 | A-1에서 nullable로 변경 |
| 기존 테스트 깨짐 | CI 실패 | D-2에서 호환성 확인 |

---

## 사전 준비 (개발 전 필요)

1. **Google Cloud Console**: OAuth 2.0 클라이언트 ID 생성
   - 승인된 리다이렉트 URI: `http://localhost:3000/auth/callback?provider=google`
2. **Kakao Developers**: 앱 생성 + REST API 키 발급
   - Redirect URI: `http://localhost:3000/auth/callback?provider=kakao`
   - 동의항목: 이메일 (필수), 프로필 (선택)
3. `.env` 파일에 키 설정
