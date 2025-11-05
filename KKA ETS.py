

import json
from shapely.geometry import shape, mapping
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import random
import heapq
import math
import heapq
import numpy as np
import networkx as nx
from collections import deque


geojson = {"type":"Feature","geometry":{"coordinates":[[[112.744353,-7.277027],[112.744224,-7.274006],[112.74667,-7.2709],[112.750403,-7.267709],[112.751261,-7.26571],[112.751827,-7.262948],[112.758211,-7.264859],[112.767049,-7.265454],[112.771211,-7.266688],[112.775029,-7.267837],[112.77277,-7.281252],[112.744353,-7.277027]]],"type":"Polygon"},"properties":{},"id":"yb7By"}
geojson = {"type":"Feature","geometry":{"coordinates":[[[112.747286,-7.288063],[112.748487,-7.283211],[112.744353,-7.277027],[112.744224,-7.274006],[112.74667,-7.2709],[112.750403,-7.267709],[112.751261,-7.26571],[112.751827,-7.262948],[112.758211,-7.264859],[112.767049,-7.265454],[112.771211,-7.266688],[112.803747,-7.265502],[112.802459,-7.291208],[112.747286,-7.288063]]],"type":"Polygon"},"properties":{},"id":"yb7By"}
poly = shape(geojson['geometry'])


korban_lat = -7.269072449827058
korban_long = 112.76079654693605

korban_lat = -7.279070
korban_long = 112.790351



G = ox.graph_from_polygon(poly, network_type='drive')

gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

# print(gdf_edges['highway'].explode().unique())

# Pastikan kolom highway adalah list → ubah menjadi string tipe pertama
def get_hw_type(hw):
    if isinstance(hw, list):
        return hw[0]
    return hw

# remove tipe highway dari bad_types yang merupakan jalan kampung
bad_types = {'living_street', 'residential'}
mask = gdf_edges['highway'].apply(lambda x: any(ht in bad_types for ht in (x if isinstance(x,list) else [x])))
edges_to_drop = gdf_edges[mask]
# drop dari graph

for u,v,k in edges_to_drop.index:
    if G.has_edge(u,v,key=k):
        G.remove_edge(u,v,key=k)




hospital_gds = ox.features_from_polygon(poly, tags={'amenity':'hospital'})
# filter rumah sakit (sementara hanya menggunakan RSUD dan RS Siloam)
# hospitals = hospital_gds[hospital_gds['name'].isin(['RSUD Dr. Soetomo', 'Siloam Hospitals'])].loc[:, ['name', 'geometry']]
hospitals = hospital_gds.loc[:, ['name', 'geometry']]
# hospitals = hospital_gds
hospitals['centroid'] = hospitals['geometry'].centroid
hospitals_points = hospitals[['name', 'centroid']]
hospitals_points["x"] = hospitals_points["centroid"].x
hospitals_points["y"] = hospitals_points["centroid"].y


hospitals_points['load_percentage'] = 100
# hospitals_points['load_percentage'][1] = 20
hospitals_points['wait_time'] = (hospitals_points['load_percentage'] / 100) * 1000


for idx, row in hospitals_points.iterrows():
    nearest_node = ox.nearest_nodes(G, row['x'], row['y'])

    G.add_node(idx[1], x=row['x'], y=row['y'], load_percentage=row['load_percentage'], wait_time=row['wait_time'])

    G.add_edge(idx[1], nearest_node, length=0)
    G.add_edge(nearest_node, idx[1], length=0)

# ox.plot_graph(G, node_size=5, node_color="red")


idx_hospitals = hospitals.reset_index(drop=False)['id']
#idx_hospitals.values


