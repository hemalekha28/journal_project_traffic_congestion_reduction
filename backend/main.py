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
# Restrict CORS to explicitly allow localhost:3000
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

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

# 5. Data Loading Helper
def load_csv_data(filepath, orient='index'):
    """
    Safely load a CSV file into a dictionary.
    Raises standardized HTTP errors on failure.
    """
    try:
        if not os.path.exists(filepath):
            logger.error(f"Data file not found at path: {filepath}")
            abort(404, description="Data file not found. Ensure the algorithm pipeline has been run.")
            
        df = pd.read_csv(filepath, index_col=0)
        
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
    """Returns ranked congestion results per route."""
    data = load_csv_data('../algorithm/congestion_results.csv')
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

@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint showing data freshness and server timestamp."""
    congestion_path = '../algorithm/congestion_results.csv'
    
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
            pass # File might be missing or corrupt, treat as empty

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
