"""
<<<<<<< HEAD
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
=======
Traffic Congestion API
----------------------
This module serves as the backend for the Traffic Congestion Detection project.
It loads the Fuzzy Analytical Hierarchy Process (FAHP) results (which provide
a congestion score and HIGH/MEDIUM/LOW categorization) and raw Fuzzy K-Means (FKM)
clustering results from the underlying CSVs, serving them securely to the frontend dashboard.
>>>>>>> origin/feature/dashboard-api-fixes
"""

import os
import time
<<<<<<< HEAD
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
        # Primary_50 row is the main result
        variant_col = "Variant" if "Variant" in var_df.columns else "Run"
        p50 = var_df[var_df[variant_col] == "Primary_50"].iloc[0] if "Primary_50" in var_df[variant_col].values else None
        baseline = var_df[var_df[variant_col] == "Baseline"].iloc[0] if "Baseline" in var_df[variant_col].values else None

        if p50 is not None and baseline is not None:
            travel_time_imp = round(((baseline["Travel_Time_vehs"] - p50["Travel_Time_vehs"]) / baseline["Travel_Time_vehs"]) * 100, 2)
            co2_imp = round(((baseline["CO2_g"] - p50["CO2_g"]) / baseline["CO2_g"]) * 100, 2)
            fuel_imp = round(((baseline["Fuel_L"] - p50["Fuel_L"]) / baseline["Fuel_L"]) * 100, 2)

            rerouting_routes["!257"] = {
                "available": True,
                "recommended_variant": "Primary_50",
                "travel_time_improvement_pct": travel_time_imp,
                "co2_fuel_improvement_pct": co2_imp,
                "fuel_improvement_pct": fuel_imp,
                "description": "Reroute 50% of heavy-overlap fleet (≥30% edge overlap, 8 of 16 vehicles) around bottleneck edges 1203439472 and 1208491992.",
                "bottleneck_edges": ["1203439472#0", "1203439472#1", "1208491992#0", "1208491992#1"],
                "expected_improvement": {
                    "travel_time_pct": travel_time_imp,
                    "co2_pct": co2_imp,
                    "fuel_pct": fuel_imp,
                    "fahp_score_pct": round(rerout[rerout["Variant"] == "Primary_50"]["FAHP_Improv_%"].values[0], 2) if "Primary_50" in rerout["Variant"].values else None,
                    "entropy_score_pct": round(rerout[rerout["Variant"] == "Primary_50"]["Entropy_Improv_%"].values[0], 2) if "Primary_50" in rerout["Variant"].values else None,
                },
                "sensitivity": rerout.set_index("Variant").to_dict(orient="index"),
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

        # Geometry: two points forming a short polyline radiating from center
        angle = (2 * math.pi * i) / n + random.uniform(-0.05, 0.05)
        length = 0.005 + random.uniform(0, 0.008)          # ~0.5–1.3 km
        end_lat = CENTER_LAT + length * math.cos(angle)
        end_lon = CENTER_LON + length * math.sin(angle)
        geometry = [[CENTER_LAT, CENTER_LON], [round(end_lat, 6), round(end_lon, 6)]]

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
            **topsis_data,
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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
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
    """
    Returns all 359 routes. Optionally filter by ?tier=HIGH|MEDIUM|LOW.
    Each route includes: fahp_score, fahp_rank, congestion_tier,
    cluster_params, entropy/topsis data, and geometry.
    """
    cache = get_cache()
    routes = cache["routes"]
    if tier:
        tier_upper = tier.upper()
        routes = {k: v for k, v in routes.items() if v["congestion_tier"] == tier_upper}
    return {"count": len(routes), "routes": routes}


@app.get("/routes/congested", summary="Top congested routes, worst-first")
def congested_routes(threshold: str = "HIGH", limit: int = 10):
    """
    Returns routes at or above the threshold tier, sorted worst-first.
    threshold: HIGH (default) | MEDIUM | LOW
    limit: number of routes to return (default 10)
    """
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
    """
    Returns complete data for a single route:
    FAHP score, Entropy score, all TOPSIS ranks, cluster parameters,
    geometry, and rerouting availability.
    """
    cache = get_cache()
    # Accept both '257' and '!257'
    key = route_id if route_id.startswith("!") else f"!{route_id}"
    if key not in cache["routes"]:
        raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found.")
    return cache["routes"][key]


@app.get("/routes/{route_id}/reroute-suggestion", summary="Rerouting suggestion for a route")
def reroute_suggestion(route_id: str):
    """
    Returns rerouting experiment results if available for this route.
    Currently only Route !257 has real rerouting data.
    """
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
    """
    Returns: total routes, count per congestion tier, avg/min/max FAHP score,
    last simulation timestamp, and cache metadata.
    """
    return get_cache()["summary"]


@app.post("/pipeline/run", summary="Re-run the algorithm pipeline")
def run_pipeline(background_tasks: BackgroundTasks):
    """
    Triggers a fresh pipeline run (sensor_fusion → fkm_clustering → fahp → entropy).
    Runs asynchronously; invalidates the cache immediately so the next GET
    will block until the new CSVs are written.
    Returns immediately with a 202 Accepted.
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
            "cluster_co2": r_info.get("cluster_co2")
        }
    return {"status": "success", "data": data}




@app.get("/api/history")
def legacy_history():
    cache = get_cache()
    summary = cache["summary"]
    # Simple history mock structure for dashboard trends
    history_data = {
        "timestamp": summary.get("last_updated"),
        "total_routes": summary.get("total_routes"),
        "high_congestion_count": summary.get("high_count"),
        "medium_congestion_count": summary.get("medium_count"),
        "low_congestion_count": summary.get("low_count"),
    }
    return {"status": "success", "data": history_data}


@app.get("/api/status")
def legacy_status():
    cache = get_cache()
    summary = cache["summary"]
    return {
        "status": "online",
        "last_updated": summary.get("last_updated"),
        "pipeline": "FastAPI pre-computed CSV backend",
        "total_routes": summary.get("total_routes")
    }

=======
import logging
import subprocess
import pandas as pd
from flask import Flask, jsonify, abort, request
from flask_cors import CORS

# 1. Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 2. App & CORS Setup
app = Flask(__name__)
# Allow both Vite default port and configured port
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
]}})

# 3. Request Logging Hook
@app.before_request
def log_request_info():
    logger.info(f"Received {request.method} request to {request.url}")

# 4. Global Error Handlers
@app.errorhandler(404)
def resource_not_found(e):
    logger.warning(f"404 Not Found: {e}")
    return jsonify(error=str(e)), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 Internal Error: {e}")
    return jsonify(error=str(e)), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    return jsonify(error="An unexpected error occurred processing your request."), 500

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def resolve_path(filepath):
    """Resolve a relative path against the backend script directory."""
    if not os.path.isabs(filepath):
        return os.path.abspath(os.path.join(BASE_DIR, filepath))
    return filepath

# 5. Data Loading Helper
def load_csv_data(filepath, orient='index'):
    """
    Safely load a CSV file into a dictionary.
    Raises standardized HTTP errors on failure.
    """
    try:
        abs_path = resolve_path(filepath)
        if not os.path.exists(abs_path):
            logger.error(f"Data file not found at path: {abs_path}")
            abort(404, description=f"Data file not found at {abs_path}. Ensure the algorithm pipeline has been run.")

        df = pd.read_csv(abs_path, index_col=0)

        if df.empty:
            logger.error(f"Data file is empty: {filepath}")
            abort(500, description="Data file exists but is empty.")

        return df.to_dict(orient=orient)

    except pd.errors.EmptyDataError:
        logger.error(f"Pandas EmptyDataError on file: {filepath}")
        abort(500, description="Data file is corrupted or improperly formatted.")
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        abort(500, description="Internal error while loading data.")

# 6. Routes

@app.route('/api/congestion', methods=['GET'])
def get_congestion():
    """Returns ranked congestion results per route with Hybrid FAHP-EWM rerouting."""
    data = load_csv_data('../algorithm/congestion_results.csv')
    
    try:
        cluster_data = load_csv_data('../algorithm/cluster_results.csv')
        
        # 1. Load FAHP and EWM weights
        import sys
        alg_dir = resolve_path('../algorithm')
        if alg_dir not in sys.path:
            sys.path.append(alg_dir)
        from fahp import FAHP_WEIGHTS
        
        ewm_weights = {}
        ewm_path = resolve_path('../algorithm/entropy_weights.csv')
        if os.path.exists(ewm_path):
            ewm_df = pd.read_csv(ewm_path)
            ewm_weights = dict(zip(ewm_df['parameter'], ewm_df['weight']))
            
        # 2. Calculate Hybrid Weights W_hybrid = W_fahp * W_ewm
        hybrid_weights = {}
        for param in FAHP_WEIGHTS:
            if param in ewm_weights:
                hybrid_weights[param] = FAHP_WEIGHTS[param] * ewm_weights[param]
                
        # Normalize
        total_weight = sum(hybrid_weights.values())
        if total_weight > 0:
            for param in hybrid_weights:
                hybrid_weights[param] /= total_weight
                
        # 3. Calculate Hybrid Score for each route
        hybrid_scores = {}
        for route_id, row in cluster_data.items():
            score = sum(row.get(param, 0) * weight for param, weight in hybrid_weights.items())
            hybrid_scores[route_id] = round(score, 4)
            if route_id in data:
                data[route_id]['hybrid_score'] = hybrid_scores[route_id]
                
        # 4. Find alternate route for HIGH congestion routes
        if hybrid_scores:
            best_route_id = min(hybrid_scores, key=hybrid_scores.get)
            for route_id, route_info in data.items():
                if route_info.get('status') == 'HIGH':
                    if route_id != best_route_id:
                        route_info['alternate_route'] = best_route_id
                        route_info['alternate_reason'] = "Lowest Hybrid Score (FAHP + EWM)"
                    else:
                        sorted_routes = sorted(hybrid_scores, key=hybrid_scores.get)
                        if len(sorted_routes) > 1:
                            route_info['alternate_route'] = sorted_routes[1]
                            route_info['alternate_reason'] = "Lowest Hybrid Score (FAHP + EWM)"
    except Exception as e:
        logger.error(f"Error computing hybrid scores: {e}", exc_info=True)

    return jsonify({"status": "success", "data": data})

@app.route('/api/congestion/<route_id>', methods=['GET'])
def get_route_congestion(route_id):
    """Returns congestion detail for a single route."""
    data = load_csv_data('../algorithm/congestion_results.csv')

    if route_id not in data:
        logger.warning(f"Requested route_id '{route_id}' not found in data.")
        abort(404, description=f"Route ID '{route_id}' not found.")

    return jsonify({"status": "success", "route_id": route_id, "data": data[route_id]})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Returns the raw cluster results data (underlying parameter values)."""
    data = load_csv_data('../algorithm/cluster_results.csv')
    return jsonify({"status": "success", "data": data})

@app.route('/api/emissions', methods=['GET'])
def get_emissions():
    """Returns detailed emissions breakdown per route from cluster results."""
    data = load_csv_data('../algorithm/cluster_results.csv')
    # Enrich with congestion status
    try:
        cong = load_csv_data('../algorithm/congestion_results.csv')
        for route_id in data:
            if route_id in cong:
                data[route_id]['status'] = cong[route_id].get('status', 'UNKNOWN')
                data[route_id]['congestion_score'] = cong[route_id].get('congestion_score', 0)
    except Exception:
        pass
    return jsonify({"status": "success", "data": data})

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Returns aggregate statistics across all monitored routes."""
    try:
        congestion_path = resolve_path('../algorithm/congestion_results.csv')
        cluster_path = resolve_path('../algorithm/cluster_results.csv')

        if not os.path.exists(congestion_path) or not os.path.exists(cluster_path):
            abort(404, description="Data files not found. Run the algorithm pipeline first.")

        cong_df = pd.read_csv(congestion_path, index_col=0)
        clust_df = pd.read_csv(cluster_path, index_col=0)

        routes = cong_df.index.tolist()
        scores = cong_df['congestion_score'].tolist()

        worst_idx = cong_df['congestion_score'].idxmax()
        best_idx = cong_df['congestion_score'].idxmin()

        avg_speed = round(float(clust_df['speed'].mean()), 2) if 'speed' in clust_df.columns else None
        avg_co2 = round(float(clust_df['co2_emission'].mean()), 1) if 'co2_emission' in clust_df.columns else None
        avg_co = round(float(clust_df['co_emission'].mean()), 2) if 'co_emission' in clust_df.columns else None
        avg_nox = round(float(clust_df['nox_emission'].mean()), 3) if 'nox_emission' in clust_df.columns else None
        avg_fuel = round(float(clust_df['fuel_consumption'].mean()), 3) if 'fuel_consumption' in clust_df.columns else None

        status_counts = cong_df['status'].value_counts().to_dict() if 'status' in cong_df.columns else {}

        return jsonify({
            "status": "success",
            "data": {
                "total_routes": len(routes),
                "worst_route": {
                    "id": worst_idx,
                    "score": round(float(cong_df.loc[worst_idx, 'congestion_score']), 2),
                    "status": cong_df.loc[worst_idx, 'status'] if 'status' in cong_df.columns else 'UNKNOWN'
                },
                "best_route": {
                    "id": best_idx,
                    "score": round(float(cong_df.loc[best_idx, 'congestion_score']), 2),
                    "status": cong_df.loc[best_idx, 'status'] if 'status' in cong_df.columns else 'UNKNOWN'
                },
                "avg_score": round(float(sum(scores) / len(scores)), 2),
                "avg_speed": avg_speed,
                "avg_co2": avg_co2,
                "avg_co": avg_co,
                "avg_nox": avg_nox,
                "avg_fuel": avg_fuel,
                "high_count": int(status_counts.get('HIGH', 0)),
                "medium_count": int(status_counts.get('MEDIUM', 0)),
                "low_count": int(status_counts.get('LOW', 0)),
            }
        })
    except Exception as e:
        logger.error(f"Error computing summary: {e}", exc_info=True)
        abort(500, description="Error computing summary statistics.")

@app.route('/api/real-data', methods=['GET'])
def get_real_data():
    """Returns top-N results from the real data congestion pipeline."""
    limit = request.args.get('limit', 20, type=int)
    try:
        filepath = resolve_path('../algorithm/congestion_results_real_data.csv')
        if not os.path.exists(filepath):
            abort(404, description="Real data file not found.")

        df = pd.read_csv(filepath, index_col=0)
        df_top = df.head(limit)

        return jsonify({
            "status": "success",
            "total": len(df),
            "returned": len(df_top),
            "data": df_top.to_dict(orient='index')
        })
    except Exception as e:
        logger.error(f"Error loading real data: {e}", exc_info=True)
        abort(500, description="Error loading real dataset.")

@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint showing data freshness and server timestamp."""
    congestion_path = resolve_path('../algorithm/congestion_results.csv')

    data_timestamp = None
    if os.path.exists(congestion_path):
        data_timestamp = os.path.getmtime(congestion_path)
        data_freshness = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data_timestamp))
    else:
        data_freshness = "Data file missing"

    return jsonify({
        "status": "running",
        "server_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        "data_last_updated": data_freshness
    })

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Re-runs the algorithm pipeline via subprocess and returns before/after diff."""
    congestion_path = '../algorithm/congestion_results.csv'

    # 1. Capture before state
    before_data = {}
    if os.path.exists(congestion_path):
        try:
            df_before = pd.read_csv(congestion_path, index_col=0)
            before_data = df_before.to_dict(orient='index')
        except Exception:
            pass  # File might be missing or corrupt, treat as empty

    # 2. Run subprocesses
    scripts_to_run = [
        "sensor_fusion.py",
        "fkm_clustering.py",
        "fahp.py"
    ]

    alg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'algorithm'))

    for script in scripts_to_run:
        logger.info(f"Running script: {script}")
        try:
            result = subprocess.run(
                ["python", script],
                cwd=alg_dir,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"{script} output:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run {script}. Error:\n{e.stderr}")
            abort(500, description=f"Algorithm pipeline failed at {script}.")
        except FileNotFoundError:
            logger.error(f"Python executable not found or script {script} missing.")
            abort(500, description=f"Execution environment error while running {script}.")

    # 3. Capture after state
    after_data = load_csv_data(congestion_path)

    # 4. Generate diff report
    diff = {}
    for route_id, after_info in after_data.items():
        before_info = before_data.get(route_id, {})
        diff[route_id] = {
            "before_score": before_info.get("congestion_score", None),
            "after_score": after_info.get("congestion_score"),
            "before_status": before_info.get("status", "UNKNOWN"),
            "after_status": after_info.get("status")
        }

    return jsonify({
        "status": "success",
        "message": "Algorithm pipeline completed successfully.",
        "diff": diff,
        "new_data": after_data
    })

if __name__ == '__main__':
    logger.info("Starting Traffic Congestion Backend API...")
    app.run(debug=False, port=5000)
>>>>>>> origin/feature/dashboard-api-fixes
