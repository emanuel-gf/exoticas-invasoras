import streamlit as st
import json
import os
import subprocess
import pandas as pd
import geopandas as gpd
from io import StringIO
from pathlib import Path

## import built functions
from src.func import parse_kml, generate_csv_from_gdf, convert_csv_to_gpkg

# --- Constants and Setup ---
# Use /app/app_src (container's working directory) as base 
CONTAINER_APP_DIR = Path("/app/app_src/")

# For temporary/output files, use a dedicated volume mount
OUTPUT_BASE = Path("/app/outputs")  # This should be a volume in docker-compose.yml

# Create output directory 
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

SCHEMA_FILE = CONTAINER_APP_DIR / "config" / "schema.json"
KML_READER_SCRIPT = CONTAINER_APP_DIR / "kml_reader.py"
PREPROCESS_SCRIPT = CONTAINER_APP_DIR / "preprocess.py"
DB_IMPORTER_SCRIPT = CONTAINER_APP_DIR / "db_importer.py"
GENERATE_CSV_SCRIPT = CONTAINER_APP_DIR / "generate_csv.py"
TEMP_KML_PATH = OUTPUT_BASE / "temp_uploaded.kml"

logo_path = str(CONTAINER_APP_DIR / "imgs" / "icmbio_logo.webp")
DEFAULT_OUTPUT_BASE = OUTPUT_BASE
DEFAULT_TEMP_DIR = OUTPUT_BASE / "temp"
DEFAULT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
TEMP_PREPROCESS_PATH = DEFAULT_TEMP_DIR / "temp_preprocess.gpkg"
TEMP_CONVERTED_GPKG_PATH = DEFAULT_TEMP_DIR / "temp_converted.gpkg"


# Load schema.json
@st.cache_data
def load_schema(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"Configuration file not found")

schema_data = load_schema(SCHEMA_FILE)


def read_kml_data_and_columns(kml_path):
    """Run the parse_kml function and returns the columns and geodataframe."""
    st.info(f"Running reading kml ")
    print('This is func: read_kml_data_and_columns')
    gdf = parse_kml(kml_path=kml_path)
    print(gdf)
    cols = gdf.columns.tolist()
    return cols, gdf


# BUTTON FUNCTION - page1
## READ KML
def read_kml_and_display_data():
    if TEMP_KML_PATH.exists():
        try:
            # get output
            kml_cols, raw_gdf = read_kml_data_and_columns(TEMP_KML_PATH)
            
            ## **FIX 2: Handle geometry column for PyArrow serialization**
            # Convert the geometry column to a string representation (WKT) 
            # for safe display in st.dataframe. This avoids the ArrowTypeError.
            if isinstance(raw_gdf, gpd.GeoDataFrame) and 'geometry' in raw_gdf.columns:
                display_gdf = raw_gdf.copy()
                display_gdf['geometry'] = display_gdf['geometry'].astype(str)
            else:
                display_gdf = raw_gdf

            ## update state
            st.session_state.kml_columns = kml_cols
            st.session_state.kml_gdf_raw = raw_gdf # Keep the original GeoDataFrame in state
            
            # --- UPDATE THE CONTAINER ---
            df_output_container.empty()
            
            with df_output_container:
                st.success(f"KML Columns read: {', '.join(kml_cols)}")
                # **FIX 1: Replace use_container_width=True with width='stretch'**
                st.dataframe(display_gdf, width='stretch')
            # ------------------------------
            
        except Exception as e:
            with df_output_container:
                st.error(f"Error reading KML data: {e}")
            st.session_state.kml_columns = None
            st.session_state.kml_gdf_raw = None
    else:
        with df_output_container:
                st.warning("Please upload a KML file first.")


## 


