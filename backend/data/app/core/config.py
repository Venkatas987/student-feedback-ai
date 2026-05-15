# app/core/config.py
# Centralized configuration settings for the application.
# Uses Pydantic Settings for type-safe environment variable management.

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Resolve absolute paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # ── Application settings ──────────────────────────────────────────────────────
    APP_NAME: str = "Student Feedback AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # ── Server ────────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ──────────────────────────────────────────────────────────────────────
    # Vite runs on 5173. Both included for flexibility.
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Production: Vercel deployment
        "https://student-feedback-ai.vercel.app",
        "https://student-feedback-ai-git-main.vercel.app",  # preview branch
    ]

    # ── Upload settings ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100 MB
    ALLOWED_EXTENSIONS: set = {".csv", ".xlsx", ".json"}

    # ── ML Model paths ────────────────────────────────────────────────────────────
    ML_MODELS_DIR: str = str(BASE_DIR / "ml" / "models")
    TFIDF_VECTORIZER_PATH: str = str(BASE_DIR / "ml" / "models" / "tfidf_vectorizer.pkl")
    SVD_MODEL_PATH: str = str(BASE_DIR / "ml" / "models" / "svd_model.pkl")
    KMEANS_MODEL_PATH: str = str(BASE_DIR / "ml" / "models" / "kmeans_model.pkl")
    CLUSTER_NAMES_PATH: str = str(BASE_DIR / "ml" / "models" / "cluster_names.json")

    # ── Database ──────────────────────────────────────────────────────────────────
    # For local development with SQLite: sqlite+aiosqlite:///./student_feedback.db
    # For production with PostgreSQL: postgresql+asyncpg://postgres:postgres@localhost:5432/student_feedback
    DATABASE_URL: str = "sqlite+aiosqlite:///./student_feedback.db"

    # ── JWT Authentication ────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-256-bit-random"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Optional display hints (Phase 2 themes); real labels come from DB / uploads ─
    INSTITUTIONAL_CLUSTERS: List[str] = [
        "Research & Technology Resources",
        "Teaching Quality & Engagement",
        "Financial Aid & Administration",
        "Diversity & Inclusion Support",
        "Academic Support & Wellbeing",
        "Career & Internship Opportunities",
        "Campus Infrastructure",
        "Food & Cafeteria Services",
        "Online Learning & Platform Issues",
        "Sports Issues",
        "Unclassified Institutional Feedback",
    ]

    # Load from .env file
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()