import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException

app = FastAPI(title="catalog-service", version="0.1.0")

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

# In-memory "DB"
TITLES = {
    "t_palm_springs": {
        "id": "t_palm_springs",
        "type": "movie",
        "localizations": {
            "en-US": {"title": "Palm Springs"},
            "es-MX": {"title": "Palm Springs (ES)"},
        },
        "assets": {
            # pretend this is per device type
            "tv_4k": {
                "artwork_updated_at": (now_utc() - timedelta(hours=2)).isoformat()
            }
        },
    },
    "t_foo": {
        "id": "t_foo",
        "type": "movie",
        "localizations": {"en-US": {"title": "Foo"}},
        "assets": {"tv_4k": {"artwork_updated_at": (now_utc() - timedelta(hours=10)).isoformat()}},
    },
}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/titles/{title_id}")
def get_title(title_id: str):
    t = TITLES.get(title_id)
    if not t:
        raise HTTPException(status_code=404, detail="title not found")
    return t

# Demo breakage endpoints (for your README demo scripts)

@app.post("/admin/break/artwork_stale/{title_id}")
def break_artwork_stale(title_id: str):
    t = TITLES.get(title_id)
    if not t:
        raise HTTPException(status_code=404, detail="title not found")
    t["assets"].setdefault("tv_4k", {})
    t["assets"]["tv_4k"]["artwork_updated_at"] = (now_utc() - timedelta(hours=999)).isoformat()
    return {"ok": True, "message": "artwork set to stale"}

@app.post("/admin/break/remove_localization/{title_id}/{locale}")
def break_remove_localization(title_id: str, locale: str):
    t = TITLES.get(title_id)
    if not t:
        raise HTTPException(status_code=404, detail="title not found")
    t.get("localizations", {}).pop(locale, None)
    return {"ok": True, "message": f"localization {locale} removed"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
