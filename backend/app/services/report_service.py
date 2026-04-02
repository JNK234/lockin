# ABOUTME: Computes focus report metrics from raw Neo4j data and generates
# ABOUTME: distraction pattern analysis via RocketRide/GPT-4o.

import json
import logging

from rocketride.schema import Question

logger = logging.getLogger(__name__)


def compute_metrics(report_data: dict) -> dict:
    """Compute focus percentages, streaks, and site summaries from raw data."""
    timeline = report_data["timeline"]
    sites = report_data["sites"]
    start_time = report_data["start_time"]
    end_time = report_data["end_time"]

    # Total session duration (Neo4j returns neo4j.time.DateTime, not Python datetime)
    if start_time and end_time:
        # Convert to Python datetime for arithmetic
        py_start = start_time.to_native() if hasattr(start_time, "to_native") else start_time
        py_end = end_time.to_native() if hasattr(end_time, "to_native") else end_time
        total_seconds = (py_end - py_start).total_seconds()
        duration_minutes = round(total_seconds / 60.0, 1)
    else:
        duration_minutes = 0

    # Time by classification
    on_task_min = sum(s["total_minutes"] for s in sites if s["classification"] == "on_task")
    distraction_min = sum(s["total_minutes"] for s in sites if s["classification"] == "distraction")
    ambiguous_min = sum(s["total_minutes"] for s in sites if s["classification"] == "ambiguous")
    total_min = on_task_min + distraction_min + ambiguous_min

    if total_min > 0:
        on_task_pct = round(on_task_min / total_min * 100, 1)
        distraction_pct = round(distraction_min / total_min * 100, 1)
        ambiguous_pct = round(ambiguous_min / total_min * 100, 1)
    else:
        on_task_pct = distraction_pct = ambiguous_pct = 0

    # Longest focus streak (consecutive on_task visits)
    longest_streak = 0
    current_streak = 0
    for entry in timeline:
        if entry["classification"] == "on_task":
            current_streak += entry["duration_min"]
        else:
            longest_streak = max(longest_streak, current_streak)
            current_streak = 0
    longest_streak = max(longest_streak, current_streak)

    # Total site switches
    total_switches = max(0, len(timeline) - 1)

    # Split sites
    top_distractions = [
        {"domain": s["domain"], "total_minutes": s["total_minutes"], "visit_count": s["visit_count"]}
        for s in sites if s["classification"] == "distraction"
    ]
    on_task_sites = [
        {"domain": s["domain"], "total_minutes": s["total_minutes"], "visit_count": s["visit_count"]}
        for s in sites if s["classification"] == "on_task"
    ]

    # Format timeline for response (handle neo4j.time.DateTime)
    formatted_timeline = []
    for entry in timeline:
        t = entry["time"]
        if hasattr(t, "to_native"):
            time_str = t.to_native().strftime("%H:%M")
        elif hasattr(t, "strftime"):
            time_str = t.strftime("%H:%M")
        else:
            time_str = str(t)
        formatted_timeline.append({
            "time": time_str,
            "domain": entry["domain"],
            "classification": entry["classification"],
            "duration_min": entry["duration_min"],
        })

    return {
        "duration_minutes": duration_minutes,
        "on_task_percentage": on_task_pct,
        "distraction_percentage": distraction_pct,
        "ambiguous_percentage": ambiguous_pct,
        "longest_focus_streak_minutes": round(longest_streak, 1),
        "total_site_switches": total_switches,
        "top_distractions": top_distractions,
        "on_task_sites": on_task_sites,
        "timeline": formatted_timeline,
    }


async def generate_patterns(rr_client, rr_token: str, task: str,
                            timeline: list, sites: list, chains: list) -> dict:
    """Send session data to GPT-4o via RocketRide for pattern analysis.

    Returns focus_score and distraction_patterns.
    """
    try:
        question = Question(expectJson=True)
        question.addContext({
            "task": task,
            "timeline": timeline,
            "sites": sites,
            "distraction_transitions": chains,
        })
        question.addQuestion(
            "Analyze this focus session. The user was working on the task above. "
            "Return JSON with:\n"
            '- "focus_score": 0-100 (percentage of on-task time, weighted by streak length — '
            "longer unbroken focus = higher score)\n"
            '- "distraction_patterns": array of 2-4 plain strings (not objects), each a specific '
            "observation about when/why focus was lost. Be specific about times and sites, not generic advice."
        )

        response = await rr_client.chat(token=rr_token, question=question)
        answers = response.get("answers", [])
        if not answers:
            logger.warning("No answer from report pipeline")
            return {"focus_score": 0, "distraction_patterns": []}

        answer = answers[0]
        if isinstance(answer, str):
            parsed = json.loads(answer)
        elif isinstance(answer, dict):
            parsed = answer
        else:
            return {"focus_score": 0, "distraction_patterns": []}

        # Normalize distraction_patterns — GPT-4o may return strings or dicts
        raw_patterns = parsed.get("distraction_patterns", [])
        patterns = []
        for p in raw_patterns:
            if isinstance(p, str):
                patterns.append(p)
            elif isinstance(p, dict):
                patterns.append(p.get("observation", str(p)))
            else:
                patterns.append(str(p))

        return {
            "focus_score": min(100, max(0, int(parsed.get("focus_score", 0)))),
            "distraction_patterns": patterns,
        }

    except Exception:
        logger.exception("Pattern analysis failed")
        return {"focus_score": 0, "distraction_patterns": ["Pattern analysis unavailable"]}
