# ABOUTME: Pydantic request/response models for the webhook event ingestion endpoint.
# ABOUTME: Defines the shape of Chrome extension events and API responses.

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
