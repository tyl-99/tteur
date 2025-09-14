import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_APIKEY"))

def analyze_news_batch_with_gemini(news_articles: list[dict]) -> dict:
    """
    Processes a batch of news articles using the Gemini LLM to get a combined sentiment and potential impact on EUR/USD.
    """
    if not news_articles:
        return {"sentiment": "Neutral (No News)", "impact_explanation": "No news articles provided for analysis."} 
    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # Using gemini-2.5-flash as requested

        # Construct a combined prompt for all articles
        news_content = ""
        for i, article in enumerate(news_articles):
            news_content += f"Article {i+1} Title: {article.get('title', 'N/A')}\n"
            news_content += f"Article {i+1} Summary: {article.get('text', 'N/A')}\n\n"

        prompt = f"""
Analyze the following collection of forex news articles.
Synthesize the information from all articles to provide a single, overall sentiment (Bullish, Bearish, or Neutral) for the EUR/USD currency pair.
Also, provide a short, combined explanation of the potential impact on EUR/USD based on all the news.

News Articles:
{news_content}

Format your response as a JSON object with 'sentiment' and 'impact_explanation' keys.
Example: {{"sentiment": "Neutral", "impact_explanation": "ECB held rates steady, and US inflation was in line, leading to no strong directional bias for EUR/USD."}}
"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        if response_text.startswith('```json') and response_text.endswith('```'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```') and response_text.endswith('```'):
            response_text = response_text[3:-3].strip()
        
        return json.loads(response_text)
    except Exception as e:
        print(f"Error processing news batch with Gemini: {e}")
        return {"sentiment": "Neutral (Error)", "impact_explanation": f"Failed to process news batch: {e}"}
