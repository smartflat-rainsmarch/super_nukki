from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from error_handlers import register_error_handlers
from routers import admin, api_keys, assets, auth, batch, billing, export, model_config, projects_list, sla, sso, teams, upload, project, download, usage

app = FastAPI(
    title="UI2PSD Studio API",
    description="UI 이미지를 PSD 레이어 파일로 변환하는 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.include_router(admin.router)
app.include_router(api_keys.router)
app.include_router(assets.router)
app.include_router(auth.router)
app.include_router(batch.router)
app.include_router(billing.router)
app.include_router(export.router)
app.include_router(model_config.router)
app.include_router(projects_list.router)
app.include_router(sla.router)
app.include_router(sso.router)
app.include_router(teams.router)
app.include_router(upload.router)
app.include_router(project.router)
app.include_router(download.router)
app.include_router(usage.router)


register_error_handlers(app)


@app.on_event("startup")
def on_startup():
    from database import Base, _get_engine
    Base.metadata.create_all(bind=_get_engine())


@app.get("/health")
async def health_check():
    return {"status": "ok"}
