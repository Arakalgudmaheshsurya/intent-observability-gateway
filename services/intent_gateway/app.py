import os
import glob
import yaml
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException

app = FastAPI(title="intent-gateway", version="0.1.0")

CATALOG_BASE_URL = os.environ.get("CATALOG_BASE_URL", "http://localhost:8001")
SURFACE_BASE_URL = os.environ.get("SURFACE_BASE_URL", "http://localhost:8002")
CHECKS_DIR = os.environ.get("CHECKS_DIR", "./checks")

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_checks() -> list[dict]:
    paths = sorted(glob.glob(os.path.join(CHECKS_DIR, "*.yaml")))
    checks: list[dict] = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            checks.append(yaml.safe_load(f))
    return checks

def get_field(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur

async def run_check(check: dict) -> dict:
    assert_block = check.get("assert", {})
    atype = assert_block.get("type")

    evidence = {}
    suspected_causes = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        if atype == "contains_title":
            tgt = check.get("target", {})
            region = tgt.get("region", "US")
            locale = tgt.get("locale", "en-US")
            title_id = assert_block.get("title_id")
            if not title_id:
                raise ValueError("contains_title requires assert.title_id")

            r = await client.get(f"{SURFACE_BASE_URL}/surfaces/trending", params={"region": region, "locale": locale})
            r.raise_for_status()
            data = r.json()
            ids = data.get("title_ids", [])
            evidence = {
                "surface": "trending",
                "region": region,
                "locale": locale,
                "surface_response_sample": ids[:25],
                "expected_title_id": title_id,
            }
            status = "PASS" if title_id in ids else "FAIL"
            if status == "FAIL":
                suspected_causes = ["surface index not refreshed", "eligibility/ranking rule change", "region/locale mismatch"]

        elif atype == "asset_freshness_hours":
            tgt = check.get("target", {})
            title_id = tgt.get("title_id")
            device = tgt.get("device", "tv_4k")
            max_age_hours = float(assert_block.get("max_age_hours", 24))

            if not title_id:
                raise ValueError("asset_freshness_hours requires target.title_id")

            r = await client.get(f"{CATALOG_BASE_URL}/titles/{title_id}")
            r.raise_for_status()
            data = r.json()
            updated_at = get_field(data, f"assets.{device}.artwork_updated_at")
            evidence = {"title_id": title_id, "device": device, "artwork_updated_at": updated_at, "max_age_hours": max_age_hours}

            if not updated_at:
                status = "FAIL"
                suspected_causes = ["asset missing for device", "ingestion pipeline failure"]
            else:
                dt = datetime.fromisoformat(updated_at)
                age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
                evidence["age_hours"] = round(age_hours, 3)
                status = "PASS" if age_hours <= max_age_hours else "FAIL"
                if status == "FAIL":
                    suspected_causes = ["asset generation stalled", "CDN/artwork pipeline delay", "bad clock or timestamp"]

        elif atype == "field_exists":
            tgt = check.get("target", {})
            title_id = tgt.get("title_id")
            field = assert_block.get("field")
            if not title_id or not field:
                raise ValueError("field_exists requires target.title_id and assert.field")

            r = await client.get(f"{CATALOG_BASE_URL}/titles/{title_id}")
            r.raise_for_status()
            data = r.json()
            val = get_field(data, field)
            evidence = {"title_id": title_id, "field": field, "field_value_preview": val if isinstance(val, (str, int, float, bool)) else None}
            status = "PASS" if val is not None else "FAIL"
            if status == "FAIL":
                suspected_causes = ["localization missing", "schema migration issue", "bad data publish"]

        else:
            raise ValueError(f"Unknown assert.type: {atype}")

    return {
        "check_id": check.get("id"),
        "description": check.get("description", ""),
        "severity": check.get("severity", "low"),
        "status": status,
        "timestamp": now_utc_iso(),
        "evidence": evidence,
        "suspected_causes": suspected_causes,
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/checks")
def list_checks():
    checks = load_checks()
    # Only return safe fields
    return [{
        "id": c.get("id"),
        "description": c.get("description"),
        "severity": c.get("severity"),
        "schedule": c.get("schedule"),
        "assert": c.get("assert"),
        "target": c.get("target"),
    } for c in checks]

@app.post("/run/{check_id}")
async def run_single(check_id: str):
    checks = load_checks()
    c = next((x for x in checks if x.get("id") == check_id), None)
    if not c:
        raise HTTPException(status_code=404, detail="check not found")
    try:
        return await run_check(c)
    except Exception as e:
        return {
            "check_id": check_id,
            "status": "ERROR",
            "timestamp": now_utc_iso(),
            "error": str(e),
        }

@app.post("/run_all")
async def run_all():
    checks = load_checks()
    results = []
    for c in checks:
        try:
            results.append(await run_check(c))
        except Exception as e:
            results.append({"check_id": c.get("id"), "status": "ERROR", "timestamp": now_utc_iso(), "error": str(e)})
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8003"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
