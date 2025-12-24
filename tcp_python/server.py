import socket
import json
import matplotlib.pyplot as plt
from datetime import datetime
import os
import threading
import psycopg2

HOST = '0.0.0.0'
PORT = 8080

lats, lons, rsrps = [], [], []
lock = threading.Lock()

def connect_db():
    try:
        return psycopg2.connect(
            dbname="mobile_tracking",
            user="postgres",
            password="new_password",
            host="localhost",
            port="5432"
        )
    except:
        return None

def save_json(data):
    try:
        os.makedirs('gps_logs', exist_ok=True)
        
        filename = f"gps_logs/gps_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        data['server_time'] = datetime.now().isoformat()
        
        with open(filename, "a", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")
        
        print(f"Saved to JSON: {filename}")
        return True
    except Exception as e:
        print(f"JSON error: {e}")
        return False

def save_db(data):
    try:
        conn = connect_db()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        loc = data['location']
        cur.execute("""
            INSERT INTO locations (latitude, longitude, altitude, timestamp, speed, accuracy)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (loc['latitude'], loc['longitude'], loc['altitude'], 
              loc['timestamp'], loc['speed'], loc['accuracy']))
        
        loc_id = cur.fetchone()[0]
        
        if 'cell_info_lte' in data:
            cell = data['cell_info_lte']
            cur.execute("""
                INSERT INTO cell_info_lte (location_id, mcc, mnc, rsrp, rsrq)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                loc_id,
                cell['cell_identity_lte'].get('mcc', 0),
                cell['cell_identity_lte'].get('mnc', 0),
                cell['cell_signal_strength_lte'].get('rsrp', 0),
                cell['cell_signal_strength_lte'].get('rsrq', 0)
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        print("Saved to DB")
        return True
    except Exception as e:
        print(f"DB error: {e}")
        return False

def add_to_plot(data):
    with lock:
        lat = data['location']['latitude']
        lon = data['location']['longitude']
        lats.append(lat)
        lons.append(lon)
        
        rsrp = -100
        if 'cell_info_lte' in data:
            rsrp = data['cell_info_lte']['cell_signal_strength_lte'].get('rsrp', -100)
        rsrps.append(rsrp)
        
        print(f"Point: ({lat:.6f}, {lon:.6f}), RSRP: {rsrp}")

def create_plot():
    with lock:
        if len(lats) < 1:
            print("No data for plot")
            return
        
        print(f"\nCreating plot with {len(lats)} points")
        
        plt.figure(figsize=(12, 9))
        
        colors = []
        for rsrp in rsrps:
            if rsrp >= -80:
                colors.append('#00ff00')
            elif rsrp >= -90:
                colors.append('#90ee90')
            elif rsrp >= -100:
                colors.append('#ffff00')
            elif rsrp >= -110:
                colors.append('#ffa500')
            else:
                colors.append('#ff0000')
        
        plt.scatter(lons, lats, c=colors, s=100, alpha=0.8, edgecolors='black', linewidth=0.5)
        
        plt.xlabel('Longitude', fontsize=12)
        plt.ylabel('Latitude', fontsize=12)
        plt.title(f'GPS Track with Signal Strength\nPoints: {len(lats)} | Time: {datetime.now().strftime("%H:%M:%S")}', fontsize=14)
        plt.grid(True, alpha=0.3)
        
        import matplotlib.patches as mpatches
        legend = [
            mpatches.Patch(color='#00ff00', label='Excellent (≥ -80 dBm)'),
            mpatches.Patch(color='#90ee90', label='Good (-90 to -80)'),
            mpatches.Patch(color='#ffff00', label='Fair (-100 to -90)'),
            mpatches.Patch(color='#ffa500', label='Poor (-110 to -100)'),
            mpatches.Patch(color='#ff0000', label='Very Poor (< -110)')
        ]
        plt.legend(handles=legend, loc='upper right')
        
        os.makedirs('plots', exist_ok=True)
        filename = f'plots/map_{datetime.now().strftime("%H%M%S")}.png'
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        plt.savefig('plots/current_map.png', dpi=120, bbox_inches='tight')
        plt.close()
        
        print(f"Plot saved: {filename}")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(5)

print("=" * 50)
print(f"GPS Tracking Server")
print(f"Host: {HOST}:{PORT}")
print(f"Saving: JSON + PostgreSQL")
print("=" * 50)
print("Waiting for connections...\n")

try:
    while True:
        client, addr = server.accept()
        print(f"\nClient connected: {addr}")
        
        client.settimeout(10)
        count = 0
        
        while True:
            try:
                data = client.recv(4096).decode().strip()
                if not data:
                    break
                
                count += 1
                
                try:
                    json_data = json.loads(data)
                    
                    if 'location' in json_data:
                        loc = json_data['location']
                        rsrp = None
                        if 'cell_info_lte' in json_data:
                            rsrp = json_data['cell_info_lte']['cell_signal_strength_lte'].get('rsrp')
                        
                        print(f"[{count}] Lat: {loc['latitude']:.6f}, Lon: {loc['longitude']:.6f}")
                        print(f"     RSRP: {rsrp} dBm | Speed: {loc['speed']:.1f} m/s")
                        
                        save_json(json_data) 
                        save_db(json_data)    
                        add_to_plot(json_data) 
                        
                        response = f"OK#{count}"
                    else:
                        response = "ERROR: No location"
                        
                except json.JSONDecodeError:
                    response = "ERROR: Bad JSON"
                
                client.send((response + "\n").encode())
                
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError):
                print(f"Connection closed by {addr}")
                break
            except Exception as e:
                print(f"Error: {e}")
                break
        
        client.close()
        print(f"Client disconnected: {addr} ({count} messages)")
        
        create_plot()

except KeyboardInterrupt:
    print("\n\nServer stopped by user")
finally:
    server.close()
    print("Server closed")