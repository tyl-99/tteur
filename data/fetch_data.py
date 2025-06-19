import pandas as pd
import datetime
import calendar
import os
import logging
from twisted.internet import reactor
from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

forex_symbols = {
    "EUR/USD": 1, "GBP/USD": 2, "EUR/JPY": 3, "EUR/GBP": 9, "USD/JPY": 4, "GBP/JPY": 7
}

class DataFetcher:
    def __init__(self):
        self.client_id = os.getenv("CTRADER_CLIENT_ID")
        self.client_secret = os.getenv("CTRADER_CLIENT_SECRET")
        self.account_id = int(os.getenv("CTRADER_ACCOUNT_ID"))
        self.access_token = os.getenv("CTRADER_ACCESS_TOKEN")
        
        self.host = EndPoints.PROTOBUF_DEMO_HOST
        self.client = Client(self.host, EndPoints.PROTOBUF_PORT, TcpProtocol)
        
        self.pairs_to_fetch = []
        self.current_pair_index = 0
        self.start_date = None
        self.end_date = None
        self.all_data = {}
        
    def fetch_data(self, pairs, start_date, end_date):
        self.pairs_to_fetch = pairs
        self.start_date = start_date
        self.end_date = end_date
        self.current_pair_index = 0
        self.all_data = {}
        
        logger.info(f"🚀 Fetching data for {pairs}")
        logger.info(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        self.client.setConnectedCallback(self.connected)
        self.client.setDisconnectedCallback(self.disconnected)
        self.client.startService()
        
        reactor.run()
    
    def connected(self, client):
        logger.info("✅ Connected to cTrader server")
        self.authenticate_app()
    
    def authenticate_app(self):
        logger.info("🔐 Authenticating application...")
        appAuth = ProtoOAApplicationAuthReq()
        appAuth.clientId = self.client_id
        appAuth.clientSecret = self.client_secret
        deferred = self.client.send(appAuth)
        deferred.addCallbacks(self.onAppAuthSuccess, self.onError)
    
    def onAppAuthSuccess(self, response):
        logger.info("✅ Application authenticated")
        self.authenticate_user()
    
    def authenticate_user(self):
        logger.info("🔐 Authenticating user...")
        userAuth = ProtoOAAccountAuthReq()
        userAuth.ctidTraderAccountId = self.account_id
        userAuth.accessToken = self.access_token
        deferred = self.client.send(userAuth)
        deferred.addCallbacks(self.onUserAuthSuccess, self.onError)
    
    def onUserAuthSuccess(self, response):
        logger.info("✅ User authenticated successfully")
        logger.info(f"📊 Starting data fetch for {len(self.pairs_to_fetch)} pairs")
        self.fetch_next_pair()
    
    def fetch_next_pair(self):
        if self.current_pair_index >= len(self.pairs_to_fetch):
            logger.info("✅ All data fetched. Saving to Excel...")
            self.save_to_excel()
            reactor.stop()
            return
        
        pair = self.pairs_to_fetch[self.current_pair_index]
        logger.info(f"📈 Fetching {pair} data... ({self.current_pair_index + 1}/{len(self.pairs_to_fetch)})")
        self.sendTrendbarReq(pair)
    
    def sendTrendbarReq(self, pair):
        """Send trendbar request - based on ctrader.py method"""
        request = ProtoOAGetTrendbarsReq()
        request.ctidTraderAccountId = self.account_id
        request.period = ProtoOATrendbarPeriod.Value("M30")  # 30-minute bars
        
        # Set time range
        request.fromTimestamp = int(calendar.timegm(self.start_date.utctimetuple())) * 1000
        request.toTimestamp = int(calendar.timegm(self.end_date.utctimetuple())) * 1000
        request.count = 1000000
        
        # Get symbol ID
        symbol_id = forex_symbols.get(pair)
        if not symbol_id:
            logger.error(f"❌ Symbol ID not found for {pair}. Skipping.")
            self.all_data[pair] = pd.DataFrame()
            self.current_pair_index += 1
            reactor.callLater(0.5, self.fetch_next_pair)
            return
            
        request.symbolId = symbol_id
        
        deferred = self.client.send(request, clientMsgId=None)  # Same as ctrader.py
        deferred.addCallbacks(self.onTrendbarDataReceived, self.onError)
    
    def onTrendbarDataReceived(self, response):
        """Process trendbar data - based on ctrader.py method"""
        pair = self.pairs_to_fetch[self.current_pair_index]
        
        try:
            # Extract the response using Protobuf.extract (same as ctrader.py)
            parsed = Protobuf.extract(response)
            trendbars = parsed.trendbar  # This is a list of trendbar objects
            
            if not trendbars:
                logger.warning(f"⚠️ No data received for {pair}")
                self.all_data[pair] = pd.DataFrame()
            else:
                # Convert to DataFrame (exact same logic as ctrader.py)
                data = []
                for tb in trendbars:
                    data.append({
                        'timestamp': datetime.datetime.utcfromtimestamp(tb.utcTimestampInMinutes * 60),
                        'open': (tb.low + tb.deltaOpen) / 1e5,
                        'high': (tb.low + tb.deltaHigh) / 1e5,
                        'low': tb.low / 1e5,
                        'close': (tb.low + tb.deltaClose) / 1e5,
                        'volume': tb.volume
                    })
                
                df = pd.DataFrame(data)
                df.sort_values('timestamp', inplace=True, ascending=True)  # Sort ascending for backtest
                self.all_data[pair] = df
                logger.info(f"✅ {pair}: {len(df)} bars loaded")
            
        except Exception as e:
            logger.error(f"❌ Error processing data for {pair}: {e}")
            self.all_data[pair] = pd.DataFrame()
        
        # Move to next pair
        self.current_pair_index += 1
        reactor.callLater(0.5, self.fetch_next_pair)  # Small delay between requests
    
    def save_to_excel(self):
        """Save all data to Excel file"""
        os.makedirs('backtest_data', exist_ok=True)
        
        try:
            with pd.ExcelWriter('backtest_data/forex_data1.xlsx', engine='openpyxl') as writer:
                total_bars = 0
                for pair, df in self.all_data.items():
                    if not df.empty:
                        sheet_name = pair.replace('/', '_')
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        total_bars += len(df)
                        logger.info(f"💾 Saved {pair} to sheet {sheet_name} ({len(df)} bars)")
                    else:
                        logger.warning(f"⚠️ No data to save for {pair}")
            
            logger.info(f"🎉 All data saved to backtest_data/forex_data.xlsx")
            logger.info(f"📊 Total bars fetched: {total_bars:,}")
            
        except Exception as e:
            logger.error(f"❌ Error saving to Excel: {e}")
    
    def onError(self, failure):
        logger.error(f"❌ cTrader API Error: {failure}")
        reactor.stop()
    
    def disconnected(self, client, reason):
        logger.info(f"🔌 Disconnected from cTrader: {reason}")

if __name__ == "__main__":
    try:
        fetcher = DataFetcher()
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'EUR/JPY', 'GBP/JPY', 'EUR/GBP']
        
        # MAY 2024 TO MAY 2025 (1 YEAR OF RECENT DATA)
        start = datetime.datetime(2023, 5, 1)    # May 1, 2024
        end = datetime.datetime(2025, 5, 31)     # May 31, 2025
        
        logger.info(f"🎯 Fetching RECENT YEAR of data: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        logger.info(f"📊 Expected bars per pair: ~18,720 (390 days × 48 bars/day)")
        
        fetcher.fetch_data(pairs, start, end)
        
    except KeyboardInterrupt:
        logger.info("🛑 Data fetch interrupted by user")
        if reactor.running:
            reactor.stop()
    except Exception as e:
        logger.error(f"❌ Error in data fetcher: {e}")
        if reactor.running:
            reactor.stop()