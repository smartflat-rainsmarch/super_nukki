# 이메일 인증번호 회원가입 작업순서

> 기획서: [EMAIL_VERIFICATION_PRD.md](./EMAIL_VERIFICATION_PRD.md)

## 작업 순서

```
Step 1: DB 모델 + Config
    ↓
Step 2: 이메일 발송 모듈
    ↓
Step 3: API 엔드포인트 (send-code, verify-code, register 수정)
    ↓
Step 4: 프론트 3단계 UI
    ↓
Step 5: 번역 키 + 테스트
```

## Step 1: DB 모델 + Config
- `models.py`: EmailVerification 테이블 추가
- `config.py`: SMTP 환경변수 4개 추가
- `.env.example`: SMTP 설정 추가

## Step 2: 이메일 발송 모듈
- `email_sender.py` 신규 생성
- SMTP 설정 시 → Gmail SMTP로 발송
- SMTP 미설정 시 → 콘솔 출력 + API 응답에 dev_code 포함

## Step 3: API 엔드포인트
- `POST /api/auth/send-code`: 6자리 생성, DB 저장, 이메일 발송
- `POST /api/auth/verify-code`: 코드 검증, verified_token(JWT) 반환
- `POST /api/auth/register` 수정: verified_token 필수 파라미터 추가

## Step 4: 프론트 3단계 UI
- register/page.tsx 리팩토링: step 상태 관리
- Step 1: 이메일 → 인증번호 받기
- Step 2: 6자리 입력 → 확인
- Step 3: 비밀번호 → 가입

## Step 5: 번역 키 + 테스트
- ko.json, en.json에 verify 관련 키 추가
- 테스트: send-code, verify-code, register with token

## 변경 파일 (10개)

| # | 파일 | 유형 |
|---|------|------|
| 1 | `apps/api/models.py` | 수정 |
| 2 | `apps/api/config.py` | 수정 |
| 3 | `apps/api/email_sender.py` | 신규 |
| 4 | `apps/api/routers/auth.py` | 수정 |
| 5 | `apps/web/src/app/register/page.tsx` | 수정 |
| 6 | `apps/web/src/lib/locales/ko.json` | 수정 |
| 7 | `apps/web/src/lib/locales/en.json` | 수정 |
| 8 | `.env.example` | 수정 |
| 9 | `docs/EMAIL_VERIFICATION_PRD.md` | 신규 |
| 10 | `docs/EMAIL_VERIFICATION_PLAN.md` | 신규 |
