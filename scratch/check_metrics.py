import urllib.request
import json
import os

try:
    hist = json.loads(urllib.request.urlopen('http://localhost:5000/api/history').read())['data']
    summ = json.loads(urllib.request.urlopen('http://localhost:5000/api/summary').read())['data']
    for route in ['!288', '!336', '!314']:
        print('Route: ' + route)
        h = hist.get(route)
        speed = h.get('speed')
        co2 = h.get('co2_emission')
        fuel = h.get('fuel_consumption')
        print(f'  Speed: {speed:.1f} vs Avg: {summ.get("avg_speed",0):.1f}')
        print(f'  CO2: {co2:.0f} vs Avg: {summ.get("avg_co2",0):.0f}')
        print(f'  Fuel: {fuel:.1f}')
except Exception as e:
    print(e)
