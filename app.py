import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from api_call import parse_results_with_llm, search_query
from google.oauth2.service_account import Credentials
import gspread
import logging
import io
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", message="Examining the path of torch.classes raised")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize session state variables
if "data" not in st.session_state:
    st.session_state["data"] = None
if "selected_column" not in st.session_state:
    st.session_state["selected_column"] = None
if "generated_queries" not in st.session_state:
    st.session_state["generated_queries"] = None
if "parsed_results" not in st.session_state:
    st.session_state["parsed_results"] = None
if "data_source" not in st.session_state:
    st.session_state["data_source"] = None
if "query_template" not in st.session_state:
    st.session_state["query_template"] = None  # Ensure query template is initialized

# Function to load data from Google Sheets
def load_google_sheet(sheet_url):
    try:
        credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = gspread.authorize(credentials)
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.get_worksheet(0)  # First sheet
        data = pd.DataFrame(worksheet.get_all_records())
        return data
    except Exception as e:
        st.error(f"Error loading Google Sheet: {e}")
        return None

# Function to upload CSV or Google Sheets data
def upload_data():
    st.sidebar.title("Data Input")
    data_source = st.sidebar.radio("Choose Data Source:", ["Upload CSV", "Google Sheets URL"])

    data = None
    if data_source == "Upload CSV":
        uploaded_file = st.sidebar.file_uploader("Upload your CSV file", type=["csv"])
        if uploaded_file:
            data = pd.read_csv(uploaded_file)
            st.session_state["data"] = data
            st.session_state["data_source"] = "CSV"  
            st.success("CSV file uploaded successfully!")
    elif data_source == "Google Sheets URL":
        sheet_url = st.sidebar.text_input("Enter Google Sheets URL")
        if sheet_url:
            data = load_google_sheet(sheet_url)
            if data is not None:
                st.session_state["data"] = data
                st.session_state["data_source"] = "Google Sheets"  
                st.success("Data loaded successfully from Google Sheets!")
    
    return st.session_state.get("data")

# Function for dynamic query input
def dynamic_query_input(data):
    st.header("Dynamic Query Input with Custom Prompt")
    
    if data is not None and st.checkbox("Dynamic_Query"):
        primary_column = st.selectbox("Select the main column for entity replacement", data.columns, key="dynamic_query_input_column")
        
        # Set the selected column in session state
        if primary_column:
            st.session_state["selected_column"] = primary_column

        query_template = st.text_input("Enter a custom prompt with {entity} placeholder", 
                                "Get me the email address of {entity} company for contacting them")

        if primary_column and query_template:
            generated_queries = [query_template.replace("{entity}", str(entity)) for entity in data[primary_column].unique()]
            st.write("Generated Queries:")
            for query in generated_queries:
                st.write(query)
            st.session_state["generated_queries"] = generated_queries
            st.session_state["query_template"] = query_template  # Store the custom prompt for later use
    else:
        st.warning("No data available. Please Enable Dynamic_Query.")

# Function to perform automated web search and parse results with LLM
def automated_web_search_and_parse(filtered_data):
    entity_column = st.session_state.get("selected_column")
    
    # Check if a valid column for entities is selected
    if entity_column is None or entity_column not in filtered_data.columns:
        st.error("Please select a valid column for entities.")
        return

    st.header("Automated Web Search and LLM Parsing")

    # Check if generated queries are available in session state
    if "generated_queries" not in st.session_state or not st.session_state["generated_queries"]:
        st.warning("Please generate queries first using the custom prompt.")
        return

    # Enable search and parsing if the checkbox and button are selected
    if st.checkbox("Enable Automated Web Search and Parsing") and st.button("Run Automated Web Search and Parse"):
        results_storage = {}
        query_template = st.session_state.get("query_template", "Get me the email address of {entity}")
        
        # Get unique entities from the selected column in the filtered data
        unique_entities = filtered_data[entity_column].unique()
        
        for entity in unique_entities:
            query = query_template.replace("{entity}", str(entity))
            st.write(f"Searching for: {query}")
            logging.info(f"Running search query for entity '{entity}' with query: '{query}'")
            try:
                # Perform the search query using the provided entity
                search_results = search_query(entity, query)
                
                # Check if search results are valid and structured correctly
                if isinstance(search_results, list) and all(isinstance(result, dict) for result in search_results):
                    # Structure results for parsing
                    structured_results = [
                        {
                            "entity": entity,
                            "title": result.get("title", "N/A"),
                            "link": result.get("link", "N/A"),
                            "snippet": result.get("snippet", "N/A")
                        }
                        for result in search_results
                    ]
                    parsed_output = parse_results_with_llm(structured_results)
                    results_storage[entity] = parsed_output
                    
                else:
                    st.write(f"No valid results found for {entity}.")
                    logging.warning(f"Unexpected search results format for entity '{entity}': {search_results}")

            except Exception as e:
                logging.error(f"Error for entity '{entity}': {e}")
                st.error(f"Error for entity '{entity}': {e}")
                continue

        # Store parsed results in session state
        st.session_state["parsed_results"] = results_storage
        st.success("Search and parsing completed.")

            
