# UI2PSD Studio

AI가 UI 이미지를 분석하여 편집 가능한 PSD 레이어 파일로 변환하는 SaaS.

## Quick Start (Development)

```bash
# 환경 변수 설정
cp .env.example .env

# Docker로 실행
docker compose up --build

# 접속
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Quick Start (Production)

```bash
docker compose -f docker-compose.prod.yml up --build -d
# http://localhost (nginx reverse proxy)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Celery |
| AI Engine | OpenCV, PaddleOCR, Pillow |
| Database | PostgreSQL, Redis |
| Payment | Stripe |
| Infra | Docker, Nginx |

## Testing

```bash
# API tests
cd apps/api
py -3.12 -m pytest tests/ -v
```

## Project Structure

```
apps/
  api/          FastAPI backend + AI engine
  web/          Next.js frontend
  worker/       Celery workers (shared with api)
storage/        uploads, outputs, temp files
docs/           project documentation
```
