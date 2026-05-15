# app/main.py
# Main FastAPI application entry point.
# This file creates the FastAPI app, includes routers, and configures middleware.

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging

from app.core.config import settings
from app.core.database import init_db
from app.api.api import api_router
from app.services.nlp_pipeline import verify_nltk_resources

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager.
    Code before 'yield' runs during startup.
    Code after 'yield' runs during shutdown.
    """
    logger.info("=" * 60)
    logger.info("APPLICATION STARTUP")
    logger.info("=" * 60)

    # 1. Initialize database tables
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # 2. Verify ML/NLP resources
    logger.info("Verifying ML/NLP resources...")
    try:
        await asyncio.to_thread(verify_nltk_resources)
    except Exception as e:
        logger.error(f"ML/NLP resources verification failed: {e}")
        raise

    logger.info("✓ Startup complete. Ready to accept requests.")
    logger.info("=" * 60)

    yield

    logger.info("=" * 60)
    logger.info("APPLICATION SHUTDOWN")
    logger.info("=" * 60)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered platform for analyzing student feedback to improve institutional quality.",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers (upload lives under /api/v1/upload — see app.api.api)
app.include_router(api_router, prefix="/api/v1")

# Phase 2 visualization PNGs (generated offline)
_viz_dir = Path(__file__).resolve().parent.parent / "assets" / "visualizations"
if _viz_dir.is_dir():
    app.mount(
        "/static/visualizations",
        StaticFiles(directory=str(_viz_dir)),
        name="phase2_visualizations",
    )

# Root endpoint
@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}"}


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Future: Add more routers for processing, results, etc.