# Function to display parsed results and provide options to download or update Google Sheets
def display_and_store_results():
    st.header("Extracted Information")
    
    if "parsed_results" in st.session_state and st.session_state["parsed_results"]:
        parsed_data = st.session_state["parsed_results"]
        
        # Convert parsed results to a DataFrame for display and download
        results_df = pd.DataFrame([
            {"Entity": entity, "Extracted Info": info}
            for entity, info in parsed_data.items()
        ])

        # Display results in a table format
        st.write("Parsed Data:")
        st.dataframe(results_df)

        # Provide download option as CSV
        csv_buffer = io.StringIO()
        results_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="extracted_info.csv",
            mime="text/csv"
        )

        # Update Google Sheets option if Google Sheets is connected
        if st.session_state.get("data_source") == "Google Sheets":
            if st.button("Update Google Sheet"):
                try:
                    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
                    client = gspread.authorize(credentials)
                    sheet = client.open_by_url(st.session_state.get("sheet_url"))
                    worksheet = sheet.get_worksheet(0)
                    worksheet.update([results_df.columns.values.tolist()] + results_df.values.tolist())
                    st.success("Google Sheet updated successfully!")
                except Exception as e:
                    st.error(f"Failed to update Google Sheet: {e}")
    else:
        st.warning("No extracted data available to display.")

# Function for histogram display
def display_histogram(data):
    st.header("Histogram")
    numeric_columns = data.select_dtypes(include='number').columns
    if not numeric_columns.empty:
        hist_field = st.selectbox("Select a field for histogram:", numeric_columns)
        if hist_field:
            plt.figure(figsize=(10, 5))
            sns.histplot(data[hist_field], kde=True)
            st.pyplot(plt)
    else:
        st.info("No numeric columns available for histogram.")

# Function for filtering data
def data_filtering(data):
    st.header("Data Filtering Options")
    filter_field = st.selectbox("Select a field to filter by:", data.columns)
    if filter_field:
        if pd.api.types.is_numeric_dtype(data[filter_field]):
            filter_type = st.selectbox("Select filter type:", ["Range", "Greater than or equal to", "Less than or equal to", "Equal to"])
            if filter_type == "Range":
                min_val, max_val = st.slider("Select range:", 
                                             min_value=float(data[filter_field].min()), 
                                             max_value=float(data[filter_field].max()), 
                                             value=(float(data[filter_field].min()), float(data[filter_field].max())))
                data = data[(data[filter_field] >= min_val) & (data[filter_field] <= max_val)]
            elif filter_type == "Greater than or equal to":
                min_val = st.number_input("Minimum value:", value=float(data[filter_field].min()))
                data = data[data[filter_field] >= min_val]
            elif filter_type == "Less than or equal to":
                max_val = st.number_input("Maximum value:", value=float(data[filter_field].max()))
                data = data[data[filter_field] <= max_val]
            elif filter_type == "Equal to":
                value = st.number_input("Value to equal:", value=float(data[filter_field].min()))
                data = data[data[filter_field] == value]
        else:
            unique_values = data[filter_field].unique()
            selected_values = st.multiselect("Select values:", unique_values)
            if selected_values:
                data = data[data[filter_field].isin(selected_values)]
    st.write("Filtered Data")
    st.dataframe(data)
    return data

# main function
def main():
    st.title("AI Agent Dashboard")

    # Upload and load data
    data = upload_data()

    # Allow user to filter data
    if data is not None:
        st.write("### Data Preview ###")
        st.dataframe(data)
        
                # Filtering enabled if selected
        if st.sidebar.checkbox("Enable Filtering"):
            filtered_data = data_filtering(data)
        else:
            filtered_data = data
        
        # Display histogram if enabled
        if st.sidebar.checkbox("Show Histogram"):
            display_histogram(filtered_data)
        
        # Dynamic query input and generation
        dynamic_query_input(filtered_data)

        # Automated web search and parsing
        automated_web_search_and_parse(filtered_data)

        # Display and store parsed results
        display_and_store_results()
    else:
        st.warning("No data uploaded or loaded. Please provide data to proceed.")

if __name__ == "__main__":
    main()
