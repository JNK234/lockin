# LockIn

**Focus. Track. Achieve.**

LockIn is a browser extension that helps you stay focused during work sessions. It passively tracks your browsing, uses AI to classify each page visit as on-task or distraction, nudges you when you drift, and generates a detailed focus report when your session ends.

## Architecture

```
+------------------+       +------------------+       +----------+
| Chrome Extension | <---> |  FastAPI Backend  | <---> |  Neo4j   |
| (Manifest V3)    |  HTTP |  (Python 3.12)   | Bolt  | Graph DB |
+------------------+       +--------+---------+       +----------+
                                     |
                                     | HTTP
                                     v
                            +------------------+
                            |  RocketRide +    |
                            |  GPT-4o          |
                            +------------------+
```

- **Chrome Extension** captures page visits, shows nudge overlays, manages session lifecycle
- **FastAPI Backend** ingests events, orchestrates classification and report generation
- **Neo4j** stores sessions, visits, sites, and their relationships as a graph
- **RocketRide + GPT-4o** classifies pages and analyzes focus patterns

## Features

- Start a focus session with a work goal
- Automatic page visit tracking on every tab load
- AI-powered classification: on-task, distraction, or ambiguous
- Nudge overlays when distracted (with "Go Back" to return to productive work)
- Focus report dashboard with score ring, timeline, site breakdown, and AI insights
- Natural language Q&A about your sessions
- Configurable API backend URL and nudge interval

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, FastAPI |
| Database | Neo4j (graph DB with APOC + GDS) |
| AI/LLM | RocketRide, OpenAI GPT-4o |
| Frontend | Chrome Extension (Manifest V3) |
| Templates | Jinja2 |
| Deployment | Docker Compose |

## Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Google Chrome
- RocketRide account (for AI classification)
- OpenAI API key

### 1. Start Neo4j

```bash
docker-compose up -d
```

This starts Neo4j on `localhost:7474` (browser) and `localhost:7687` (Bolt).

### 2. Configure Backend

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your keys:
```
ROCKETRIDE_APIKEY=your-rocketride-key
ROCKETRIDE_OPENAI_KEY=your-openai-key
```

### 3. Install & Run Backend

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`. Check health: `http://localhost:8000/health`

### 4. Load Extension

1. Open `chrome://extensions` in Chrome
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked** and select the `frontend/` directory
4. Pin the LockIn extension in the toolbar

### 5. (Optional) Load Demo Data

Open the Neo4j Browser at `http://localhost:7474`, connect with `neo4j`/`lockin2026`, and paste the contents of `backend/seed/mock_data.cypher`.

Then visit `http://localhost:8000/report/demo-session-001` to see a sample report.

## Usage

1. Click the LockIn extension icon in Chrome
2. Enter your work goal (e.g., "Fix auth bug in login flow")
3. Click **Start Task** — tracking begins
4. Browse normally. Every page load is captured and classified
5. If you drift to a distraction, a nudge overlay appears after ~60 seconds
6. Click **End Session** when done — a focus report opens in a new tab
7. Review your focus score, timeline, top distractions, and AI insights

## Configuration

Click the gear icon in the popup header to open settings:

- **API Base URL** — Backend server address (default: `http://localhost:8000`)
- **Nudge Interval** — How often to check for distractions, 1-30 minutes (default: 1)

## Project Structure

```
lockin/
  backend/
    app/
      config.py          # Environment settings
      main.py            # FastAPI app entry point
      models/
        events.py        # Request/response Pydantic models
      routers/
        webhook.py       # POST /webhook/save — event ingestion
        nudge.py         # GET /api/sessions/{id}/nudge
        session.py       # POST /end, GET /report (JSON)
        report.py        # GET /report/{id} (HTML dashboard)
        query.py         # POST /api/query — Q&A agent
      services/
        neo4j_service.py # Graph database operations
        classifier.py    # RocketRide classification pipeline
        report_service.py# Metrics computation + AI patterns
        query_service.py # RocketRide Q&A agent pipeline
      templates/
        report.html      # Focus report dashboard template
    pipelines/
      classify_site.pipe # Site classification pipeline
      query_agent.pipe   # Q&A agent pipeline
    seed/
      mock_data.cypher   # Demo session data
    requirements.txt
  frontend/
    manifest.json        # Chrome extension manifest (V3)
    background.js        # Service worker — event ingestion, nudges, sessions
    content.js           # Page scraper — extracts page context
    overlay.js           # Nudge overlay UI
    popup.html           # Extension popup UI
    popup.js             # Popup logic — idle/tracking states, timer
    config.js            # Shared configuration resolver
    options.html         # Settings page
    options.js           # Settings logic
  docker-compose.yml     # Neo4j service
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook/save` | Ingest a page visit event |
| GET | `/api/sessions/{id}/nudge` | Check if user is distracted |
| POST | `/api/sessions/{id}/end` | End a focus session |
| GET | `/api/sessions/{id}/report` | Get focus report (JSON) |
| GET | `/report/{id}` | Focus report dashboard (HTML) |
| POST | `/api/query` | Ask a question about sessions |
| GET | `/health` | Service health check |

## License

Hackathon project — HackWithChicago April 2026
