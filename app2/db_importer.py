import geopandas as gpd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger
import os
from dotenv import load_dotenv
import pandas as pd
import sys # <-- ADDED: Import sys for standard output redirection


class DataImporter:
    """Import GPKG data into PostgreSQL/PostGIS database tables."""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize the importer with database configuration.
        
        Args:
            db_config: Dictionary with keys: host, port, database, user, password
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def get_max_id(self, table_name: str) -> int:
        """
        Get the maximum ID from a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Maximum ID value, or 0 if table is empty
        """
        try:
            query = sql.SQL("SELECT COALESCE(MAX(id), 0) FROM {}").format(
                sql.Identifier(table_name)
            )
            self.cursor.execute(query)
            max_id = self.cursor.fetchone()[0]
            logger.info(f"Current max ID in TABLE: {table_name}: {max_id}")
            return max_id
        except Exception as e:
            logger.error(f"Error getting max ID from {table_name}: {e}")
            raise
        
    def get_cols_dtypes(self, table_name:str) -> dict:
        """
        Get the columns, dtypes and boolean information of nullables for each
        column of the table.
        Returns a dict with keys of cols, dtypes and nullable
        Args:
            table_name: str
                Name of the table
        """
        dict_out = {}
        try: 
            query = sql.SQL("""
                             SELECT column_name, data_type, is_nullable
                                 FROM information_schema.columns
                                 WHERE table_name = {} 
                                 AND table_schema = 'public'
                                 ORDER BY ordinal_position;
                             """
            ).format(sql.Literal(table_name))
            
            self.cursor.execute(query)
            
            ## rows is a list of tuples that contains (cols, dtype, nullable)
            rows = self.cursor.fetchall()
            
            ## Return in a dict
            dict_out['cols'] = [row[0] for row in rows]
            dict_out['dtypes'] = [row[1] for row in rows] 
            dict_out['nullable'] = [row[2] for row in rows] 
            
            
        except Exception as e:
            logger.error(f"Error getting Cols and Dtypes from {table_name}: {e}")
            raise
        
        return dict_out
    
    def import_ocorrencia(self, gdf: gpd.GeoDataFrame, layer_name: Optional[str] = None):
        """
        Import data from GPKG file into ocorrencia table.
        
        """
        gdf = gdf.copy()
        try:          
            # Get next ID
            max_id = self.get_max_id('ocorrencia')
            next_id = max_id + 1
            
            # Prepare data for insertion
            records = []
            for idx, row in gdf.iterrows():
                record = (
                    next_id + idx,
                    row.get('name'),
                    row.get('elevation'),
                    row.get('date'),
                    row.get('time'),
                    row['especie'],
                    row.get('nivel_prioridade'),
                    row.get('risco_invasao'),
                    row.get('estagio_invasao'),
                    row.get('grau_dispersao'),
                    row['individuos'],
                    row.get('zona'),
                    row.get('area_degradada'),
                    row.geometry.wkb_hex if row.geometry else None,
                    row.get('comentario'),
                    row.get('description')
                )
                records.append(record)
            
            # Insert records
            insert_query = """
                INSERT INTO ocorrencia (
                    id, name, elevation, date, time, especie, nivel_prioridade,
                    risco_invasao, estagio_invasao, grau_dispersao, individuos,
                    zona, area_degradada, geom, comentario, description
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    ST_GeomFromWKB(%s::geometry, 4326), %s, %s
                )
            """
            
            execute_batch(self.cursor, insert_query, records, page_size=100)
            self.conn.commit()
            
            logger.info(f"Successfully imported {len(records)} records into ocorrencia")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error importing ocorrencia data: {e}")
            raise
    
    def import_manejo(self, gdf: gpd.GeoDataFrame):
        """
        Import data from GPKG file into manejo table.
        
        Args:
            gdf: gdf object
        """
        gdf = gdf.copy()
        try:
            # Get next ID
            max_id = self.get_max_id('manejo')
            next_id = max_id + 1
            
            # Prepare data for insertion
            records = []
            for idx, row in gdf.iterrows():
                record = (
                    next_id + idx,
                    row.get('name'),
                    row.get('elevation'),
                    row.get('date'),
                    row.get('time'),
                    row.get('tipo_acao'),
                    row.get('zona'),
                    row.get('especie'),
                    row.get('status_remocao'),
                    row.get('individuos'),
                    row.get('plantulas_rev'),
                    row.get('jovens_rev'),
                    row.get('adultos_rev'),
                    row.get('metodo_controle'),
                    row.get('mec_controle'),
                    row.get('principio_ativo'),
                    row.get('quimic_concentr'),
                    row.get('quimic_l'),
                    row.get('inicio'),
                    row.get('fim'),
                    row.get('num_manej'),
                    row.get('num_equipe'),
                    row.get('custo'),
                    row.geometry.wkb_hex if row.geometry else None,
                    row.get('comentario'),
                    row.get('description')
                )
                records.append(record)
            
            # Insert records
            insert_query = """
                INSERT INTO manejo (
                    id, name, elevation, date, time, tipo_acao, zona, especie,
                    status_remocao, individuos, plantulas_rev, jovens_rev, adultos_rev,
                    metodo_controle, mec_controle, principio_ativo, quimic_concentr,
                    quimic_l, inicio, fim, num_manej, num_equipe, custo, geom,
                    comentario, description
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, ST_GeomFromWKB(%s::geometry, 4326),
                    %s, %s
                )
            """
            
            execute_batch(self.cursor, insert_query, records, page_size=100)
            self.conn.commit()
            
            logger.info(f"Successfully imported {len(records)} records into manejo")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error importing manejo data: {e}")
            raise


