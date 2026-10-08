from fastapi import Depends, FastAPI
from app.core.gestionnaires import installer_gestionnaires
from app.core.origine import verifier_origine
from app.core.openapi import personnaliser_openapi
from app.routes.authentification import router as authentification_router
from app.routes.budgets import router as budgets_router
from app.routes.categories import router as categories_router
from app.routes.depenses import router as depenses_router
from app.routes.health import router as health_router

# Dépendance globale (pas un middleware) : un refus passe par les gestionnaires d'erreurs communs.
app = FastAPI(title="Cashmire API", version="0.1.0", dependencies=[Depends(verifier_origine)])
installer_gestionnaires(app)
app.include_router(health_router, prefix="/api", tags=["systeme"])
app.include_router(authentification_router, prefix="/api/authentification", tags=["authentification"])
app.include_router(budgets_router, prefix="/api", tags=["budgets"])
app.include_router(categories_router, prefix="/api/categories", tags=["categories"])
app.include_router(depenses_router, prefix="/api/depenses", tags=["depenses"])
personnaliser_openapi(app)
