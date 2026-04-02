# ABOUTME: FastAPI application entry point for Lockin backend
# ABOUTME: Initializes Neo4j driver and RocketRide client on startup, exposes health check

from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import GraphDatabase

from app.config import settings


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
    print(f"Connected to Neo4j at {settings.neo4j_uri}")

    yield

    # Cleanup
    if neo4j_driver:
        neo4j_driver.close()


app = FastAPI(title="Lockin", description="Browser focus tracker API", lifespan=lifespan)


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
    }