# --- Session State Initialization ---
if 'schema_data' not in st.session_state: st.session_state.schema_data = schema_data
if 'kml_columns' not in st.session_state: st.session_state.kml_columns = None
if 'kml_gdf_raw' not in st.session_state: st.session_state.kml_gdf_raw = None 
if 'uploaded_file_name' not in st.session_state: st.session_state.uploaded_file_name = None
if 'current_input_path' not in st.session_state: st.session_state.current_input_path = None
if 'output_path' not in st.session_state: st.session_state.output_path = str(DEFAULT_OUTPUT_BASE)
if 'output_folder_name' not in st.session_state: st.session_state.output_folder_name = "processed_data"
if 'output_filename_base' not in st.session_state: st.session_state.output_filename_base = "default_ps.gpkg"
if 'output_filename_gpkg' not in st.session_state: st.session_state.output_filename_gpkg = "default_ps.gpkg"
if 'preprocessing_completed' not in st.session_state: st.session_state.preprocessing_completed = False
if 'processed_file_path' not in st.session_state: st.session_state.processed_file_path = None
if 'manual_import_file_path' not in st.session_state: st.session_state.manual_import_file_path = None
if 'current_step' not in st.session_state: st.session_state.current_step = "Step 1: Avenza File (kml)"
if 'case_type_selector' not in st.session_state: st.session_state.case_type_selector = "ocorrencia" 
if 'db_host' not in st.session_state: st.session_state.db_host = 'localhost'
if 'db_port' not in st.session_state: st.session_state.db_port = '5432'
if 'db_database' not in st.session_state: st.session_state.db_database = 'postgres'
if 'db_user' not in st.session_state: st.session_state.db_user = 'postgres'
if 'db_password' not in st.session_state: st.session_state.db_password = ''

if 'csv_export_message' not in st.session_state: st.session_state.csv_export_message = None
if 'csv_export_status' not in st.session_state: st.session_state.csv_export_status = None

# Renamed variables for generic file export status
if 'last_export_message' not in st.session_state: st.session_state.last_export_message = None
if 'last_export_status' not in st.session_state: st.session_state.last_export_status = None

if 'show_mapping_table' not in st.session_state: st.session_state.show_mapping_table = False # Start visible by default


# ...
# --- Header ---
col1, col2 = st.columns([2, 5])
with col1:
    st.image(logo_path, width=150)
with col2:
    st.header("Estação Ecologica do Carijos")
st.title("Preprocessamento Especies Exoticas Invasoras")

# --- NAVIGATION RADIO BUTTONS (The main flow) ---
st.divider()
step_options = [
    "Step 1: Avenza File (kml)",
    "Pre-Processing",
    "Database Import"
]

st.radio(
    "Application Step Navigation",
    options=step_options,
    key='current_step', 
    index=step_options.index(st.session_state.current_step),
    horizontal=True 
)

current_step = st.session_state.current_step
st.divider()

