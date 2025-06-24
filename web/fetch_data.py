import pandas as pd
import datetime
import calendar
import os
import logging
import requests
import json
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self, output_dir="web"):
        self.output_dir = output_dir
        
    def fetch_data_simple(self, pairs, start_date, end_date):
        """Simplified data fetching without Twisted reactor"""
        logger.info(f"🚀 Fetching data for {pairs}")
        logger.info(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Create mock data for now (since the cTrader API has issues in threading)
        all_data = {}
        
        for pair in pairs:
            logger.info(f"📈 Generating sample data for {pair}...")
            
            # Generate sample trendbar data
            data = []
            current_time = start_date
            base_price = self.get_base_price(pair)
            
            while current_time < end_date:
                # Create realistic price movement
                open_price = base_price + (hash(str(current_time)) % 1000 - 500) / 100000
                high_price = open_price + abs(hash(str(current_time + datetime.timedelta(minutes=15))) % 100) / 100000
                low_price = open_price - abs(hash(str(current_time + datetime.timedelta(minutes=10))) % 100) / 100000
                close_price = open_price + (hash(str(current_time + datetime.timedelta(minutes=30))) % 200 - 100) / 100000
                volume = abs(hash(str(current_time)) % 10000) + 1000
                
                data.append({
                    'timestamp': current_time,
                    'open': round(open_price, 5),
                    'high': round(max(open_price, high_price, close_price), 5),
                    'low': round(min(open_price, low_price, close_price), 5),
                    'close': round(close_price, 5),
                    'volume': volume
                })
                
                current_time += datetime.timedelta(minutes=30)  # 30-minute intervals
            
            df = pd.DataFrame(data)
            all_data[pair] = df
            logger.info(f"✅ {pair}: {len(df)} bars generated")
        
        self.save_to_excel(all_data)
        return all_data
    
    def get_base_price(self, pair):
        """Get realistic base prices for currency pairs"""
        base_prices = {
            'EUR/USD': 1.08000,
            'GBP/USD': 1.27000,
            'USD/JPY': 157.000,
            'EUR/JPY': 169.000,
            'GBP/JPY': 200.000,
            'EUR/GBP': 0.85000
        }
        return base_prices.get(pair, 1.0000)
    
    def save_to_excel(self, all_data):
        """Save all data to Excel file in web directory"""
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create timestamp for filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trendbar_data_{timestamp}.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        
        # Also save as latest version
        latest_filepath = os.path.join(self.output_dir, "latest_trendbar_data.xlsx")
        
        try:
            # Only save if we have data
            if not all_data or all(df.empty for df in all_data.values()):
                logger.error("❌ No data to save - all DataFrames are empty")
                return
            
            # Save timestamped version
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                total_bars = 0
                sheets_written = 0
                for pair, df in all_data.items():
                    if not df.empty:
                        sheet_name = pair.replace('/', '_')
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        total_bars += len(df)
                        sheets_written += 1
                        logger.info(f"💾 Saved {pair} to sheet {sheet_name} ({len(df)} bars)")
                    else:
                        logger.warning(f"⚠️ No data to save for {pair}")
                
                if sheets_written == 0:
                    logger.error("❌ No sheets written - cannot create empty Excel file")
                    return
            
            # Save latest version (overwrite)
            with pd.ExcelWriter(latest_filepath, engine='openpyxl') as writer:
                for pair, df in all_data.items():
                    if not df.empty:
                        sheet_name = pair.replace('/', '_')
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"🎉 Data saved to {filepath}")
            logger.info(f"🎉 Latest data saved to {latest_filepath}")
            logger.info(f"📊 Total bars saved: {total_bars:,}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to Excel: {e}")

def fetch_latest_data():
    """Function to be called when website launches - simplified version"""
    try:
        fetcher = DataFetcher(output_dir=".")
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'EUR/JPY', 'GBP/JPY', 'EUR/GBP']
        
        # From January 1, 2025 to current date
        start = datetime.datetime(2025, 1, 1)
        end = datetime.datetime.now()
        
        logger.info(f"🎯 Generating sample data from: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        days_diff = (end - start).days
        expected_bars = days_diff * 48  # 48 bars per day for 30-min intervals
        logger.info(f"📊 Expected bars per pair: ~{expected_bars:,} ({days_diff} days × 48 bars/day)")
        
        return fetcher.fetch_data_simple(pairs, start, end)
        
    except Exception as e:
        logger.error(f"❌ Error in data fetcher: {e}")
        return None

if __name__ == "__main__":
    fetch_latest_data()