# assigning random traffic value and 
for u, v, k, data in G.edges(keys=True, data=True):

  if u in idx_hospitals.values or v in idx_hospitals.values:
    data['speed_limit'] = 100
  else:
    data['speed_limit'] = random.choice([100,60,40,20,10,5,1])
  data['cost'] = (data['length']) / (data['speed_limit'] * 1000 / 3600)

  if "load_percentage" in G.nodes[v]:
    print(v)
    # load =  (G.nodes[v]['load_percentage'] / 100)
    const_increaser = 1000
    load =  (G.nodes[v]['load_percentage'] / 100) * const_increaser
    # G.nodes[v]['wait_time'] = load 
    data['cost'] = load # karena length rs ke node terdekat 0

  # print(u, v, k, data)


def generate_node_korban(lat, long):
  nearest_node = ox.nearest_nodes(G, long, lat)
  korban_node = random.randint(1000, 9999)
  G.add_node(korban_node, x=long, y=lat)
  G.add_edge(nearest_node, korban_node, length=0)
  G.add_edge(korban_node, nearest_node, length=0)
  return korban_node



korban_node = generate_node_korban(korban_lat, korban_long)


# for u, v, k, data in G.edges(keys=True, data=True):

#   print(u, v, k, data)



hospitals_data = hospitals.reset_index(drop=False)





rs_node = hospitals_data['id'].values

def ucs(G, start, goal):
    pq = [(0, start, [start])]
    visited = {}

    while pq:
        cost_so_far, current, path = heapq.heappop(pq)

        if current == goal:
            return path, cost_so_far

        if current in visited and visited[current] <= cost_so_far:
            continue

        visited[current] = cost_so_far

        for neighbor in G.neighbors(current):
            edge_cost = G[current][neighbor].get("cost", 1)
            new_cost = cost_so_far + edge_cost
            heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))

    return None, float("inf")


def dijkstra_search(G, start, goal):
    path = nx.dijkstra_path(G, start, goal, weight="cost")
    cost = nx.dijkstra_path_length(G, start, goal, weight="cost")
    return path, cost

def astar_func(G, start, goal, heuristic):
    pq = [(0, 0, start, [start])]
    visited = {}

    while pq:
        est_total, cost_so_far, current, path = heapq.heappop(pq)

        if current == goal:
            return path, cost_so_far

        if current in visited and visited[current] <= cost_so_far:
            continue

        visited[current] = cost_so_far

        for neighbor in G.neighbors(current):
            data = G[current][neighbor]
            edge_cost = data.get("cost", 1)

            new_cost = cost_so_far + edge_cost
            est = new_cost + heuristic(neighbor, goal)

            heapq.heappush(pq, (est, new_cost, neighbor, path + [neighbor]))

    return None, float("inf")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

def build_avg_speed(G):
    speeds = []
    for u, v, data in G.edges(data=True):
        if 'speed_limit' in data:
            speeds.append(data['speed_limit'] * 1000 / 3600)  # km/h → m/s
    return np.mean(speeds)

def make_heuristic(G):
    avg_speed = build_avg_speed(G)
    def heuristic(n, goal):
        x1, y1 = G.nodes[n]['x'], G.nodes[n]['y']
        x2, y2 = G.nodes[goal]['x'], G.nodes[goal]['y']
        dist = haversine(y1, x1, y2, x2)
        return dist / avg_speed
    return heuristic

heur = make_heuristic(G)


algos = ["A*", "UCS", "Dijkstra"]

algo_costs = dict()

# -------------------------------- MAIN - MAIN ------------------------------- #

# get the nearest hospital from accident_point for the ambulance source

ambulance_source_hospital_id = -1
haversine_ambulance_source = float('inf')

for col,row in hospitals_points.iterrows():
    haversine_per_hospital = haversine(row[1].x,row[1].y, korban_long,korban_lat)
    if haversine_per_hospital < haversine_ambulance_source:
        haversine_ambulance_source = haversine_per_hospital
        ambulance_source_hospital_id = col[1]

    # print(col[1])
    # print(row[0])
    # print(haversine(row[1].x,row[1].y, korban_long,korban_lat))


