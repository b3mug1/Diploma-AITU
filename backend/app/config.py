"""Environment-based application settings."""

import os

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./locker_management.db")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1").rstrip("/")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
