"""
Traffic Congestion API
----------------------
This module serves as the backend for the Traffic Congestion Detection project.
It loads the Fuzzy Analytical Hierarchy Process (FAHP) results (which provide
a congestion score and HIGH/MEDIUM/LOW categorization) and raw Fuzzy K-Means (FKM)
clustering results from the underlying CSVs, serving them securely to the frontend dashboard.
"""

import os
import time
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
