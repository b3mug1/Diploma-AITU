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

SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))
if not 1 <= SESSION_HOURS <= 168:
    raise ValueError("SESSION_HOURS must be between 1 and 168")
