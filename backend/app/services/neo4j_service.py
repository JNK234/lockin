# ABOUTME: Neo4j graph database operations for the Lockin focus tracker.
# ABOUTME: All functions are synchronous — call via asyncio.to_thread() from async code.

import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def ensure_constraints(driver):
    """Create uniqueness constraints on startup."""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (si:Site) REQUIRE si.domain IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Visit) REQUIRE v.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Task) REQUIRE t.name IS UNIQUE",
    ]
    with driver.session() as session:
        for cypher in constraints:
            session.run(cypher)
    logger.info("Neo4j constraints ensured")


def find_or_create_session(driver, task: str, timestamp: str) -> str:
    """Find an active session for this task, or create one. Returns session_id."""
    cypher = """
    MERGE (t:Task {name: $task})
    ON CREATE SET t.created_at = datetime($timestamp)
    WITH t
    MERGE (s:Session {task: $task, status: 'active'})
    ON CREATE SET s.id = $session_id, s.start_time = datetime($timestamp)
    MERGE (s)-[:HAS_TASK]->(t)
    RETURN s.id AS session_id
    """
    session_id = str(uuid.uuid4())
    with driver.session() as session:
        result = session.execute_write(
            lambda tx: tx.run(
                cypher,
                task=task,
                timestamp=timestamp,
                session_id=session_id,
            ).single()
        )
        return result["session_id"]


def create_visit(driver, visit_id: str, url: str, title: str,
                 timestamp: str, session_id: str, domain: str) -> dict:
    """Create a Visit node, merge Site, wire all relationships. Returns visit info."""
    cypher = """
    MATCH (s:Session {id: $session_id})

    // Merge the Site node (domain-level grouping)
    MERGE (site:Site {domain: $domain})
    ON CREATE SET site.first_seen = datetime($timestamp),
                  site.classification = 'pending',
                  site.classified_by = 'pending'

    // Create the Visit node
    CREATE (v:Visit {
        id: $visit_id,
        url: $url,
        title: $title,
        start_time: datetime($timestamp),
        classification: 'pending',
        active: true
    })

    // Wire relationships
    CREATE (s)-[:CONTAINS]->(v)
    CREATE (v)-[:TO_SITE]->(site)

    // Mark previous visit as inactive and create NEXT link
    WITH s, v, site
    OPTIONAL MATCH (s)-[:CONTAINS]->(prev:Visit {active: true})
    WHERE prev.id <> $visit_id
    WITH v, site, prev
    ORDER BY prev.start_time DESC
    LIMIT 1
    FOREACH (_ IN CASE WHEN prev IS NOT NULL THEN [1] ELSE [] END |
        SET prev.active = false
        CREATE (prev)-[:NEXT]->(v)
    )

    RETURN v.id AS visit_id, site.domain AS domain, site.classification AS site_classification
    """
    with driver.session() as session:
        result = session.execute_write(
            lambda tx: tx.run(
                cypher,
                visit_id=visit_id,
                url=url,
                title=title,
                timestamp=timestamp,
                session_id=session_id,
                domain=domain,
            ).single()
        )
        return {
            "visit_id": result["visit_id"],
            "domain": result["domain"],
            "site_classification": result["site_classification"],
        }


def update_visit_classification(driver, visit_id: str, classification: str):
    """Set classification on a Visit node."""
    cypher = """
    MATCH (v:Visit {id: $visit_id})
    SET v.classification = $classification
    """
    with driver.session() as session:
        session.execute_write(
            lambda tx: tx.run(cypher, visit_id=visit_id, classification=classification)
        )
    logger.info(f"Visit {visit_id} classified as {classification}")


def update_site_classification(driver, domain: str, classification: str, task: str):
    """Update Site classification and create task-relevance relationship."""
    cypher = """
    MATCH (site:Site {domain: $domain})
    SET site.classification = $classification, site.classified_by = 'llm'
    WITH site
    MATCH (t:Task {name: $task})
    WITH site, t, $classification AS cls
    FOREACH (_ IN CASE WHEN cls = 'on_task' THEN [1] ELSE [] END |
        MERGE (site)-[:ON_TASK_FOR]->(t))
    FOREACH (_ IN CASE WHEN cls = 'distraction' THEN [1] ELSE [] END |
        MERGE (site)-[:DISTRACTION_FROM]->(t))
    """
    with driver.session() as session:
        session.execute_write(
            lambda tx: tx.run(cypher, domain=domain, classification=classification, task=task)
        )
    logger.info(f"Site {domain} classified as {classification} for task '{task}'")


def check_nudge(driver, session_id: str) -> dict | None:
    """Check if the user should be nudged. Returns nudge data or None.

    Looks at the current (active) visit: if it's classified as 'distraction',
    walks backward through the NEXT chain to sum consecutive distraction time,
    and finds the last on-task URL to suggest returning to.
    """
    cypher = """
    MATCH (s:Session {id: $session_id, status: 'active'})-[:HAS_TASK]->(t:Task)
    MATCH (s)-[:CONTAINS]->(current:Visit {active: true})-[:TO_SITE]->(site:Site)
    WHERE current.classification = 'distraction'

    // Walk backward through NEXT chain to sum consecutive distraction time
    WITH s, t, current, site
    OPTIONAL MATCH path = (first:Visit)-[:NEXT*0..20]->(current)
    WHERE (s)-[:CONTAINS]->(first)
      AND ALL(v IN nodes(path) WHERE v.classification = 'distraction')
    WITH s, t, current, site, nodes(path) AS chain
    ORDER BY size(chain) DESC
    LIMIT 1

    // Calculate total distraction seconds from the chain
    WITH s, t, current, site, chain,
         reduce(total = 0, v IN chain |
           total + CASE WHEN v.start_time IS NOT NULL
                        THEN duration.between(v.start_time, datetime()).seconds
                        ELSE 0 END
         ) AS raw_seconds

    // Find most recent on-task visit for return_to URL
    OPTIONAL MATCH (s)-[:CONTAINS]->(ontask:Visit)-[:TO_SITE]->(:Site)
    WHERE ontask.classification = 'on_task'
    WITH t, current, site, raw_seconds, ontask
    ORDER BY ontask.start_time DESC
    LIMIT 1

    RETURN t.name AS task,
           site.domain AS current_domain,
           raw_seconds AS off_task_seconds,
           ontask.url AS return_to
    """
    with driver.session() as session:
        result = session.execute_read(
            lambda tx: tx.run(cypher, session_id=session_id).single()
        )
        if result is None:
            return None
        return {
            "task": result["task"],
            "current_domain": result["current_domain"],
            "off_task_seconds": result["off_task_seconds"] or 0,
            "return_to": result["return_to"],
        }


def record_nudge(driver, session_id: str, domain: str, message: str):
    """Log a nudge event in the graph for later reporting."""
    cypher = """
    MATCH (s:Session {id: $session_id})
    CREATE (n:Nudge {
        id: $nudge_id,
        domain: $domain,
        message: $message,
        timestamp: datetime($timestamp)
    })
    CREATE (s)-[:HAS_NUDGE]->(n)
    """
    with driver.session() as session:
        session.execute_write(
            lambda tx: tx.run(
                cypher,
                session_id=session_id,
                nudge_id=str(uuid.uuid4()),
                domain=domain,
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
    logger.info(f"Nudge recorded for session {session_id}: {domain}")
