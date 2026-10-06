from fastapi import FastAPI
from app.core.gestionnaires import installer_gestionnaires
from app.routes.categories import router as categories_router
from app.routes.health import router as health_router

app = FastAPI(title="Cashmire API", version="0.1.0")
installer_gestionnaires(app)
app.include_router(health_router, prefix="/api", tags=["systeme"])
app.include_router(categories_router, prefix="/api", tags=["categories"])
