import geopandas as gpd    
import fiona
import pandas as pd
from datetime import datetime
from loguru import logger
import sys
import os
import argparse
from pathlib import Path
import json

from pathlib import Path
from lxml import etree
from shapely.geometry import Point


def create_logger(file_name: Path, logger_dir = Path("output/logger")):
    # Configure loguru logging
    log_dir = logger_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate log filename with current date
    log_filename = log_dir / f"Preprocess-{file_name.stem}-{datetime.now().strftime('%Y-%m-%d')}.log"
    logger.add(
        log_filename,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        rotation="00:00",  # New file at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip"  # Compress old logs
    )

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
    logger.info(f"Starting KML parsing for file: {kml_file}")
    
    try:
        # Parse the KML file
        tree = etree.parse(kml_file)
        root = tree.getroot()
        logger.debug("KML file parsed successfully")

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
        logger.success(f"KML parsing completed: {len(gdf)} records extracted with {len(gdf.columns)} columns")
        
        return gdf
    
    except Exception as e:
        logger.error(f"Failed to parse KML file: {e}")
        raise


class Preprocessor():
    """
    Class to preprocess KML data with schema application and text cleaning.
    """
    def __init__(self, gdf:gpd.GeoDataFrame, schema:dict, cleaning_cols:list,
                 map_gdf_db:dict, verbose:int = 1) -> gpd.GeoDataFrame:
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
        self.verbose = verbose
        
        logger.info("="*50)
        logger.info("Preprocessor initialized")
        logger.debug(f"Input GDF shape: {self.gdf.shape}")
        logger.debug(f"Schema keys: {list(self.schema.keys())}")
        logger.debug(f"Cleaning columns: {self.cleaning_cols}")
    
    def apply_schema(self):
        """Apply data type schema to geodataframe columns."""
        logger.info("Applying schema to geodataframe...")
        
        datetime_l = []
        int_l = []
        time_l = []
        float_l = []
        bool_l = []
        
        for col, dtype in self.schema.items():
            if col not in self.gdf.columns:
                logger.warning(f"Column '{col}' from schema not found in GDF, skipping")
                continue
                
            try:
                if dtype == "datetime":
                    datetime_l.append(col)
                    self.gdf[col] = pd.to_datetime(self.gdf[col], errors="coerce")

                elif dtype == "int":
                    int_l.append(col)
                    self.gdf[col] = pd.to_numeric(self.gdf[col], errors="coerce").astype("Int64")

                elif dtype == "float":
                    float_l.append(col)
                    self.gdf[col] = pd.to_numeric(self.gdf[col], errors="coerce")
                
                elif dtype == "time":
                    time_l.append(col)
                    self.gdf[col] = pd.to_datetime(self.gdf[col], errors="coerce").apply(lambda x: x.time())

                elif dtype == "bool":
                    bool_l.append(col)
                    self.gdf[col] = self.gdf[col].apply(lambda x: bool(x))
                    
                logger.debug(f"Applied {dtype} type to column '{col}'")
                
            except Exception as e:
                logger.error(f"Error applying schema to column '{col}': {e}")
        
        logger.info(f"Schema applied successfully:")
        logger.info(f"  - Datetime columns: {datetime_l}")
        logger.info(f"  - Integer columns: {int_l}")
        logger.info(f"  - Float columns: {float_l}")
        logger.info(f"  - Time columns: {time_l}")
        logger.info(f"  - Boolean columns: {bool_l}")
        
        return self.gdf

        
    def apply_cleaning(self):
        """
        Split the text input referenced by "-". Return the number which represents the first
        item of the list.
        """
        logger.info("Applying text cleaning to specified columns...")
        
        def clean_txt(txt):
            if pd.isna(txt):
                return txt
            s = str(txt).split('-')
            if len(s) > 0:
                return s[0].strip()
            else:
                return txt
        
        # Loop through the cleaning columns list
        cleaned_count = 0
        for col in self.cleaning_cols:
            if col in self.gdf.columns:
                self.gdf[col] = self.gdf[col].apply(lambda x: clean_txt(x))
                cleaned_count += 1
                logger.debug(f"Cleaned column: '{col}'")
            else:
                logger.warning(f"Column '{col}' not found for cleaning, skipping")
        
        logger.success(f"Text cleaning completed on {cleaned_count} columns")
        return self
    
    def create_new_cols(self):
        """
        CREATE: ID, DATE, TIME 
        """
        logger.info("Creating new date and time columns...")
        
        try:
            ## convert date
            self.gdf['date'] = self.gdf['date_og'].apply(lambda x: x.date())
            logger.debug("Created 'date' column")

            ## get time
            self.gdf['time'] = self.gdf['date_og'].apply(lambda x: x.time())
            logger.debug("Created 'time' column")
            
            logger.success("New columns created successfully")
            
        except Exception as e:
            logger.error(f"Error creating new columns: {e}")
            raise
        
        return self.gdf
        
    def get_gdf(self):  
        """Return the processed geodataframe."""
        return self.gdf
    
    def process(self):
        """Execute full preprocessing pipeline."""
        logger.info("Starting full preprocessing pipeline...")
        
        try:
            self.apply_cleaning()
            self.apply_schema()
            self.create_new_cols()
            logger.success("Preprocessing pipeline completed successfully")
            return self.get_gdf()
        except Exception as e:
            logger.error(f"Preprocessing pipeline failed: {e}")
            raise
    
    def prepare_gdf_db(self):
        """
        Correct on the gdf the name of the columns, which is retrieved by the map dict.
        Rename and drop unmatched columns.
        """
        logger.info("Preparing GDF to match database table structure...")
        logger.debug(f"GDF shape before preparation: {self.gdf.shape}")
        
        # Filter out mappings where db_column is None or "None"
        valid_mappings = {k: v for k, v in self.map_gdf_db.items() 
                            if v is not None and v != "None"}
        
        removed_cols = [k for k, v in self.map_gdf_db.items() 
                            if v is None or v == "None"]
        if removed_cols:
            logger.info(f"Columns mapped to None (will be removed): {removed_cols}")
        
        # Rename columns based on the valid mapping only
        self.gdf = self.gdf.rename(columns=valid_mappings)
        logger.debug(f"Renamed columns according to mapping")

        # Columns expected by the DB (values of the valid mapping dict)
        cols_db = set(valid_mappings.values())

        # CRITICAL: Always preserve the geometry column
        cols_to_keep = cols_db.union({'geometry'})
        
        # Identify extra columns not present in the DB table
        cols_to_drop = self.gdf.columns.difference(cols_to_keep)

        if len(cols_to_drop) > 0:
            logger.info(f"Dropping {len(cols_to_drop)} columns that don't match database: {list(cols_to_drop)}")
        
        # Drop unnecessary columns   
        self.gdf = self.gdf.drop(columns=list(cols_to_drop), axis='columns')
        
        logger.success(f"GDF prepared for database: {self.gdf.shape}")
        logger.debug(f"Final columns: {list(self.gdf.columns)}")
        
        return self.gdf  


