import sys
import fiona
from lxml import etree
from shapely.geometry import Point
import geopandas as gpd 

def parse_kml(kml_path)-> None:
    """
    Process kml file into a geodataframe.
    Appends all metadata inside the Placemark schema1. 
    
    Returns:
        Print the columns which are captured in the main_app
    
    args:
        kml_file: Path
            Path of the file
    """
    # Parse the KML file
    tree = etree.parse(kml_path)
    root = tree.getroot()

    # Define namespaces
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Extract placemarks with schema1 data
    try:
        data = []
        for placemark in root.findall('.//kml:Placemark', ns):
            schema_data = placemark.find('.//kml:SchemaData[@schemaUrl="#schema1"]', ns)
            if schema_data is not None:
                # Get coordinates
                coords_text = placemark.find('.//kml:coordinates', ns).text.strip()
                lon, lat, alt = map(float, coords_text.split(','))
                
                # Get name
                name = placemark.find('.//kml:name', ns).text
                
                # Get timestamp if available
                timestamp_elem = placemark.find('.//kml:when', ns)
                timestamp = timestamp_elem.text if timestamp_elem is not None else None
                
                # Extract all SimpleData fields
                record = {'name': name,
                        'geometry': Point(lon, lat),
                        'elevation':alt,
                        "date_og":timestamp}
                for simple_data in schema_data.findall('.//kml:SimpleData', ns):
                    field_name = simple_data.get('name')
                    field_value = simple_data.text
                    record[field_name] = field_value
                
                data.append(record)

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(data, crs='EPSG:4326').rename(str.lower, axis='columns')
        
        # Print the list of columns as a comma-separated string for main_app.py to read
        columns = gdf.columns.tolist()
        print(','.join(columns))
        
    except fiona.errors.DriverError as e:
        print(f"Error reading KML file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python kml_reader.py <kml_file_path>", file=sys.stderr)
        sys.exit(1)
    
    kml_file_path = sys.argv[1]
    parse_kml(kml_file_path)