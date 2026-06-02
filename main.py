"""
Módulo de alertas de seguridad para mujeres — Cali
====================================================
Uso como sub-aplicación (integración recomendada):

    from modulo_alertas.backend.main import alertas_app
    main_app.mount("/alertas", alertas_app)

Uso autónomo (desarrollo / testing):

    uvicorn modulo_alertas.backend.main:alertas_app --reload --port 8001
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import webhook, usuarios, admin
from .config import settings

alertas_app = FastAPI(
    title="Módulo de Alertas — Seguridad de Género",
    description="Sistema de alerta discreta vía WhatsApp para mujeres en riesgo en Cali.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — ajustar origins según la plataforma principal
alertas_app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
alertas_app.include_router(webhook.router)
alertas_app.include_router(usuarios.router)
alertas_app.include_router(admin.router)

@alertas_app.on_event("startup")
async def startup():
    await init_db()

@alertas_app.get("/health")
async def health():
    return {"status": "ok", "modulo": "alertas"}

# ── Punto de entrada autónomo ─────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("modulo_alertas.backend.main:alertas_app", host="0.0.0.0", port=8001, reload=True)
