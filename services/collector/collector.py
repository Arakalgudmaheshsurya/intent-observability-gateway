"""
collector.py

Runs intent checks via the intent-gateway and stores results in Postgres.

Expected env vars (set via docker-compose.yml):
- INTENT_GATEWAY_BASE_URL (e.g. http://intent-gateway:8003)
- DATABASE_URL (e.g. postgresql+psycopg://intent:intent@postgres:5432/intentdb)
- DEFAULT_INTERVAL_SECONDS (optional, default 60)

Notes:
- Uses SQLAlchemy + psycopg.
- Stores evidence and suspected_causes as JSONB.
"""

import os
import time
import httpx
from datetime import datetime, timezone

from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.dialects.postgresql import JSONB


INTENT_GATEWAY_BASE_URL = os.environ.get("INTENT_GATEWAY_BASE_URL", "http://localhost:8003")
DATABASE_URL = os.environ.get("DATABASE_URL")
DEFAULT_INTERVAL_SECONDS = int(os.environ.get("DEFAULT_INTERVAL_SECONDS", "60"))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(ts: str) -> datetime:
    # FastAPI isoformat includes timezone; fromisoformat handles it
    return datetime.fromisoformat(ts)


def ensure_schema() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS intent_results (
                    id BIGSERIAL PRIMARY KEY,
                    check_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    ts TIMESTAMPTZ NOT NULL,
                    severity TEXT,
                    description TEXT,
                    evidence JSONB,
                    suspected_causes JSONB
                );
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_intent_results_check_ts ON intent_results (check_id, ts DESC);"
            )
        )


# Prepare insert statement once (faster + avoids placeholder issues)
INSERT_STMT = (
    text(
        """
        INSERT INTO intent_results
        (check_id, status, ts, severity, description, evidence, suspected_causes)
        VALUES (:check_id, :status, :ts, :severity, :description, :evidence, :suspected_causes)
        """
    )
    .bindparams(
        bindparam("evidence", type_=JSONB),
        bindparam("suspected_causes", type_=JSONB),
    )
)


def upsert_result(result: dict) -> None:
    # Store dict/list directly; SQLAlchemy will encode to JSONB.
    payload = {
        "check_id": result.get("check_id"),
        "status": result.get("status"),
        "ts": parse_iso(result["timestamp"]) if result.get("timestamp") else now_utc(),
        "severity": result.get("severity"),
        "description": result.get("description"),
        "evidence": result.get("evidence", {}),
        "suspected_causes": result.get("suspected_causes", []),
    }

    # Basic validation—helps catch unexpected result shapes early
    if not payload["check_id"] or not payload["status"]:
        raise ValueError(f"Bad result payload (missing check_id/status): {result}")

    with engine.begin() as conn:
        conn.execute(INSERT_STMT, payload)


def get_checks() -> list[dict]:
    r = httpx.get(f"{INTENT_GATEWAY_BASE_URL}/checks", timeout=5.0)
    r.raise_for_status()
    return r.json()


def run_check(check_id: str) -> dict:
    r = httpx.post(f"{INTENT_GATEWAY_BASE_URL}/run/{check_id}", timeout=10.0)
    r.raise_for_status()
    return r.json()


def main() -> None:
    ensure_schema()
    print("collector: schema ensured")

    while True:
        try:
            checks = get_checks()
            for c in checks:
                check_id = c["id"]

                # (MVP) We currently run all checks each loop.
                # Later: per-check scheduling using c["schedule"]["every_seconds"].
                res = run_check(check_id)

                # If gateway returns ERROR, store it anyway (optional behavior).
                # Here we store it; you can choose to skip if you want.
                upsert_result(res)

                print(f"collector: stored {check_id} => {res.get('status')}")

            # Keep loop responsive; MVP approach
            time.sleep(min(DEFAULT_INTERVAL_SECONDS, 10))

        except Exception as e:
            print(f"collector error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
