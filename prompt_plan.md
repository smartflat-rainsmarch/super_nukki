# 현재 계획: 소셜 로그인 구현

> 기획서: [docs/SOCIAL_LOGIN_PRD.md](docs/SOCIAL_LOGIN_PRD.md)
> 계획서: [docs/SOCIAL_LOGIN_PLAN.md](docs/SOCIAL_LOGIN_PLAN.md)
> 상태: 계획 확정 대기

## 요약

로그인 옵션 3개 구현:
1. Google로 계속하기 (OAuth 2.0 / OIDC)
2. 카카오로 계속하기 (OAuth 2.0)
3. 이메일로 계속하기 (기존)

## 구현 순서

- Phase A: DB + 백엔드 기반 (모델 확장, OAuth 유틸, 라우터)
- Phase B: 기존 로그인 로직 보강 (소셜 계정 체크, 응답 확장)
- Phase C: 프론트엔드 UI (소셜 버튼, 콜백 페이지)
- Phase D: 테스트 + 검증

## 변경 파일: 12개

상세: [docs/SOCIAL_LOGIN_PLAN.md](docs/SOCIAL_LOGIN_PLAN.md) 참조
