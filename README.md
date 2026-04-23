# NetGraph — Apex Platform

A real-time network operations platform built around a Neo4j digital twin. It simulates a production telecom infrastructure, injects faults and failure scenarios, normalises telemetry into TMF-642 alarms, and presents everything on an operator dashboard with live WebSocket updates.

## What it is

NetGraph is a **NOC training and validation platform**. It lets operators:

- Visualise a live digital twin of 460+ network devices and their links
- Inject production-grade fault scenarios (BGP hijack, fibre cut, DDoS, STP storm, etc.)
- Watch telemetry flow through the ingestion pipeline in real time
- Execute VNF lifecycle operations (migrate, patch, verify) via the MANO API
- Reset the entire network state back to baseline with one click

## Architecture

Three FastAPI services communicate over HTTP and WebSockets:

```
Browser ──WS──► Hub (8888) ──HTTP──► Simulator (9999)
                    │                       │
                    └──Neo4j──┘      ScenarioEngine
                    └──HTTP──► MANO API (9998)
```

| Service | Port | File |
|---|---|---|
| Hub / UI Server | 8888 | `src/ui/server.py` |
| Infrastructure Simulator | 9999 | `src/sim/network_app.py` |
| MANO API | 9998 | `src/sim/orchestrator_api.py` |

## Getting Started

### Prerequisites
- Python 3.10+
- Neo4j 5.x running on `bolt://localhost:7687`

### Setup
```bash
# Install dependencies
pip install fastapi uvicorn neo4j apscheduler httpx python-dotenv pydantic

# Configure environment
cp .env.example .env   # set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

# Load the graph (first time only)
python -m src.data.ingest_to_neo4j

# Start all three services (separate terminals)
python -m uvicorn src.ui.server:app --port 8888
python -m uvicorn src.sim.network_app:app --port 9999
python -m uvicorn src.sim.orchestrator_api:app --port 9998
```

Open `http://localhost:8888` — the Discovery view.

## Pages

| URL | Page | Purpose |
|---|---|---|
| `/` | Discovery | Live topology graph + fault injection rack + incident panel |
| `/ops` | NAPI Ops | VNF operations console — migrate, patch, verify |
| `/inventory` | Inventory | Device inventory table |

## Project Structure

```
src/
  ui/           Hub server, frontend templates, static JS/CSS
  sim/          Infrastructure simulator, scenario engine, MANO API
  data/         Neo4j ingestion scripts, synthetic data generators
  graph/        Neo4j connection helpers and schema
  core/         Shared config, logging, exceptions
docs/
  fault_symptoms_database.json   Fault → symptom mappings used by simulator
data/
  apex/         Infrastructure topology JSON (fallback if Neo4j offline)
```
