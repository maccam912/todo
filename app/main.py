"""Main FastAPI application."""
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes import auth, groups, tasks
from app.config import get_settings
from app.database import init_db
from app.telemetry import TelemetryManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

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
    return {"message": "SmartTodo API", "version": "0.1.0"}


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
