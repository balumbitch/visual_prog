import json
import os

def create_map_from_json():
    
    json_files = [f for f in os.listdir('gps_logs') if f.endswith('.json')]
    if not json_files:
        print("No JSON files found in gps_logs/")
        return
    
    latest_file = max(json_files)
    json_path = os.path.join('gps_logs', latest_file)
    
    print(f"Using file: {latest_file}")
    
    # Читаем данные
    points = []
    rsrp_values = []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    
                    if 'location' in data:
                        lat = data['location']['latitude']
                        lon = data['location']['longitude']
                        rsrp = -100
                        if 'cell_info_lte' in data:
                            rsrp = data['cell_info_lte']['cell_signal_strength_lte'].get('rsrp', -100)
                    elif 'lat' in data and 'lon' in data:
                        lat = data['lat']
                        lon = data['lon']
                        rsrp = data.get('rsrp', -100)
                    else:
                        continue
                    
                    points.append([lat, lon])
                    rsrp_values.append(rsrp)
                    
                except:
                    continue
    
    if not points:
        print("No valid points found")
        return
    
    print(f"Found {len(points)} GPS points")
    
    points_js = []
    for i, (point, rsrp) in enumerate(zip(points, rsrp_values)):
        lat, lon = point
        
        # Цвет по RSRP
        if rsrp >= -80:
            color = '#00ff00'  # Зеленый
        elif rsrp >= -90:
            color = '#90ee90'  # Светло-зеленый
        elif rsrp >= -100:
            color = '#ffff00'  # Желтый
        elif rsrp >= -110:
            color = '#ffa500'  # Оранжевый
        else:
            color = '#ff0000'  # Красный
        
        points_js.append(f"""
            L.circleMarker([{lat}, {lon}], {{
                radius: 8,
                fillColor: '{color}',
                color: '#000',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.6
            }}).addTo(map).bindPopup(`
                Point {i+1}<br>
                Lat: {lat:.6f}<br>
                Lon: {lon:.6f}<br>
                RSRP: {rsrp} dBm
            `);
        """)
    
    points_js_str = '\n'.join(points_js)
    
    html = f'''
<html>
<head>
    <title>GPS Signal Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <style>
        #map {{ height: 600px; width: 100%; }}
        body {{ margin: 20px; font-family: Arial; }}
        .legend {{ display: flex; justify-content: center; margin: 10px 0; }}
        .legend-item {{ display: flex; align-items: center; margin: 0 10px; }}
        .legend-color {{ width: 20px; height: 20px; margin-right: 5px; border: 1px solid #666; }}
    </style>
</head>
<body>
    <h1>GPS Signal Strength ({len(points)} points)</h1>
    
    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background:#00ff00"></div>≥ -80 dBm</div>
        <div class="legend-item"><div class="legend-color" style="background:#90ee90"></div>-90 to -80</div>
        <div class="legend-item"><div class="legend-color" style="background:#ffff00"></div>-100 to -90</div>
        <div class="legend-item"><div class="legend-color" style="background:#ffa500"></div>-110 to -100</div>
        <div class="legend-item"><div class="legend-color" style="background:#ff0000"></div>< -110 dBm</div>
    </div>
    
    <div id="map"></div>
    
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([{points[0][0]}, {points[0][1]}], 13);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
        
        // Добавляем точки с цветами
        {points_js_str}
        
        // Автозум
        var bounds = L.latLngBounds({json.dumps(points)});
        map.fitBounds(bounds);
    </script>
</body>
</html>
'''
    
    with open('gps_map.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Map with colored points created: gps_map.html")

if __name__ == "__main__":
    create_map_from_json()