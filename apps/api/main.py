from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from error_handlers import register_error_handlers
from routers import admin, assets, auth, batch, billing, projects_list, teams, upload, project, download, usage

app = FastAPI(
    title="UI2PSD Studio API",
    description="UI 이미지를 PSD 레이어 파일로 변환하는 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(admin.router)
app.include_router(assets.router)
app.include_router(auth.router)
app.include_router(batch.router)
app.include_router(billing.router)
app.include_router(projects_list.router)
app.include_router(teams.router)
app.include_router(upload.router)
app.include_router(project.router)
app.include_router(download.router)
app.include_router(usage.router)


register_error_handlers(app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
