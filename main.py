from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import date

app = FastAPI(title="Grant Drafting Assistant")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

GRANTS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Local Small Business Support Program",
        "organization": "City Economic Development Office",
        "min_amount": 5000,
        "max_amount": 25000,
        "eligible_locations": ["CA"],
        "eligible_applicant_types": ["individual", "llc"],
        "sectors": ["small_business"],
        "required_sections": ["Project Narrative","Budget Outline","Timeline"],
        "deadline": "rolling",
        "source_url": "https://example.org",
        "last_verified_at": str(date.today())
    }
]

def score_band(score:int):
    if score >= 80: return "Likely Match"
    if score >= 50: return "Possible Match"
    return "Low Match"

@app.get("/", response_class=HTMLResponse)
def home():
    index = static_dir / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))

@app.post("/api/grants/discover")
def discover(profile: dict):
    return JSONResponse([])

@app.get("/api/health")
def health():
    return {"ok": True}