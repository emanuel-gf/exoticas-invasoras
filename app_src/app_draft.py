import streamlit as st
import json
import os
import subprocess
import pandas as pd
from io import StringIO
from pathlib import Path

# Use os.path.expanduser to find the user's home directory and set the Desktop as default base
# Check for common Desktop paths across Windows, macOS, and Linux
# This assumes a standard environment setup.

HOME_DIR = Path.home()
DEFAULT_OUTPUT_BASE = HOME_DIR / "Desktop" / "output"


# Set up the file paths
SCHEMA_FILE = Path("config/schema.json")
KML_READER_SCRIPT = "kml_reader.py"
PREPROCESS_SCRIPT = "preprocess.py"
DB_IMPORTER_SCRIPT = "db_importer.py"
TEMP_KML_PATH = Path("./temp_uploaded.kml")

logo_path = "imgs/icmbio_logo.webp" 

# --- Initial Setup and Schema Loading ---

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

# Initialize Streamlit session state
if 'schema_data' not in st.session_state:
    st.session_state.schema_data = schema_data
if 'kml_columns' not in st.session_state:
    st.session_state.kml_columns = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
    
# FIX 1: Initialize missing attributes
if 'output_path' not in st.session_state:
    st.session_state.output_path = str(DEFAULT_OUTPUT_BASE)
    
if 'output_folder_name' not in st.session_state:
    st.session_state.output_folder_name = "processed_data"

if 'output_filename_base' not in st.session_state:
    st.session_state.output_filename_base = "default_ps.gpkg" # Simpler default

## handles the tab session
if 'active_tab_index' not in st.session_state:
    st.session_state.active_tab_index = 0 # Default to the first tab (Step 1)
    
if 'active_tab_label' not in st.session_state:
    st.session_state.active_tab_label = "Step 1: File/Type Selection" # Default to the first tab label
    
# --- DB Configuration State ---
if 'db_host' not in st.session_state:
    st.session_state.db_host = 'localhost'
if 'db_port' not in st.session_state:
    st.session_state.db_port = '5432'
if 'db_database' not in st.session_state:
    st.session_state.db_database = 'postgres'
if 'db_user' not in st.session_state:
    st.session_state.db_user = 'postgres'
if 'db_password' not in st.session_state:
    st.session_state.db_password = '' # Sensitive data
    

# Create a container with two columns for the logo and the title
col1, col2 = st.columns([2, 5]) # Ratio: 1 for the logo, 6 for the title

with col1:
    # Use st.image for the logo. The width is important for alignment.
    st.image(logo_path, width=150) # Adjust width as needed

with col2:
    # Use st.header or st.subheader to control the size of the title text
    # st.title would be too large and misaligned.
    st.header("Estação Ecologica do Carijos")
    # You can remove the emoji from the title text here if the logo serves the purpose
st.title("Preprocessamento Especies Exoticas Invasoras")

# --- Application Layout (Tabs) ---
# We use st.session_state.active_tab_label to set the index on re-run
tab_names = ["Step 1: File/Type Selection", "Step 2: Column Mapping & Run", "Step 3: Database Import"]
tab1, tab2, tab3 = st.tabs(tab_names) 

# --- Tab Click Handlers (Implicit in the structure below) ---
# Note: Streamlit updates the widget state when the tab is clicked,
# but since st.tabs is complex, the simplest reliable method is to 
# ensure the 'Run Preprocessing' action itself updates the state to the second tab.

# The key fix is that when the button is clicked, we set the state
# to point to the second tab *before* the script re-runs.

# ==============================================================================
#                                  TAB 1: Selection
# ==============================================================================

