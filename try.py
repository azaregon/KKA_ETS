import folium
from branca.element import Element

# Create map centered at Jakarta
m = folium.Map()

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
                <button onclick="window.location.href='/save_location?lat=${{lat}}&lon=${{lon}}'"
                    style="background:#007bff;color:white;border:none;padding:5px 10px;
                           border-radius:4px;cursor:pointer;">
                    Save location
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

# Save to file
m.save("clickable_map.html")
print("✅ Map saved as clickable_map.html — open it in your browser.")
