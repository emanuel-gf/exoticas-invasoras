import streamlit as st
import json
import os
import subprocess
import pandas as pd
from io import StringIO
from pathlib import Path

# --- Constants and Setup ---
HOME_DIR = Path.home()
DEFAULT_OUTPUT_BASE = HOME_DIR / "Desktop" / "output"

SCHEMA_FILE = Path("config/schema.json")
KML_READER_SCRIPT = "kml_reader.py"
PREPROCESS_SCRIPT = "preprocess.py"
DB_IMPORTER_SCRIPT = "db_importer.py"
TEMP_KML_PATH = Path("./temp_uploaded.kml")

logo_path = "imgs/icmbio_logo.webp" 

# Load schema.json
@st.cache_data
def load_schema(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Configuration file not found at: {file_path}")
        return None

schema_data = load_schema(SCHEMA_FILE)

# --- Session State Initialization ---
if 'schema_data' not in st.session_state:
    st.session_state.schema_data = schema_data
if 'kml_columns' not in st.session_state:
    st.session_state.kml_columns = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
if 'output_path' not in st.session_state:
    st.session_state.output_path = str(DEFAULT_OUTPUT_BASE)
if 'output_folder_name' not in st.session_state:
    st.session_state.output_folder_name = "processed_data"
if 'output_filename_base' not in st.session_state:
    st.session_state.output_filename_base = "default_ps.gpkg"
if 'output_filename' not in st.session_state:
    st.session_state.output_filename = "default_ps.gpkg"
if 'preprocessing_completed' not in st.session_state:
    st.session_state.preprocessing_completed = False
# This stores the path from Step 2's successful run.
if 'processed_file_path' not in st.session_state:
    st.session_state.processed_file_path = None
# This stores the path from Step 3's manual upload. It is independent.
if 'manual_import_file_path' not in st.session_state:
    st.session_state.manual_import_file_path = None
# Navigation state
if 'current_step' not in st.session_state:
    st.session_state.current_step = "Step 1: Input & Info"

# Case type selector initialization
if 'case_type_selector' not in st.session_state:
    st.session_state.case_type_selector = "ocorrencia" 

# DB Configuration State
if 'db_host' not in st.session_state:
    st.session_state.db_host = 'localhost'
if 'db_port' not in st.session_state:
    st.session_state.db_port = '5432'
if 'db_database' not in st.session_state:
    st.session_state.db_database = 'postgres'
if 'db_user' not in st.session_state:
    st.session_state.db_user = 'postgres'
if 'db_password' not in st.session_state:
    st.session_state.db_password = ''

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
    "Step 1: Input & Info",
    "Step 2: Column Mapping & Run",
    "Step 3: Database Import"
]

current_step = st.radio(
    "Navigation",
    options=step_options,
    index=step_options.index(st.session_state.current_step),
    horizontal=True,
    key="step_selector"
)

st.session_state.current_step = current_step
st.divider()

# ==============================================================================
#                                STEP 1: Selection (Now with Tabs)
# ==============================================================================

