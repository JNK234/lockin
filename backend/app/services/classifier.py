# ABOUTME: RocketRide pipeline wrapper for classifying page visits using GPT-4o.
# ABOUTME: Uses chat pipeline with Question(expectJson=True) for structured classification.

import json
import asyncio
import logging
import os

from rocketride import RocketRideClient
from rocketride.schema import Question

from app.services.neo4j_service import update_visit_classification, update_site_classification

logger = logging.getLogger(__name__)

# Max chars of page content to send to LLM (controls token cost)
MAX_CONTENT_LENGTH = 2000

# Path to the pipeline file, resolved relative to backend/ directory
PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pipelines", "classify_site.pipe")


async def init_classifier():
    """Initialize RocketRide client and start the classification pipeline.
    Returns (client, token) to be stored on app.state.
    """
    client = RocketRideClient()
    await client.connect()
    result = await client.use(filepath=PIPELINE_PATH, use_existing=True)
    token = result["token"]
    logger.info(f"Classification pipeline started with token: {token}")
    return client, token


async def shutdown_classifier(client):
    """Disconnect the RocketRide client."""
    if client:
        await client.disconnect()
        logger.info("RocketRide client disconnected")


async def classify_visit_background(
    neo4j_driver,
    rr_client,
    rr_token: str,
    visit_id: str,
    domain: str,
    task: str,
    url: str,
    title: str,
    page_content: str,
):
    """Background task: classify a page visit via RocketRide and update Neo4j.

    Uses all available context (task, URL, title, page content) for an informed
    classification decision. Runs as asyncio.create_task() so it doesn't block
    the webhook response.
    """
    try:
        # Build a structured question with all available context
        question = Question(expectJson=True)
        question.addContext({
            "task": task,
            "url": url,
            "title": title,
            "page_content": page_content[:MAX_CONTENT_LENGTH],
        })
        question.addQuestion(
            "Classify this page visit relative to the user's focus task. "
            "Is this page on_task (directly helpful for the task), "
            "distraction (clearly unrelated — social media, entertainment, news), "
            "or ambiguous (could go either way)? "
            'Respond with JSON: {"classification": "on_task" | "distraction" | "ambiguous", "reason": "brief explanation"}'
        )

        # Send to RocketRide pipeline
        response = await rr_client.chat(token=rr_token, question=question)

        # Extract classification from response
        answers = response.get("answers", [])
        if not answers:
            logger.warning(f"No answer from classifier for visit {visit_id}")
            return

        answer = answers[0]

        # Parse the JSON response (answer may be a string or already parsed)
        if isinstance(answer, str):
            parsed = json.loads(answer)
        elif isinstance(answer, dict):
            parsed = answer
        else:
            logger.warning(f"Unexpected answer type for visit {visit_id}: {type(answer)}")
            return

        classification = parsed.get("classification", "ambiguous")
        reason = parsed.get("reason", "")

        # Validate classification value
        if classification not in ("on_task", "distraction", "ambiguous"):
            logger.warning(f"Invalid classification '{classification}' for visit {visit_id}, defaulting to ambiguous")
            classification = "ambiguous"

        logger.info(f"Visit {visit_id} ({domain}): {classification} — {reason}")

        # Update Neo4j with classification results
        await asyncio.to_thread(update_visit_classification, neo4j_driver, visit_id, classification)
        await asyncio.to_thread(update_site_classification, neo4j_driver, domain, classification, task)

    except Exception:
        logger.exception(f"Classification failed for visit {visit_id} ({domain})")
