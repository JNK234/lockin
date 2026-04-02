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

    // Remove contradicting edge before creating new one
    FOREACH (_ IN CASE WHEN cls = 'on_task' THEN [1] ELSE [] END |
        MERGE (site)-[:ON_TASK_FOR]->(t))
    FOREACH (_ IN CASE WHEN cls = 'distraction' THEN [1] ELSE [] END |
        MERGE (site)-[:DISTRACTION_FROM]->(t))
    WITH site, t, cls
    OPTIONAL MATCH (site)-[bad_on:ON_TASK_FOR]->(t) WHERE cls = 'distraction'
    OPTIONAL MATCH (site)-[bad_off:DISTRACTION_FROM]->(t) WHERE cls = 'on_task'
    DELETE bad_on, bad_off
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

    // Walk backward to find the earliest visit in the consecutive distraction streak
    WITH s, t, current, site
    OPTIONAL MATCH path = (first:Visit)-[:NEXT*0..20]->(current)
    WHERE (s)-[:CONTAINS]->(first)
      AND ALL(v IN nodes(path) WHERE v.classification = 'distraction')
    WITH s, t, current, site, first
    ORDER BY first.start_time ASC
    LIMIT 1

    // Distraction time = wall clock from streak start to now
    WITH s, t, current, site,
         duration.between(first.start_time, datetime()).seconds AS off_task_seconds

    // Find most recent on-task visit for return_to URL
    OPTIONAL MATCH (s)-[:CONTAINS]->(ontask:Visit)
    WHERE ontask.classification = 'on_task'
    WITH t, site, off_task_seconds, ontask
    ORDER BY ontask.start_time DESC
    LIMIT 1

    RETURN t.name AS task,
           site.domain AS current_domain,
           off_task_seconds,
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


def has_recent_nudge(driver, session_id: str, within_seconds: int = 300) -> bool:
    """Check if a nudge was already recorded recently (default: last 5 min)."""
    cypher = """
    MATCH (s:Session {id: $session_id})-[:HAS_NUDGE]->(n:Nudge)
    WHERE duration.between(n.timestamp, datetime()).seconds < $within_seconds
    RETURN count(n) > 0 AS recent
    """
    with driver.session() as session:
        result = session.execute_read(
            lambda tx: tx.run(cypher, session_id=session_id, within_seconds=within_seconds).single()
        )
        return result["recent"] if result else False


def end_session(driver, session_id: str) -> dict:
    """End a session: set status to completed, calculate visit durations.

    Visit durations are computed from the gap between consecutive start_times.
    The last visit's duration runs from its start_time to session end_time.
    """
    cypher = """
    MATCH (s:Session {id: $session_id, status: 'active'})

    // Set end_time to max(now, latest visit start_time + 1 min) to handle future timestamps
    WITH s
    OPTIONAL MATCH (s)-[:CONTAINS]->(last_v:Visit)
    WITH s, max(last_v.start_time) AS last_visit_time
    WITH s, CASE WHEN last_visit_time > datetime()
                 THEN last_visit_time + duration({minutes: 1})
                 ELSE datetime()
            END AS end_ts
    SET s.status = 'completed', s.end_time = end_ts

    // Mark last active visit as inactive
    WITH s
    OPTIONAL MATCH (s)-[:CONTAINS]->(v:Visit {active: true})
    SET v.active = false

    // Calculate durations from NEXT chain
    WITH s
    MATCH (s)-[:CONTAINS]->(v:Visit)
    OPTIONAL MATCH (v)-[:NEXT]->(next_v:Visit)
    WITH s, v,
         CASE WHEN next_v IS NOT NULL
              THEN duration.between(v.start_time, next_v.start_time).seconds
              ELSE duration.between(v.start_time, s.end_time).seconds
         END AS dur
    SET v.duration_seconds = dur

    WITH s
    MATCH (s)-[:HAS_TASK]->(t:Task)
    RETURN s.id AS session_id, s.task AS task, s.status AS status
    """
    with driver.session() as session:
        result = session.execute_write(
            lambda tx: tx.run(cypher, session_id=session_id).single()
        )
        if result is None:
            return None
        return {
            "session_id": result["session_id"],
            "task": result["task"],
            "status": result["status"],
        }


def get_session_report_data(driver, session_id: str) -> dict | None:
    """Fetch all raw data needed to build a focus report.

    Returns session metadata, site aggregation, timeline, distraction chains,
    and nudge count — all from a single set of Cypher queries.
    """
    with driver.session() as session:
        # Session metadata
        meta = session.execute_read(
            lambda tx: tx.run("""
                MATCH (s:Session {id: $session_id})-[:HAS_TASK]->(t:Task)
                RETURN s.task AS task, s.start_time AS start_time,
                       s.end_time AS end_time, s.status AS status
            """, session_id=session_id).single()
        )
        if meta is None:
            return None

        # Site aggregation
        sites = session.execute_read(
            lambda tx: tx.run("""
                MATCH (s:Session {id: $session_id})-[:CONTAINS]->(v:Visit)-[:TO_SITE]->(site:Site)
                WITH site.domain AS domain, site.classification AS classification,
                     count(v) AS visit_count,
                     sum(coalesce(v.duration_seconds, 0)) AS total_seconds
                RETURN domain, classification, visit_count,
                       round(total_seconds / 60.0, 1) AS total_minutes
                ORDER BY total_seconds DESC
            """, session_id=session_id).values()
        )

        # Timeline
        timeline = session.execute_read(
            lambda tx: tx.run("""
                MATCH (s:Session {id: $session_id})-[:CONTAINS]->(v:Visit)-[:TO_SITE]->(site:Site)
                RETURN v.start_time AS time, site.domain AS domain,
                       v.classification AS classification,
                       round(coalesce(v.duration_seconds, 0) / 60.0, 1) AS duration_min
                ORDER BY v.start_time
            """, session_id=session_id).values()
        )

        # Distraction chains (on_task → distraction transitions)
        chains = session.execute_read(
            lambda tx: tx.run("""
                MATCH (s:Session {id: $session_id})-[:CONTAINS]->(v1:Visit)-[:NEXT]->(v2:Visit)
                MATCH (v1)-[:TO_SITE]->(s1:Site), (v2)-[:TO_SITE]->(s2:Site)
                WHERE v1.classification = 'on_task' AND v2.classification = 'distraction'
                RETURN s1.domain AS from_site, s2.domain AS to_distraction,
                       coalesce(v1.duration_seconds, 0) AS focus_seconds_before,
                       v1.start_time AS drift_time
                ORDER BY v1.start_time
            """, session_id=session_id).values()
        )

        # Nudge count
        nudge_count = session.execute_read(
            lambda tx: tx.run("""
                MATCH (s:Session {id: $session_id})-[:HAS_NUDGE]->(n:Nudge)
                RETURN count(n) AS cnt
            """, session_id=session_id).single()
        )

        return {
            "task": meta["task"],
            "start_time": meta["start_time"],
            "end_time": meta["end_time"],
            "status": meta["status"],
            "sites": [
                {"domain": r[0], "classification": r[1], "visit_count": r[2], "total_minutes": r[3]}
                for r in sites
            ],
            "timeline": [
                {"time": r[0], "domain": r[1], "classification": r[2], "duration_min": r[3]}
                for r in timeline
            ],
            "chains": [
                {"from_site": r[0], "to_distraction": r[1], "focus_seconds_before": r[2], "drift_time": r[3]}
                for r in chains
            ],
            "nudge_count": nudge_count["cnt"] if nudge_count else 0,
        }
