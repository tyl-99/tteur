import datetime,calendar
import pandas as pd
import requests
import pandas as pd
import numpy as np
import anthropic
import logging
import json
import re
import os
from dotenv import load_dotenv
from Strategy import Strategy
from twisted.internet import reactor
from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth, EndPoints
from ctrader_open_api.endpoints import EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import reactor
from google import genai
import threading
import sys


# Forex symbols mapping with IDs
forex_symbols = {
    "EUR/USD": 1,
    "GBP/USD": 2,
    "EUR/JPY": 3,
    "EUR/GBP": 9,
    "USD/JPY": 4,
    "GBP/JPY": 7
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('forex_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Trader:
    def __init__(self):
        self.gemini_apikey = os.getenv("GEMINI_APIKEY")
        self.client_id = os.getenv("CTRADER_CLIENT_ID")
        self.client_secret = os.getenv("CTRADER_CLIENT_SECRET")
        self.account_id = int(os.getenv("CTRADER_ACCOUNT_ID"))

        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
        
        self.host = EndPoints.PROTOBUF_DEMO_HOST
        self.client = Client(self.host, EndPoints.PROTOBUF_PORT, TcpProtocol)
        
        self.trendbarReq = None
        self.trendbar = None
        # To store pending order params
        self.pending_order = None
        self.action = None
        self.df = None

        self.pairIndex = 0
        self.pairs = [
            {'from': 'EUR', 'to': 'USD'},
            {'from': 'GBP', 'to': 'USD'},
            {'from': 'USD', 'to': 'JPY'},
            {'from': 'EUR', 'to': 'JPY'},
            {'from': 'EUR', 'to': 'GBP'},
            {'from': 'GBP', 'to': 'JPY'}
        ]
        self.current_pair = None

        self.active_order = []

        self.connect()
        
    def onError(self, failure):
        print("Error:", failure)

    def connected(self, client):
        print("Connected to server.")
        self.authenticate_app()

    def authenticate_app(self):
        appAuth = ProtoOAApplicationAuthReq()
        appAuth.clientId = self.client_id
        appAuth.clientSecret = self.client_secret
        deferred = self.client.send(appAuth)
        deferred.addCallbacks(self.onAppAuthSuccess, self.onError)

    def onAppAuthSuccess(self, response):
        print("App authenticated.")
        accessToken = os.getenv("CTRADER_ACCESS_TOKEN")
        self.authenticate_user(accessToken)

    def authenticate_user(self, accessToken):
        userAuth = ProtoOAAccountAuthReq()
        userAuth.ctidTraderAccountId = self.account_id
        userAuth.accessToken = accessToken
        deferred = self.client.send(userAuth)
        deferred.addCallbacks(self.onUserAuthSuccess, self.onError)

    def disconnected(self, client, reason):
        print("Disconnected:", reason)

    def onMessageReceived(self, client, message):
        print("Message received:")
        #print(Protobuf.extract(message))

    def connect(self):

        self.client.setConnectedCallback(self.connected)
        self.client.setDisconnectedCallback(self.disconnected)
        self.client.setMessageReceivedCallback(self.onMessageReceived)

        self.client.startService()

        reactor.run()

    def onUserAuthSuccess(self, response):
        print("User authenticated.")
        self.getActivePosition()

    def sendOrderReq(self, symbol, trade_data):
        # Extract data from the trade_data object
        volume = round(float(trade_data.get("volume")), 2) * 100000
        stop_loss = float(trade_data.get("stop_loss"))
        take_profit = float(trade_data.get("take_profit"))
        decision = trade_data.get("decision")
        
        # Store additional trade info for notifications/logging
        self.pending_order = {
            "symbol": symbol,
            "volume": volume,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "decision": decision,
            "entry_price": float(trade_data.get("entry_price", 0)),
            "reason": trade_data.get("reason", ""),
            "winrate": trade_data.get("winrate", ""),
            "risk_reward_ratio": trade_data.get("risk_reward_ratio", ""),
            "potential_loss_usd": trade_data.get("potential_loss_usd", ""),
            "potential_win_usd": trade_data.get("potential_win_usd", ""),
            "volume_calculation": trade_data.get("volume_calculation", ""),
            "loss_calculation": trade_data.get("loss_calculation", ""),
            "win_calculation": trade_data.get("win_calculation", "")
        }
        self.active_order.append(self.pending_order)
        symbol_id = forex_symbols.get(self.pending_order["symbol"])
        
        if symbol_id is not None:
            print(f"Placing market order for {self.pending_order['symbol']}")

            order = ProtoOANewOrderReq()
            order.ctidTraderAccountId = self.account_id
            order.symbolId = symbol_id
            order.volume = int(self.pending_order["volume"])*100

            order.orderType = ProtoOAOrderType.MARKET
            if(self.pending_order["decision"] == "BUY"):
                order.tradeSide = ProtoOATradeSide.BUY
            elif(self.pending_order["decision"] =="SELL"):
                order.tradeSide = ProtoOATradeSide.SELL
            print(f"Placing {order.tradeSide} order for symbol {order.symbolId} with volume {order.volume}")

            deferred = self.client.send(order)
            deferred.addCallbacks(self.onOrderSent, self.onError)
        else:
            print(f"{self.pending_order['symbol']} symbol not found in the dictionary!")

    def onOrderSent(self, response):
        print("Market order sent successfully!")
        message = Protobuf.extract(response)
        print(message)
        position_id = message.position.positionId 
        self.send_pushover_notification()
        self.amend_sl_tp(position_id, self.pending_order["stop_loss"], self.pending_order["take_profit"])

    def amend_sl_tp(self, position_id, stop_loss_price, take_profit_price):
        amend = ProtoOAAmendPositionSLTPReq()
        amend.ctidTraderAccountId = self.account_id
        amend.positionId = position_id
        amend.stopLoss = stop_loss_price
        amend.takeProfit = take_profit_price

        print(f"Setting SL {stop_loss_price} and TP {take_profit_price} for position {position_id}")

        deferred = self.client.send(amend)
        deferred.addCallbacks(self.onAmendSent, self.onError)

    def onAmendSent(self, response):
        print("Amend SL/TP sent successfully!")
        if(self.pairIndex<len(self.pairs)-1):
            self.pairIndex += 1
            self.run_trading_cycle(self.pairs[self.pairIndex])
        elif(self.pairIndex == len(self.pairs)-1):
            print("All Key pairs done.")
            reactor.stop()

    def sendTrendbarReq(self, weeks, period, symbolId):
        self.trendbarReq = (weeks,period,symbolId)
        request = ProtoOAGetTrendbarsReq()
        request.ctidTraderAccountId = self.account_id
        request.period = ProtoOATrendbarPeriod.Value(self.trendbarReq[1])
        if(period != "M1"):
            request.fromTimestamp = int(calendar.timegm((datetime.datetime.utcnow() - datetime.timedelta(weeks=int(self.trendbarReq[0]))).utctimetuple())) * 1000
            request.toTimestamp = int(calendar.timegm(datetime.datetime.utcnow().utctimetuple())) * 1000
        elif(period == "M1"):
            request.fromTimestamp = int(calendar.timegm((datetime.datetime.utcnow() - datetime.timedelta(minutes=40)).utctimetuple())) * 1000
            request.toTimestamp = int(calendar.timegm(datetime.datetime.utcnow().utctimetuple())) * 1000
        request.symbolId = int(forex_symbols.get(self.trendbarReq[2]))
        self.trendbarReq = None
        deferred = self.client.send(request, clientMsgId=None)
        deferred.addCallbacks(self.onTrendbarDataReceived, self.onError)

    def onTrendbarDataReceived(self, response):
        print("Trendbar data received:")
        parsed = Protobuf.extract(response)
        trendbars = parsed.trendbar  # This is a list of trendbar objects
        
        # Convert trendbars to DataFrame
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
        df.sort_values('timestamp', inplace=True, ascending=False)
        df['timestamp'] = df['timestamp'].astype(str)
        if len(self.trendbar) == 0:
            self.trendbar = df
        else:
            # Keep the head (latest value) regardless of minutes
            df_head = df.head(1)
            
            # Filter to keep only rows where minutes are 00 or 30
            df_filtered = df[df['timestamp'].str.extract(r':(\d{2}):')[0].isin(['00', '30'])]
            if not df_filtered.empty:
                # Keep the latest filtered value (first row since sorted descending)
                df_filtered = df_filtered.head(1)
                # Combine head and filtered data
                df = pd.concat([df_head, df_filtered], ignore_index=True).drop_duplicates()
            else:
                # If no 00 or 30 minute data, just use the head
                df = df_head
            self.trendbar = pd.concat([self.trendbar, df], ignore_index=True)
        #news = self.getForexNews()
        #self.sendTrendbarReq(weeks=4, period="M30", symbolId=pair_name)
        if not self.latest_data:
            self.latest_data = True
            self.sendTrendbarReq(weeks=4, period="M1", symbolId=self.current_pair)
            return
        self.trendbar.sort_values('timestamp', inplace=True, ascending=True)
        prompt = Strategy.strategy(df=self.trendbar, pair=self.current_pair)
        self.analyze_with_gemini(prompt)

    def getForexNews(self)->str:

        prompt = f"Find for me forex news for pair {self.current_pair} for today return me in JSON format, including impact and forecast those"
        response = self.claude_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=1024
        )
        claude_response = response.content[0].text
        return claude_response
        

    # def analyze_with_claude(self, prompt):
       
    #     response = self.claude_client.messages.create(
    #         model="claude-3-7-sonnet-20250219",
    #         messages=[
    #             {
    #                 "role": "user",
    #                 "content": prompt,
    #             }
    #         ],
    #         max_tokens=1024
    #     )
    #     claude_response = response.content[0].text
    #     logger.info(f"\n=== Claude's Decision for {self.current_pair} ===")
    #     logger.info(json.dumps(claude_response, indent=2))
        
    #     # Remove markdown code block (```json ... ```)
    #     claude_decision = re.sub(r"```json\n|```", "", claude_response).strip()

    #     # Parse the JSON
    #     claude_decision = json.loads(claude_decision)

    #     decision = claude_decision.get("decision")

    #     if(decision == "NO TRADE"):
    #         #self.send_pushover_notification()
    #         if(self.pairIndex<len(self.pairs)-1):
    #             self.pairIndex += 1
    #             self.run_trading_cycle(self.pairs[self.pairIndex])
    #         elif(self.pairIndex == len(self.pairs)-1):
    #             print("All Key pairs done.")
    #             reactor.stop()
    #     else:
    #         volume = round(float(claude_decision.get("volume")),2)*100000
    #         stop_loss = float(claude_decision.get("stop_loss"))
    #         take_profit = float(claude_decision.get("take_profit"))

    #         self.sendOrderReq(self.current_pair, volume,stop_loss,take_profit,decision)
    #         #self.send_pushover_notification()
    #         #self.get_symbol_list()
    
    def analyze_with_gemini(self, prompt):

        client = genai.Client(api_key=self.gemini_apikey)

        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17", contents=prompt
        )
        gemini_response = response.text
        logger.info(f"\n=== Gemini's Decision for {self.current_pair} ===")
        logger.info(json.dumps(gemini_response, indent=2))
        
        # Remove markdown code block (```json ... ```)
        gemini_decision = re.sub(r"```json\n|```", "", gemini_response).strip()

        # Parse the JSON
        gemini_decision = json.loads(gemini_decision)

        decision = gemini_decision.get("decision")

        if(decision == "NO TRADE"):
            #self.send_pushover_notification()
            if(self.pairIndex<len(self.pairs)-1):
                self.pairIndex += 1
                self.run_trading_cycle(self.pairs[self.pairIndex])
            elif(self.pairIndex == len(self.pairs)-1):
                print("All Key pairs done.")
                reactor.stop()
        else:
            

            self.sendOrderReq(self.current_pair, gemini_decision)
            #self.send_pushover_notification()
            #self.get_symbol_list()
    
    def send_pushover_notification(self):
        APP_TOKEN = "ah7dehvsrm6j3pmwg9se5h7svwj333"
        USER_KEY = "u4ipwwnphbcs2j8iiosg3gqvompfs2"

        # Create organized message with all trade details
        message = self.format_trade_notification()

        payload = {
            "token": APP_TOKEN,
            "user": USER_KEY,
            "message": message,
            "title": f"🚀 {self.pending_order['decision']} Trade Alert - {self.pending_order['symbol']}",
            "priority": 1,  # High priority for trade notifications
            "sound": "cashregister"  # Custom sound for trade alerts
        }

        try:
            response = requests.post("https://api.pushover.net/1/messages.json", data=payload)
            if response.status_code == 200:
                print("📲 Enhanced Pushover notification sent successfully.")
                logger.info(f"Trade notification sent for {self.pending_order['symbol']}")
            else:
                print(f"❌ Failed to send notification. Status: {response.status_code}, Error: {response.text}")
                logger.error(f"Pushover notification failed: {response.text}")
        except Exception as e:
            print(f"❌ Error sending Pushover notification: {e}")
            logger.error(f"Pushover notification error: {str(e)}")

    def format_trade_notification(self):
        """Format comprehensive trade notification message"""
        
        # Header with trade action and pair
        message_parts = [
            f"🎯 {self.pending_order['decision']} TRADE EXECUTED",
            f"💱 Pair: {self.pending_order['symbol']}",
            "",
            "📊 TRADE DETAILS:",
            f"Entry: ${self.pending_order.get('entry_price', 'Market Price'):.5f}",
            f"Stop Loss: ${self.pending_order['stop_loss']:.5f}",
            f"Take Profit: ${self.pending_order['take_profit']:.5f}",
            f"Volume: {self.pending_order['volume'] / 100000:.2f} lots",
            "",
            "📈 RISK ANALYSIS:",
            f"R:R Ratio: {self.pending_order.get('risk_reward_ratio', 'N/A')}",
            f"Max Risk: {self.pending_order.get('potential_loss_usd', '$50')}",
            f"Potential Win: {self.pending_order.get('potential_win_usd', 'N/A')}",
            f"Confidence: {self.pending_order.get('winrate', 'N/A')}",
            "",
            "💡 STRATEGY REASON:",
            f"{self.pending_order.get('reason', 'Technical analysis setup')[:100]}{'...' if len(self.pending_order.get('reason', '')) > 100 else ''}",
            "",
            "🔢 CALCULATIONS:",
            f"Volume: {self.pending_order.get('volume_calculation', 'Risk-based sizing')}",
            f"Loss: {self.pending_order.get('loss_calculation', 'SL distance calculation')}",
            f"Win: {self.pending_order.get('win_calculation', 'TP distance calculation')}",
            "",
            f"⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ]
        
        return "\n".join(message_parts)

    def format_compact_notification(self):
        """Alternative compact version for shorter notifications"""
        
        compact_message = (
            f"🚀 {self.pending_order['decision']} {self.pending_order['symbol']}\n"
            f"📊 Entry: ${self.pending_order.get('entry_price', 0):.5f}\n"
            f"🛑 SL: ${self.pending_order['stop_loss']:.5f} | 🎯 TP: ${self.pending_order['take_profit']:.5f}\n"
            f"📈 R:R: {self.pending_order.get('risk_reward_ratio', 'N/A')} | 🎲 Conf: {self.pending_order.get('winrate', 'N/A')}\n"
            f"💰 Risk: {self.pending_order.get('potential_loss_usd', '$50')} | Win: {self.pending_order.get('potential_win_usd', 'N/A')}\n"
            f"💡 {self.pending_order.get('reason', '')[:80]}{'...' if len(self.pending_order.get('reason', '')) > 80 else ''}\n"
            f"⏰ {datetime.datetime.now().strftime('%H:%M:%S')}"
        )
        
        return compact_message
    
    def getActivePosition(self):
        req = ProtoOAReconcileReq()
        req.ctidTraderAccountId = self.account_id
        deferred = self.client.send(req)
        deferred.addCallbacks(self.onActivePositionReceived, self.onError)
                
    def onActivePositionReceived(self, response):
        parsed = Protobuf.extract(response)
        positions = parsed.position  # List of active positions

        # Store positions as list of dictionaries
        self.active_positions = []

        for pos in positions:
            self.active_positions.append({
                "positionId": pos.positionId,
                "symbolId": pos.tradeData.symbolId,
                "side": "BUY" if pos.tradeData.tradeSide == 1 else "SELL",
                "volume": pos.tradeData.volume,
                "openPrice": pos.price,
                "stopLoss": pos.stopLoss,
                "takeProfit": pos.takeProfit,
            })

        self.pairIndex = 0
        self.run_trading_cycle(self.pairs[self.pairIndex])

    def get_symbol_list(self):
        req = ProtoOASymbolsListReq()
        req.ctidTraderAccountId = self.account_id
        req.includeArchivedSymbols = True
        deferred = self.client.send(req)
        deferred.addCallbacks(self.onSymbolsReceived, self.onError)

    def onSymbolsReceived(self, message):
        print("Message received:")
        try:
            parsed_message = Protobuf.extract(message)
            
            with open("symbols.txt", "w") as f:
                for symbol in parsed_message.symbol:
                    line = f"{symbol.symbolName} (ID: {symbol.symbolId})\n"
                    print(line.strip())  # print to console
                    f.write(line)        # write to file

        except Exception as e:
            print(f"Failed to parse message: {e}")
            print(message)

    def is_symbol_active(self, symbol_id):
        return any(pos["symbolId"] == symbol_id for pos in self.active_positions)

    def run_trading_cycle(self, pair):
    
        try:
            from_curr = pair['from']
            to_curr = pair['to']
            pair_name = f"{from_curr}/{to_curr}"
            logger.info(f"Processing {pair_name}")

            symbol_id = forex_symbols.get(pair_name)
            self.latest_data  = False
            self.trendbar = []

            if(self.is_symbol_active(symbol_id)):
                print(f"{pair_name} is currently Active!")
                if(self.pairIndex<len(self.pairs)-1):
                    self.pairIndex += 1
                    self.run_trading_cycle(self.pairs[self.pairIndex])
                elif(self.pairIndex == len(self.pairs)-1):
                    print("All Key pairs done.")
                    reactor.stop()
            else:
                self.current_pair = pair_name
            
                self.sendTrendbarReq(weeks=4, period="M30", symbolId=pair_name)
                #self.getActivePosition()
                #self.get_symbol_list()

        except Exception as e:
            logger.error(f"Error processing {pair_name}: {str(e)}")

if __name__ == "__main__":
    load_dotenv()
    def force_exit():
        print("Program exceeded 5 minutes. Exiting.")
        reactor.stop()
        sys.exit(1)

    timer = threading.Timer(300, force_exit)  # 300 seconds = 5 minutes
    timer.start()

    trader = Trader()
    