def coltype_unified_schema(schema:dict, table_name:"str"):
    """
    Return dict mapping from GDF col -> gdf type
    """
    logger.debug(f"Creating column type mapping for table: {table_name}")
    dict_out = dict(zip([var['source_column'] for var in schema[table_name]['mappings']],
                        [var['data_type_source'] for var in schema[table_name]['mappings']]
                        )
                    )
    return dict_out


def map_gdf_db_unified_schema(schema:dict, table_name:"str"):
    """
    Return dict mapping from GDF col -> DB col
    """
    logger.debug(f"Creating GDF to DB column mapping for table: {table_name}")
    dict_out = dict(zip([var['source_column'] for var in schema[table_name]['mappings']],
                        [var['db_column'] for var in schema[table_name]['mappings']]
                        )
                    )
    return dict_out 

def main(args)->None:
        # Parse arguments
    overwrite = args.overwrite
    file_name = Path(args.file)
    case_type = str(args.type).lower()
    
    create_logger(file_name)
    logger.info("="*70)
    logger.info(f"Arguments: {vars(args)}")
    logger.info("STARTING KML PREPROCESSING APPLICATION")
    logger.info("="*70)
    
    try:
        # Load unified schema
        schema_file = Path("config/schema.json")
        logger.info(f"Loading schema from: {schema_file}")
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
            
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_unif = json.load(f)
        logger.success("Schema loaded successfully")

        # Cleaning lists
        list_manejo = ['risco da invasao','estagio invasao','grau dispersao','zona']
        list_ocorrencia = ['zone','risco da invasao','estagio invasao','grau dispersao']
        


        # Setup output paths
        folder_path = Path(args.path_folder_name)
        folder_name = args.folder_name
        output_dir = folder_path / folder_name
        
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory created/verified: {output_dir}")
        
        # Check if file is KML
        if file_name.suffix != ".kml":
            logger.error(f"Invalid file format. Expected .kml, got {file_name.suffix}")
            raise ValueError(f"File must be a .kml file. Got {file_name.suffix}")
        
        if not file_name.exists():
            logger.error(f"Input file not found: {file_name}")
            raise FileNotFoundError(f"Input file not found: {file_name}")
        
        # Parse KML file
        gdf = parse_kml(file_name)
        
        # Process based on type
        logger.info(f"Processing data as type: {case_type.upper()}")
        
        match case_type:
            case "ocorrencia":
                table_name = "ocorrencia"
                preprocessor = Preprocessor(
                    gdf,
                    coltype_unified_schema(schema_unif, table_name),
                    list_ocorrencia,
                    map_gdf_db_unified_schema(schema_unif, table_name),
                    verbose=1
                )
                
                gdf_processed = preprocessor.process()
                gdf_out = preprocessor.prepare_gdf_db()
                
            case "manejo":
                table_name = 'manejo'
                preprocessor = Preprocessor(
                    gdf,
                    coltype_unified_schema(schema_unif, table_name),
                    list_manejo,
                    map_gdf_db_unified_schema(schema_unif, table_name),
                    verbose=1
                )
                
                gdf_processed = preprocessor.process()
                gdf_out = preprocessor.prepare_gdf_db()
                
            case _:
                logger.error(f"Unknown type '{case_type}'. Must be 'ocorrencia' or 'manejo'")
                raise ValueError(f"Unknown type '{case_type}'. Must be 'ocorrencia' or 'manejo'")
        
        # Save processed data
        output_file = output_dir / f"{file_name.stem}_ps.gpkg"
        logger.info(f"Saving processed data to: {output_file}")
        
        gdf_out.to_file(output_file, driver="GPKG", overwrite=overwrite)
        
        logger.success("="*70)
        logger.success(f"FILE SAVED SUCCESSFULLY: {output_file}")
        logger.success(f"Total records processed: {len(gdf_out)}")
        logger.success(f"Total columns: {len(gdf_out.columns)}")
        logger.success("="*70)
        
    except Exception as e:
        logger.exception(f"Application failed with error: {e}")
        raise
    
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
    
    
    # Run main
    main(args)