from fastapi import APIRouter

from app.api.routes import admin, applications, assistant, auth, bot, documents, export, forms, health, jobs, notices, pdf_tools, photo, profile, search

api_router = APIRouter()
for module in (health, auth, profile, documents, notices, photo, forms, applications, assistant, bot, admin, export, jobs, search, pdf_tools):
    api_router.include_router(module.router)
