import geopandas as gpd    
import fiona
import pandas as pd
from datetime import datetime
import loguru
import sys
import os
import argparse
from pathlib import Path
import json

from pathlib import Path
from lxml import etree
from shapely.geometry import Point


def parse_kml(kml_file):
    """
    Process kml file into a geodataframe.
    Appends all metadata inside the Placemark schema1. 
    
    Returns:
        GeoDataFrame at 4326.
    
    args:
        kml_file: Path
            Path of the file
    """
    # Parse the KML file
    tree = etree.parse(kml_file)
    root = tree.getroot()

    # Define namespaces
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Extract placemarks with schema1 data
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
    return gdf


class Preprocessor():
    """
    Class to preprocess KML data with schema application and text cleaning.
    """
    def __init__(self, gdf:gpd.GeoDataFrame, schema:dict, cleaning_cols:list,
                 map_gdf_db:dict,verbose:int = 1) -> gpd.GeoDataFrame:
        """
        Init Preprocessor:
        It cleans the coming GDF by casting the values following the `schemas.json`. Apply Schema Step
        Split mixed string and numerical columns by catching the number only, based on the given columns to clean it up. Clean Step
        Create Date and Time columns based on the timestamp that comes from Avenza Map app.
        
        Args:
            gdf: gdf.GeoDataFrame
                Gdf to be processed.
            schema: dict
                Schema to parse the data type at each column of the gdf. 
            cleaning_cols: list
                Columns that will receive the operation of cleaning. Unmixing strings and numerical data type vars.
            map_gdf_db: dict. 
                Dict that contains as key the columns representing the gdf and as values the columns representing the PostgreSQL table. 
            verbose:Int (1 to print, 0 not)
        """
        self.gdf = gdf
        self.schema = schema
        self.cleaning_cols = cleaning_cols
        self.map_gdf_db = map_gdf_db
        self.verbose=verbose
        
        if self.verbose==1:
            print("-"*30)
            print("Preprocessor Running")
    
    def apply_schema(self):
        """Apply data type schema to geodataframe columns."""
        datetime_l = int_l = time_l = float_l = bool_l = []
        for col, dtype in self.schema.items():
            if col not in self.gdf.columns:
                continue  # safely skip missing columns
            if dtype == "datetime":
                datetime_l.append(col)
                self.gdf[col] = pd.to_datetime(self.gdf[col], errors="coerce")

            elif dtype == "int":
                int_l.append(col)
                self.gdf[col] = pd.to_numeric(self.gdf[col], errors="coerce" ).astype("Int64")

            elif dtype == "float":
                float_l.append(col)
                self.gdf[col] = pd.to_numeric(self.gdf[col], errors="coerce")
            
            elif dtype == "time":
                time_l.append(col)
                self.gdf[col] = pd.to_datetime(self.gdf[col], errors="coerce").apply(lambda x: x.time())

            elif dtype == "bool":
                bool_l.append(col)
                self.gdf[col] = self.gdf[col].apply(lambda x: bool(x))
        
        if self.verbose==1:
            print(f" The following columns were append at:")
            print(f"Datetime: {datetime_l}")
            print(f"Int: {int_l}")
            print(f"Float: {float_l}")
            print(f"Time: {time_l}")
            print(f"Bool: {bool_l}\n")
            
            print("-"*30)
            print(self.gdf.info())
        return self.gdf

        
    def apply_cleaning(self):
        """
        Split the text input referenced by "-". Return the number which represents the first
        item of the list.
        """
        def clean_txt(txt):
            if pd.isna(txt):
                return txt
            s = str(txt).split('-')
            if len(s) > 0:
                return s[0].strip()
            else:
                return txt
        
        # Loop through the cleaning columns list
        for col in self.cleaning_cols:
            if col in self.gdf.columns:
                self.gdf[col] = self.gdf[col].apply(lambda x: clean_txt(x))

        return self
    
    def create_new_cols(self):
        """
        CREATE: ID, DATE, TIME 
        """
        ## convert date
        self.gdf['date'] = self.gdf['date_og'].apply(lambda x:x.date())

        ## get time
        self.gdf['time'] = self.gdf['date_og'].apply(lambda x:x.time())
        
        return self.gdf
        
    def get_gdf(self):
        """Return the processed geodataframe."""
        return self.gdf
    
    def process(self):
        """Execute full preprocessing pipeline."""
        self.apply_cleaning()
        self.apply_schema()
        self.create_new_cols()
        return self.get_gdf()   
    
    def prepare_gdf_db(self):
        """
        Correct on the gdf the name of the columns, which is retrieved by the map dict.
        Rename and drop unmatched columns.
        """

        if self.verbose==1:
            print("-"*30)
            print('Preparing the gdf to match Database Table')
            print(f"Before Drop: {self.gdf.shape}") 
        
        # Rename columns based on the mapping
        self.gdf = self.gdf.rename(columns=self.map_gdf_db)

        # Columns expected by the DB (values of the mapping dict) | True columns of the Database 
        cols_db = set(self.map_gdf_db.values())

        # Identify extra columns not present in the DB table
        cols_to_drop = self.gdf.columns.difference(cols_db)

        print(f"Columns that don't match the database: {list(cols_to_drop)}")
        
        # Drop unnecessary columns   
        self.gdf = self.gdf.drop(columns=list(cols_to_drop), axis='columns')
        
        if self.verbose==1:
            print(f"After Drop: {self.gdf.shape}")
            print(self.gdf.info())
        
        return self.gdf  


       
