# ABOUTME: Session management router — end sessions and retrieve focus reports.
# ABOUTME: POST /end closes a session; GET /report returns the full focus analysis.

import asyncio
import logging

from fastapi import APIRouter, Request, HTTPException

from app.models.events import SessionEndResponse, ReportResponse
from app.services.neo4j_service import end_session, get_session_report_data
from app.services.report_service import compute_metrics, generate_patterns

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/{session_id}/end", response_model=SessionEndResponse)
async def end_session_endpoint(session_id: str, request: Request):
    """End an active focus session.

    Marks session as completed, calculates visit durations from the NEXT chain,
    and deactivates the last visit.
    """
    driver = request.app.state.neo4j_driver

    result = await asyncio.to_thread(end_session, driver, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found or already ended")

    logger.info(f"Session ended: {session_id}")
    return SessionEndResponse(status="completed", session_id=session_id)


@router.get("/{session_id}/report", response_model=ReportResponse)
async def get_report(session_id: str, request: Request):
    """Generate and return a focus report for a completed session.

    1. Queries Neo4j for raw session data (visits, sites, timeline, chains)
    2. Computes metrics in Python (percentages, streaks, aggregations)
    3. Sends to GPT-4o via RocketRide for focus_score + distraction_patterns
    4. Assembles and returns the full report
    """
    driver = request.app.state.neo4j_driver
    rr_client = request.app.state.rr_client
    rr_token = request.app.state.rr_token

    # Step 1: Get raw data from Neo4j
    report_data = await asyncio.to_thread(get_session_report_data, driver, session_id)
    if report_data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Step 2: Compute metrics
    metrics = compute_metrics(report_data)

    # Step 3: Pattern analysis via GPT-4o
    patterns = {"focus_score": None, "distraction_patterns": []}
    if rr_client and rr_token:
        patterns = await generate_patterns(
            rr_client, rr_token,
            task=report_data["task"],
            timeline=metrics["timeline"],
            sites=report_data["sites"],
            chains=report_data["chains"],
        )

    # Step 4: Assemble report
    return ReportResponse(
        session_id=session_id,
        task=report_data["task"],
        duration_minutes=metrics["duration_minutes"],
        focus_score=patterns["focus_score"],
        on_task_percentage=metrics["on_task_percentage"],
        distraction_percentage=metrics["distraction_percentage"],
        ambiguous_percentage=metrics["ambiguous_percentage"],
        longest_focus_streak_minutes=metrics["longest_focus_streak_minutes"],
        total_site_switches=metrics["total_site_switches"],
        nudge_count=report_data["nudge_count"],
        top_distractions=metrics["top_distractions"],
        on_task_sites=metrics["on_task_sites"],
        distraction_patterns=patterns["distraction_patterns"],
        timeline=metrics["timeline"],
    )