def validate_file(file_path: Path) -> bool:
    """
    Validate if file exists and is a GPKG file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if valid, False otherwise
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path.absolute()}")
        return False
    
    if not file_path.is_file():
        logger.error(f"Path is not a file: {file_path.absolute()}")
        return False
    
    if file_path.suffix.lower() != '.gpkg':
        logger.error(f"File is not a GPKG file: {file_path.absolute()}")
        return False
    
    return True

def create_logger(file_name: Path, logger_dir = Path("output/logger")):
    # Configure loguru logging to pipe output to sys.stdout
    logger.remove() # Remove default Loguru handler
    logger.add(
        sys.stdout, # <-- Redirect log output to standard output
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    
    # Optional: File logging configuration (uncomment if needed)
    # log_dir = logger_dir
    # log_dir.mkdir(parents=True, exist_ok=True)
    # log_filename = log_dir / f"{file_name.stem}-{datetime.now().strftime('%Y-%m-%d')}.log"
    # logger.add(
    #     log_filename,
    #     format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    #     level="INFO",
    #     rotation="00:00",
    #     retention="30 days",
    #     compression="zip"
    # )
    

def get_pandas_dtype_map() -> Dict[str, str]:
    """
    Map PostgreSQL data types to pandas dtypes.
    
    Returns:
        Dictionary mapping PostgreSQL types to pandas types
    """
    return {
        'integer': 'Int64',  # Nullable integer
        'bigint': 'Int64',
        'smallint': 'Int32',
        'numeric': 'float64',
        'real': 'float32',
        'double precision': 'float64',
        'character varying': 'string',
        'varchar': 'string',
        'text': 'string',
        'char': 'string',
        'character': 'string',
        'date': 'object',  # Will convert later
        'time without time zone': 'object',  # Will convert later
        'time with time zone': 'object',
        'timestamp without time zone': 'object',  # Will convert later
        'timestamp with time zone': 'object',
        'boolean': 'boolean',
        'bool': 'boolean',
        'USER-DEFINED': None,  # Skip geometry and custom types
    }

def cast_gdf_to_schema(gdf: gpd.GeoDataFrame, pg_schema: Dict[str, str]) -> gpd.GeoDataFrame:
    """
    Cast GeoDataFrame columns to match PostgreSQL schema.
    
    Args:
        gdf: GeoDataFrame to cast
        pg_schema: Dictionary mapping column names to PostgreSQL types
        
    Returns:
        GeoDataFrame with properly typed columns
    """
    dtype_map = get_pandas_dtype_map()
    gdf_copy = gdf.copy()
    
    for col, pg_type in pg_schema.items():
        # Skip if column doesn't exist in GeoDataFrame
        if col not in gdf_copy.columns:
            logger.debug(f"Column '{col}' not found in GeoDataFrame, skipping")
            continue
        
        # Skip geometry column
        if col == 'geom' or col == 'geometry':
            continue
        
        # Skip auto-generated columns
        if col in ['id', 'created_at', 'updated_at']:
            continue
        
        # Get corresponding pandas dtype
        pandas_dtype = dtype_map.get(pg_type)
        
        if pandas_dtype is None:
            logger.debug(f"Skipping column '{col}' with type '{pg_type}'")
            continue
        
        try:
            # Handle date/time types specially
            if pg_type == 'date':
                gdf_copy[col] = pd.to_datetime(gdf_copy[col], errors='coerce').dt.date
            elif pg_type in ['time without time zone', 'time with time zone']:
                gdf_copy[col] = pd.to_datetime(gdf_copy[col], format='%H:%M:%S', errors='coerce').dt.time
            elif pg_type in ['timestamp without time zone', 'timestamp with time zone']:
                gdf_copy[col] = pd.to_datetime(gdf_copy[col], errors='coerce')
            else:
                # Cast to the appropriate dtype
                if pandas_dtype == 'Int64':
                    # Convert to float first (handles NaN), then replace NaN with None
                    gdf_copy[col] = pd.to_numeric(gdf_copy[col], errors='coerce')
                    # Convert to regular float64 instead of nullable Int64
                elif pandas_dtype in ['float64', 'float32']:
                    gdf_copy[col] = pd.to_numeric(gdf_copy[col], errors='coerce')
                elif pandas_dtype == 'string':
                    gdf_copy[col] = gdf_copy[col].astype('object')
                elif pandas_dtype == 'boolean':
                    gdf_copy[col] = gdf_copy[col].astype('object')
                else:
                    gdf_copy[col] = gdf_copy[col].astype(pandas_dtype)
            
            logger.debug(f"Converted column '{col}' from {gdf[col].dtype} to {pandas_dtype} ({pg_type})")
            
        except Exception as e:
            logger.warning(f"Failed to convert column '{col}' to {pandas_dtype}: {e}")
    
    # Convert pd.NA and NaN to None for PostgreSQL compatibility
    # Replace all NaN/NA values with None
    gdf_copy = gdf_copy.replace({pd.NA: None, float('nan'): None})
    
    # Also use mask to catch any remaining NA values
    for col in gdf_copy.columns:
        if col != 'geometry':
            gdf_copy[col] = gdf_copy[col].where(pd.notna(gdf_copy[col]), None)
    
    return gdf_copy


def validate_schema_match(gdf: gpd.GeoDataFrame, pg_schema: Dict[str, str]) -> Dict[str, str]:
    """
    Validate which columns from schema are present in GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame to validate
        pg_schema: PostgreSQL schema dictionary
        
    Returns:
        Dictionary of validation results
    """
    results = {
        'present': [],
        'missing': [],
        'extra': []
    }
    
    # Exclude auto-generated columns
    auto_columns = ['id', 'created_at', 'updated_at']
    schema_cols = set(pg_schema.keys()) - set(auto_columns) - {'geom'}
    gdf_cols = set(gdf.columns) - {'geometry'}
    
    results['present'] = list(schema_cols & gdf_cols)
    results['missing'] = list(schema_cols - gdf_cols)
    results['extra'] = list(gdf_cols - schema_cols)
    
    logger.info(f"Schema validation: {len(results['present'])} matched, "
                f"{len(results['missing'])} missing, {len(results['extra'])} extra")
    
    if results['missing']:
        logger.warning(f"Missing columns in GeoDataFrame: {results['missing']}")
    if results['extra']:
        logger.info(f"Extra columns in GeoDataFrame: {results['extra']}")
    
    return results


def main(args):
    """
    Main function to import GPKG data into database.
    
    Args:
        args: Command line arguments with 'type' and 'file_name' attributes
    """
    ## parse args
    case_type = args.type.lower()
    file_name = Path(args.file_name)
    
    ## Logger
    create_logger(file_name)
        
    # Validate input type
    valid_types = ['ocorrencia', 'manejo']
    if case_type not in valid_types:
        logger.error(f"Invalid type '{case_type}'. Must be one of: {', '.join(valid_types)}")
        return 1
    
    # Validate file
    if not validate_file(file_name):
        return 1
    
    # Database configuration
    db_config = {
        'host': os.environ['host'],
        'port': int(os.environ['port']),
        'database': os.environ['database'],
        'user': os.environ['user'],
        'password': os.environ['password']
    }
    
    # Initialize importer class
    importer = DataImporter(db_config)
    
    # Read GPKG file
    try:
        gdf = gpd.read_file(file_name)
    except Exception as e:
        logger.error(f"Failed to read GPKG file {file_name.absolute()}: {e}")
        return 1
    
    logger.info(f"Loaded {len(gdf)} records.")
    
    ## Validate Schema and dtype before attempting to import
    logger.info(f"Validating schema")
    table_name = case_type.strip()
    
    try:
        # Connect to database ONCE
        importer.connect()
        
        ## Fetch the columns and dtypes of the destination table
        dict_out = importer.get_cols_dtypes(table_name=table_name)
        
        ## Create the true schema table (Cols | Dtype)
        schema_dict = dict(zip(dict_out['cols'], dict_out['dtypes']))
        
        ## validate schema
        results_val = validate_schema_match(gdf, schema_dict)
        if results_val['missing']:
            logger.error(f"There are columns missing in the geodataframe.")
            return 1
        else:
            logger.success("Schema Validated!")
            
        ## Cast to schema
        new_gdf = cast_gdf_to_schema(gdf, schema_dict)
        logger.success(f"Casting to schema complete!")
        
        # Now do the actual import
        logger.info(f"Processing {case_type} data from: {file_name.absolute()}")
        
        # Import based on type
        if case_type == 'ocorrencia':
            importer.import_ocorrencia(new_gdf)
        elif case_type == 'manejo':
            importer.import_manejo(new_gdf)
        
        logger.success(f"Import completed successfully for {case_type}")
        return 0
        
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return 1
    except psycopg2.Error as e:
        logger.error(f"Database error during import: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during import: {e}")
        return 1
    finally:
        # disconnect
        try:
            importer.disconnect()
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Import GPKG data into manejo database'
    )
    parser.add_argument(
        '--type',
        choices=['ocorrencia', 'manejo'],
        help='Table to be imported.'
    )
    parser.add_argument(
        '--file_name',
        help='Path to the GPKG file to import'
    )
    
    args = parser.parse_args()
    
    ## load environment variables env
    load_dotenv()
    
    exit_code = main(args)
    exit(exit_code)