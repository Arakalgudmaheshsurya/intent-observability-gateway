import os
from fastapi import FastAPI

app = FastAPI(title="surface-service", version="0.1.0")

# In-memory trending index keyed by (region, locale)
TRENDING = {
    ("US", "en-US"): ["t_foo", "t_palm_springs"],
    ("US", "es-MX"): ["t_foo", "t_palm_springs"],
}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/surfaces/trending")
def trending(region: str = "US", locale: str = "en-US"):
    return {
        "surface": "trending",
        "region": region,
        "locale": locale,
        "title_ids": TRENDING.get((region, locale), []),
    }

# Demo breakage endpoint
@app.post("/admin/break/remove_from_trending")
def break_remove_from_trending(region: str = "US", locale: str = "en-US", title_id: str = "t_palm_springs"):
    ids = TRENDING.get((region, locale), [])
    TRENDING[(region, locale)] = [t for t in ids if t != title_id]
    return {"ok": True, "message": f"removed {title_id} from trending {region}/{locale}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8002"))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
