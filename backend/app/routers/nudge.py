# ABOUTME: Nudge router — checks if the user is distracted and returns a nudge.
# ABOUTME: Polled by the Chrome extension every 60 seconds during active sessions.

import asyncio
import logging

from fastapi import APIRouter, Request

from app.models.events import NudgeResponse
from app.services.neo4j_service import check_nudge, record_nudge, has_recent_nudge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["nudge"])


@router.get("/{session_id}/nudge", response_model=NudgeResponse)
async def get_nudge(session_id: str, request: Request):
    """Check if the user should be nudged back to their task.

    Queries Neo4j for the current visit's classification. If it's a distraction,
    returns a nudge with context (how long, what to return to). Logs the nudge
    in the graph for the session report.
    """
    driver = request.app.state.neo4j_driver

    nudge_data = await asyncio.to_thread(check_nudge, driver, session_id)

    if nudge_data is None:
        return NudgeResponse(nudge=False)

    domain = nudge_data["current_domain"]
    seconds = nudge_data["off_task_seconds"]
    minutes = max(1, seconds // 60)
    message = f"You've been on {domain} for {minutes} minute{'s' if minutes != 1 else ''} — get back to your task!"

    # Log the nudge in Neo4j (dedup: skip if nudged recently)
    already_nudged = await asyncio.to_thread(has_recent_nudge, driver, session_id)
    if not already_nudged:
        await asyncio.to_thread(record_nudge, driver, session_id, domain, message)

    return NudgeResponse(
        nudge=True,
        message=message,
        task=nudge_data["task"],
        current_domain=domain,
        off_task_seconds=seconds,
        return_to=nudge_data["return_to"],
    )
