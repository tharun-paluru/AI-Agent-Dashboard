# AI Agent Dashboard

## Project Description
The AI Agent Dashboard is a Streamlit-based application that allows users to upload datasets, dynamically generate queries, perform automated web searches, and extract structured information using language models. This tool is designed to streamline data-driven insights and enhance productivity.

## Features  and Technical Stack
- Upload CSV files or connect Google Sheets for real-time data input.
- Dynamic query generation with customizable templates.
- Automated web search and parsing using Hugging Face models.
- Download parsed results as CSV or update directly to Google Sheets.
- Data filtering and histogram visualization for numerical insights.

●  Dashboard/UI  : Streamlit
●  Data Handling  :  pandas  for CSV files 
●  Search API  : ScraperAPI
●  LLM API  : HuggingFaceAPI 
●  Backend  : Python


 

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/tharun-paluru/AI-Agent-Dashboard.git
   cd AI-Agent-Dashboard
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Add your API keys to environment variables:
   - `API_KEY_SCRAPER`: Your ScraperAPI key.
   - `api_token`: Your Hugging Face API token.
   - Use a `.env` file or set them directly in the terminal.

## Usage Guide
1. Run the application:
   ```bash
   streamlit run app.py
   ```
2. Upload a CSV file or connect to a Google Sheet.
3. Define dynamic query templates and run automated searches.
4. View parsed results and download or update Google Sheets.

## API Keys and Environment Variables
- Store your API keys securely in environment variables.
- Add the following to a `.env` file:
  ```env
  API_KEY_SCRAPER=your_scraperapi_key
  API_TOKEN_HUGGING_FACE=your_hugging_face_api_token
  ```
- Ensure the `.env` file is not pushed to the repository by including it in `.gitignore`.

## Optional Features
- Added histogram visualization for numeric fields.
- Supports filtering data based on user-defined conditions.

## Loom Video
[Watch the Video Walkthrough](#) *(Replace `#` with the actual Loom video link after recording)*

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