# ==============================================================================
#                                STEP 1: Read KML (Refactored TAB1)
# ==============================================================================
if current_step == "Step 1: Avenza File (kml)":
    st.header("1. KML File Reader and CSV Export")
    
    st.subheader("File & Type Selection")
    
    uploaded_file = st.file_uploader(
        "Upload KML File", 
        type=['kml'],
        key="kml_uploader",
        help="Select the KML file to be analyzed."
    )
    
    if uploaded_file is not None:
        if st.session_state.uploaded_file_name != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.kml_columns = None
            st.session_state.kml_gdf_raw = None
            st.session_state.preprocessing_completed = False 
            st.session_state.processed_file_path = None
            st.session_state.manual_import_file_path = None
            
            # Set GPKG output filename based on KML filename
            file_stem = Path(uploaded_file.name).stem
            st.session_state.output_filename_gpkg = f"{file_stem}.gpkg"
    
        try:
            bytes_data = uploaded_file.getvalue()
            with open(TEMP_KML_PATH, "wb") as f:
                f.write(bytes_data)
            st.success(f"File **{uploaded_file.name}** uploaded successfully.")
        except Exception as e:
            st.error(f"Error saving temporary file: {e}")


    st.divider()
    
    st.subheader("Visualize Avenza KML Data")

    # BUTTON
    st.button(
        "1. Read KML & Display Data", 
        on_click=read_kml_and_display_data, 
        type="primary",
        disabled=uploaded_file is None
    )

    # DEFINE THE CONTAINER FOR THE DATAFRAME OUTPUT
    df_output_container = st.container()
    

    # 4. RENDER PERSISTENT DATA 
    if st.session_state.kml_gdf_raw is not None:
         # **FIX 2: Handle geometry column for PyArrow serialization (repeated for persistent render)**
         display_gdf = st.session_state.kml_gdf_raw.copy()
         if isinstance(display_gdf, gpd.GeoDataFrame) and 'geometry' in display_gdf.columns:
            display_gdf['geometry'] = display_gdf['geometry'].astype(str)
            
         with df_output_container:
            st.success(f"Columns loaded from KML: {', '.join(st.session_state.kml_columns)}")
            st.dataframe(display_gdf, width='stretch')

    st.markdown("---")
    st.subheader("2. Export Data")
    ## EXPORT CSV
    # 5. EXPORT TO CSV BUTTON

    ## EXPORT CSV
    # 5. EXPORT TO CSV BUTTON
    def export_gdf_to_csv():
        # Clear previous messages
        st.session_state.last_export_message = None
        st.session_state.last_export_status = None
        
        if st.session_state.kml_gdf_raw is None:
            st.session_state.last_export_message = "Please read the KML data first using the button above."
            st.session_state.last_export_status = "error"
            return

        if st.session_state.uploaded_file_name and TEMP_KML_PATH.exists():
            try:
                kml_name_stem = Path(st.session_state.uploaded_file_name).stem
            except Exception:
                kml_name_stem = "exported_data"
                
            csv_filename = f"{kml_name_stem}.csv"
            
            try:
                final_csv_path = generate_csv_from_gdf(
                    st.session_state.kml_gdf_raw, 
                    DEFAULT_OUTPUT_BASE,
                    csv_filename, 
                    target_folder='csv'
                )           
                
                st.session_state.last_export_message = f"Exported to CSV successfully: `{final_csv_path}`"
                st.session_state.last_export_status = "success"
                
            except Exception as e:
                st.session_state.last_export_message = f"Error exporting to CSV: {e}"
                st.session_state.last_export_status = "error"
        
        else:
            st.session_state.last_export_message = "Please upload a KML file first."
            st.session_state.last_export_status = "warning"
        
    
    df_output_container2 = st.container()

    ## FUNCIONT
    def export_gdf_to_gpkg():
        # Clear previous messages
        st.session_state.last_export_message = None
        st.session_state.last_export_status = None

        if st.session_state.kml_gdf_raw is None:
            st.session_state.last_export_message = "Please read the KML data first using the button above."
            st.session_state.last_export_status = "error"
            return

        if TEMP_KML_PATH.exists():
            # Use the GPKG filename set earlier in the script (Step 1 file upload)
            gpkg_filename = st.session_state.output_filename_gpkg
            
            # Define the full output path
            output_folder = DEFAULT_OUTPUT_BASE / "raw_data"
            output_folder.mkdir(parents=True, exist_ok=True) # Ensure folder exists
            final_gpkg_path = output_folder / gpkg_filename

            try:
                # Check if it's a GeoDataFrame before using to_file
                if not isinstance(st.session_state.kml_gdf_raw, gpd.GeoDataFrame):
                    raise TypeError("Data is not a valid GeoDataFrame for GPKG export.")
                    
                # Use GeoPandas to write the GeoPackage file
                st.session_state.kml_gdf_raw.to_file(final_gpkg_path, driver='GPKG', encoding="utf-8")
                
                st.session_state.last_export_message = f"Exported to GeoPackage successfully: `{final_gpkg_path}`"
                st.session_state.last_export_status = "success"
                
            except Exception as e:
                st.session_state.last_export_message = f"Error exporting to GPKG: {e}"
                st.session_state.last_export_status = "error"
        
        else:
            st.session_state.last_export_message = "Please upload a KML file first."
            st.session_state.last_export_status = "warning"
    # -- BUTTONS LAYOUT ---
    col_csv, col_gpkg = st.columns(2)
    
    with col_csv:
        st.button(
            "Export to CSV", 
            on_click=export_gdf_to_csv, 
            disabled=st.session_state.kml_gdf_raw is None,
            use_container_width=True
        )

    with col_gpkg:
        st.button(
            "Export to GeoPackage (.gpkg)", 
            on_click=export_gdf_to_gpkg, 
            disabled=st.session_state.kml_gdf_raw is None,
            type="secondary", # Use a different type for visual distinction
            use_container_width=True
        )
    # --------------------------

    # --- Persistent Message Rendering (Updated to use generic keys) ---
    if st.session_state.last_export_message:
        with df_output_container2:
            if st.session_state.last_export_status == "success":
                st.success(st.session_state.last_export_message)
            elif st.session_state.last_export_status == "error":
                st.error(st.session_state.last_export_message)
            elif st.session_state.last_export_status == "warning":
                st.warning(st.session_state.last_export_message)


