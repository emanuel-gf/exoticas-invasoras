import sys
import fiona
from lxml import etree
from shapely.geometry import Point
import geopandas as gpd 
from pathlib import Path
import os 
import pandas as pd

def parse_kml(kml_path)-> None:
    """
    Process kml file into a geodataframe.
    Appends all metadata inside the Placemark schema1. 
    
    Returns:
        gdf and columns
    
    args:
        kml_file: Path
            Path of the file
    """
    tree = etree.parse(kml_path)
    root = tree.getroot()

    # --- Auto-detect the KML namespace ---
    nsmap = root.nsmap
    if None in nsmap:                  # default namespace
        ns = {"k": nsmap[None]}
    else:                              # fallback to standard KML
        ns = {"k": "http://www.opengis.net/kml/2.2"}

    data = []

    # --- iterate through all Placemarks ---
    for placemark in root.findall(".//k:Placemark", ns):

        record = {}

        # --- name ---
        record["name"] = placemark.findtext(".//k:name", default=None, namespaces=ns)

        # --- timestamp (optional) ---
        record["date_og"] = placemark.findtext(".//k:when", default=None, namespaces=ns)

        # --- coordinates ---
        coords_text = placemark.findtext(".//k:coordinates", default=None, namespaces=ns)
        if coords_text:
            lon, lat, *rest = [float(v) for v in coords_text.split(",")]
            alt = rest[0] if rest else None
            record["geometry"] = Point(lon, lat)
            record["elevation"] = alt
        else:
            # Skip features without point coordinates
            continue

        # --- extract ALL SimpleData fields, regardless of schema ---
        for sd in placemark.findall(".//k:SimpleData", ns):
            field_name = sd.get("name")
            if field_name:
                record[field_name] = sd.text

        data.append(record)

    # --- build GeoDataFrame ---
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    gdf.columns = gdf.columns.str.lower()  # normalize naming

    return gdf




def generate_csv_from_gdf(gdf, DEFAULT_OUTPUT_BASE, target_file_name, target_folder = 'csv'):
    """Export the gdf to a csv on the given folder.
    Returns:
        Output_path: WHere the csv has been saved. 
    Args:
        gdf: gdf generated from the parse_kml function. 
        DEFAULT_OUTPUT_BASE: Path of the Path.home() + Desktop + output folder
        target_file_name: output file name. The same name as the input file but saved as csv. 
        target_folder: output_folder
        """

    ## Build the path 
    output_path = DEFAULT_OUTPUT_BASE/ Path(target_folder) / target_file_name
    
    ## make dir if not exists
    os.makedirs(output_path.parent, exist_ok=True)
    ## split the points into x and y 
    gdf['x'] = gdf.geometry.x
    gdf['y'] = gdf.geometry.y

    ## export the gdf without the geometry
    gdf.drop(columns='geometry').to_csv('test.csv', index=False)

    # Simulate saving to CSV
    gdf.to_csv(output_path, index=False)
    
    return output_path 


def convert_csv_to_gpkg(csv_path,TEMP_CONVERTED_GPKG_PATH):
    """
    Reads a CSV file, transforms it into a GeoDataFrame using 'x' and 'y' columns,
    and saves the result to a temporary GPKG file.

    Returns:
        Path to the temporary GPKG file.

    Args:
        csv_path (str or Path): Path to the input CSV file.
        TEMP_CONVERTED_GPKG_PATH = (str or Path): Path where temporary GPKG file will be saved.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    # --- Check for required 'x' and 'y' columns ---
    if 'x' not in df.columns or 'y' not in df.columns:
        raise KeyError("CSV file must contain 'x' and 'y' columns for conversion to GeoPackage.")

    # --- Conversion to GeoDataFrame ---
    try:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.x, df.y),
            crs='EPSG:4326'
        )
    except Exception as e:
        raise RuntimeError(f"Error creating geometry from x/y columns: {e}")

    # --- Save to Temporary GPKG ---
    try:
        gdf.to_file(TEMP_CONVERTED_GPKG_PATH, driver='GPKG', encoding="utf-8")
        return Path(TEMP_CONVERTED_GPKG_PATH)
    except Exception as e:
        raise RuntimeError(f"Error saving converted GeoDataFrame to GPKG: {e}")
    



#### CURRENT WORK
from shapely.geometry import LineString, Polygon

def parse_kml_with_logging(kml_path, log=True):
    """
    Flexible KML parser:
    - Auto-detects namespaces
    - Supports Point, LineString, Polygon
    - Extracts all SimpleData fields
    - Logs Placemark content (optional)
    """

    tree = etree.parse(kml_path)
    root = tree.getroot()

    # Auto-detect namespace
    nsmap = root.nsmap
    ns = {"k": nsmap.get(None, "http://www.opengis.net/kml/2.2")}

    data = []

    for placemark in root.findall(".//k:Placemark", ns):
        record = {}

        # Basic metadata
        record["name"] = placemark.findtext(".//k:name", default=None, namespaces=ns)
        record["date_og"] = placemark.findtext(".//k:when", default=None, namespaces=ns)

        # ---- GEOMETRY PARSING ----
        geometry = None

        # POINT
        coords_text = placemark.findtext(".//k:Point/k:coordinates", namespaces=ns)
        if coords_text:
            lon, lat, *rest = map(float, coords_text.split(","))
            alt = rest[0] if rest else None
            geometry = Point(lon, lat)
            record["elevation"] = alt

        # LINESTRING
        if geometry is None:
            ls_text = placemark.findtext(".//k:LineString/k:coordinates", namespaces=ns)
            if ls_text:
                coords = []
                for pair in ls_text.strip().split():
                    lon, lat, *rest = map(float, pair.split(","))
                    coords.append((lon, lat))
                geometry = LineString(coords)

        # POLYGON
        if geometry is None:
            poly_text = placemark.findtext(".//k:Polygon//k:coordinates", namespaces=ns)
            if poly_text:
                coords = []
                for pair in poly_text.strip().split():
                    lon, lat, *rest = map(float, pair.split(","))
                    coords.append((lon, lat))
                geometry = Polygon(coords)

        # If no geometry found → skip
        if geometry is None:
            if log:
                print("⚠️ Missing geometry in Placemark:", record.get("name"))
            continue

        record["geometry"] = geometry

        # ---- SimpleData fields ----
        simple_fields = {}
        for sd in placemark.findall(".//k:SimpleData", ns):
            fname = sd.get("name")
            if fname:
                simple_fields[fname] = sd.text
                record[fname] = sd.text

        # ---- LOGGING ----
        if log:
            print("\n-------------------------")
            print("Placemark:", record.get("name"))
            print("Geometry type:", geometry.geom_type)
            print("SimpleData fields found:", list(simple_fields.keys()))
            print("-------------------------\n")

        data.append(record)

    # Build GeoDataFrame
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    gdf.columns = gdf.columns.str.lower()

    return gdf
