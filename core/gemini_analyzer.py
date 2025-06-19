import os
import json
import re
import time
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self, use_real_gemini=True):
        self.use_real_gemini = use_real_gemini
        self.api_call_count = 0
        self.client = None
        
        if use_real_gemini:
            self.gemini_apikey = os.getenv("GEMINI_APIKEY")
            if self.gemini_apikey:
                try:
                    # Initialize exactly like in ctrader.py
                    self.client = genai.Client(api_key=self.gemini_apikey)
                    logger.info("✅ Gemini API initialized")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Gemini: {e}")
                    self.use_real_gemini = False
            else:
                logger.error("❌ GEMINI_APIKEY not found")
                self.use_real_gemini = False
    
    def analyze(self, prompt, pair, timestamp):
        """Analyze trading prompt and return decision"""
        if not self.use_real_gemini or not self.client:
            return {"decision": "NO TRADE", "reason": "Gemini disabled", "volume": 0, "entry_price": 0, "stop_loss": 0, "take_profit": 0}
        
        try:
            self.api_call_count += 1
            logger.info(f"🤖 Gemini call #{self.api_call_count} for {pair}")
            
            # Call Gemini exactly like in ctrader.py
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-04-17", contents=prompt
            )
            gemini_response = response.text
            
            # Clean and parse JSON exactly like ctrader.py
            gemini_decision = re.sub(r"```json\n|```", "", gemini_response).strip()
            result = json.loads(gemini_decision)
            
            # Validate required fields
            required_fields = ["decision", "volume", "entry_price", "stop_loss", "take_profit"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"⚠️ Missing field '{field}' in Gemini response for {pair}")
                    return {"decision": "NO TRADE", "reason": f"Missing {field}", "volume": 0, "entry_price": 0, "stop_loss": 0, "take_profit": 0}
            
            time.sleep(1.5)  # Rate limiting
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error for {pair}: {e}")
            return {"decision": "NO TRADE", "reason": "Invalid JSON", "volume": 0, "entry_price": 0, "stop_loss": 0, "take_profit": 0}
        except Exception as e:
            logger.error(f"❌ Gemini error for {pair}: {e}")
            return {"decision": "NO TRADE", "reason": f"API Error: {str(e)}", "volume": 0, "entry_price": 0, "stop_loss": 0, "take_profit": 0}