# ==============================================================================
#                                STEP 2: Mapping & Run
# ==============================================================================
elif current_step == "Pre-Processing":
    
    # 1. CASE TYPE SELECTION (MOVED TO TOP)
    st.subheader("Data Type Selection")
    type_options = ["ocorrencia", "manejo"]
    # Use the selectbox here to define the type BEFORE the header and mapping logic
    st.selectbox(
        "Selecione a entrada de Dados: (Ocorrencia or Manejo)", 
        options=type_options,
        index=type_options.index(st.session_state.case_type_selector) if st.session_state.case_type_selector in type_options else 0,
        key="case_type_selector"
    )
    
    # Now retrieve the case_type from the updated session state
    case_type = st.session_state.case_type_selector
    st.header(f"2. Preprocessing **{case_type.upper()}**")
    
    st.subheader("File & Type Selection")
    
    uploaded_file = st.file_uploader(
        "Upload File", 
        type=['csv','gpkg'],
        key="uploader_preprocess",
        help="Select the csv or gpkg file to be preprocessed."
    )
    
    current_input_path = []
    if uploaded_file is not None:
        if st.session_state.uploaded_file_name != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.preprocessing_completed = False 
            st.session_state.processed_file_path = None
            
            st.session_state.uploaded_file_type = Path(uploaded_file.name).suffix
        
        ## check the file type and convert if necessary
        match st.session_state.uploaded_file_type:
            case '.csv':
                st.info("CSV file detected. Will convert to GeoPackage (GPKG) using 'x' and 'y' columns.")
                # convert 
                converted_gpkg_path = convert_csv_to_gpkg(uploaded_file, TEMP_CONVERTED_GPKG_PATH)
                st.session_state.current_input_path = converted_gpkg_path 
                st.success(f"Conversion complete. Using temporary GPKG: `{st.session_state.current_input_path.name}`")
            case '.gpkg':
                st.info("GeoPackage file detected. Ready for preprocessing.")
                output_file_name = DEFAULT_TEMP_DIR / uploaded_file.name
                with open(output_file_name, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Now, create a Path object from the saved file's string path
                st.session_state.current_input_path = output_file_name  
                st.success(f"File saved. Using temporary GPKG: `{st.session_state.current_input_path.name}`")
            case '.kml':
                st.error("KML files are not supported in this step. Please upload a CSV or GPKG file.")
                st.stop()
            case _:
                st.error("Unsupported file type. Please upload a CSV or GPKG file.")
                st.stop()
    

    st.info(f"File that will be mapped/processed: `{st.session_state.current_input_path or 'None'}`")
    
    st.divider()
    
    st.subheader("Column Mapping Configuration")

    st.checkbox(
        "Show/Edit Variable Mapping Table",
        value=st.session_state.show_mapping_table,
        key='show_mapping_table'
    )

    ## Print the columns present at the dataset 
    if (st.session_state.show_mapping_table== True) & (st.session_state.uploaded_file_name is not None):
        def print_cols(path):
            gdf = gpd.read_file(path)
            return gdf.columns.tolist()
        st.info(f"The columns presented at the dataframe are: {print_cols(st.session_state.current_input_path)}")
    
    # --- Mapping and Run Logic (Based on the case_type set at the top) ---
    if st.session_state.schema_data and case_type in st.session_state.schema_data:
        
        # load json based on case type
        table_config = st.session_state.schema_data[case_type]['mappings']
        data = []
        for mapping in table_config:
            data.append({
                "GDF Column (Editable)": mapping['source_column'],
                "Database Column": mapping['db_column'],
                "GDF Type": mapping['data_type_source'],
                "DB Type": mapping['data_type_db']
            })
            
        df_config = pd.DataFrame(data)
        
        # --- CONDITIONAL DISPLAY OF THE MAPPING TABLE ---
        if st.session_state.show_mapping_table:
            st.info("Edit the 'GDF Column' names to match your data's column names.")
            
            edited_df = st.data_editor(
                df_config,
                column_config={
                    "GDF Column (Editable)": st.column_config.TextColumn("GDF Column (Editable)", help="The column name in the GeoDataFrame (from input file)", required=True),
                    "Database Column": st.column_config.TextColumn(disabled=True),
                    "GDF Type": st.column_config.TextColumn(disabled=True),
                    "DB Type": st.column_config.TextColumn(disabled=True)
                },
                key="mapping_editor",
                hide_index=True,
                width='stretch'
            )
        else:
            if 'mapping_editor' in st.session_state:
                edited_df = st.session_state.mapping_editor
            else:
                edited_df = df_config 
                
        st.divider()
        
        st.subheader("Run Preprocessing Script")
        
        if st.button("▶️ Run Preprocessing", type="primary"):
            
            if st.session_state.current_input_path is None:
                st.error("Cannot run: No valid input file path found.")
                st.stop()

            st.info("Starting preprocessing...")
            final_path = None
            
            # Use the currently selected case_type from session state
            current_case_type = st.session_state.case_type_selector
            
            # Use the stem of the original uploaded file for the output file name
            expected_output_filename = st.session_state.current_input_path.stem + "_ps.gpkg"

            args = [
                "python", 
                PREPROCESS_SCRIPT,
                # PASS THE CORRECT CASE TYPE
                "--type", current_case_type, 
                # PASS THE CORRECT INPUT FILE PATH
                "--file", st.session_state.current_input_path, 
                "--output-file-name", expected_output_filename,
                "--path-folder-name", st.session_state.output_path,
                "--overwrite", "True"
            ]

            with st.spinner('Running the preprocessing script...'):
                try:
                    process_result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=120)
                    st.code(process_result.stdout)
                    
                    # FINAL_PATH DEFINITION (ONLY ON SUCCESS)
                    final_path = Path(st.session_state.output_path) / st.session_state.output_folder_name / expected_output_filename

                    st.session_state.processed_file_path = str(final_path) 
                    st.session_state.preprocessing_completed = True
                    st.session_state.manual_import_file_path = None
                    
                except subprocess.CalledProcessError as e:
                    # Catch the specific non-zero exit error
                    st.subheader("Preprocessing Error (Failed Script Execution)")
                    st.error("The preprocessing script failed to execute correctly (non-zero exit status).")
                    
                    st.warning("Error Output (stderr) from script:")
                    st.code(e.stderr or "No stderr captured.")
                    
                    st.info("Standard Output (stdout) from script:")
                    st.code(e.stdout or "No stdout captured.")

                except subprocess.TimeoutExpired:
                    st.error("The preprocessing script timed out.")

                except FileNotFoundError:
                    st.error(f"Error: `{PREPROCESS_SCRIPT}` not found. Check your file paths.")

                except Exception as e:
                    # Catch all other unexpected errors
                    st.subheader("Unexpected Error")
                    st.error(f"An unexpected error occurred: {e}")
                
                finally:
                    st.success(f" **Bora mané nao mosca!** File saved to: `{final_path}`")
                    st.balloons()
                    if TEMP_KML_PATH.exists():
                        os.remove(TEMP_KML_PATH)
                        os.remove(TEMP_PREPROCESS_PATH)
                        os.remove(TEMP_CONVERTED_GPKG_PATH)
                        pass
    
    else:
        st.error("Error: Schema configuration not loaded for the selected data type.")

