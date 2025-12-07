import streamlit as st
import json
import os
import subprocess
import pandas as pd
import geopandas as gpd
from io import StringIO
from pathlib import Path

## import build functions
from src.func import parse_kml, generate_csv_from_gdf


# --- Configuration and Setup ---
try:
    from streamlit_extras.switch_page_button import switch_page
    # REMOVED: from streamlit_extras.stylable_container import stylable_container
    # REMOVED: from streamlit_extras.row import row
except ImportError:
    st.error("Please install 'streamlit-extras' module: `pip install streamlit-extras`")
    def switch_page(*args, **kwargs): st.warning("Mocked switch_page")

# --- Constants and Setup ---
HOME_DIR = Path.home()  ## point to home directory 
DEFAULT_OUTPUT_BASE = HOME_DIR / "Desktop" / "output"

SCHEMA_FILE = Path("config/schema.json")
KML_READER_SCRIPT = "kml_reader.py"
PREPROCESS_SCRIPT = "preprocess.py"
DB_IMPORTER_SCRIPT = "db_importer.py"
GENERATE_CSV_SCRIPT = "generate_csv.py"

## create a temp kml to use during the app
TEMP_KML_PATH = Path("./temp_uploaded.kml")

logo_path = "imgs/icmbio_logo.webp"

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
    "Step 2: Column Mapping & Run",
    "Step 3: Database Import"
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
            st.session_state.output_filename_gpkg = f"{file_stem}_ps.gpkg"
    
        try:
            bytes_data = uploaded_file.getvalue()
            with open(TEMP_KML_PATH, "wb") as f:
                f.write(bytes_data)
            st.success(f"File **{uploaded_file.name}** uploaded successfully.")
        except Exception as e:
            st.error(f"Error saving temporary file: {e}")

    ## OLD 
    # type_options = ["ocorrencia", "manejo"]
    # st.selectbox(
    #     "Selecione a entrada de Dados: (Ocorrencia or Manejo)", 
    #     options=type_options,
    #     index=0,
    #     key="case_type_selector"
    # )
    
    # st.subheader("Output Settings (GeoPackage)")
    
    # st.text_input(
    #     "GeoPackage Output Filename (Read-only)",
    #     value=st.session_state.output_filename_gpkg,
    #     help="The name of the processed GeoPackage filename (e.g., mydata_ps.gpkg).",
    #     disabled=True 
    # )

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
            output_folder = DEFAULT_OUTPUT_BASE / "processed_data" # Using a generic folder
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

# ... (STEP 2 and STEP 3 remain the same as they do not contain the dataframe display)