if current_step == "Step 1: Input & Info":
    st.header("1. Input Configuration & Information")
    
    # --- Step 1 Tabs ---
    tab1, tab2 = st.tabs(["**File Upload and Settings**", "**Additional Information**"])
    
    with tab1:
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
                st.session_state.preprocessing_completed = False 
                st.session_state.processed_file_path = None
                st.session_state.manual_import_file_path = None # Reset manual file path too
                
                file_stem = Path(uploaded_file.name).stem
                st.session_state.output_filename = f"{file_stem}_ps.gpkg"
        
            try:
                bytes_data = uploaded_file.getvalue()
                with open(TEMP_KML_PATH, "wb") as f:
                    f.write(bytes_data)
                st.success(f"File **{uploaded_file.name}** uploaded successfully.")
            except Exception as e:
                st.error(f"Error saving temporary file: {e}")

        type_options = ["ocorrencia", "manejo"]
        st.selectbox(
            "Selecione a entrada de Dados: (Ocorrencia or Manejo)", 
            options=type_options,
            index=0,
            key="case_type_selector"
        )
        
        st.subheader("Output Settings")
        
        st.text_input(
            "Output Base Folder Path", 
            key="output_path",
            help="The prefix path where the processed_data folder will be created. E.g., './output'"
        )
        
        # Output Filename
        if st.session_state.preprocessing_completed:
            st.text_input(
                "Output Filename (excluding path)",
                key="output_filename",
                help=f"This file was generated by preprocessing: {st.session_state.output_filename}",
                disabled=True 
            )
        else:
            st.text_input(
                "Output Filename (excluding path)",
                key="output_filename",
                help="The final processed GeoPackage filename (e.g., mydata_ps.gpkg).",
                disabled=st.session_state.uploaded_file_name is None
            )

        st.subheader("Action")
        
        def read_kml_columns():
            if TEMP_KML_PATH.exists():
                try:
                    result = subprocess.run(
                        ["python", KML_READER_SCRIPT, str(TEMP_KML_PATH)],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    kml_cols = result.stdout.strip().split(',')
                    st.session_state.kml_columns = kml_cols
                    st.success(f"KML Columns read: {', '.join(kml_cols)}")
                
                except subprocess.CalledProcessError as e:
                    st.error(f"Error reading KML columns: {e.stderr.strip()}")
                    st.session_state.kml_columns = None
                except FileNotFoundError:
                    st.error(f"Error: `{KML_READER_SCRIPT}` not found.")
                    st.session_state.kml_columns = None
            else:
                st.warning("Please upload a KML file first.")

        st.button("Read KML Columns", on_click=read_kml_columns, type="primary")
        
    with tab2:
        st.subheader("System Information")
        st.markdown(
            """
            > **Epslium Loteris:** Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
            > Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
            > Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi 
            > ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit 
            > in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
            > Excepteur sint occaecat cupidatat non proident, sunt in culpa qui 
            > officia deserunt mollit anim id est laborum.
            """
        )

# ==============================================================================
#                                STEP 2: Mapping & Run
# ==============================================================================

elif current_step == "Step 2: Column Mapping & Run":
    # ... [Keep the entire original logic for Step 2] ...
    case_type = st.session_state.case_type_selector
    st.header(f"2. Mapping for **{case_type.upper()}**")
    
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
        
        st.subheader("KML Columns Found")
        if st.session_state.kml_columns:
            st.code(', '.join(st.session_state.kml_columns))
        else:
            st.warning("No KML columns loaded yet. Go to Step 1 and click 'Read KML Columns'.")

        st.divider()

        if st.button("▶️ Run Preprocessing", type="primary"):
            if not TEMP_KML_PATH.exists():
                st.error("Cannot run: KML file is not uploaded.")
                st.stop()
            if not st.session_state.kml_columns:
                st.error("Cannot run: Please read KML columns first.")
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
                with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.updated_schema, f, indent=4)
                st.success("Configuration saved for script execution.")
            except Exception as e:
                st.error(f"Error saving temporary schema: {e}")
                st.session_state.schema_data = load_schema(SCHEMA_FILE) 
                st.stop()
            
            args = [
                "python", 
                PREPROCESS_SCRIPT,
                "--type", case_type,
                "--file", str(TEMP_KML_PATH),
                "--folder-name", st.session_state.output_folder_name,
                "--path-folder-name", st.session_state.output_path,
                "--overwrite", "True" 
            ]

            with st.spinner('Running the KML preprocessing script...'):
                try:
                    process_result = subprocess.run(
                        args,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=120
                    )
                    
                    st.subheader("Preprocessing Log (Success)")
                    st.code(process_result.stdout)
                    
                    expected_output_filename = f"{Path(st.session_state.uploaded_file_name).stem}_ps.gpkg"
                    final_path = Path(st.session_state.output_path) / st.session_state.output_folder_name / expected_output_filename

                    # Store BOTH the filename AND the complete path in session state
                    st.session_state.output_filename = expected_output_filename
                    st.session_state.processed_file_path = str(final_path) 
                    st.session_state.preprocessing_completed = True
                    st.session_state.manual_import_file_path = None # Clear manual file path
                    
                    st.success(f" **Bora mané nao mosca!** File saved to: `{final_path}`")
                    st.balloons()
                    
                    
                    
                except subprocess.CalledProcessError as e:
                    st.subheader("Preprocessing Error (Failure)")
                    st.error("The preprocessing script failed to run.")
                    st.code(e.stderr)
                    if e.stdout:
                          st.code(e.stdout)
                except subprocess.TimeoutExpired:
                    st.error("The preprocessing script timed out.")
                except FileNotFoundError:
                    st.error(f"Error: `{PREPROCESS_SCRIPT}` not found. Check your file paths.")
                finally:
                    if TEMP_KML_PATH.exists():
                        os.remove(TEMP_KML_PATH)

    else:
        st.error("Error: Schema configuration not loaded or selected type is invalid.")

# ==============================================================================
#                                 STEP 3: Database Import (Independent Page)
# ==============================================================================

elif current_step == "Step 3: Database Import":
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

    st.header("3. Import into PostgreSQL/PostGIS")
    st.info("Enter your database connection details below to push the processed GeoPackage.")

    # --- File Selection Logic ---
    st.subheader("File Selection (GeoPackage)")

    # Option to use file from preprocessing OR upload a new one
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
            # Save the uploaded file temporarily
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
             # Retain the previous manual upload if the page reloaded
             import_file_path = Path(st.session_state.manual_import_file_path)
             st.info(f"Using previously uploaded file: `{import_file_path.name}`")
        
        # If manually uploading, allow the user to select the case type again
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