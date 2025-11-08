
from flask import request, abort
from branca.element import Element
import pandas as pd
import flask
import pickle
import folium

import dbmodel
import funcs

app = flask.Flask(__name__)


@app.route('/')
def index():
    # Create base map

    geojson = funcs.load_geojson("feed-data/polygon-bounds-geojson.json")
    print(geojson['geometry']['coordinates'][0][0])
    m = folium.Map(location= tuple(geojson['geometry']['coordinates'][0][0][::-1]),zoom_start=12)
    folium.GeoJson(geojson).add_to(m)
    # Get Folium's internal JS variable name (e.g. map_abc123)
    map_id = m.get_name()

    # JavaScript that waits until the map variable exists before binding the click event
    click_js = f"""
    function attachClickHandler() {{
        if (typeof {map_id} === 'undefined') {{
            // Wait and try again if the map variable isn't ready yet
            setTimeout(attachClickHandler, 50);
            return;
        }}

        {map_id}.on('click', function(e) {{
            var lat = e.latlng.lat.toFixed(6);
            var lon = e.latlng.lng.toFixed(6);

            var popupContent = `
                <div style="text-align:center;">
                    <b>Latitude:</b> ${{lat}}<br>
                    <b>Longitude:</b> ${{lon}}<br><br>
                    <button onclick="window.location.href='/needhelp_say?lat=${{lat}}&lon=${{lon}}'"
                        style="background:#007bff;color:white;border:none;padding:5px 10px;
                            border-radius:4px;cursor:pointer;">
                        please_help
                    </button>
                </div>
            `;

            L.popup()
                .setLatLng(e.latlng)
                .setContent(popupContent)
                .openOn({map_id});
        }});
    }}

    attachClickHandler();
    """

    # Attach the JS to the map
    m.get_root().script.add_child(Element(click_js))

    return m.get_root().render()
    # return flask.render_template("index.html", map_html=m._repr_html_())

    
@app.route("/map/<map_uuid>")
def getRoute(map_uuid):
    return flask.send_file(f"map_data/{map_uuid}.html", mimetype="text/html")

@app.route('/ambulance/<rs_id>')
def ambulanceRequestList(rs_id):
    db_query = dbmodel.getAllAmbulanceRequest(rs_id)
    return flask.render_template('outgoAmbulance.html',ambulance_list= db_query)

@app.route("/incoming_patient/<rs_id>")
def incomingPatientList(rs_id):
    db_query = dbmodel.getAllAmbulanceRequest(rs_id)
    return flask.render_template('outgoAmbulance.html',ambulance_list= db_query)


@app.route("/needhelp_say")
def needhelp_say():

    lat_q = request.args.get('lat') or request.args.get('latitude')
    lon_q = request.args.get('long') or request.args.get('lon') or request.args.get('lng') or request.args.get('longitude')

    if not lat_q or not lon_q:
        return abort(400, "Missing required query parameters: lat and long")

    try:
        lat = float(lat_q)
        lon = float(lon_q)
    except ValueError:
        return abort(400, "Invalid lat/long values")

    print(lat,lon)

    geojson = funcs.load_geojson("feed-data/polygon-bounds-geojson.json")

    hospitals = pd.read_json('hospital_seeding_data.json')
    hospitals = hospitals.set_index('ID')

    with open('map-data.pkl', 'rb') as pickle_file:
        G = pickle.load(pickle_file)

    m, target_data = funcs.get_fastest_route(G, lat, lon, geojson, hospitals, hospitals.index.tolist())
    inserted_data = dbmodel.addNewpatientTransportRecord(target_data['ambulance_source_hospital_id'],target_data['best_hospital_id'])
    m.save(f"map_data/{inserted_data['html_fname']}")
    # return str(target_data)

    return flask.redirect(flask.url_for('getRoute',map_uuid=inserted_data['ID']))





if __name__ == '__main__':
    app.run(debug=True)