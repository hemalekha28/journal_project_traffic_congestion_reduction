# Smart Traffic Congestion Detection — First Review Build

Base paper: Mohanty et al., "Integrating Cognitive Intelligence and VANET for
Effective Traffic Congestion Detection in Smart Urban Mobility", IEEE Access 2025.

## Pipeline
SUMO simulation → sensor fusion → FKM clustering → FAHP scoring → Flask API → React dashboard

## Setup

### 1. SUMO
Install SUMO, set `SUMO_HOME`, then from `simulation/sumo_config/`:
```
netconvert --osm-files map.osm --output-file network.net.xml \
  --geometry.remove --roundabouts.guess --ramps.guess \
  --junctions.join --tls.guess-signals --tls.discard-simple --tls.join

python "%SUMO_HOME%/tools/randomTrips.py" -n network.net.xml -r routes.rou.xml -e 3600 -p 10
```

### 2. Generate data
```
cd simulation
python traci_runner.py
# OR, if SUMO isn't ready yet:
python generate_fallback_data.py
```

### 3. Run the algorithm
```
cd algorithm
python sensor_fusion.py
python fkm_clustering.py
python fahp.py
```

### 4. Run backend
```
cd backend
pip install flask flask-cors pandas
python main.py
```

### 5. Run dashboard
```
cd web-dashboard
npx create-react-app . --template minimal   # if not scaffolded yet
npm install leaflet react-leaflet axios
npm start
```

## Status
- [x] Sensor fusion — tested, working
- [x] FKM clustering — tested, working (route2 correctly flagged as congested)
- [x] FAHP scoring — tested, working
- [ ] SUMO real data (currently using fallback synthetic data for testing)
- [ ] Backend running
- [ ] Dashboard running
