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
        accessToken = "huwYoufihXnGtq-H6YAzWRzSMt2jyb8-O4RIuJLScE0"
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

    def sendOrderReq(self, symbol, volume, stop_loss, take_profit, decision):
        self.pending_order = {
            "symbol": symbol,
            "volume": volume,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "decision": decision
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
        request.fromTimestamp = int(calendar.timegm((datetime.datetime.utcnow() - datetime.timedelta(weeks=int(self.trendbarReq[0]))).utctimetuple())) * 1000
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
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        self.trendbar = df
        prompt = Strategy.strategy(df=df, pair=self.current_pair)
        self.analyze_with_claude(prompt)

    def analyze_with_claude(self, prompt):
       
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
        logger.info(f"\n=== Claude's Decision for {self.current_pair} ===")
        logger.info(json.dumps(claude_response, indent=2))
        
        # Remove markdown code block (```json ... ```)
        claude_decision = re.sub(r"```json\n|```", "", claude_response).strip()

        # Parse the JSON
        claude_decision = json.loads(claude_decision)

        decision = claude_decision.get("decision")

        if(decision == "NO TRADE"):
            #self.send_pushover_notification()
            if(self.pairIndex<len(self.pairs)-1):
                self.pairIndex += 1
                self.run_trading_cycle(self.pairs[self.pairIndex])
            elif(self.pairIndex == len(self.pairs)-1):
                print("All Key pairs done.")
                reactor.stop()
        else:
            volume = float(claude_decision.get("volume"))*100000
            stop_loss = float(claude_decision.get("stop_loss"))
            take_profit = float(claude_decision.get("take_profit"))

            self.sendOrderReq(self.current_pair, volume,stop_loss,take_profit,decision)
            #self.send_pushover_notification()
            #self.get_symbol_list()
    
    def send_pushover_notification(self):
        # Replace with your actual credentials from Pushover
        APP_TOKEN = "ah7dehvsrm6j3pmwg9se5h7svwj333"
        USER_KEY = "u4ipwwnphbcs2j8iiosg3gqvompfs2"

        payload = {
            "token": APP_TOKEN,
            "user": USER_KEY,
            "message": f"{self.pending_order['decision']} Executed for Pair {self.pending_order['symbol']}\nStop Loss :{self.pending_order['stop_loss']} ; Take Profit:{self.pending_order['take_profit']}"
        }

        try:
            response = requests.post("https://api.pushover.net/1/messages.json", data=payload)
            if response.status_code == 200:
                print("📲 Pushover notification sent successfully.")
            else:
                print(f"❌ Failed to send notification. Status: {response.status_code}, Error: {response.text}")
        except Exception as e:
            print(f"❌ Error sending Pushover notification: {e}")
    
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
    trader = Trader()
    

