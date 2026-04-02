# ABOUTME: Webhook router for receiving Chrome extension browsing events.
# ABOUTME: Stores visits in Neo4j and triggers background classification via RocketRide.

import asyncio
import uuid
import logging

from fastapi import APIRouter, Request

from app.models.events import WebhookEvent, WebhookResponse
from app.utils.url import extract_domain
from app.services.neo4j_service import find_or_create_session, create_visit
from app.services.classifier import classify_visit_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/save", response_model=WebhookResponse)
async def save_event(event: WebhookEvent, request: Request):
    """Receive a browsing event from the Chrome extension.

    1. Extract domain from URL (for site grouping)
    2. Find or create an active session for this task
    3. Create a Visit node and wire graph relationships
    4. Kick off background classification with full page context
    5. Return immediately
    """
    driver = request.app.state.neo4j_driver
    rr_client = request.app.state.rr_client
    rr_token = request.app.state.rr_token

    domain = extract_domain(event.pageInfo.url)
    visit_id = str(uuid.uuid4())

    # Store in Neo4j (sync driver, run in thread)
    session_id = await asyncio.to_thread(
        find_or_create_session, driver, event.task, event.pageInfo.timestamp
    )
    visit_data = await asyncio.to_thread(
        create_visit, driver, visit_id, event.pageInfo.url,
        event.pageInfo.title, event.pageInfo.timestamp, session_id, domain
    )

    # Classify in background — don't block the response
    asyncio.create_task(
        classify_visit_background(
            neo4j_driver=driver,
            rr_client=rr_client,
            rr_token=rr_token,
            visit_id=visit_id,
            domain=domain,
            task=event.task,
            url=event.pageInfo.url,
            title=event.pageInfo.title,
            page_content=event.pageInfo.content,
        )
    )

    logger.info(f"Event saved: visit={visit_id} session={session_id} domain={domain}")

    return WebhookResponse(
        status="ok",
        visit_id=visit_id,
        session_id=session_id,
        domain=domain,
        classification="pending",
    )
