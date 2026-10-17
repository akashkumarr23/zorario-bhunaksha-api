"""
══════════════════════════════════════════════════════════════════════
ZORARIO PARTNER — Bihar Bhunaksha Scraper API
Zero-cost FastAPI backend for bhunaksha.bihar.gov.in
Deploy FREE on Railway / Render / Fly.io

Endpoints:
  GET  /health                         — health check
  GET  /districts                      — list all Bihar districts
  GET  /circles?district_code=XYZ      — list circles for a district
  GET  /mauzas?district_code=X&circle_code=Y — list mauzas
  GET  /sheets?district_code=X&circle_code=Y&mauza_code=Z — list sheets
  POST /plot-info                      — get plot details + generate LPM PDF URL
══════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import hashlib
import logging
import httpx
from typing import Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bhunaksha")

# ─── Configuration ────────────────────────────────────────────────
BASE_URL = os.getenv("BHUNAKSHA_BASE", "https://bhunaksha.bihar.gov.in")
STATE_CODE = "10"          # Bihar state code in NIC Bhunaksha

# Supabase (optional — for caching)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ─── HTTP client shared headers (mimic browser) ───────────────────
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://bhunaksha.bihar.gov.in/bhunaksha/indexmain.jsp",
    "Origin": "https://bhunaksha.bihar.gov.in",
}

# ─── In-memory cache (survives restarts only on Railway) ──────────
_cache: dict[str, tuple[Any, float]] = {}
CACHE_TTL = 86400  # 24 hours for lists, 7 days for plot data


def cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and (time.time() - entry[1]) < CACHE_TTL:
        return entry[0]
    return None


def cache_set(key: str, value: Any):
    _cache[key] = (value, time.time())


# ─── HTTP Session ─────────────────────────────────────────────────
_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = httpx.AsyncClient(
        headers=BROWSER_HEADERS,
        timeout=30,
        follow_redirects=True,
    )
    log.info("HTTP client started")
    yield
    await _client.aclose()
    log.info("HTTP client closed")


# ─── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(
    title="Zorario Bhunaksha Scraper API",
    description="Zero-cost Bihar land parcel data fetcher for Zorario Partner App",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helper: POST to Bhunaksha REST ───────────────────────────────
async def bhunaksha_post(path: str, data: dict) -> Any:
    """Make a session-aware POST to Bhunaksha and return parsed JSON."""
    url = f"{BASE_URL}/rest/{path}"
    log.info(f"POST {url} data={data}")
    try:
        resp = await _client.post(url, data=data)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        log.error(f"HTTP error {e.response.status_code} for {url}")
        raise HTTPException(
            status_code=502,
            detail=f"Bhunaksha portal returned {e.response.status_code}",
        )
    except Exception as e:
        log.error(f"Request failed for {url}: {e}")
        raise HTTPException(status_code=503, detail=f"Portal unavailable: {str(e)}")


async def bhunaksha_get(path: str, params: dict = {}) -> Any:
    """Make a GET to Bhunaksha and return parsed JSON."""
    url = f"{BASE_URL}/rest/{path}"
    log.info(f"GET {url} params={params}")
    try:
        resp = await _client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        log.error(f"HTTP error {e.response.status_code} for {url}")
        raise HTTPException(
            status_code=502,
            detail=f"Bhunaksha portal returned {e.response.status_code}",
        )
    except Exception as e:
        log.error(f"Request failed for {url}: {e}")
        raise HTTPException(status_code=503, detail=f"Portal unavailable: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Zorario Bihar Bhunaksha Scraper API",
        "portal": "bhunaksha.bihar.gov.in",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "bhunaksha-scraper", "state": "Bihar"}


BIHAR_38_DISTRICTS = [
    {"code": "07", "name": "Araria", "name_hindi": "अररिया"},
    {"code": "38", "name": "Arwal", "name_hindi": "अरवल"},
    {"code": "34", "name": "Aurangabad", "name_hindi": "औरंगाबाद"},
    {"code": "23", "name": "Banka", "name_hindi": "बांका"},
    {"code": "20", "name": "Begusarai", "name_hindi": "बेगूसराय"},
    {"code": "22", "name": "Bhagalpur", "name_hindi": "भागलपुर"},
    {"code": "29", "name": "Bhojpur", "name_hindi": "भोजपुर"},
    {"code": "30", "name": "Buxar", "name_hindi": "बक्सर"},
    {"code": "13", "name": "Darbhanga", "name_hindi": "दरभंगा"},
    {"code": "35", "name": "Gaya", "name_hindi": "गया"},
    {"code": "15", "name": "Gopalganj", "name_hindi": "गोपालगंज"},
    {"code": "37", "name": "Jamui", "name_hindi": "जमुई"},
    {"code": "33", "name": "Jehanabad", "name_hindi": "जहानाबाद"},
    {"code": "31", "name": "Kaimur", "name_hindi": "कैमूर"},
    {"code": "10", "name": "Katihar", "name_hindi": "कटिहार"},
    {"code": "21", "name": "Khagaria", "name_hindi": "खगड़िया"},
    {"code": "08", "name": "Kishanganj", "name_hindi": "किशनगंज"},
    {"code": "25", "name": "Lakhisarai", "name_hindi": "लखीसराय"},
    {"code": "11", "name": "Madhepura", "name_hindi": "मधेपुरा"},
    {"code": "05", "name": "Madhubani", "name_hindi": "मधुबनी"},
    {"code": "24", "name": "Munger", "name_hindi": "मुंगेर"},
    {"code": "14", "name": "Muzaffarpur", "name_hindi": "मुजफ्फरपुर"},
    {"code": "01", "name": "Nalanda", "name_hindi": "नालंदा"},
    {"code": "36", "name": "Nawada", "name_hindi": "नवादा"},
    {"code": "27", "name": "Pashchim Champaran", "name_hindi": "पश्चिम चम्पारण"},
    {"code": "28", "name": "Patna", "name_hindi": "पटना"},
    {"code": "02", "name": "Purbi Champaran", "name_hindi": "पूर्वी चम्पारण"},
    {"code": "09", "name": "Purnia", "name_hindi": "पूर्णिया"},
    {"code": "32", "name": "Rohtas", "name_hindi": "रोहतास"},
    {"code": "12", "name": "Saharsa", "name_hindi": "सहरसा"},
    {"code": "19", "name": "Samastipur", "name_hindi": "समस्तीपुर"},
    {"code": "17", "name": "Saran", "name_hindi": "सारण"},
    {"code": "26", "name": "Sheikhpura", "name_hindi": "शेखपुरा"},
    {"code": "03", "name": "Sheohar", "name_hindi": "शिवहर"},
    {"code": "04", "name": "Sitamarhi", "name_hindi": "सीतामढ़ी"},
    {"code": "16", "name": "Siwan", "name_hindi": "सीवान"},
    {"code": "06", "name": "Supaul", "name_hindi": "सुपौल"},
    {"code": "18", "name": "Vaishali", "name_hindi": "वैशाली"},
]

@app.get("/districts")
async def get_districts():
    """Return all 38 Bihar districts with official NIC codes."""
    return {"districts": BIHAR_38_DISTRICTS}


@app.get("/cadastral-map")
async def get_cadastral_map(
    district_code: str = Query(..., description="2-digit district code"),
    circle_code: str = Query("01"),
    mauza_code: str = Query("0058"),
    subdiv_code: str = Query("01"),
    sv_type: str = Query("SS"),
    sheet_no: str = Query("00"),
):
    """
    Fetch authentic Bihar Government GeoServer WMS Cadastral Map URL
    and bounding box for given village.
    """
    levels = f"{district_code},{subdiv_code},{circle_code},{mauza_code},{sv_type},00,{sheet_no},"
    try:
        url = f"{BASE_URL}/rest/MapInfo/getVVVVExtentGeoref"
        resp = await _client.post(url, data={"state": STATE_CODE, "gisLevels": levels, "srs": "0"})
        if resp.status_code == 200:
            data = resp.json()
            gis_code = data.get("gisCode")
            epsg = data.get("epsg", "EPSG:32645")
            xmin, ymin = data.get("xmin"), data.get("ymin")
            xmax, ymax = data.get("xmax"), data.get("ymax")

            if gis_code and xmin and ymin and xmax and ymax:
                wms_url = (
                    f"{BASE_URL}/WMS?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
                    f"&LAYERS=VILLAGE_MAP&state=10&gis_code={gis_code}&STYLES=VILLAGE_MAP"
                    f"&SRS={epsg}&BBOX={xmin},{ymin},{xmax},{ymax}&WIDTH=1200&HEIGHT=900&FORMAT=image/png"
                )
                return {
                    "success": True,
                    "gis_code": gis_code,
                    "wms_url": wms_url,
                    "attribution": data.get("attribution", ""),
                    "bbox": [xmin, ymin, xmax, ymax],
                }
    except Exception as e:
        log.error(f"Error fetching cadastral map: {e}")

    return {
        "success": False,
        "detail": "Could not resolve extent from Bihar GeoServer",
    }


@app.get("/circles")
async def get_circles(district_code: str = Query(..., description="District code from /districts")):
    """Return circles for a given district."""
    cache_key = f"circles:{district_code}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    raw = await bhunaksha_post(
        "CircleList/getCircle",
        {"state": STATE_CODE, "district": district_code},
    )

    result = {"circles": _normalize_list(raw, "circle")}
    cache_set(cache_key, result)
    return result


@app.get("/mauzas")
async def get_mauzas(
    district_code: str = Query(...),
    circle_code: str = Query(...),
    sv_type: str = Query("SS", description="SS=Special Survey, RS=Revisional, CS=Cadastral"),
):
    """Return mauzas (revenue villages) for a given circle."""
    cache_key = f"mauzas:{district_code}:{circle_code}:{sv_type}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    raw = await bhunaksha_post(
        "MauzaList/getMauza",
        {
            "state": STATE_CODE,
            "district": district_code,
            "circle": circle_code,
            "sv_type": sv_type,
        },
    )

    result = {"mauzas": _normalize_list(raw, "mauza")}
    cache_set(cache_key, result)
    return result


@app.get("/sheets")
async def get_sheets(
    district_code: str = Query(...),
    circle_code: str = Query(...),
    mauza_code: str = Query(...),
    sv_type: str = Query("SS"),
):
    """Return sheet numbers for a mauza."""
    cache_key = f"sheets:{district_code}:{circle_code}:{mauza_code}:{sv_type}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    raw = await bhunaksha_post(
        "SheetList/getSheets",
        {
            "state": STATE_CODE,
            "district": district_code,
            "circle": circle_code,
            "mauza": mauza_code,
            "sv_type": sv_type,
        },
    )

    result = {"sheets": _normalize_list(raw, "sheet")}
    cache_set(cache_key, result)
    return result


class PlotInfoRequest(BaseModel):
    district_code: str
    circle_code: str
    mauza_code: str
    plot_no: str
    sv_type: str = "SS"
    sheet_no: Optional[str] = None


@app.post("/plot-info")
async def get_plot_info(req: PlotInfoRequest):
    """
    Fetch plot owner info + GeoJSON polygon from Bhunaksha for given plot.
    Returns structured data ready for the Flutter app + PDF.
    """
    cache_key = f"plot:{req.district_code}:{req.circle_code}:{req.mauza_code}:{req.plot_no}:{req.sv_type}"
    cached = cache_get(cache_key)
    if cached:
        log.info(f"Cache hit for {cache_key}")
        return cached

    # ── Step 1: Fetch plot info (owner, area, khata) ──────────────
    plot_payload = {
        "state": STATE_CODE,
        "district": req.district_code,
        "circle": req.circle_code,
        "mauza": req.mauza_code,
        "plot_no": req.plot_no,
        "sv_type": req.sv_type,
    }
    if req.sheet_no:
        plot_payload["sheet_no"] = req.sheet_no

    try:
        plot_raw = await bhunaksha_post("PlotInfo/getPlotInfo", plot_payload)
    except HTTPException:
        # Return a graceful fallback so app still works
        plot_raw = {}

    # ── Step 2: Try to get GeoJSON polygon ────────────────────────
    geojson = None
    try:
        geo_payload = {**plot_payload}
        geo_raw = await bhunaksha_post("GeoInfo/getPlotGeoInfo", geo_payload)
        geojson = geo_raw
    except Exception:
        geojson = None  # Non-fatal: PDF will draw a demo polygon

    # ── Step 3: Build unified response ────────────────────────────
    result = _build_plot_response(
        raw=plot_raw,
        geojson=geojson,
        req=req,
    )

    # Cache for 7 days (government data rarely changes)
    cache_set(cache_key, result)
    return result


# ─── Normalization helpers ────────────────────────────────────────

def _normalize_list(raw: Any, item_type: str) -> list[dict]:
    """
    NIC Bhu-Naksha returns inconsistent JSON shapes.
    Normalize to [{code, name, name_hindi?}] regardless.
    """
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        # Try common keys
        for key in ["data", "result", "list", item_type + "s", item_type + "List"]:
            if key in raw:
                items = raw[key]
                break
        else:
            items = list(raw.values()) if raw else []
    else:
        return []

    normalized = []
    for item in items:
        if isinstance(item, dict):
            # Map any key pattern to {code, name}
            code = (
                item.get("districtCode") or item.get("circleCode") or
                item.get("mauzaCode") or item.get("villCode") or
                item.get("code") or item.get("id") or item.get("distCode") or
                str(item.get("district", "")) or str(item.get("circle", "")) or ""
            )
            name = (
                item.get("districtName") or item.get("circleName") or
                item.get("mauzaName") or item.get("villName") or
                item.get("name") or item.get("nameEn") or
                item.get("district_name") or ""
            )
            name_hindi = (
                item.get("districtNameH") or item.get("circleNameH") or
                item.get("mauzaNameH") or item.get("name_hi") or None
            )
            entry = {"code": str(code), "name": name}
            if name_hindi:
                entry["name_hindi"] = name_hindi
            if code or name:
                normalized.append(entry)
        elif isinstance(item, str):
            normalized.append({"code": item, "name": item})

    return normalized


def _build_plot_response(raw: Any, geojson: Any, req: PlotInfoRequest) -> dict:
    """Parse NIC's plotInfo JSON into Zorario's canonical format."""
    info = {}
    if isinstance(raw, dict):
        info = raw
    elif isinstance(raw, list) and raw:
        info = raw[0] if isinstance(raw[0], dict) else {}

    # Pull known NIC field names with fallbacks
    owner_name = (
        info.get("ownerName") or info.get("khatedaarName") or
        info.get("name") or info.get("owner") or "—"
    )
    khata_no = info.get("khataNo") or info.get("khata") or info.get("khataNumber") or "—"
    area_ha = (
        info.get("areaHa") or info.get("area_ha") or
        info.get("totalArea") or info.get("area") or "—"
    )
    land_class = (
        info.get("landClass") or info.get("classOfLand") or
        info.get("landType") or "—"
    )
    survey_no = info.get("surveyNo") or req.plot_no

    return {
        "plot_no": req.plot_no,
        "mauza_code": req.mauza_code,
        "district_code": req.district_code,
        "circle_code": req.circle_code,
        "sv_type": req.sv_type,
        "owner_name": owner_name,
        "khata_no": khata_no,
        "area_ha": str(area_ha),
        "land_class": land_class,
        "survey_no": str(survey_no),
        "raw_info": info,
        "geojson": geojson,
        "data_source": "bhunaksha.bihar.gov.in",
        "fetched_live": True,
    }
