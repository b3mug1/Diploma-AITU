"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.config import API_PREFIX, FRONTEND_ORIGINS
from app.repairs import router as repair_router
from app.routes import router

app = FastAPI(
    title="Locker Management System API",
    description="Locker registries, role-based access and repair operations.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router, prefix=API_PREFIX)

app.include_router(auth_router, prefix=API_PREFIX)


app.include_router(repair_router, prefix=API_PREFIX)
