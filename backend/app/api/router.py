from fastapi import APIRouter

from app.api.routes import admin, applications, assistant, auth, bot, documents, export, forms, health, jobs, notices, photo, profile, search

api_router = APIRouter()
for module in (health, auth, profile, documents, notices, photo, forms, applications, assistant, bot, admin, export, jobs, search):
    api_router.include_router(module.router)
