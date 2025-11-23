import pandas as pd
import geopandas as gpd
from typing import Dict
import numpy as np
from loguru import logger


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
                    # Handle nullable integers
                    gdf_copy[col] = pd.to_numeric(gdf_copy[col], errors='coerce').astype('Int64')
                elif pandas_dtype in ['float64', 'float32']:
                    gdf_copy[col] = pd.to_numeric(gdf_copy[col], errors='coerce')
                elif pandas_dtype == 'string':
                    gdf_copy[col] = gdf_copy[col].astype('string')
                elif pandas_dtype == 'boolean':
                    gdf_copy[col] = gdf_copy[col].astype('boolean')
                else:
                    gdf_copy[col] = gdf_copy[col].astype(pandas_dtype)
            
            logger.debug(f"Converted column '{col}' from {gdf[col].dtype} to {pandas_dtype} ({pg_type})")
            
        except Exception as e:
            logger.warning(f"Failed to convert column '{col}' to {pandas_dtype}: {e}")
    
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