# ==============================================================================
#                                 Database Import (Keep as is)
# ==============================================================================
elif current_step == "Database Import":
    def run_db_import(file_path, case_type, host, port, database, user, password):
        os.environ['host'] = host
        os.environ['port'] = str(port)
        os.environ['database'] = database
        os.environ['user'] = user
        os.environ['password'] = password
        
        args = [
            "python", 
            DB_IMPORTER_SCRIPT,
            "--type", case_type,
            "--file_name", str(file_path)
        ]
        
        try:
            process_result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True,
                timeout=300
            )
            st.subheader("Database Import Log (Success)")
            st.code(process_result.stdout)
            st.success(f"✅ Data for **{case_type.upper()}** successfully imported into the database!")
            return True

        except subprocess.CalledProcessError as e:
            st.subheader("Database Import Error (Failure)")
            st.error("The database import script failed to run.")
            st.code(e.stderr)
            if e.stdout:
                st.code(e.stdout)
            return False
        except subprocess.TimeoutExpired:
            st.error("The database import script timed out.")
            return False
        except FileNotFoundError:
            st.error(f"Error: `{DB_IMPORTER_SCRIPT}` not found. Check your file paths.")
            return False
        finally:
            for key in ['host', 'port', 'database', 'user', 'password']:
                if key in os.environ:
                    del os.environ[key]

    st.header(" Import into PostgreSQL/PostGIS")

    # --- File Selection Logic ---
    st.subheader("File Selection")

    import_file_path = None
    case_type = st.session_state.case_type_selector


    st.info("Select or upload a GeoPackage (.gpkg) file to import.")
        
    uploaded_gpkg_file = st.file_uploader(
            "Upload GeoPackage (.gpkg) File", 
            type=['gpkg'],
            key="gpkg_uploader",
            help="Select the GPKG file for direct import to the database."
        )

    if uploaded_gpkg_file is not None:
        try:
            bytes_data = uploaded_gpkg_file.getvalue()
            output_file_name = DEFAULT_TEMP_DIR / uploaded_gpkg_file.name
            with open(output_file_name, "wb") as f:
                f.write(bytes_data)
            st.session_state.manual_import_file_path = str(output_file_name)
            import_file_path = output_file_name
            st.success(f"File **{uploaded_gpkg_file.name}** uploaded successfully.")
        except Exception as e:
            st.error(f"Error saving temporary GPKG file: {e}")
            st.session_state.manual_import_file_path = None
    elif st.session_state.manual_import_file_path:
            import_file_path = Path(st.session_state.manual_import_file_path)
            st.info(f"Using previously uploaded file: `{import_file_path.name}`")
    
    st.divider()
    st.subheader("Select the Table to be imported")
    case_type_options = ["ocorrencia", "manejo"]
    case_type = st.selectbox(
        "Selecione em qual tabela será importado os arquivo.", 
        options=case_type_options,
        index=case_type_options.index(st.session_state.case_type_selector),
        key="import_case_type_selector",
        help="The table structure in the database depends on this type."
    )


    st.markdown("---")

    if import_file_path:
        st.markdown(f"**Target File:** `{import_file_path}` (Type: **{case_type.upper()}**)")
    else:
        st.error("No GeoPackage file selected for import.")
        st.stop()
        
    st.subheader("Database Credentials")
    st.info("Enter your database connection details below to push the processed GeoPackage.")

    col_host, col_port = st.columns([3, 1])
    with col_host:
        st.text_input("Host", key="db_host")
    with col_port:
        st.text_input("Port", key="db_port")
        
    st.text_input("Database Name", key="db_database")
    st.text_input("User", key="db_user")
    st.text_input("Password", type="password", key="db_password")

    st.markdown("---")
    
    if st.button("🚀 Start Database Import", type="primary"):
        if not import_file_path.exists():
            st.error(f"Cannot run import: File not found at: `{import_file_path}`.")
            st.stop()
        
        with st.spinner(f'Connecting to database and importing {case_type} data...'):
            run_db_import(
                file_path=import_file_path,
                case_type=case_type,
                host=st.session_state.db_host,
                port=st.session_state.db_port,
                database=st.session_state.db_database,
                user=st.session_state.db_user,
                password=st.session_state.db_password
            )