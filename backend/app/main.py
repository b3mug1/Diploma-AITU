"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX, FRONTEND_ORIGINS
from app.database import Base, engine
from app import models  # noqa: F401 — register model metadata before create_all.
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Create tables for the initial local prototype."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Locker Management System API",
    description=(
        "Initial API slice for student and locker registries and locker assignments. "
        "Authentication and repair-request workflows are not included in this contribution."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router, prefix=API_PREFIX)
