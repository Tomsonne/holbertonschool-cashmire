from fastapi import FastAPI
from app.core.gestionnaires import installer_gestionnaires
from app.routes.authentification import router as authentification_router
from app.routes.depenses import router as depenses_router
from app.routes.health import router as health_router

app = FastAPI(title="Cashmire API", version="0.1.0")
installer_gestionnaires(app)
app.include_router(health_router, prefix="/api", tags=["systeme"])
app.include_router(authentification_router, prefix="/api/authentification", tags=["authentification"])
app.include_router(depenses_router, prefix="/api/depenses", tags=["depenses"])
