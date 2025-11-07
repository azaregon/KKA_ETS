
import json
from shapely.geometry import shape, mapping
import geopandas as gpd
import osmnx as ox
import matplotlib.pyplot as plt
import random
import pickle
import pandas as pd
from collections import deque
import networkx as nx
import numpy as np
import math
import heapq
import folium

from flask import Flask
from flask import request, abort
import flask
import dbmodel
from branca.element import Element

def load_graph(geojson):
    poly = shape(geojson['geometry'])
    G = ox.graph_from_polygon(poly, network_type='drive')
    return G, poly

def get_hw_type(hw):
    if isinstance(hw, list):
        return hw[0]
    return hw

def save_graph(G, name_file):
    map_graph_file_path = name_file
    with open(map_graph_file_path, "wb") as file:
        pickle.dump(G, file)
    print(f"Variable saved to {map_graph_file_path}")

def get_hospital_data(poly,use_all=False, choose_hospital=[]):
    hospital_gds = ox.features_from_polygon(poly, tags={'amenity':'hospital'})

    if use_all :
        hospitals = hospital_gds.loc[:, ['name', 'geometry']]
    else :
        hospitals = hospital_gds[hospital_gds['name'].isin(choose_hospital)].loc[:, ['name', 'geometry']]

    hospitals['x'] = hospitals['geometry'].centroid.x
    hospitals['y'] = hospitals['geometry'].centroid.y

    return hospitals

def load_wait_time(hospitals):
    hospitals['load_percentage'] = 100
    # hospitals['load_percentage'][3] = 10
    # hospitals['load_percentage'][4] = 15
    hospitals['wait_time'] = (hospitals['load_percentage'] / 100) * 500
    return hospitals

def add_hospitals_to_graph(G, hospitals):
    hospitals_points = hospitals[['x', 'y', 'load_percentage']].copy()
    for idx, row in hospitals_points.iterrows():
        nearest_node = ox.nearest_nodes(G, row['x'], row['y'])

        G.add_node(idx[1], x=row['x'], y=row['y'], load_percentage=row['load_percentage'])

        G.add_edge(idx[1], nearest_node, length=0)
        G.add_edge(nearest_node, idx[1], length=0)
    return G, hospitals_points


def plot_graph_with_hospitals(G, hospitals):
    fig, ax = ox.plot_graph(G, node_size=0, edge_color="gray", show=False, close=False)

    hospital_x = hospitals['x'].values
    hospital_y = hospitals['y'].values

    ax.scatter(hospital_x, hospital_y, c='red', s=80, label='Rumah Sakit', zorder=5)
    ax.legend()
    plt.show()

def generate_cost_edges(G, hospitals):

    idx_hospitals = hospitals.reset_index(drop=False)['id']

    for u, v, k, data in G.edges(keys=True, data=True):

        if u in idx_hospitals.values or v in idx_hospitals.values:
            data['speed_limit'] = 100
        else:
            data['speed_limit'] = 100#random.choice([100,60,40,20,10,5,1])
        data['cost'] = (data['length']) / (data['speed_limit'] * 1000 / 3600)

        if "load_percentage" in G.nodes[v]:
            print(v)
            load =  (G.nodes[v]['load_percentage'] / 100)
            const_increaser = 1000
            load =  (G.nodes[v]['load_percentage'] / 100) * const_increaser
            G.nodes[v]['wait_time'] = load 
            data['cost'] = load # karena length rs ke node terdekat 0

    return G

def generate_node_korban(G, lat, long):
    nearest_node = ox.nearest_nodes(G, long, lat)
    korban_node = random.randint(1000, 9999)
    G.add_node(korban_node, x=long, y=lat)
    G.add_edge(nearest_node, korban_node, length=0)
    G.add_edge(korban_node, nearest_node, length=0)
    return korban_node

def save_hospital_data(hospitals, filename):
    hospitals_data = hospitals.reset_index(drop=False)
    hospitals_data = hospitals_data.rename(columns={'id': 'ID'})
    hospitals_data = hospitals_data[['ID', 'name', 'x', 'y', 'load_percentage', 'wait_time']]
    hospitals_data.to_json(filename, orient='records', indent=4)
    print(f"Hospital data saved to {filename}")

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

