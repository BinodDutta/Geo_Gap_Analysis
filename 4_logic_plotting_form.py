import os
import pandas as pd
import folium
from folium.plugins import HeatMap
import requests
from branca.element import Template, MacroElement
import json
from shapely.geometry import shape, Point
from shapely.geometry.polygon import Polygon

# --- 1. CONFIGURATION ---
GEOJSON_URL = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"

# --- 2. LOAD DATA ---
print(" Loading Data...")
try:
    df_data = pd.read_json("Cleaned_Data/statistical_gap_analysis.json", orient='records')
    df_data['pincode'] = df_data['pincode'].astype(str).str.strip()
    
    df_geo = pd.read_csv("Cleaned_Data/pincode_master_clean.csv", dtype=str)
    df_geo.columns = df_geo.columns.str.lower().str.strip()
    df_geo['pincode'] = df_geo['pincode'].str.strip().str.split('.').str[0]
    df_geo['latitude'] = pd.to_numeric(df_geo['latitude'], errors='coerce')
    df_geo['longitude'] = pd.to_numeric(df_geo['longitude'], errors='coerce')
    
    df_final = pd.merge(df_data, df_geo, on='pincode', how='inner')
    raw_points = df_final.dropna(subset=['latitude', 'longitude', 'z_score'])

except Exception as e:
    print(f" Error loading data: {e}")
    exit()

# --- 3. POLYGON FILTER ---
print(" Filtering Points (Official Boundary Check)...")
try:
    resp = requests.get(GEOJSON_URL)
    geo_data = resp.json()
    india_shape = shape(geo_data['features'][0]['geometry'])
    
    def is_inside_india(row):
        point = Point(row['longitude'], row['latitude'])
        return india_shape.contains(point)

    valid_data = raw_points[raw_points.apply(is_inside_india, axis=1)].copy()

except Exception:
    valid_data = raw_points # Fallback

valid_data = valid_data.sort_values(by='z_score', ascending=True)

# --- 4. MAP SETUP ---
india_map = folium.Map(
    location=[22.5, 82.0], 
    zoom_start=5,
    min_zoom=4,
    max_bounds=True,
    tiles='CartoDB dark_matter'
)

# --- 5. BORDER OVERLAY ---
folium.GeoJson(
    geo_data,
    name="Official Boundary",
    style_function=lambda x: {
        'fillColor': 'transparent', 
        'color': '#ffffff',      
        'weight': 0.7,           
        'opacity': 0.8
    }
).add_to(india_map)

# --- 6. PLOT POINTS (Service Terminology) ---
print(" Rendering Map Particles...")

def get_marker_properties(z_score):
    # Returns: Radius, Opacity, Color, Text_Label
    if z_score >= 3.0:   return 4.0, 0.8, '#ff0033', "Underserved"
    elif z_score >= 2.0: return 3.5, 0.7, '#ff6600', "Moderately Served"
    elif z_score >= 1.0: return 2.5, 0.6, '#ffff00', "Adequately Served"
    else:                return 1.5, 0.3, '#00ffff', "Well Served"

for _, row in valid_data.iterrows():
    radius, opacity, color, label = get_marker_properties(row['z_score'])
    
    dist_name = str(row['district']).title()
    
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=radius,
        color=color,
        weight=0, 
        fill=True,
        fill_color=color,
        fill_opacity=opacity,
        
        # --- EMPATHY-DRIVEN POPUP ---
        popup=f"""
        <div style='font-family:sans-serif; width:160px;'>
            <b>{dist_name}</b><br>
            <span style='color:{color}; font-weight:bold;'>{label}</span><br>
            <span style='font-size:10px; color:#aaa;'>PIN: {row['pincode']}</span>
        </div>
        """
    ).add_to(india_map)

# --- 7. HEATMAP ---
heat_data = valid_data[['latitude', 'longitude', 'z_score']].values.tolist()
HeatMap(
    heat_data, radius=20, blur=15, min_opacity=0.2,
    gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
).add_to(india_map)

# --- 8. LEGEND (Service Levels) ---
template = """
{% macro html(this, kwargs) %}
<div style="
    position: fixed; 
    bottom: 30px; left: 30px; 
    width: 230px; 
    z-index:9999; 
    background-color: rgba(0, 0, 0, 0.85); 
    color: white;
    padding: 15px; 
    border-radius: 8px; 
    border: 1px solid #444;
    font-family: 'Segoe UI', sans-serif;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    ">
    <h4 style="margin-top:0; margin-bottom:12px; color:#fff; font-size:14px; border-bottom:1px solid #555; padding-bottom:8px;">
        Aadhaar Service Coverage
    </h4>
    
    <div style="margin-bottom:8px; display:flex; align-items:center;">
        <span style="color:#ff0033; font-size:18px; margin-right:10px;">&#9679;</span> 
        <div>
            <div style="font-weight:bold; font-size:13px;"> Underserved</div>
        </div>
    </div>
    
    <div style="margin-bottom:8px; display:flex; align-items:center;">
        <span style="color:#ff6600; font-size:18px; margin-right:10px;">&#9679;</span> 
        <div style="font-size:13px;">Partially Served</div>
    </div>
    
    <div style="margin-bottom:8px; display:flex; align-items:center;">
        <span style="color:#ffff00; font-size:18px; margin-right:10px;">&#9679;</span> 
        <div style="font-size:13px;"> Served</div>
    </div>
    
    <div style="display:flex; align-items:center;">
        <span style="color:#00ffff; font-size:18px; margin-right:10px;">&#9679;</span> 
        <div style="font-size:13px;">Well Served</div>
    </div>
</div>
{% endmacro %}
"""
macro = MacroElement()
macro._template = Template(template)
india_map.get_root().add_child(macro)

# --- 9. SAVE ---
output_file = "visuals_graphs/India_Map_Service_Coverage.html"
folder_name = os.path.dirname(output_file)
if folder_name and not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Created new folder: {folder_name}")

india_map.save(output_file)
print(f" SUCCESS! Service-focused map saved to {output_file}")