import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
import psycopg2
import geopandas as gpd
from sqlalchemy import create_engine

# 1. Database Connection
# On Heroku, the DATABASE_URL is provided automatically.
DB_URL = st.secrets.get("DATABASE_URL", "postgresql://user:pass@localhost:5432/postgis_db")

@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

# 2. Sidebar Filters
st.sidebar.title("🌿 Species Filter")
selected_date = st.sidebar.date_input("Filter by Date")
species_type = st.sidebar.multiselect("Species Type", ["Plant A", "Plant B"], default=["Plant A"])

# 3. Data Loading (PostGIS Queries)
def load_data():
    engine = get_engine()
    # Query Points (Occurrences)
    points_sql = "SELECT id, species, date, geom FROM species_points"
    gdf_points = gpd.read_postgis(points_sql, engine, geom_col='geom')
    
    # Query Polygons (Zones)
    zones_sql = "SELECT zone_name, geom FROM species_zones"
    gdf_zones = gpd.read_postgis(zones_sql, engine, geom_col='geom')
    
    return gdf_points, gdf_zones

st.title("Exotic Species Tracker")

try:
    points, zones = load_data()

    # 4. Map Visualization
    m = leafmap.Map(center=[0, 0], zoom=2)
    
    # Add Polygons (Zones) with styling
    m.add_gdf(zones, layer_name="Invasion Zones", fill_colors=["red"])
    
    # Add Points (Occurrences)
    m.add_gdf(points, layer_name="Occurrences")

    m.to_streamlit(height=600)

except Exception as e:
    st.error(f"Error connecting to PostGIS: {e}")
    st.info("Ensure your PostGIS container is running and the DATABASE_URL is correct.")