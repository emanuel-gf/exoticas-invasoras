
import geopandas as gpd
import pandas as pd
import json

class Preprocessor():
    """
    Class to preprocess KML data with schema application and text cleaning.
    """
    def __init__(self, gdf:gpd.GeoDataFrame, schema:dict, cleaning_cols:list) -> gpd.GeoDataFrame:
        """
        Init Preprocessor:
        
        Args:
            gdf: gdf.GeoDataFrame
            schema: dict
            cleaning_cols: list
        """
        self.gdf = gdf
        self.schema = schema
        self.cleaning_cols = cleaning_cols
    
    def apply_schema(self):
        """Apply data type schema to geodataframe columns."""
        for col, dtype in self.schema.items():
            if col not in self.gdf.columns:
                continue  # safely skip missing columns
            if dtype == "datetime":
                print(f"Converting {col} to datetime")
                self.gdf[col] = pd.to_datetime(self.gdf[col], errors="coerce")

            elif dtype == "int":
                self.gdf[col] = pd.to_numeric(self.gdf[col], errors="coerce").astype("Int64")

            elif dtype == "float":
                self.gdf[col] = pd.to_numeric(self.gdf[col], errors="coerce")

            elif dtype == "bool":
                self.gdf[col] = self.gdf[col].apply(lambda x: bool(x))

        return self

        
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
    
    def get_gdf(self):
        """Return the processed geodataframe."""
        return self.gdf
    
    def process(self):
        """Execute full preprocessing pipeline."""
        self.apply_cleaning()
        self.apply_schema()
        return self.get_gdf()   
        