def main(args)->None:
    print(args)

    #ADD LOGGER 
    ## SCHEMAS
    with open("schemas.json", "r", encoding="utf-8") as f:
        schemas = json.load(f)
        
    ## MAP DICTS
    with open("map_gdf_db.json", "r", encoding="utf-8") as f:
        map_gdf_db = json.load(f)

    ## cleaning list - IMPROVE
    list_manejo = ['risco da invasao','estagio invasao','grau dispersao','zona']
    list_ocorrencia = ['zone','risco da invasao','estagio invasao','grau dispersao']
    
    ## args
    overwrite=args.overwrite
    file_name = Path(args.file)
    case_type = str(args.type).lower()

   # Setup output paths
    folder_path = Path(args.path_folder_name)
    folder_name = args.folder_name
    output_dir = folder_path / folder_name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Check if file is KML
    if file_name.suffix != ".kml":
        print(f"Error: File must be a .kml file. Got {file_name.suffix}")
        return None
    
    # Parse KML file
    print("Parsing KML file...")
    gdf = parse_kml(file_name)
    print(f"Loaded {len(gdf)} records from KML")
    print(f"Loaded {len(gdf.columns)} COLUMNS from KML")
    
    # Process based on type
    match case_type:
        case "ocorrencia":
            print("Processing as Ocorrencia...")
            preprocessor = Preprocessor(gdf, schemas['ocorrencia'], list_ocorrencia,  map_gdf_db['ocorrencia'], verbose=1)
            
            ## save the intermediate step gdf in case of further analysis
            gdf_processed = preprocessor.process()
            
            ## Correct columns name
            gdf_out = preprocessor.prepare_gdf_db()
            
        case "manejo":
            print("Processing as Manejo...")
            preprocessor = Preprocessor(gdf, schemas['manejo'], list_manejo,  map_gdf_db['manejo'], verbose=1)
            
            ## save the intermediate step gdf in case of further analysis
            gdf_processed = preprocessor.process()
            
            ## Correct columns name
            gdf_out = preprocessor.prepare_gdf_db()
        case _:
            print(f"Error: Unknown type '{case_type}'. Must be 'ocorrencia' or 'manejo'")
            return None
    
    
    # Save processed data
    output_file = output_dir / f"{file_name.stem}_ps.gpkg"
    print(f"Saving to: {output_file}")
    gdf_out.to_file(output_file, driver="GPKG", overwrite=overwrite)
    print(f"File saved successfully!")    
    
    return None

if __name__ =='__main__':
    parser = argparse.ArgumentParser(
        description="Pre Processamento - Pre Processamento dos dados de Ocorrencia e Manejo para a estação de Carijos"
    )
    parser.add_argument(
        "--type", 
        type=str, 
        required=True, 
        help="Ocorrencia ou Manejo"
    )
    parser.add_argument(
        "--file", 
        type=str, 
        required=True,
        help="O caminho do arquivo KML"
    )
    parser.add_argument(
        "--folder-name",
        type=str,
        default="processed_data",
        help="Nome da pasta onde salvar os arquivos processados (default: processed_data)"
    )
    parser.add_argument(
        "--path-folder-name",
        type=str,
        default="./output",
        help="Caminho prefixo da pasta (default: ./output)"
    )
    
    parser.add_argument(
        "--overwrite",
        type=str,
        default=False,
        help="To overwrite the file or note. Default False"
    )
    args = parser.parse_args()
    
    ## main
    main(args)