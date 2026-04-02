# ABOUTME: FastAPI application entry point for Lockin backend.
# ABOUTME: Initializes Neo4j driver, RocketRide classifier, and registers routers.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

from app.config import settings
from app.services.neo4j_service import ensure_constraints
from app.services.classifier import init_classifier, shutdown_classifier
from app.routers.webhook import router as webhook_router
from app.routers.nudge import router as nudge_router
from app.routers.session import router as session_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

neo4j_driver = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global neo4j_driver

    # Connect to Neo4j
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    neo4j_driver.verify_connectivity()
    logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")

    # Store on app.state for dependency access in routers
    app.state.neo4j_driver = neo4j_driver

    # Create graph constraints
    ensure_constraints(neo4j_driver)

    # Initialize RocketRide classification pipeline
    try:
        rr_client, rr_token = await init_classifier()
        app.state.rr_client = rr_client
        app.state.rr_token = rr_token
    except Exception:
        logger.exception("RocketRide init failed — classification will be unavailable")
        app.state.rr_client = None
        app.state.rr_token = None

    yield

    # Cleanup
    await shutdown_classifier(getattr(app.state, "rr_client", None))
    if neo4j_driver:
        neo4j_driver.close()


app = FastAPI(title="Lockin", description="Browser focus tracker API", lifespan=lifespan)

# CORS — allow Chrome extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(webhook_router)
app.include_router(nudge_router)
app.include_router(session_router)


@app.get("/health")
def health_check():
    neo4j_status = "error"
    try:
        neo4j_driver.verify_connectivity()
        neo4j_status = "ok"
    except Exception as e:
        neo4j_status = str(e)

    return {
        "status": "running",
        "neo4j": neo4j_status,
        "rocketride_uri": settings.rocketride_uri,
        "rocketride_connected": app.state.rr_client is not None,
    }
