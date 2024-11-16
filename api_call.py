import os
import requests
import logging
import time
from bs4 import BeautifulSoup
import urllib
from transformers import pipeline
from huggingface_hub import login
import tensorflow as tf
import warnings
import re

# Disable TensorFlow warnings
tf.get_logger().setLevel('ERROR')
warnings.filterwarnings("ignore", message="Examining the path of torch.classes raised")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Ensure API keys are set
API_KEY_SCRAPER = os.getenv("API_KEY_SCRAPER") #replace with your own API key from ScraperAPI
api_token = os.getenv("API_TOKEN_HUGGING_FACE") #replace with your own API token from Hugging Face


if not API_KEY_SCRAPER:
    raise ValueError("Scraper API key not found. Set the 'API_KEY_Scraper' environment variable.")
if not api_token:
    raise ValueError("Hugging Face API token not found. Set the 'HUGGING_FACE_API_TOKEN' environment variable.")

# Login to Hugging Face
try:
    login(token=api_token)
except Exception as e:
    logging.error(f"Error during Hugging Face login: {e}")

# Function to perform web search with exponential backoff and filtering for email presence
def search_query(entity, custom_prompt, max_retries=5):
    """
    Perform a web search for a given entity using ScraperAPI, with exponential backoff for rate limiting
    and marking results where emails are not found.

    Args:
    - entity (str): The entity to search for.
    - custom_prompt (str): Custom search prompt.
    - max_retries (int): Maximum number of retries for rate limiting.

    Returns:
    - list: Search results with entries where emails were not found marked accordingly.
    """
    query = custom_prompt.format(entity=entity)
    encoded_query = urllib.parse.quote(query)
    search_url = f"http://api.scraperapi.com?api_key={API_KEY_SCRAPER}&url=https://www.google.com/search?q={encoded_query}"
    headers = {"User-Agent": "Mozilla/5.0"}

    retries = 0
    backoff_time = 1  # Initial backoff time in seconds

    while retries < max_retries:
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            for i, result in enumerate(soup.select(".g")):
                if i >= 5:  # Limit to the first 5 results
                    break
                title = result.select_one("h3").get_text() if result.select_one("h3") else "No title available"
                link = result.select_one("a")["href"] if result.select_one("a") else "No link available"
                snippet = result.select_one(".VwiC3b").get_text() if result.select_one(".VwiC3b") else "No snippet available"
                if "email" in snippet.lower():
                    results.append({
                        "entity": entity,
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
            return results
        
        except requests.exceptions.RequestException as e:
            # Handle rate limiting or connection errors with exponential backoff
            logging.warning(f"Request error for entity '{entity}': {e}. Retrying in {backoff_time} seconds.")
            time.sleep(backoff_time)
            retries += 1
            backoff_time *= 2  # Exponential backoff
        
    # If all retries are exhausted, log an error and return an empty list
    logging.error(f"Max retries reached for entity '{entity}'. No results retrieved.")
    return []

# Load the QA model from Hugging Face
generator = pipeline("question-answering", model="deepset/roberta-base-squad2", tokenizer="deepset/roberta-base-squad2")

def call_llm_with_huggingface(prompt, context):
    """
    Uses Hugging Face's question-answering model to extract specific information 
    based on a prompt and context, with enhanced debugging.

    Args:
    - prompt (str): The question or instruction to guide the extraction.
    - context (str): The text from which the information should be extracted.

    Returns:
    - str: Extracted answer from the context based on the prompt or an error message if extraction fails.
    """
    logging.debug(f"Calling LLM with prompt: {prompt}")
    logging.debug(f"Context provided to LLM: {context}")

    try:
        # Perform question-answering
        results = generator(question=prompt, context=context)
        answer = results['answer']  # Extract the answer directly
        logging.info(f"LLM extracted answer: {answer}")
        return answer
    except Exception as e:
        logging.error(f"Error during Hugging Face model call: {e}", exc_info=True)
        return "Failed to get a response from the Hugging Face model."

def parse_results_with_llm(results):
    """
    Parses a list of search results to extract information (e.g., email addresses) 
    for each entity using the question-answering LLM, with enhanced response validation.

    Args:
    - results (list of dict): Each dictionary contains 'entity', 'title', 'link', and 'snippet' fields.

    Returns:
    - str: The extracted information or a message indicating parsing was unsuccessful.
    """
    if not results:
        logging.warning("No results to parse.")
        return "No results to parse."
    
    # Define a base prompt for email extraction
    base_prompt = "Extract the email address for the given Entity from the following search results if email not found then return the snippet:"

    # Construct context by aggregating snippets for each entity
    context = ""
    for result in results:
        context += f"Entity: {result['entity']}\nTitle: {result['title']}\nLink: {result['link']}\nSnippet: {result['snippet']}\n\n"
        logging.debug(f"Appended result for entity '{result['entity']}' to context.")

    # Attempt to extract information using the LLM
    try:
        response = call_llm_with_huggingface(base_prompt, context)
        
        
        # Use a regex pattern to find a valid email address
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, response)

        # Validate response format and content
        if response and isinstance(response, str) and (matches or "@" in response):
            email = matches[0]
            logging.info(f"Extracted information: {response}")
            return response + email + result['link'] + result['snippet']
        else:
            logging.warning(f"LLM returned an incomplete or invalid response for context: {context}")
            logging.info(f"Extracted information: {response}")
            return  response + result['link'] + result['snippet'] +"(Exact email not found because LLM may not have found relevant data to extract email.)"
    
    except Exception as e:
        logging.error("Error in parse_results_with_llm", exc_info=True)
        return "Error during parsing of results."