# ==============================================================================
#                                STEP 2: Mapping & Run
# ==============================================================================
elif current_step == "Step 2: Column Mapping & Run":
    case_type = st.session_state.case_type_selector
    st.header(f"2. Mapping for **{case_type.upper()}**")
    
    # --- Column Check Button (Previously Tab 2) ---
    st.subheader("Check KML Columns (Dependent on Step 1)")
    
    if st.button("Check KML Columns"):
        if st.session_state.kml_columns:
            st.info("The columns read from your KML file are:")
            st.code(', '.join(st.session_state.kml_columns))
        else:
            st.warning("No KML columns loaded. Go back to **Step 1: Avenza File (kml)** and click '1. Read KML & Display Data'.")
    
    st.divider()
    
    # --- Mapping and Run Logic (Keep the rest of the original logic) ---
    if st.session_state.schema_data and case_type in st.session_state.schema_data:
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
        
        st.subheader("Column Mapping Configuration")
        st.info("Edit the 'GDF Column' names to match your KML file's column names.")
        
        edited_df = st.data_editor(
            df_config,
            column_config={
                "GDF Column (Editable)": st.column_config.TextColumn(
                    "GDF Column (Editable)",
                    help="The column name in the GeoDataFrame (from KML)",
                    required=True,
                ),
                "Database Column": st.column_config.TextColumn(disabled=True),
                "GDF Type": st.column_config.TextColumn(disabled=True),
                "DB Type": st.column_config.TextColumn(disabled=True)
            },
            key="mapping_editor",
            hide_index=True
        )

        st.divider()

        if st.button("▶️ Run Preprocessing", type="primary"):
            if not TEMP_KML_PATH.exists():
                st.error("Cannot run: KML file is not uploaded.")
                st.stop()
            if not st.session_state.kml_columns:
                st.error("Cannot run: Please read KML columns first in Step 1.")
                st.stop()
            
            st.info("Starting preprocessing...")
            
            # Update schema
            st.session_state.updated_schema = st.session_state.schema_data.copy()
            updated_mappings = []
            for index, row in edited_df.iterrows():
                original_map = table_config[index]
                updated_mappings.append({
                    "source_column": row["GDF Column (Editable)"],
                    "db_column": original_map["db_column"],
                    "data_type_source": original_map["data_type_source"],
                    "data_type_db": original_map["data_type_db"]
                })
            
            st.session_state.updated_schema[case_type]['mappings'] = updated_mappings
            
            try:
                # Save the temporary updated schema (as in original code)
                with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.updated_schema, f, indent=4)
                st.success("Configuration saved for script execution.")
            except Exception as e:
                st.error(f"Error saving temporary schema: {e}")
                st.session_state.schema_data = load_schema(SCHEMA_FILE) 
                st.stop()
            
            # Use the new, read-only GPKG filename
            expected_output_filename = st.session_state.output_filename_gpkg

            args = [
                "python", 
                PREPROCESS_SCRIPT,
                "--type", case_type,
                "--file", str(TEMP_KML_PATH),
                "--folder-name", st.session_state.output_folder_name,
                "--path-folder-name", st.session_state.output_path,
                "--overwrite", "True",
                # The script should be updated to use the Path.stem logic internally
            ]

            with st.spinner('Running the KML preprocessing script...'):
                try:
                    # Mock subprocess execution for demonstration
                    # process_result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=120)
                    
                    st.subheader("Preprocessing Log (Success - Mocked)")
                    st.code(f"MOCK: Script called with args: {args}")
                    
                    final_path = Path(st.session_state.output_path) / st.session_state.output_folder_name / expected_output_filename

                    st.session_state.processed_file_path = str(final_path) 
                    st.session_state.preprocessing_completed = True
                    st.session_state.manual_import_file_path = None
                    
                    st.success(f" **Bora mané nao mosca!** File saved to: `{final_path}`")
                    st.balloons()
                    
                except Exception as e:
                    # In a real run, this would be `subprocess.CalledProcessError`
                    st.subheader("Preprocessing Error (Failure - Mocked)")
                    st.error(f"The preprocessing script failed to run. Error: {e}")
                finally:
                    if TEMP_KML_PATH.exists():
                        # os.remove(TEMP_KML_PATH)
                        pass # Keep for dev, remove in production

    else:
        st.error("Error: Schema configuration not loaded or selected type is invalid.")

# ==============================================================================
#                                 STEP 3: Database Import (Keep as is)
# ==============================================================================
elif current_step == "Step 3: Database Import":
    # --- Keep the entire original logic for Step 3 ---
    def run_db_import(file_path, case_type, host, port, database, user, password):
        # ... (Original run_db_import function logic)
        st.warning("MOCK: DB import skipped. This function needs the DB_IMPORTER_SCRIPT to run.")
        st.success(f"MOCK: Data for **{case_type.upper()}** successfully imported for file: {file_path}")
        return True # Mock success

    st.header("3. Import into PostgreSQL/PostGIS")
    st.info("Enter your database connection details below to push the processed GeoPackage.")

    # --- File Selection Logic ---
    st.subheader("File Selection (GeoPackage)")

    use_preprocessed = st.checkbox(
        "Use GeoPackage from Step 2 Preprocessing",
        value=st.session_state.preprocessing_completed and st.session_state.processed_file_path is not None,
        disabled=not st.session_state.preprocessing_completed
    )

    import_file_path = None
    case_type = st.session_state.case_type_selector

    if use_preprocessed and st.session_state.processed_file_path:
        import_file_path = Path(st.session_state.processed_file_path)
        st.success(f"Using preprocessed file: `{import_file_path}`")
    else:
        st.warning("Select or upload a GeoPackage (.gpkg) file to import.")
        
        uploaded_gpkg_file = st.file_uploader(
            "Upload GeoPackage (.gpkg) File", 
            type=['gpkg'],
            key="gpkg_uploader",
            help="Select the GPKG file for direct import to the database."
        )

        if uploaded_gpkg_file is not None:
            temp_gpkg_path = Path("./temp_uploaded.gpkg")
            try:
                bytes_data = uploaded_gpkg_file.getvalue()
                with open(temp_gpkg_path, "wb") as f:
                    f.write(bytes_data)
                st.session_state.manual_import_file_path = str(temp_gpkg_path)
                import_file_path = temp_gpkg_path
                st.success(f"File **{uploaded_gpkg_file.name}** uploaded successfully.")
            except Exception as e:
                st.error(f"Error saving temporary GPKG file: {e}")
                st.session_state.manual_import_file_path = None
        elif st.session_state.manual_import_file_path:
             import_file_path = Path(st.session_state.manual_import_file_path)
             st.info(f"Using previously uploaded file: `{import_file_path.name}`")
        
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