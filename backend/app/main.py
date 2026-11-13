from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.complaints import router as complaints_router
from app.api.routes.equipment import router as equipment_router
from app.api.routes.finance import router as finance_router
from app.api.routes.invoices import router as invoices_router
from app.api.routes.leads import router as leads_router
from app.api.routes.members import router as members_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.message_templates import router as message_templates_router
from app.api.routes.messages import router as messages_router
from app.api.routes.payments import router as payments_router
from app.api.routes.plans import router as plans_router
from app.api.routes.reminders import router as reminders_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.staff import router as staff_router
from app.api.routes.trainers import router as trainers_router
from app.api.routes.users import router as users_router
from app.api.routes.whatsapp import router as whatsapp_router

app = FastAPI(title="GymOS API", version="0.1.0")
app.include_router(auth_router)
app.include_router(members_router)
app.include_router(plans_router)
app.include_router(memberships_router)
app.include_router(invoices_router)
app.include_router(payments_router)
app.include_router(message_templates_router)
app.include_router(messages_router)
app.include_router(reminders_router)
app.include_router(trainers_router)
app.include_router(users_router)
app.include_router(whatsapp_router)
app.include_router(sessions_router)
app.include_router(staff_router)
app.include_router(finance_router)
app.include_router(leads_router)
app.include_router(complaints_router)
app.include_router(equipment_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

