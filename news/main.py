import pandas as pd
from forex_news_api import get_forex_news # Corrected import
from gemini_processor import analyze_news_batch_with_gemini # Corrected import
import datetime

def run_news_processing_for_backtest(currency_pair: str, start_date_str: str, end_date_str: str):
    """
    Fetches historical news for the specified period with fixed item limit.
    """
    print(f"Fetching raw news for {currency_pair} from {start_date_str} to {end_date_str}...")

    all_raw_news = []
    current_page = 1
    MAX_FOREXNEWSAPI_PAGES = 1 # Hardcoded to 1 page
    items_per_page = 10 # Hardcoded to 3 items per page

    while current_page <= MAX_FOREXNEWSAPI_PAGES:
        print(f"Fetching page {current_page} from Forex News API...")
        news_data = get_forex_news(
            currency_pair=currency_pair,
            items=items_per_page,
            page=current_page,
            start_date=start_date_str,
            end_date=end_date_str
        )

        if news_data and "data" in news_data and len(news_data["data"]) > 0:
            for article in news_data["data"]:
                # Only store necessary fields for Gemini processing
                all_raw_news.append({
                    'date': article.get('date'),
                    'title': article.get('title'),
                    'text': article.get('text'),
                    'news_url': article.get('news_url')
                })
            current_page += 1
        else:
            print(f"No more news found or an error occurred after page {current_page}.")
            break

    if all_raw_news:
        df_raw_news = pd.DataFrame(all_raw_news)
        df_raw_news['date'] = pd.to_datetime(df_raw_news['date'], errors='coerce', utc=True)
        df_raw_news = df_raw_news.dropna(subset=['date'])
        df_raw_news = df_raw_news.sort_values(by='date').reset_index(drop=True)
        print(f"Successfully fetched {len(df_raw_news)} raw news articles.")
        return df_raw_news
    else:
        print("No raw news articles were fetched.")
        return pd.DataFrame()


# Removed simulate_backtest_with_news_analysis function

if __name__ == "__main__":
    # Hardcoded example date range as requested
    BACKTEST_START_DATE_STR = "01302025" # MMDDYYYY
    BACKTEST_END_DATE_STR = "01312025"   # MMDDYYYY
    CURRENCY_PAIR = "EUR-USD"

    # Step 1: Fetch raw news for the specified period (will be max 3 articles)
    raw_news_df = run_news_processing_for_backtest(CURRENCY_PAIR, BACKTEST_START_DATE_STR, BACKTEST_END_DATE_STR)

    if not raw_news_df.empty:
        print("\n--- Analyzing Fetched News Batch with Gemini ---")
        # Convert DataFrame records to list of dicts for Gemini processing
        news_batch_for_gemini = raw_news_df.to_dict(orient='records')

        gemini_result = analyze_news_batch_with_gemini(news_batch_for_gemini)
        
        # ONLY print the sentiment as requested
        print(f"  Gemini Combined Sentiment: {gemini_result.get('sentiment')}")
        
        print("\n--- Analysis Complete ---")
        print("You would now use this combined sentiment as an additional filter for your trade signals.")
        print("For example: if your strategy signals BUY, and Gemini sentiment is 'Bullish', then execute.")
        print("If it's 'Bearish', consider cancelling or reversing the trade.")
    else:
        print("No news articles were available for Gemini analysis.")
