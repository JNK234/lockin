# ABOUTME: HTML report route — renders the focus dashboard as a web page.
# ABOUTME: GET /report/{session_id} reuses the JSON report logic and renders via Jinja2.

import logging

from fastapi import APIRouter, Request, HTTPException

from app.routers.session import get_report

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report"])


@router.get("/report/{session_id}")
async def report_view(session_id: str, request: Request):
    """Render the focus report as an HTML dashboard page."""
    templates = request.app.state.templates

    try:
        report = await get_report(session_id, request)
    except HTTPException:
        raise

    report_dict = report.model_dump()

    return templates.TemplateResponse("report.html", {
        "request": request,
        "report": report_dict,
    })
