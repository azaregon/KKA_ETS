from flask import Flask, jsonify
import flask
import osmnx as ox
import pickle

app = Flask(__name__)

# Pastikan G sudah dibuat sebelumnya
# G = ox.graph_from_polygon(...)
with open('map_data.pkl', 'rb') as file:
    G = pickle.load(file)


@app.get("/api/bounds")
def get_bounds():
    nodes = ox.graph_to_gdfs(G, edges=False)
    north = nodes['y'].max()
    south = nodes['y'].min()
    east = nodes['x'].max()
    west = nodes['x'].min()
    return jsonify({
        "north": north,
        "south": south,
        "east": east,
        "west": west
    })


@app.get("/api/hospitals")
def get_hospitals():
    # Pastikan kamu punya hospitals_points DataFrame
    data = []
    for _, row in hospitals_points.iterrows():
        data.append({
            "id": row['id'],
            "name": row['name'],
            "lat": row['y'],
            "lon": row['x'],
            "load_index": row['load_percentage']
        })
    return jsonify(data)

@app.route('/')
def index():
    return flask.send_file('templates/index.html')



app.run()