from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.members import router as members_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.plans import router as plans_router

app = FastAPI(title="GymOS API", version="0.1.0")
app.include_router(auth_router)
app.include_router(members_router)
app.include_router(plans_router)
app.include_router(memberships_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
