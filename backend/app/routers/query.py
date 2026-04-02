# ABOUTME: Q&A router — lets users ask questions about their browsing history.
# ABOUTME: Uses the RocketRide agent pipeline with db_neo4j to query the knowledge graph.

import logging

from fastapi import APIRouter, Request

from app.models.events import QueryRequest, QueryResponse
from app.services.query_service import ask_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest, request: Request):
    """Ask a natural language question about browsing sessions.

    The RocketRide agent queries Neo4j directly to find answers about
    focus history, distraction patterns, session data, and site usage.
    """
    rr_client = request.app.state.query_client
    rr_token = request.app.state.query_token

    if not rr_client or not rr_token:
        return QueryResponse(answer="Q&A agent is not available. Check RocketRide connection.")

    answer = await ask_query(rr_client, rr_token, req.query, req.session_id)

    logger.info(f"Query: '{req.query}' → answered")
    return QueryResponse(answer=answer)
