import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("FOREXNEWS_API_TOKEN")
BASE_URL = "https://forexnewsapi.com/api/v1"

def get_forex_news(currency_pair, items=3, page=1, start_date=None, end_date=None, token=API_TOKEN):
    """
    Fetches forex news from Forex News API for a specific currency pair.
    """
    params = {
        "currencypair": currency_pair,
        "items": items,
        "page": page,
        "token": token
    }
    if start_date and end_date:
        params["date"] = f"{start_date}-{end_date}"

    if not token:
        # In a module, it's better to raise an exception or handle this more robustly
        raise ValueError("Error: API Token not found. Please set FOREXNEWS_API_TOKEN in your .env file.")

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status() # Raise an exception for HTTP errors
        news_data = response.json()
        return news_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching forex news: {e}")
        return None
