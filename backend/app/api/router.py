from fastapi import APIRouter

from app.api.routes import admin, applications, assistant, auth, bot, documents, export, forms, health, notices, photo, profile

api_router = APIRouter()
for module in (health, auth, profile, documents, notices, photo, forms, applications, assistant, bot, admin, export):
    api_router.include_router(module.router)
