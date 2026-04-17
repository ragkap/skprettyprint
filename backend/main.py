import logging
import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

load_dotenv()

REQUIRED_ENV = ("DB_NAME", "DB_HOST", "DB_USER", "DB_PASSWORD", "DB_PORT")
missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

from backend.services.primer import build_primer, search_entities

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("prettyprint")

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="Smartkarma Pretty Print Utility")


@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1, max_length=60)):
    try:
        return {"results": search_entities(q, limit=10)}
    except Exception as e:
        log.exception("Search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@app.get("/api/primer")
def api_primer(ticker: str = Query(..., min_length=1, max_length=40)):
    bb_ticker = ticker.strip().upper()
    log.info("Generating primer for %s", bb_ticker)
    try:
        result = build_primer(bb_ticker)
    except Exception as e:
        log.exception("Primer generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    if result is None:
        raise HTTPException(status_code=404, detail=f"No primer found for ticker '{bb_ticker}'")

    pdf_bytes, filename = result
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote(filename)}"'},
    )


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
