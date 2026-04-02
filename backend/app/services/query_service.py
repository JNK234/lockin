# ABOUTME: Q&A service using the RocketRide agent pipeline with Neo4j integration.
# ABOUTME: Initializes the query_agent pipeline and handles user questions.

import logging
import os

from rocketride import RocketRideClient
from rocketride.schema import Question

logger = logging.getLogger(__name__)

PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pipelines", "query_agent.pipe")


async def init_query_agent():
    """Initialize RocketRide client and start the query agent pipeline.
    Returns (client, token) to be stored on app.state.
    """
    client = RocketRideClient()
    await client.connect()
    result = await client.use(filepath=PIPELINE_PATH, use_existing=True)
    token = result["token"]
    logger.info(f"Query agent pipeline started with token: {token}")
    return client, token


async def shutdown_query_agent(client):
    """Disconnect the query agent RocketRide client."""
    if client:
        await client.disconnect()
        logger.info("Query agent client disconnected")


async def ask_query(rr_client, rr_token: str, query: str, session_id: str = None) -> str:
    """Send a user question to the RocketRide agent pipeline.

    The agent has access to Neo4j via db_neo4j tool and will query the graph
    to answer questions about browsing sessions, focus, and history.
    """
    try:
        question = Question()

        # Add session context hint so the agent knows which session to focus on
        if session_id:
            question.addContext(f"The user's current active session ID is: {session_id}")

        question.addQuestion(query)

        response = await rr_client.chat(token=rr_token, question=question)
        answers = response.get("answers", [])

        if not answers:
            return "I couldn't find an answer. Try asking about your sessions, sites, or focus history."

        return answers[0] if isinstance(answers[0], str) else str(answers[0])

    except Exception:
        logger.exception("Query agent failed")
        return "Sorry, I couldn't process your question. The agent encountered an error."
