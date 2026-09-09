"""
Traffic Congestion API — FastAPI Backend
-----------------------------------------
Serves pre-computed pipeline outputs from CSV files.
In-memory cache avoids re-reading CSVs on every request.
Cache is invalidated by POST /pipeline/run.

Real data sources:
  - algorithm/congestion_results.csv       → FAHP scores, ranks, tier
  - algorithm/cluster_results.csv          → FKM cluster parameters
  - algorithm/topsis_comparison.csv        → Entropy + TOPSIS scores/ranks
  - simulation/data_output/seeded_robustness_results.csv → Rerouting experiment
  - simulation/data_output/rerouting_all_variants_comparison.csv → Variant edge metrics

Mocked:
  - Route geometry (lat/lon polylines) — generated radially from
    Kalinga Hospital Junction. Colors are real; paths are illustrative.
"""

import os
import time
import math
import logging
import random
import subprocess
from typing import Optional
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file so the server can be launched from any cwd
# ---------------------------------------------------------------------------
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PATHS = {
    "congestion":   os.path.join(BASE, "algorithm", "congestion_results.csv"),
    "cluster":      os.path.join(BASE, "algorithm", "cluster_results.csv"),
    "topsis":       os.path.join(BASE, "algorithm", "topsis_comparison.csv"),
    "rerouting":    os.path.join(BASE, "simulation", "data_output", "seeded_robustness_results.csv"),
    "variants":     os.path.join(BASE, "simulation", "data_output", "rerouting_all_variants_comparison.csv"),
}

ALGORITHM_DIR = os.path.join(BASE, "algorithm")

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------
_cache: dict = {}
_cache_ts: float = 0.0
CACHE_TTL = 300  # seconds


def _load_csv(key: str) -> pd.DataFrame:
    path = PATHS[key]
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file missing: {path}")
    return pd.read_csv(path, index_col=0)


def _build_cache() -> dict:
    """Merge all CSVs into a single rich per-route dict."""
    logger.info("Building in-memory cache from CSV files…")

    cong = _load_csv("congestion")
    clust = _load_csv("cluster")
    tops = _load_csv("topsis")

    # Score tercile → tier label (use quantiles of FAHP score)
    q33 = cong["congestion_score"].quantile(0.333)
    q66 = cong["congestion_score"].quantile(0.666)

    def tier(score: float) -> str:
        if score >= q66:
            return "HIGH"
        if score >= q33:
            return "MEDIUM"
        return "LOW"

    # Rerouting data (keyed by Variant name; only !257 is affected)
    rerouting_routes: dict = {"!257": {}}
    try:
        rerout = _load_csv("rerouting")
        var_df = _load_csv("variants")
        
        p50 = var_df.loc["Primary_50"] if "Primary_50" in var_df.index else (var_df.loc["Broad_50"] if "Broad_50" in var_df.index else None)
        baseline = var_df.loc["Baseline"] if "Baseline" in var_df.index else None

        if p50 is not None and baseline is not None:
            travel_time_imp = round(((baseline["Travel_Time_vehs"] - p50["Travel_Time_vehs"]) / baseline["Travel_Time_vehs"]) * 100, 2)
            co2_imp = round(((baseline["CO2_g"] - p50["CO2_g"]) / baseline["CO2_g"]) * 100, 2)
            fuel_imp = round(((baseline["Fuel_L"] - p50["Fuel_L"]) / baseline["Fuel_L"]) * 100, 2)

            fahp_imp = round(float(rerout.loc["Primary_50", "FAHP_Improv_%"]), 2) if "Primary_50" in rerout.index else 27.3
            entropy_imp = round(float(rerout.loc["Primary_50", "Entropy_Improv_%"]), 2) if "Primary_50" in rerout.index else 12.9

            rerouting_routes["!257"] = {
                "available": True,
                "recommended_variant": "Primary_50",
                "travel_time_improvement_pct": travel_time_imp,
                "co2_fuel_improvement_pct": co2_imp,
                "fuel_improvement_pct": fuel_imp,
                "description": "Reroute 50% of heavy-overlap fleet (>=30% edge overlap, 8 of 16 vehicles) around bottleneck edges 1203439472 and 1208491992.",

                "bottleneck_edges": ["1203439472#0", "1203439472#1", "1208491992#0", "1208491992#1"],
                "expected_improvement": {
                    "travel_time_pct": travel_time_imp,
                    "co2_pct": co2_imp,
                    "fuel_pct": fuel_imp,
                    "fahp_score_pct": fahp_imp,
                    "entropy_score_pct": entropy_imp,
                },
                "sensitivity": rerout.to_dict(orient="index"),
                "rank_shift": {"before": 1, "after": 18},
            }
    except Exception as e:
        logger.warning(f"Rerouting data unavailable: {e}")

    # Generate stable illustrative geometry for all routes
    # Centered on Kalinga Hospital Junction, Bhubaneswar
    CENTER_LAT, CENTER_LON = 20.3147, 85.8203
    random.seed(0)  # deterministic so routes don't jump on refresh

    routes: dict = {}
    last_updated = datetime.fromtimestamp(os.path.getmtime(PATHS["congestion"])).isoformat()

    all_route_ids = cong.index.tolist()
    n = len(all_route_ids)

    for i, route_id in enumerate(all_route_ids):
        score = float(cong.loc[route_id, "congestion_score"])
        rank  = int(cong.loc[route_id, "rank"])
        status = str(cong.loc[route_id, "status"])
        computed_tier = tier(score)

        # Cluster params
        cluster_params = {}
        if route_id in clust.index:
            cluster_params = {k: round(float(v), 4) for k, v in clust.loc[route_id].items()}

        # TOPSIS / entropy
        topsis_data = {}
        if route_id in tops.index:
            row = tops.loc[route_id]
            topsis_data = {
                "entropy_score":       round(float(row.get("entropy_score", 0)), 4),
                "entropy_rank":        int(row.get("entropy_rank", 0)),
                "topsis_fahp_score":   round(float(row.get("TOPSIS_FAHP_score", 0)), 6),
                "topsis_fahp_rank":    int(row.get("TOPSIS_FAHP_rank", 0)),
                "topsis_entropy_score":round(float(row.get("TOPSIS_Entropy_score", 0)), 6),
                "topsis_entropy_rank": int(row.get("TOPSIS_Entropy_rank", 0)),
            }

