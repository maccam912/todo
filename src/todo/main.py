"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from todo.api.routes import auth, groups, tasks
from todo.config import get_settings
from todo.core.logging import setup_logging
from todo.database import init_db
from todo.telemetry import TelemetryManager

# Get settings
settings = get_settings()

# Configure logging
setup_logging(settings)
logger = logging.getLogger(__name__)

# Initialize telemetry
telemetry_manager = TelemetryManager(settings)
telemetry_manager.setup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting SmartTodo application")

    # Initialize database
    init_db(settings)
    logger.info("Database initialized")

    yield

    # Shutdown telemetry
    telemetry_manager.shutdown()
    logger.info("Shutting down SmartTodo application")


# Create FastAPI application
app = FastAPI(
    title="SmartTodo",
    description="AI-powered task management system with natural language processing",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with OpenTelemetry
if settings.otel_enabled:
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented with OpenTelemetry")

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(groups.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