for algo in algos:
    best_cost = float('inf')
    best_route = None
    best_hospital = None

    print(f"Algorithm: {algo}")
    algo_costs[algo] = {}
    for rs in rs_node:
        if algo == "A*":
          route_to_accident, cost_to_accident = astar_func(G, ambulance_source_hospital_id, korban_node, heuristic=heur)
          route_to_hospital, cost_to_hospital = astar_func(G, korban_node, rs, heuristic=heur)
          total_cost = cost_to_accident + cost_to_hospital + G.nodes[rs]['wait_time']

        elif algo == "UCS":
          route_to_accident, cost_to_accident = ucs(G, ambulance_source_hospital_id, korban_node)
          route_to_hospital, cost_to_hospital = ucs(G, korban_node, rs)
          total_cost = cost_to_accident + cost_to_hospital + G.nodes[rs]['wait_time']

        elif algo == "Dijkstra":
          route_to_accident, cost_to_accident = dijkstra_search(G, ambulance_source_hospital_id, korban_node)
          route_to_hospital, cost_to_hospital = dijkstra_search(G, korban_node, rs)
          total_cost = cost_to_accident + cost_to_hospital + G.nodes[rs]['wait_time']

    
        print(f"RS {hospitals_data[hospitals_data['id'] == rs]['name'].values[0]}: total waktu tempuh = {total_cost:.2f} detik")

        if total_cost < best_cost:
            best_cost = total_cost
            best_hospital = rs
            best_route = route_to_accident + route_to_hospital[1:]

    print("=== HASIL ===")
    print(f"Asal ambulans        → {hospitals_data[hospitals_data['id'] == ambulance_source_hospital_id]['name'].values[0]}")
    print(f"Rumah Sakit terbaik  → {hospitals_data[hospitals_data['id'] == best_hospital]['name'].values[0]}")
    print(f"Total waktu tempuh   → {best_cost:.2f} detik")
    print(f"Total node dilalui   → {len(best_route)}")
    print(f"Total cost ke tujuan → {total_cost}")
    print("="*60)
    algo_costs[algo]['cost'] = best_cost
    algo_costs[algo]['route'] = best_route
    algo_costs[algo]['hospital'] = hospitals_data[hospitals_data['id'] == best_hospital]['name'].values[0]

sorted_cost_algos =  sorted(algo_costs.items(), key=lambda x: x[1]['cost'])
print(f"Best Algorithm: {sorted_cost_algos[0][0]}")
print(f"Best Cost: {sorted_cost_algos[0][1]['cost']}")
print(f"Best Hospital: {sorted_cost_algos[0][1]['hospital']}")
best_route = sorted_cost_algos[0][1]['route']






import folium
route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in best_route]
route_to_accident_show = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_to_accident]
route_to_hospital_show = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_to_hospital]

center_lat = G.nodes[korban_node]['y']
center_lon = G.nodes[korban_node]['x']

m = folium.Map(location=[center_lat, center_lon], zoom_start=15)

folium.Marker(
    location=[G.nodes[korban_node]['y'], G.nodes[korban_node]['x']],
    popup="Lokasi Korban",
    icon=folium.Icon(color='red', icon='plus')
).add_to(m)

folium.Marker(
    location=[G.nodes[ambulance_source_hospital_id]['y'], G.nodes[ambulance_source_hospital_id]['x']],
    popup=f"Asal Ambulans (Cost: {best_cost:.2f})",
    icon=folium.Icon(color='blue', icon='hospital')
).add_to(m)

folium.Marker(
    location=[G.nodes[best_hospital]['y'], G.nodes[best_hospital]['x']],
    popup=f"Rumah Sakit Terpilih (Cost: {best_cost:.2f})",
    icon=folium.Icon(color='blue', icon='hospital')
).add_to(m)

folium.PolyLine(route_coords, weight=6, color='green', opacity=0.5).add_to(m)
folium.PolyLine(route_to_accident_show, weight=4, color='red', opacity=0.3).add_to(m)
folium.PolyLine(route_to_hospital_show, weight=4, color='blue', opacity=0.3).add_to(m)




from flask import Flask

app = Flask(__name__)

@app.route("/")
def show_map():
    return m.get_root().render()


app.run(use_reloader=False, debug=True)