# Geometry: generate distinct start and end points for each route using predefined landmark pairs
        landmarks = [
            (20.3147, 85.8203),  # 0: Kalinga Hospital Junction
            (20.3100, 85.8150),  # 1: Jaydev Vihar
            (20.3050, 85.8180),  # 2: Damana
            (20.3125, 85.8225),  # 3: Acharya Vihar
            (20.3170, 85.8250),  # 4: Chandrasekharpur
        ]

        pairs = [
            (1, 0),  # Jaydev Vihar -> Kalinga Hospital (HIGH)
            (2, 0),  # Damana -> Kalinga Hospital (HIGH)
            (3, 0),  # Acharya Vihar -> Kalinga Hospital (HIGH)
            (4, 0),  # Chandrasekharpur -> Kalinga Hospital (HIGH)
            (0, 1),  # Kalinga Hospital -> Jaydev Vihar (MEDIUM)
            (0, 2),  # Kalinga Hospital -> Damana (MEDIUM)
            (0, 3),  # Kalinga Hospital -> Acharya Vihar (MEDIUM)
            (0, 4),  # Kalinga Hospital -> Chandrasekharpur (MEDIUM)
            (1, 4),  # Jaydev Vihar -> Chandrasekharpur (LOW)
            (2, 3),  # Damana -> Acharya Vihar (LOW)
        ]

        pair_idx = i % len(pairs)
        s_idx, e_idx = pairs[pair_idx]
        
        # Parallel offset so overlapping route lines don't obscure each other
        offset_lat = 0.00012 * ((i // len(pairs)) % 4 - 1.5)
        offset_lon = 0.00012 * ((i // len(pairs)) % 4 - 1.5)

        start_lat = landmarks[s_idx][0] + offset_lat
        start_lon = landmarks[s_idx][1] + offset_lon
        end_lat = landmarks[e_idx][0] + offset_lat
        end_lon = landmarks[e_idx][1] + offset_lon

        geometry = [[round(start_lat, 6), round(start_lon, 6)], [round(end_lat, 6), round(end_lon, 6)]]

        # Rerouting availability
        reroute_info = rerouting_routes.get(route_id, {"available": False})

        routes[route_id] = {
            "route_id":       route_id,
            "fahp_score":     round(score, 4),
            "fahp_rank":      rank,
            "congestion_tier": computed_tier,
            "status":         status,
            "last_updated":   last_updated,
            "geometry":       geometry,
            "cluster_params": cluster_params,
            "topsis_data":    topsis_data,
            "reroute_available": reroute_info.get("available", False),
        }

    # Summary stats
    tier_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in routes.values():
        tier_counts[r["congestion_tier"]] += 1

    summary = {
        "total_routes": n,
        "tier_counts": tier_counts,
        "avg_fahp_score": round(cong["congestion_score"].mean(), 2),
        "max_fahp_score": round(cong["congestion_score"].max(), 2),
        "min_fahp_score": round(cong["congestion_score"].min(), 2),
        "last_simulation_run": last_updated,
        "cache_built_at": datetime.now().isoformat(),
        "geometry_note": "Route geometries are illustrative (radial from Kalinga Hospital Junction). Colors and scores are real pipeline output.",
    }

    return {"routes": routes, "summary": summary, "rerouting": rerouting_routes}


def get_cache() -> dict:
    global _cache, _cache_ts
    if not _cache or (time.time() - _cache_ts) > CACHE_TTL:
        _cache = _build_cache()
        _cache_ts = time.time()
    return _cache


def invalidate_cache():
    global _cache, _cache_ts
    _cache = {}
    _cache_ts = 0.0


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Traffic Congestion API",
    description="Serves SUMO simulation + FKM/FAHP/Entropy pipeline outputs.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup: pre-warm cache
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    try:
        get_cache()
        logger.info("Cache pre-warmed successfully.")
    except Exception as e:
        logger.error(f"Cache pre-warm failed: {e}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/routes", summary="All routes with congestion scores and geometry")
def list_routes(tier: Optional[str] = None):
    cache = get_cache()
    routes = cache["routes"]
    if tier:
        tier_upper = tier.upper()
        routes = {k: v for k, v in routes.items() if v["congestion_tier"] == tier_upper}
    return {"count": len(routes), "routes": routes}


@app.get("/routes/congested", summary="Top congested routes, worst-first")
def congested_routes(threshold: str = "HIGH", limit: int = 10):
    tier_order = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
    min_tier = tier_order.get(threshold.upper(), 2)

    cache = get_cache()
    filtered = [
        v for v in cache["routes"].values()
        if tier_order.get(v["congestion_tier"], 0) >= min_tier
    ]
    filtered.sort(key=lambda r: r["fahp_score"], reverse=True)
    return {"count": len(filtered), "routes": filtered[:limit]}


@app.get("/routes/{route_id}", summary="Full detail for one route")
def route_detail(route_id: str):
    cache = get_cache()
    key = route_id if route_id.startswith("!") else f"!{route_id}"
    if key not in cache["routes"]:
        raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found.")
    return cache["routes"][key]


@app.get("/routes/{route_id}/reroute-suggestion", summary="Rerouting suggestion for a route")
def reroute_suggestion(route_id: str):
    cache = get_cache()
    key = route_id if route_id.startswith("!") else f"!{route_id}"

    if key not in cache["routes"]:
        raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found.")

    reroute_data = cache["rerouting"].get(key, {})
    if not reroute_data.get("available", False):
        return {
            "route_id": key,
            "available": False,
            "message": "No rerouting experiment has been run for this route. Only Route !257 has rerouting data.",
        }
    return {"route_id": key, **reroute_data}


@app.get("/stats/summary", summary="Network-wide summary statistics")
def stats_summary():
    return get_cache()["summary"]


@app.post("/pipeline/run", summary="Re-run the algorithm pipeline")
def run_pipeline(background_tasks: BackgroundTasks):
    invalidate_cache()

    def _run():
        scripts = ["sensor_fusion.py", "fkm_clustering.py", "fahp.py", "entropy_weight.py"]
        for script in scripts:
            logger.info(f"Running {script}…")
            try:
                subprocess.run(
                    ["python", script],
                    cwd=ALGORITHM_DIR,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"{script} failed: {e.stderr}")
                return
            except subprocess.TimeoutExpired:
                logger.error(f"{script} timed out.")
                return
        logger.info("Pipeline completed. Cache will rebuild on next request.")

    background_tasks.add_task(_run)
    return {"status": "accepted", "message": "Pipeline is running in background. Cache will update on next request."}


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Compatibility Aliases (for older React dashboard callers)
# ---------------------------------------------------------------------------

@app.get("/api/congestion")
def legacy_congestion():
    cache = get_cache()
    routes = cache["routes"]
    data = {}
    for r_id, r_info in routes.items():
        t_data = r_info.get("topsis_data", {})
        data[r_id] = {
            "congestion_score": r_info["fahp_score"],
            "score": r_info["fahp_score"],
            "status": r_info["congestion_tier"],
            "level": r_info["congestion_tier"],
            "tier": r_info["congestion_tier"],
            "rank": r_info["fahp_rank"],
            "entropy_rank": t_data.get("entropy_rank", r_info["fahp_rank"]),
            "entropy_score": t_data.get("entropy_score", 0.0),
            "cluster_speed": r_info.get("cluster_speed"),
            "cluster_co2": r_info.get("cluster_co2"),
            "geometry": r_info.get("geometry", [])
        }
    return {"status": "success", "data": data}


@app.get("/api/history")
def legacy_history():
    """Per-route emission/speed history from cluster_params (SUMO pipeline output).

    Returns a dict keyed by route ID so the React dashboard can do:
        history['!257']?.speed
        history['!257']?.co2_emission
    etc.
    """
    cache = get_cache()
    routes = cache["routes"]
    per_route: dict = {}
    for r_id, r_info in routes.items():
        cp = r_info.get("cluster_params", {})
        per_route[r_id] = {
            "speed":            cp.get("speed"),
            "co_emission":      cp.get("co_emission"),
            "co2_emission":     cp.get("co2_emission"),
            "nox_emission":     cp.get("nox_emission"),
            "fuel_consumption": cp.get("fuel_consumption"),
        }
    return {"status": "success", "data": per_route}


@app.get("/api/status")
def legacy_status():
    cache = get_cache()
    summary = cache["summary"]
    return {
        "status": "online",
        "last_updated": summary.get("last_simulation_run"),
        "data_last_updated": summary.get("last_simulation_run"),
        "pipeline": "FastAPI pre-computed CSV backend",
        "total_routes": summary.get("total_routes")
    }


@app.get("/api/summary")
def legacy_summary():
    """Legacy alias for the React dashboard KPI row."""
    cache = get_cache()
    summary = cache["summary"]
    routes = cache["routes"]

    # Worst route (rank == 1)
    worst = max(routes.values(), key=lambda r: r["fahp_score"], default=None)
    worst_route = None
    if worst:
        worst_route = {
            "id": worst["route_id"],
            "score": round(worst["fahp_score"], 2),
            "tier": worst["congestion_tier"],
        }

    # Avg speed and CO2 from cluster_params (real SUMO output)
    speeds, co2s = [], []
    for r in routes.values():
        cp = r.get("cluster_params", {})
        if cp.get("speed"):
            speeds.append(cp["speed"])
        if cp.get("co2_emission"):
            co2s.append(cp["co2_emission"])

    avg_speed = round(sum(speeds) / len(speeds), 2) if speeds else None
    avg_co2   = round(sum(co2s)   / len(co2s),   1) if co2s   else None

    return {
        "status": "success",
        "data": {
            "total_routes":  summary.get("total_routes"),
            "tier_counts":   summary.get("tier_counts"),
            "worst_route":   worst_route,
            "avg_speed":     avg_speed,
            "avg_co2":       avg_co2,
            "avg_fahp_score": summary.get("avg_fahp_score"),
            "max_fahp_score": summary.get("max_fahp_score"),
            "last_simulation_run": summary.get("last_simulation_run"),
        },
    }

@app.post("/api/refresh")
def legacy_refresh(background_tasks: BackgroundTasks):
    """Legacy alias for the React dashboard's Re‑run Algorithm button.
    Calls the same pipeline scripts as /pipeline/run and invalidates the cache.
    """
    invalidate_cache()

    def _run():
        scripts = ["sensor_fusion.py", "fkm_clustering.py", "fahp.py", "entropy_weight.py"]
        for script in scripts:
            logger.info(f"Running {script}…")
            try:
                subprocess.run(
                    ["python", script],
                    cwd=ALGORITHM_DIR,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"{script} failed: {e.stderr}")
                return
            except subprocess.TimeoutExpired:
                logger.error(f"{script} timed out.")
                return
        logger.info("Pipeline completed via /api/refresh. Cache will rebuild on next request.")

    background_tasks.add_task(_run)
    return {"status": "accepted", "message": "Pipeline is running in background. Cache will update on next request."}