# -------------------------------- MAIN - MAIN ------------------------------- #
def findRoute(G, hospitals_data, rs_node, korban_node, korban_lat, korban_long):

    algos = ["A*", "UCS", "Dijkstra"]
    algo_costs = dict()

    heur = make_heuristic(G)

    ambulance_source_hospital_id = -1
    haversine_ambulance_source = float('inf')

    for idx,row in hospitals_data.iterrows():
        # print(ambulance_source_hospital_id)
        haversine_per_hospital = haversine(row['y'], row['x'], korban_lat, korban_long)
        print(f"Haversine from hospital {row['name']} to korban: {haversine_per_hospital:.2f} meters")
        if haversine_per_hospital < haversine_ambulance_source:
            haversine_ambulance_source = haversine_per_hospital
            ambulance_source_hospital_id = idx

    best_cost = float('inf')
    best_route = None
    best_hospital = None
    best_route_to_accident = None
    best_route_to_hospital = None
    for algo in algos:

        print(f"Algorithm: {algo}")
        algo_costs[algo] = {}
        for rs in rs_node:
            # print(G.nodes[rs]['wait_time'])
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

        
            print(f"RS {hospitals_data[hospitals_data.index == rs]['name'].values[0]}: total waktu tempuh = {total_cost:.2f} detik")

            if total_cost < best_cost:
                best_cost = total_cost
                best_hospital = rs
                best_route_to_accident = route_to_accident
                best_route_to_hospital = route_to_hospital[1:]
                best_route = route_to_accident + route_to_hospital[1:]

        algo_costs[algo]['cost'] = best_cost
        algo_costs[algo]['route'] = best_route
        algo_costs[algo]['route_to_hospital'] = best_route_to_hospital
        algo_costs[algo]['route_to_accident'] = best_route_to_accident
        algo_costs[algo]['hospital_id'] = hospitals_data[hospitals_data.index == best_hospital].index.values[0]
        algo_costs[algo]['hospital'] = hospitals_data[hospitals_data.index == best_hospital]['name'].values[0]

    sorted_cost_algos =  sorted(algo_costs.items(), key=lambda x: x[1]['cost'])
    best_hospital = sorted_cost_algos[0][1]['hospital_id']
    best_route = sorted_cost_algos[0][1]['route']
    best_route_to_hospital = sorted_cost_algos[0][1]['route_to_hospital']
    best_route_to_accident = sorted_cost_algos[0][1]['route_to_accident']
    best_cost = sorted_cost_algos[0][1]['cost']

    return {
        'best_route' : best_route,
        'best_route_to_accident' : best_route_to_accident,
        'best_route_to_hospital' : best_route_to_accident,
        'ambulance_source_hospital_id' : ambulance_source_hospital_id,
        # 'best_hospital_id' : hospital_id,
        'best_hospital_id' : int(best_hospital),
        'best_cost' : best_cost
    }

def get_fastest_route(G, lat,long, geojson, hospitals_data, rs_node):
    korban_node = generate_node_korban(G,lat,long)
    route_result = findRoute(G, hospitals_data, rs_node, korban_node, lat, long)

    route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_result['best_route']]
    route_coords_to_accident = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_result['best_route_to_accident']]
    route_coords_to_hospital = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_result['best_route_to_hospital']]

    center_lat = G.nodes[korban_node]['y']
    center_lon = G.nodes[korban_node]['x']

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15)

    folium.Polygon(
        locations=geojson['geometry']['coordinates'],
        smooth_factor=4,
        color="crimson",
        no_clip=True,
        tooltip="Hi there!",
    ).add_to(m)

    # ------------------------------------ --- ----------------------------------- #

    folium.Marker(
        location=[G.nodes[korban_node]['y'], G.nodes[korban_node]['x']],
        popup="Lokasi Korban",
        icon=folium.Icon(color='black', icon='burst', prefix="fa")
    ).add_to(m)

    folium.Marker(
        location=[G.nodes[route_result['ambulance_source_hospital_id']]['y'], G.nodes[route_result['ambulance_source_hospital_id']]['x']],
        popup=f"Asal Ambulans (Cost: {route_result['best_cost']:.2f})",
        icon=folium.Icon(color='orange', icon='truck-medical', prefix="fa")
    ).add_to(m)

    folium.Marker(
        location=[G.nodes[route_result['best_hospital_id']]['y'], G.nodes[route_result['best_hospital_id']]['x']],
        popup=f"Rumah Sakit Terpilih (Cost: {route_result['best_cost']:.2f})",
        icon=folium.Icon(color='blue', icon='hospital', prefix="fa")
    ).add_to(m)

    folium.PolyLine(route_coords, weight=6, color='green', opacity=0.3).add_to(m)
    folium.PolyLine(route_coords_to_accident, weight=6, color='red', opacity=0.8).add_to(m)
    folium.PolyLine(route_coords_to_hospital, weight=6, color='blue', opacity=0.3).add_to(m)

    return m, route_result