with tab1:
    st.header("1. Input Configuration")
    
    # KML File Upload
    uploaded_file = st.file_uploader(
        "Upload KML File", 
        type=['kml'],
        key="kml_uploader",
        help="Select the KML file to be analyzed."
    )
    
    # Inside the `if uploaded_file is not None:` block in tab1:
    if uploaded_file is not None:
        if st.session_state.uploaded_file_name != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.kml_columns = None # Reset columns on new file upload
            
            # Dynamically set default output filename when a new file is uploaded
            # --- MODIFIED LOGIC HERE ---
            file_stem = Path(uploaded_file.name).stem
            st.session_state.output_filename = f"{file_stem}_ps.gpkg" # Now directly update the final filename key
            # --- END MODIFIED LOGIC ---
    
        # Save the uploaded file to a temporary location for external scripts
        try:
            bytes_data = uploaded_file.getvalue()
            with open(TEMP_KML_PATH, "wb") as f:
                f.write(bytes_data)
            st.success(f"File **{uploaded_file.name}** uploaded successfully.")
        except Exception as e:
            st.error(f"Error saving temporary file: {e}")

    # Case Type Selector
    type_options = ["ocorrencia", "manejo"]
    st.selectbox(
        "Selecione a entrada de Dados: (Ocorrencia or Manejo)", 
        options=type_options,
        index=0,
        key="case_type_selector" # Value accessed via st.session_state.case_type_selector
    )
    
    # --- Output Folder and Name Selection ---
    
    st.subheader("Output Settings")
    
    # OUTPUT PATH: Using st.text_input to define folder path (since Streamlit lacks a native folder browser)
    st.text_input(
        "Output Base Folder Path", 
        key="output_path",
        help="The prefix path where the processed_data folder will be created. E.g., './output'"
    )
    
    # NEW: Final Output File Name
    st.text_input(
        "Output Filename (excluding path)",
        key="output_filename", # The value is now managed dynamically by the session state logic above
        help="The final processed GeoPackage filename (e.g., mydata_ps.gpkg).",
        disabled=st.session_state.uploaded_file_name is None
    )

    st.subheader("Action")
    
    # Button to read KML columns and update mapping table
    def read_kml_columns():
        if TEMP_KML_PATH.exists():
            try:
                # Run kml_reader.py as a subprocess to get columns
                result = subprocess.run(
                    ["python", KML_READER_SCRIPT, str(TEMP_KML_PATH)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # kml_reader prints columns to stdout as comma-separated string
                kml_cols = result.stdout.strip().split(',')
                st.session_state.kml_columns = kml_cols
                st.success(f"KML Columns read: {', '.join(kml_cols)}")
            
            except subprocess.CalledProcessError as e:
                # kml_reader prints error to stderr
                st.error(f"Error reading KML columns: {e.stderr.strip()}")
                st.session_state.kml_columns = None
            except FileNotFoundError:
                st.error(f"Error: `{KML_READER_SCRIPT}` not found.")
                st.session_state.kml_columns = None
        else:
            st.warning("Please upload a KML file first.")

    st.button("Read KML Columns", on_click=read_kml_columns, type="primary")

# ==============================================================================
#                                  TAB 2: Mapping & Run
# ==============================================================================

with tab2:
    # Use the selected type from Tab 1
    case_type = st.session_state.case_type_selector
    st.header(f"2. Mapping for **{case_type.upper()}**")
    
    if st.session_state.schema_data and case_type in st.session_state.schema_data:
        table_config = st.session_state.schema_data[case_type]['mappings']
        
        # Prepare data for Streamlit's editable data_editor
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
        
        # Editable table: The core of the second page
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

        # Run Preprocess Button
        if st.button("▶️ Run Preprocessing", type="primary"):
            
            st.info("Starting preprocessing...")
            
            # *** NEW FIX HERE ***
            # Set the session state to the second tab (index 1) so we land there on the next re-run
            st.session_state.active_tab_label = "Step 2: Database Import"
            
            if not TEMP_KML_PATH.exists():
                st.error("Cannot run: KML file is not uploaded.")
                st.stop()
            if not st.session_state.kml_columns:
                st.error("Cannot run: Please read KML columns first.")
                st.stop()
            
            st.info("Starting preprocessing...")
            
            # 1. Update the schema in memory with edited GDF column names
            st.session_state.updated_schema = st.session_state.schema_data.copy()
            updated_mappings = []
            for index, row in edited_df.iterrows():
                # Preserve original non-editable values but update source_column
                original_map = table_config[index]
                updated_mappings.append({
                    "source_column": row["GDF Column (Editable)"],
                    "db_column": original_map["db_column"],
                    "data_type_source": original_map["data_type_source"],
                    "data_type_db": original_map["data_type_db"]
                })
            
            st.session_state.updated_schema[case_type]['mappings'] = updated_mappings
            
            # 2. Save the updated schema to the configuration file location
            try:
                with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.updated_schema, f, indent=4)
                st.success("Configuration saved for script execution.")
            except Exception as e:
                st.error(f"Error saving temporary schema: {e}")
                # Optional: Revert schema data in session state if saving fails
                st.session_state.schema_data = load_schema(SCHEMA_FILE) 
                st.stop()
            
            # 3. Prepare arguments for preprocess.py
            # The preprocess.py script expects the output filename to be inferred from the KML input name,
            # but we can pass the output path and folder name as before.
            args = [
                "python", 
                PREPROCESS_SCRIPT,
                "--type", case_type,
                "--file", str(TEMP_KML_PATH),
                "--folder-name", st.session_state.output_folder_name, # Subfolder name
                "--path-folder-name", st.session_state.output_path,   # Base path
                "--overwrite", "True" 
            ]

            # 4. Run preprocess.py
            with st.spinner('Running the KML preprocessing script...'):
                try:
                    process_result = subprocess.run(
                        args,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=120 # Timeout after 120 seconds
                    )
                    
                    # Display output for debugging/confirmation
                    st.subheader("Preprocessing Log (Success)")
                    st.code(process_result.stdout)
                    
                    # Final success message: Calculate final path using the specified output_filename
                    final_path = Path(st.session_state.output_path) / st.session_state.output_folder_name / st.session_state.output_filename
                    
                    # NOTE: preprocess.py currently saves as file_stem_ps.gpkg. 
                    # If you want to use st.session_state.output_filename, 
                    # you would need to modify preprocess.py to accept an --output-name argument.
                    # For now, we confirm the file based on the default expected by preprocess.py.
                    
                    # The preprocess.py saves as f"{file_name.stem}_ps.gpkg", so we use that here for confirmation
                    expected_output_filename = f"{Path(st.session_state.uploaded_file_name).stem}_ps.gpkg"
                    final_path = Path(st.session_state.output_path) / st.session_state.output_folder_name / expected_output_filename

                    st.balloons()
                    st.success(f"🎉 **Preprocessing Complete!** File saved to: `{final_path}`")
                    st.subheader("Next Step:")
                    st.markdown("Click **'Start Database Import'** in the **'Step 3: Database Import'** tab.")
                    
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
                    # Clean up the temporary KML file
                    if TEMP_KML_PATH.exists():
                        os.remove(TEMP_KML_PATH)

    else:
        st.error("Error: Schema configuration not loaded or selected type is invalid.")
        

# ==============================================================================
#                                   TAB 3: Database Import
# ==============================================================================

with tab3:
    def run_db_import(file_path, case_type, host, port, database, user, password):
        """Function to run the database import script."""
        
        # 1. Temporarily save credentials to environment variables for the subprocess
        # Your script currently reads from os.environ
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
                timeout=300 # Longer timeout for DB operations
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
            # Clean up environment variables (optional, but good practice)
            for key in ['host', 'port', 'database', 'user', 'password']:
                if key in os.environ:
                    del os.environ[key]

    with tab3:
        st.header("3. Import into PostgreSQL/PostGIS")
        st.info("Enter your database connection details below to push the processed GeoPackage.")
        
        # Check if a file has been processed to determine the file path
        if not st.session_state.uploaded_file_name:
            st.warning("Please complete Step 1 and Step 2 first.")
            st.stop()
            
        case_type = st.session_state.case_type_selector
        output_filename = st.session_state.output_filename # Already holds the "_ps.gpkg" name
        output_path_base = Path(st.session_state.output_path)
        
        # Assuming no sub-folder (as per your request):
        final_gpkg_path = output_path_base / output_filename
        
        st.markdown(f"**Target File:** `{final_gpkg_path}` (Type: **{case_type.upper()}**)")
        st.markdown("---")

        # --- Database Credentials Input ---
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
        
        # Run Button
        if st.button("🚀 Start Database Import", type="primary"):
            
            # Check if the processed file actually exists
            if not final_gpkg_path.exists():
                st.error(f"Cannot run import: Processed file not found at: `{final_gpkg_path}`. Did Step 2 run successfully?")
                st.stop()
                
            # Set the active tab to 2 (Database Import) before running
            st.session_state.active_tab_label = "Step 3: Database Import"
            
            with st.spinner(f'Connecting to database and importing {case_type} data...'):
                run_db_import(
                    file_path=final_gpkg_path,
                    case_type=case_type,
                    host=st.session_state.db_host,
                    port=st.session_state.db_port,
                    database=st.session_state.db_database,
                    user=st.session_state.db_user,
                    password=st.session_state.db_password
                )