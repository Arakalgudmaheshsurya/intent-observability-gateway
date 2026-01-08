Intent Observability Gateway

Intent-driven observability for product correctness, not just system health.

Traditional observability answers questions like:

Is the service up?

Is latency within SLO?

This project answers a harder and more valuable question:

“Is the user experience actually correct?”

Inspired by Netflix’s work on Intent-Driven Observability, this system continuously verifies product expectations (intents) such as discoverability, localization, and content readiness — and stores the results for historical analysis.

🚨 The Problem

In large distributed systems, everything can look “healthy” while the product experience is broken:

A movie exists, but doesn’t appear in Trending

Artwork exists, but is stale on certain devices

Localization is missing for a specific region

Eligibility rules silently hide content

Metrics, logs, and traces won’t reliably catch these failures — because the system is technically working.

💡 The Solution: Intent Observability

This project introduces Intent Checks:

Declarative, continuously evaluated expectations about how the product should behave.

Examples:

“Title Palm Springs must appear in Trending for US / en-US”

“Artwork must be fresh (< 24h) for tv_4k devices”

“Localization must exist for es-MX”

These intents are:

Defined as YAML

Executed via APIs

Stored in Postgres

Queryable via a Results API

🏗️ Architecture
┌──────────────┐        ┌────────────────┐
│  YAML Checks │ ─────▶ │ Intent Gateway │
└──────────────┘        │ (FastAPI)      │
                         └──────┬─────────┘
                                │
        ┌──────────────┐        │
        │ Surface Svc  │ ◀──────┘
        │ (Trending)   │
        └──────────────┘

        ┌──────────────┐
        │ Catalog Svc  │
        │ (Metadata)   │
        └──────────────┘

                 │
                 ▼
        ┌────────────────┐
        │   Collector    │
        │ (Scheduler)   │
        └──────┬─────────┘
               │
               ▼
        ┌────────────────┐
        │   Postgres     │
        │ intent_results│
        └──────┬─────────┘
               │
               ▼
        ┌────────────────┐
        │  Results API   │
        │ (Read-only)   │
        └────────────────┘

🧩 Components
1. Intent Gateway (intent-gateway)

Loads intent definitions from YAML

Executes checks by calling backend services

Produces structured results (PASS / FAIL + evidence)

2. Catalog Service (catalog-service)

Simulated content metadata

Localization, artwork freshness, assets

3. Surface Service (surface-service)

Simulated UI surfaces (e.g., Trending)

Region and locale–aware responses

4. Collector

Periodically runs intent checks

Stores results in Postgres

Maintains historical records

5. Results API (results-api)

Read-only API for observability insights

Exposes:

Latest results

Currently failing intents

Per-intent history

Pass-rate summaries

📁 Repository Structure
intent-observability-gateway/
├── checks/                    # Intent definitions (YAML)
├── services/
│   ├── catalog-service/
│   ├── surface-service/
│   ├── intent-gateway/
│   ├── collector/
│   └── results_api/
├── scripts/
│   └── simulate_breakage.sh
├── docker-compose.yml
└── README.md

🧪 Example Intent (YAML)
id: trending_discoverable_us_en
description: Title should appear in Trending for US/en-US
target:
  surface: trending
  region: US
  locale: en-US
assert:
  type: contains_title
  title_id: t_palm_springs
severity: high
schedule:
  every_seconds: 30

▶️ Running the Project
Prerequisites

Docker + Docker Compose

Start everything
docker compose up --build

✅ Verify Services
curl http://localhost:8001/health   # catalog
curl http://localhost:8002/health   # surface
curl http://localhost:8003/health   # intent-gateway
curl http://localhost:8004/health   # results-api

🔍 Run Intent Checks
curl -X POST http://localhost:8003/run_all | python -m json.tool

💥 Simulate a Broken Experience
./scripts/simulate_breakage.sh
curl -X POST http://localhost:8003/run_all | python -m json.tool


Now inspect failing intents:

curl http://localhost:8004/api/failing | python -m json.tool

📊 Query Observability Data
Latest results
curl http://localhost:8004/api/latest

Per-intent history
curl http://localhost:8004/api/checks/trending_discoverable_us_en/history?minutes=60

Pass-rate summary
curl http://localhost:8004/api/summary

🧠 Why This Matters

This system demonstrates:

Product-level observability

Declarative health checks

Distributed system coordination

Historical correctness tracking

Real-world failure modes invisible to metrics

This approach scales especially well for:

Streaming platforms

E-commerce discovery

Recommendation systems

Internationalized products

🚀 Future Improvements

UI dashboard

Alerting on intent failures

Time-travel checks (future configs)

Change correlation (deploy → intent failure)

OpenTelemetry integration

📌 Summary

Intent Observability Gateway shifts observability from “Are systems healthy?”
to “Is the product experience correct?”

That distinction matters at scale.