def main():
    geojson = {"type":"Feature","geometry":{"coordinates":[[[112.747286,-7.288063],[112.748487,-7.283211],[112.744353,-7.277027],[112.744224,-7.274006],[112.74667,-7.2709],[112.750403,-7.267709],[112.751261,-7.26571],[112.751827,-7.262948],[112.758211,-7.264859],[112.767049,-7.265454],[112.771211,-7.266688],[112.803747,-7.265502],[112.802459,-7.291208],[112.747286,-7.288063]]],"type":"Polygon"},"properties":{},"id":"yb7By"}
    G, poly = load_graph(geojson)
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

    bad_types = {'living_street'}
    mask = gdf_edges['highway'].apply(lambda x: any(ht in bad_types for ht in (x if isinstance(x,list) else [x])))
    edges_to_drop = gdf_edges[mask]

    # drop dari graph
    for u,v,k in edges_to_drop.index:
        if G.has_edge(u,v,key=k):
            G.remove_edge(u,v,key=k)

    choose_hospital = ['RSUD Dr. Soetomo', 'Siloam Hospitals','RSU Haji Surabaya','Rumah Sakit Universitas Airlangga','RSIA Ferina Surabaya']
    hospitals = get_hospital_data(poly, use_all=False, choose_hospital=choose_hospital)
    hospitals = load_wait_time(hospitals)
    print(hospitals)

    G, hospitals_points = add_hospitals_to_graph(G, hospitals)
    G = generate_cost_edges(G, hospitals)
    save_hospital_data(hospitals, 'hospital_seeding_data.json')

    # korban_lat = -7.269072449827058
    # korban_long = 112.76079654693605

    # korban_lat = -7.273844
    # korban_long = 112.745561


    # korban_lat = -7.279070
    # korban_long = 112.790351

    # korban_lat = -7.281311
    # korban_long = 112.755946

    # korban_lat = -7.272480,
    # korban_long = 112.765108

    # korban_lat = -7.280612
    # korban_long = 112.780833

    korban_lat = -7.272162
    korban_long = 112.777660

    hospitals = pd.read_json('hospital_seeding_data.json')
    hospitals = hospitals.set_index('ID')

    korban_node = generate_node_korban(G, korban_lat, korban_long)
    m, target_data = get_fastest_route(G, korban_lat, korban_long, geojson, hospitals, hospitals.index.tolist())
    # show folium map
    m.save("test_map.html")




    # app = Flask(__name__)


    # @app.route('/')
    # def index():
    #     # Create base map
    #     m = folium.Map()

    #     # Get Folium's internal JS variable name (e.g. map_abc123)
    #     map_id = m.get_name()

    #     # JavaScript that waits until the map variable exists before binding the click event
    #     click_js = f"""
    #     function attachClickHandler() {{
    #         if (typeof {map_id} === 'undefined') {{
    #             // Wait and try again if the map variable isn't ready yet
    #             setTimeout(attachClickHandler, 50);
    #             return;
    #         }}

    #         {map_id}.on('click', function(e) {{
    #             var lat = e.latlng.lat.toFixed(6);
    #             var lon = e.latlng.lng.toFixed(6);

    #             var popupContent = `
    #                 <div style="text-align:center;">
    #                     <b>Latitude:</b> ${{lat}}<br>
    #                     <b>Longitude:</b> ${{lon}}<br><br>
    #                     <button onclick="window.location.href='/needhelp_say?lat=${{lat}}&lon=${{lon}}'"
    #                         style="background:#007bff;color:white;border:none;padding:5px 10px;
    #                             border-radius:4px;cursor:pointer;">
    #                         please_help
    #                     </button>
    #                 </div>
    #             `;

    #             L.popup()
    #                 .setLatLng(e.latlng)
    #                 .setContent(popupContent)
    #                 .openOn({map_id});
    #         }});
    #     }}

    #     attachClickHandler();
    #     """

    #     # Attach the JS to the map
    #     m.get_root().script.add_child(Element(click_js))

    #     return m.get_root().render()
    #     # return flask.render_template("index.html", map_html=m._repr_html_())

    # @app.route("/map/<map_uuid>")
    # def getRoute(map_uuid):
    #     return flask.send_file(f"map_data/{map_uuid}.html", mimetype="text/html")

    # @app.route('/ambulance/<rs_id>')
    # def ambulanceRequestList(rs_id):
    #     db_query = dbmodel.getAllAmbulanceRequest(rs_id)
    #     return flask.render_template('outgoAmbulance.html',ambulance_list= db_query)

    # @app.route("/needhelp_say")
    # def showMap():
    #     lat_q = request.args.get('lat') or request.args.get('latitude')
    #     lon_q = request.args.get('long') or request.args.get('lon') or request.args.get('lng') or request.args.get('longitude')

    #     if not lat_q or not lon_q:
    #         return abort(400, "Missing required query parameters: lat and long")

    #     try:
    #         lat = float(lat_q)
    #         lon = float(lon_q)
    #     except ValueError:
    #         return abort(400, "Invalid lat/long values")

    #     print(lat,lon)
    #     m, target_data = get_fastest_route(lat, lon)
    #     inserted_data = dbmodel.addNewpatientTransportRecord(target_data['ambulance_source_hospital_id'],target_data['best_hospital_id'])
    #     m.save(f"map_data/{inserted_data['html_fname']}")
    #     # return str(target_data)

    #     return flask.redirect(flask.url_for('getRoute',map_uuid=inserted_data['ID']))


    # app.run(use_reloader=False, debug=True)

if __name__ == "__main__":
    main()
