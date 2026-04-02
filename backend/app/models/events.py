# ABOUTME: Pydantic request/response models for all API endpoints.
# ABOUTME: Covers webhook events, nudge checks, session management, and focus reports.

from typing import Optional

from pydantic import BaseModel


class PageInfo(BaseModel):
    content: str
    timestamp: str
    title: str
    url: str


class WebhookEvent(BaseModel):
    action: str
    task: str
    pageInfo: PageInfo


class WebhookResponse(BaseModel):
    status: str
    visit_id: str
    session_id: str
    domain: str
    classification: Optional[str] = None


class NudgeResponse(BaseModel):
    nudge: bool
    message: Optional[str] = None
    task: Optional[str] = None
    current_domain: Optional[str] = None
    off_task_seconds: Optional[int] = None
    return_to: Optional[str] = None


class SessionEndResponse(BaseModel):
    status: str
    session_id: str


class SiteSummary(BaseModel):
    domain: str
    total_minutes: float
    visit_count: int


class TimelineEntry(BaseModel):
    time: str
    domain: str
    classification: str
    duration_min: float


class ReportResponse(BaseModel):
    session_id: str
    task: str
    duration_minutes: float
    focus_score: int
    on_task_percentage: float
    distraction_percentage: float
    ambiguous_percentage: float
    longest_focus_streak_minutes: float
    total_site_switches: int
    nudge_count: int
    top_distractions: list[SiteSummary]
    on_task_sites: list[SiteSummary]
    distraction_patterns: list[str]
    timeline: list[TimelineEntry]


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
