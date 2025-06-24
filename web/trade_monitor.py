import datetime
import pandas as pd
import logging
import json
import os
import time
from dotenv import load_dotenv
from twisted.internet import reactor, defer
from twisted.internet.defer import TimeoutError
from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth, EndPoints
from ctrader_open_api.endpoints import EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from twisted.internet import reactor
import threading
import sys

# Forex symbols mapping with IDs (same as in ctrader.py)
forex_symbols = {
    "EUR/USD": 1,
    "GBP/USD": 2,
    "EUR/JPY": 3,
    "EUR/GBP": 9,
    "USD/JPY": 4,
    "GBP/JPY": 7
}

# Reverse mapping for symbol names
symbol_names = {v: k for k, v in forex_symbols.items()}

# Configure logging with UTF-8 encoding for Windows
import sys

# Set up console and file logging with proper encoding
log_handlers = [
    logging.FileHandler('trade_monitor.log', encoding='utf-8'),
]

# For Windows console support
if sys.platform == "win32":
    # Create console handler without emojis to avoid encoding issues
    console_handler = logging.StreamHandler()
    log_handlers.append(console_handler)
else:
    log_handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

class TradeMonitor:
    def __init__(self, json_output=False, days_back=30, start_date=None):
        """Initialize the Trade Monitor with cTrader API credentials"""
        load_dotenv()
        
        self.client_id = os.getenv("CTRADER_CLIENT_ID")
        self.client_secret = os.getenv("CTRADER_CLIENT_SECRET")
        self.account_id = int(os.getenv("CTRADER_ACCOUNT_ID"))
        
        # Use demo host for development
        self.host = EndPoints.PROTOBUF_DEMO_HOST
        self.client = Client(self.host, EndPoints.PROTOBUF_PORT, TcpProtocol)
        
        # Store for closed deals
        self.closed_deals = []
        
        # Timeout settings
        self.api_timeout = 30  # seconds
        self.request_delay = 2  # seconds between requests
        
        # Configuration for command line arguments
        self.json_output = json_output
        self.days_back = days_back
        self.start_date = start_date

        self.connect()
        
    def connect(self):
        """Establish connection to cTrader servers"""
        self.client.setConnectedCallback(self.connected)
        self.client.setDisconnectedCallback(self.disconnected)
        self.client.setMessageReceivedCallback(self.onMessageReceived)

        self.client.startService()
        reactor.run()

    def connected(self, client):
        """Callback when connected to server"""
        if not self.json_output:
            logger.info("Connected to cTrader server.")
        self.authenticate_app()

    def disconnected(self, client, reason):
        """Callback when disconnected from server"""
        logger.info(f"Disconnected from server: {reason}")

    def onMessageReceived(self, client, message):
        """Handle all incoming messages - for debugging purposes"""
        logger.debug("Message received from server")

    def onError(self, failure):
        """Enhanced error handler with timeout handling"""
        error_type = type(failure.value).__name__
        
        if self.json_output:
            # Output error JSON and exit immediately
            output = {
                'success': False,
                'error': f'API error: {str(failure)}',
                'data': {}
            }
            print(json.dumps(output))
            reactor.stop()
            import os
            os._exit(1)
        
        if "TimeoutError" in error_type:
            logger.warning(f"API timeout occurred")
        else:
            logger.error(f"Error: {failure}")
        
        # Stop reactor on error
        reactor.stop()

    def authenticate_app(self):
        """Authenticate the application with cTrader"""
        logger.info("Authenticating application...")
        appAuth = ProtoOAApplicationAuthReq()
        appAuth.clientId = self.client_id
        appAuth.clientSecret = self.client_secret
        
        deferred = self.client.send(appAuth)
        deferred.addTimeout(self.api_timeout, reactor)
        deferred.addCallbacks(self.onAppAuthSuccess, self.onError)

    def onAppAuthSuccess(self, response):
        """Callback when application authentication is successful"""
        if not self.json_output:
            logger.info("Application authenticated successfully.")
        accessToken = os.getenv("CTRADER_ACCESS_TOKEN")
        self.authenticate_user(accessToken)

    def authenticate_user(self, accessToken):
        """Authenticate the user account"""
        if not self.json_output:
            logger.info("Authenticating user account...")
        userAuth = ProtoOAAccountAuthReq()
        userAuth.ctidTraderAccountId = self.account_id
        userAuth.accessToken = accessToken
        
        deferred = self.client.send(userAuth)
        deferred.addTimeout(self.api_timeout, reactor)
        deferred.addCallbacks(self.onUserAuthSuccess, self.onError)

    def onUserAuthSuccess(self, response):
        """Callback when user authentication is successful"""
        if not self.json_output:
            logger.info("User authenticated successfully.")
            logger.info(f"Account ID: {self.account_id}")
        
        # Start retrieving closed deals using configured parameters
        if self.start_date:
            self.get_closed_deals(start_date=self.start_date)
        else:
            # Default to June 15, 2025 if no start date specified
            self.get_closed_deals(start_date='2025-06-15', days_back=self.days_back)

    def get_closed_deals(self, start_date=None, days_back=30):
        """
        Retrieve closed deals (closed positions) for the specified time period
        
        Args:
            start_date (str): Start date in format 'YYYY-MM-DD' (e.g., '2025-06-15')
            days_back (int): Number of days to look back for closed deals (used if start_date not provided)
        """
        if start_date:
            # Parse the start date
            start_time = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            # Add one day to current time to ensure we get latest trades
            end_time = datetime.datetime.utcnow() + datetime.timedelta(days=1)
            if not self.json_output:
                logger.info(f"Requesting closed deals from {start_date} to present (+1 day buffer)...")
        else:
            # Use days_back method
            # Add one day to current time to ensure we get latest trades
            end_time = datetime.datetime.utcnow() + datetime.timedelta(days=1)
            start_time = end_time - datetime.timedelta(days=days_back + 1)  # Also extend start by 1 day
            if not self.json_output:
                logger.info(f"Requesting closed deals for the last {days_back} days (+1 day buffer)...")
        
        # Convert to Unix timestamps in milliseconds
        from_timestamp = int(start_time.timestamp() * 1000)
        to_timestamp = int(end_time.timestamp() * 1000)
        
        # Create the deal list request
        dealListReq = ProtoOADealListReq()
        dealListReq.ctidTraderAccountId = self.account_id
        dealListReq.fromTimestamp = from_timestamp
        dealListReq.toTimestamp = to_timestamp
        dealListReq.maxRows = 1000  # Maximum number of deals to retrieve
        
        if not self.json_output:
            logger.info(f"Searching deals from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        deferred = self.client.send(dealListReq)
        deferred.addTimeout(self.api_timeout, reactor)
        deferred.addCallbacks(self.onClosedDealsReceived, self.onError)

    def onClosedDealsReceived(self, response):
        """Process the response containing closed deals"""
        if not self.json_output:
            logger.info("Closed deals response received, processing...")
        
        try:
            parsed = Protobuf.extract(response)
            deals = parsed.deal  # List of deals
            
            if not deals:
                if not self.json_output:
                    logger.info("No closed deals found for the specified period.")
                    self.display_summary()
                else:
                    # Output empty JSON and exit immediately
                    output = {
                        'success': False,
                        'error': 'No trading data found',
                        'data': {}
                    }
                    print("❌ NO TRADING DATA FOUND:")
                    print("=" * 50)
                    print(json.dumps(output, indent=2))
                    print("=" * 50)
                    # Also save to file for web app
                    self.save_to_file(output)
                    reactor.stop()
                    import os
                    os._exit(0)
                reactor.stop()
                return
            
            if not self.json_output:
                logger.info(f"Found {len(deals)} closed deals")
            
            # Process each deal - filter to only show meaningful closing deals
            processed_deals = []
            for deal in deals:
                processed_deal = self.process_deal(deal)
                if processed_deal:
                    # Only include deals that have meaningful trading information
                    # (either have profit/loss or are rejected/error deals)
                    if (processed_deal['profit_loss'] != 0 or 
                        processed_deal['status'] in ['REJECTED', 'ERROR', 'MISSED'] or
                        processed_deal['close_price'] > 0):
                        processed_deals.append(processed_deal)
            
            self.closed_deals = processed_deals
            
            if self.json_output:
                self.output_json()
                # Force immediate exit for JSON mode to avoid reactor delays
                reactor.stop()
                import os
                os._exit(0)
            else:
                self.display_deals()
                self.display_summary()
                # Stop the reactor
                reactor.stop()
            
        except Exception as e:
            if self.json_output:
                # Output error JSON and exit immediately
                output = {
                    'success': False,
                    'error': f'Error processing deals: {str(e)}',
                    'data': {}
                }
                print(json.dumps(output))
                reactor.stop()
                import os
                os._exit(1)
            else:
                logger.error(f"Error processing closed deals: {e}")
                reactor.stop()

    def process_order(self, order):
        """
        Process a single order and extract comprehensive information for analysis
        
        Args:
            order: ProtoOAOrder object
            
        Returns:
            dict: Processed order information with detailed analysis
        """
        try:
            # Debug: Print available attributes
            logger.debug(f"Order attributes: {dir(order)}")
            
            # Get symbol name - handle different possible attribute names
            symbol_id = None
            if hasattr(order, 'symbolId'):
                symbol_id = order.symbolId
            elif hasattr(order, 'symbol_id'):
                symbol_id = order.symbol_id
            elif hasattr(order, 'symbolName'):
                symbol_name = order.symbolName
                symbol_id = None
            else:
                # If we can't find symbol info, log available attributes and skip
                logger.error(f"Order {order.orderId} - Available attributes: {[attr for attr in dir(order) if not attr.startswith('_')]}")
                return None
            
            if symbol_id is not None:
                symbol_name = symbol_names.get(symbol_id, f"Symbol_{symbol_id}")
            elif 'symbol_name' not in locals():
                symbol_name = "Unknown_Symbol"
            
            # Convert timestamps - handle missing timestamps
            create_time = datetime.datetime.utcnow()  # Default
            if hasattr(order, 'createTimestamp') and order.createTimestamp:
                create_time = datetime.datetime.utcfromtimestamp(order.createTimestamp / 1000)
            elif hasattr(order, 'create_timestamp') and order.create_timestamp:
                create_time = datetime.datetime.utcfromtimestamp(order.create_timestamp / 1000)
            
            update_time = create_time  # Default to create time
            if hasattr(order, 'updateTimestamp') and order.updateTimestamp:
                update_time = datetime.datetime.utcfromtimestamp(order.updateTimestamp / 1000)
            elif hasattr(order, 'update_timestamp') and order.update_timestamp:
                update_time = datetime.datetime.utcfromtimestamp(order.update_timestamp / 1000)
            
            # Convert volume from cents to lots - handle missing volume
            volume_lots = 0
            if hasattr(order, 'requestedVolume') and order.requestedVolume:
                volume_lots = order.requestedVolume / 100000
            elif hasattr(order, 'requested_volume') and order.requested_volume:
                volume_lots = order.requested_volume / 100000
            elif hasattr(order, 'volume') and order.volume:
                volume_lots = order.volume / 100000
            
            filled_volume_lots = 0
            if hasattr(order, 'filledVolume') and order.filledVolume:
                filled_volume_lots = order.filledVolume / 100000
            elif hasattr(order, 'filled_volume') and order.filled_volume:
                filled_volume_lots = order.filled_volume / 100000
            
            # Determine trade side
            trade_side = "BUY" if order.tradeSide == ProtoOATradeSide.BUY else "SELL"
            
            # Order type
            order_type_names = {
                ProtoOAOrderType.MARKET: "MARKET",
                ProtoOAOrderType.LIMIT: "LIMIT", 
                ProtoOAOrderType.STOP: "STOP",
                ProtoOAOrderType.STOP_LIMIT: "STOP_LIMIT",
                ProtoOAOrderType.MARKET_RANGE: "MARKET_RANGE",
                ProtoOAOrderType.STOP_LOSS_TAKE_PROFIT: "SL_TP"
            }
            order_type = order_type_names.get(order.orderType, "UNKNOWN")
            
            # Order status
            status_names = {
                ProtoOAOrderStatus.ORDER_STATUS_ACCEPTED: "ACCEPTED",
                ProtoOAOrderStatus.ORDER_STATUS_FILLED: "FILLED",
                ProtoOAOrderStatus.ORDER_STATUS_REJECTED: "REJECTED",
                ProtoOAOrderStatus.ORDER_STATUS_EXPIRED: "EXPIRED",
                ProtoOAOrderStatus.ORDER_STATUS_CANCELLED: "CANCELLED",
                ProtoOAOrderStatus.ORDER_STATUS_PARTIALLY_FILLED: "PARTIAL"
            }
            status = status_names.get(order.orderStatus, "UNKNOWN")
            
            # Price information
            requested_price = order.requestedPrice if hasattr(order, 'requestedPrice') else 0
            execution_price = order.executionPrice if hasattr(order, 'executionPrice') else 0
            current_price = order.currentPrice if hasattr(order, 'currentPrice') else 0
            
            # Stop Loss and Take Profit
            stop_loss = order.stopLoss if hasattr(order, 'stopLoss') and order.stopLoss else 0
            take_profit = order.takeProfit if hasattr(order, 'takeProfit') and order.takeProfit else 0
            
            # Calculate trade duration
            trade_duration = update_time - create_time
            duration_minutes = int(trade_duration.total_seconds() / 60)
            
            # Calculate unrealized P&L and analysis
            unrealized_pnl = 0
            realized_pnl = 0
            commission = 0
            swap = 0
            
            # Extract P&L information if available
            if hasattr(order, 'unrealizedPnL'):
                unrealized_pnl = order.unrealizedPnL / 100
            if hasattr(order, 'realizedPnL'):
                realized_pnl = order.realizedPnL / 100
            if hasattr(order, 'commission'):
                commission = order.commission / 100
            if hasattr(order, 'swap'):
                swap = order.swap / 100
                
            # Calculate pip movement for filled orders
            pip_size = 0.01 if 'JPY' in symbol_name else 0.0001
            pip_movement = 0
            loss_reason = "Order not filled"
            
            if execution_price > 0 and current_price > 0:
                if trade_side == "BUY":
                    pip_movement = (current_price - execution_price) / pip_size
                    if pip_movement < 0:
                        loss_reason = f"Price moved against BUY position by {abs(pip_movement):.1f} pips"
                    elif pip_movement > 0:
                        loss_reason = f"Price moved in favor by {pip_movement:.1f} pips"
                else:  # SELL
                    pip_movement = (execution_price - current_price) / pip_size
                    if pip_movement < 0:
                        loss_reason = f"Price moved against SELL position by {abs(pip_movement):.1f} pips"
                    elif pip_movement > 0:
                        loss_reason = f"Price moved in favor by {pip_movement:.1f} pips"
            elif status == "REJECTED":
                loss_reason = "Order was rejected by broker"
            elif status == "EXPIRED":
                loss_reason = "Order expired before execution"
            elif status == "CANCELLED":
                loss_reason = "Order was cancelled"
            
            # Risk management analysis
            has_stop_loss = stop_loss > 0
            has_take_profit = take_profit > 0
            risk_reward_ratio = 0
            
            if has_stop_loss and has_take_profit and execution_price > 0:
                if trade_side == "BUY":
                    risk_pips = abs(execution_price - stop_loss) / pip_size
                    reward_pips = abs(take_profit - execution_price) / pip_size
                else:  # SELL
                    risk_pips = abs(stop_loss - execution_price) / pip_size
                    reward_pips = abs(execution_price - take_profit) / pip_size
                
                if risk_pips > 0:
                    risk_reward_ratio = reward_pips / risk_pips
            
            # Order categorization
            total_pnl = realized_pnl + unrealized_pnl
            order_category = "Pending" if status in ["ACCEPTED"] else "Completed"
            if status == "FILLED":
                if total_pnl > 0:
                    order_category = "Profitable"
                elif total_pnl < 0:
                    if abs(total_pnl) > 50:
                        order_category = "Major Loss"
                    elif abs(total_pnl) > 20:
                        order_category = "Moderate Loss"
                    else:
                        order_category = "Minor Loss"
                else:
                    order_category = "Break-even"
            
            processed_order = {
                'deal_id': order.orderId,  # Use orderId as deal_id for compatibility
                'order_id': order.orderId,
                'position_id': order.positionId if hasattr(order, 'positionId') else 0,
                'symbol': symbol_name,
                'side': trade_side,
                'order_type': order_type,
                'volume_lots': volume_lots,
                'filled_volume_lots': filled_volume_lots,
                'requested_price': requested_price,
                'execution_price': execution_price,
                'current_price': current_price,
                'entry_price': execution_price,  # For compatibility
                'close_price': current_price,    # For compatibility
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'status': status,
                'create_time': create_time,
                'execution_time': update_time,  # For compatibility
                'duration_minutes': duration_minutes,
                'unrealized_pnl': unrealized_pnl,
                'realized_pnl': realized_pnl,
                'profit_loss': total_pnl,  # For compatibility
                'commission': commission,
                'swap': swap,
                'net_result': total_pnl - commission + swap,
                'pip_movement': pip_movement,
                'loss_reason': loss_reason,
                'loss_category': order_category,
                'has_stop_loss': has_stop_loss,
                'has_take_profit': has_take_profit,
                'risk_reward_ratio': risk_reward_ratio,
                'risk_per_pip': volume_lots * (10.0 if 'JPY' not in symbol_name else 7.0)
            }
            
            return processed_order
            
        except Exception as e:
            logger.error(f"Error processing order {order.orderId}: {e}")
            return None

    def process_deal(self, deal):
        """
        Process a single deal and extract comprehensive information for loss analysis
        
        Args:
            deal: ProtoOADeal object
            
        Returns:
            dict: Processed deal information with loss analysis
        """
        try:
            # Get symbol name
            symbol_name = symbol_names.get(deal.symbolId, f"Symbol_{deal.symbolId}")
            
            # Convert timestamps
            create_time = datetime.datetime.utcfromtimestamp(deal.createTimestamp / 1000)
            execution_time = datetime.datetime.utcfromtimestamp(deal.executionTimestamp / 1000)
            
            # Convert volume from cents to lots
            volume_lots = deal.filledVolume / 100000
            
            # Determine trade side
            trade_side = "BUY" if deal.tradeSide == ProtoOATradeSide.BUY else "SELL"
            
            # Deal status
            status_names = {
                ProtoOADealStatus.FILLED: "FILLED",
                ProtoOADealStatus.PARTIALLY_FILLED: "PARTIAL",
                ProtoOADealStatus.REJECTED: "REJECTED",
                ProtoOADealStatus.INTERNALLY_REJECTED: "INT_REJECTED",
                ProtoOADealStatus.ERROR: "ERROR",
                ProtoOADealStatus.MISSED: "MISSED"
            }
            status = status_names.get(deal.dealStatus, "UNKNOWN")
            
            # Enhanced profit/loss and position details
            profit_loss = 0
            swap = 0
            commission = 0
            entry_price = 0
            close_price = 0
            stop_loss = 0
            take_profit = 0
            margin_rate = 0
            

            # Extract detailed position information
            if hasattr(deal, 'closePositionDetail') and deal.closePositionDetail:
                close_detail = deal.closePositionDetail
                # Calculate PnL as grossProfit + commission (commission is already negative)
                gross_profit = close_detail.grossProfit / 100  # Convert from cents to currency units
                commission = close_detail.commission / 100 if hasattr(close_detail, 'commission') else 0
                profit_loss = gross_profit + commission  # Commission is negative, so this effectively subtracts it
                swap = close_detail.swap / 100 if hasattr(close_detail, 'swap') else 0
                entry_price = close_detail.entryPrice if hasattr(close_detail, 'entryPrice') else 0
                close_price = close_detail.closePrice if hasattr(close_detail, 'closePrice') else 0
            else:
                # Try to get profit/loss directly from the deal object
                if hasattr(deal, 'grossProfit'):
                    gross_profit = deal.grossProfit / 100
                    deal_commission = deal.commission / 100 if hasattr(deal, 'commission') and deal.commission else 0
                    profit_loss = gross_profit + deal_commission  # Commission is negative
                    commission = deal_commission
                if hasattr(deal, 'swap'):
                    swap = deal.swap / 100
            
            # Try alternative ways to get prices if closePositionDetail is not available
            if entry_price == 0 and hasattr(deal, 'executionPrice') and deal.executionPrice:
                entry_price = deal.executionPrice
            
            # For deals without closePositionDetail, try to get price info from the deal itself
            if close_price == 0:
                # Check if this is a closing deal vs opening deal
                if hasattr(deal, 'executionPrice') and deal.executionPrice:
                    # If this deal has profit/loss, it might be a closing deal
                    if profit_loss != 0:
                        close_price = deal.executionPrice
                    else:
                        entry_price = deal.executionPrice if entry_price == 0 else entry_price
            
            # Execution price (for opening trades)
            execution_price = deal.executionPrice if hasattr(deal, 'executionPrice') else entry_price
            
            # Calculate trade duration
            trade_duration = execution_time - create_time
            duration_minutes = int(trade_duration.total_seconds() / 60)
            
            # Calculate pip movement and loss analysis
            pip_size = 0.01 if 'JPY' in symbol_name else 0.0001
            pip_movement = 0
            loss_reason = "Unknown"
            
            if entry_price > 0 and close_price > 0:
                if trade_side == "BUY":
                    pip_movement = (close_price - entry_price) / pip_size
                    if pip_movement < 0:
                        loss_reason = f"Price moved against BUY position by {abs(pip_movement):.2f} pips"
                else:  # SELL
                    pip_movement = (entry_price - close_price) / pip_size
                    if pip_movement < 0:
                        loss_reason = f"Price moved against SELL position by {abs(pip_movement):.2f} pips"
            
            # Risk analysis
            risk_per_pip = volume_lots * (10.0 if 'JPY' not in symbol_name else 7.0)
            theoretical_loss = abs(pip_movement) * risk_per_pip if pip_movement < 0 else 0
            
            # Loss categorization
            loss_category = "Profit" if profit_loss > 0 else "Break-even" if profit_loss == 0 else "Loss"
            if profit_loss < 0:
                if abs(profit_loss) > 50:
                    loss_category = "Major Loss"
                elif abs(profit_loss) > 20:
                    loss_category = "Moderate Loss"
                else:
                    loss_category = "Minor Loss"
            
            processed_deal = {
                'deal_id': deal.dealId,
                'order_id': deal.orderId,
                'position_id': deal.positionId,
                'symbol': symbol_name,
                'side': trade_side,
                'volume_lots': volume_lots,
                'entry_price': entry_price if entry_price > 0 else execution_price,
                'close_price': close_price,
                'execution_price': execution_price,
                'status': status,
                'create_time': create_time,
                'execution_time': execution_time,
                'duration_minutes': duration_minutes,
                'profit_loss': profit_loss,
                'commission': commission,
                'swap': swap,
                'net_result': profit_loss - commission + swap,
                'pip_movement': pip_movement,
                'loss_reason': loss_reason,
                'loss_category': loss_category,
                'risk_per_pip': risk_per_pip,
                'theoretical_loss': theoretical_loss
            }
            
            return processed_deal
            
        except Exception as e:
            logger.error(f"Error processing deal {deal.dealId}: {e}")
            return None

    def display_orders(self):
        """Display all orders with comprehensive analysis including risk management"""
        if not self.closed_deals:
            logger.info("No orders to display")
            return
        
        # Sort orders by execution time (newest first)
        sorted_orders = sorted(self.closed_deals, key=lambda x: x['execution_time'], reverse=True)
        
        # Display comprehensive order table
        print("\n" + "="*180)
        print("COMPREHENSIVE ORDER ANALYSIS")
        print("="*180)
        
        # Header with more detailed information
        print(f"{'Order ID':<12} {'Symbol':<10} {'Type':<8} {'Side':<5} {'Volume':<8} {'Req.Price':<10} {'Exec.Price':<10} "
              f"{'Curr.Price':<10} {'SL':<10} {'TP':<10} {'R:R':<6} {'P&L':<10} {'Status':<12} {'Category':<12}")
        print("-" * 180)
        
        total_pnl = 0
        losing_orders = []
        filled_orders = []
        pending_orders = []
        
        for order in sorted_orders:
            req_price_str = f"{order['requested_price']:.5f}" if order['requested_price'] > 0 else "N/A"
            exec_price_str = f"{order['execution_price']:.5f}" if order['execution_price'] > 0 else "N/A"
            curr_price_str = f"{order['current_price']:.5f}" if order['current_price'] > 0 else "N/A"
            sl_str = f"{order['stop_loss']:.5f}" if order['stop_loss'] > 0 else "N/A"
            tp_str = f"{order['take_profit']:.5f}" if order['take_profit'] > 0 else "N/A"
            rr_str = f"{order['risk_reward_ratio']:.2f}" if order['risk_reward_ratio'] > 0 else "N/A"
            pnl_str = f"${order['profit_loss']:.2f}" if order['profit_loss'] != 0 else "$0.00"
            
            print(f"{order['order_id']:<12} {order['symbol']:<10} {order['order_type']:<8} {order['side']:<5} "
                  f"{order['volume_lots']:<8.2f} {req_price_str:<10} {exec_price_str:<10} {curr_price_str:<10} "
                  f"{sl_str:<10} {tp_str:<10} {rr_str:<6} {pnl_str:<10} {order['status']:<12} {order['loss_category']:<12}")
            
            total_pnl += order['profit_loss']
            
            # Categorize orders
            if order['status'] == 'FILLED':
                filled_orders.append(order)
                if order['profit_loss'] < 0:
                    losing_orders.append(order)
            elif order['status'] in ['ACCEPTED', 'PARTIAL']:
                pending_orders.append(order)
        
        print("-" * 180)
        print(f"{'TOTAL P&L:':<167} ${total_pnl:.2f}")
        print("="*180)
        
        # Display risk management analysis
        self.display_risk_management_analysis(sorted_orders)
        
        # Display detailed loss analysis for losing orders
        if losing_orders:
            self.display_loss_analysis(losing_orders)
        
        # Display pending orders analysis
        if pending_orders:
            self.display_pending_orders_analysis(pending_orders)
        
        # Display winning orders summary
        winning_orders = [d for d in sorted_orders if d['profit_loss'] > 0]
        if winning_orders:
            self.display_winning_analysis(winning_orders)

    def display_risk_management_analysis(self, orders):
        """Display risk management analysis"""
        print("\n" + "="*120)
        print("RISK MANAGEMENT ANALYSIS")
        print("="*120)
        
        filled_orders = [o for o in orders if o['status'] == 'FILLED']
        
        if not filled_orders:
            print("No filled orders to analyze")
            return
        
        # Risk management statistics
        orders_with_sl = [o for o in filled_orders if o['has_stop_loss']]
        orders_with_tp = [o for o in filled_orders if o['has_take_profit']]
        orders_with_both = [o for o in filled_orders if o['has_stop_loss'] and o['has_take_profit']]
        
        print(f"Total Filled Orders: {len(filled_orders)}")
        print(f"Orders with Stop Loss: {len(orders_with_sl)} ({len(orders_with_sl)/len(filled_orders)*100:.1f}%)")
        print(f"Orders with Take Profit: {len(orders_with_tp)} ({len(orders_with_tp)/len(filled_orders)*100:.1f}%)")
        print(f"Orders with Both SL & TP: {len(orders_with_both)} ({len(orders_with_both)/len(filled_orders)*100:.1f}%)")
        
        # Risk:Reward analysis
        rr_orders = [o for o in filled_orders if o['risk_reward_ratio'] > 0]
        if rr_orders:
            avg_rr = sum(o['risk_reward_ratio'] for o in rr_orders) / len(rr_orders)
            print(f"\nRisk:Reward Analysis:")
            print(f"Orders with R:R ratio: {len(rr_orders)}")
            print(f"Average R:R ratio: {avg_rr:.2f}")
            
            # R:R categories
            good_rr = [o for o in rr_orders if o['risk_reward_ratio'] >= 2.0]
            fair_rr = [o for o in rr_orders if 1.0 <= o['risk_reward_ratio'] < 2.0]
            poor_rr = [o for o in rr_orders if o['risk_reward_ratio'] < 1.0]
            
            print(f"Good R:R (>=2:1): {len(good_rr)} orders")
            print(f"Fair R:R (1:1-2:1): {len(fair_rr)} orders")
            print(f"Poor R:R (<1:1): {len(poor_rr)} orders")
        
        print("="*120)
    
    def display_pending_orders_analysis(self, pending_orders):
        """Display analysis of pending orders"""
        print("\n" + "="*120)
        print("PENDING ORDERS ANALYSIS")
        print("="*120)
        
        print(f"Total Pending Orders: {len(pending_orders)}")
        
        # Group by symbol
        symbol_pending = {}
        for order in pending_orders:
            symbol = order['symbol']
            if symbol not in symbol_pending:
                symbol_pending[symbol] = []
            symbol_pending[symbol].append(order)
        
        print(f"\nPending Orders by Symbol:")
        for symbol, orders in symbol_pending.items():
            total_volume = sum(o['volume_lots'] for o in orders)
            print(f"  {symbol}: {len(orders)} orders, {total_volume:.2f} lots total")
        
        # Risk exposure from pending orders
        total_pending_volume = sum(o['volume_lots'] for o in pending_orders)
        print(f"\nTotal Pending Volume: {total_pending_volume:.2f} lots")
        
        # Orders with risk management
        pending_with_sl = [o for o in pending_orders if o['has_stop_loss']]
        pending_with_tp = [o for o in pending_orders if o['has_take_profit']]
        
        print(f"Pending orders with Stop Loss: {len(pending_with_sl)}")
        print(f"Pending orders with Take Profit: {len(pending_with_tp)}")
        
        print("="*120)

    def display_deals(self):
        """Display all closed deals with comprehensive loss analysis"""
        if not self.closed_deals:
            logger.info("No deals to display")
            return
        
        # Sort deals by execution time (newest first)
        sorted_deals = sorted(self.closed_deals, key=lambda x: x['execution_time'], reverse=True)
        
        # Display summary table first
        print("\n" + "="*140)
        print("CLOSED DEALS SUMMARY")
        print("="*140)
        
        # Header
        print(f"{'Deal ID':<12} {'Symbol':<10} {'Side':<5} {'Volume':<8} {'Entry':<10} {'Close':<10} {'Pips':<8} {'P&L':<10} {'Category':<12} {'Duration':<10}")
        print("-" * 140)
        
        total_pnl = 0
        losing_trades = []
        
        for deal in sorted_deals:
            entry_str = f"{deal['entry_price']:.5f}" if deal['entry_price'] > 0 else "N/A"
            close_str = f"{deal['close_price']:.5f}" if deal['close_price'] > 0 else "N/A"
            pips_str = f"{deal['pip_movement']:.2f}" if deal['pip_movement'] != 0 else "N/A"
            pnl_str = f"${deal['profit_loss']:.2f}" if deal['profit_loss'] != 0 else "$0.00"
            duration_str = f"{deal['duration_minutes']}m" if deal['duration_minutes'] > 0 else "N/A"
            
            print(f"{deal['deal_id']:<12} {deal['symbol']:<10} {deal['side']:<5} {deal['volume_lots']:<8.2f} "
                  f"{entry_str:<10} {close_str:<10} {pips_str:<8} {pnl_str:<10} {deal['loss_category']:<12} {duration_str:<10}")
            
            total_pnl += deal['profit_loss']
            
            # Collect losing trades for detailed analysis
            if deal['profit_loss'] < 0:
                losing_trades.append(deal)
        
        print("-" * 140)
        print(f"{'TOTAL P&L:':<117} ${total_pnl:.2f}")
        print("="*140)
        
        # Display detailed loss analysis
        if losing_trades:
            self.display_loss_analysis(losing_trades)
        
        # Display winning trades summary
        winning_trades = [d for d in sorted_deals if d['profit_loss'] > 0]
        if winning_trades:
            self.display_winning_analysis(winning_trades)

    def display_loss_analysis(self, losing_trades):
        """Display detailed analysis of losing trades"""
        print("\n" + "="*160)
        print("DETAILED LOSS ANALYSIS - WHY TRADES LOST MONEY")
        print("="*160)
        
        # Sort by loss amount (biggest losses first)
        losing_trades.sort(key=lambda x: x['profit_loss'])
        
        print(f"{'Deal ID':<12} {'Symbol':<10} {'Side':<5} {'Entry':<10} {'Close':<10} {'Pips':<8} {'Loss':<10} {'Commission':<10} {'Net Loss':<10} {'Reason':<50}")
        print("-" * 160)
        
        total_loss = 0
        total_commission = 0
        
        for trade in losing_trades:
            entry_str = f"{trade['entry_price']:.5f}" if trade['entry_price'] > 0 else "N/A"
            close_str = f"{trade['close_price']:.5f}" if trade['close_price'] > 0 else "N/A"
            pips_str = f"{trade['pip_movement']:.2f}" if trade['pip_movement'] != 0 else "N/A"
            loss_str = f"${trade['profit_loss']:.2f}"
            commission_str = f"${trade['commission']:.2f}" if trade['commission'] != 0 else "$0.00"
            net_loss_str = f"${trade['net_result']:.2f}"
            
            print(f"{trade['deal_id']:<12} {trade['symbol']:<10} {trade['side']:<5} {entry_str:<10} {close_str:<10} "
                  f"{pips_str:<8} {loss_str:<10} {commission_str:<10} {net_loss_str:<10} {trade['loss_reason']:<50}")
            
            total_loss += trade['profit_loss']
            total_commission += trade['commission']
        
        print("-" * 160)
        print(f"{'TOTAL LOSSES:':<97} ${total_loss:.2f}")
        print(f"{'TOTAL COMMISSION PAID:':<97} ${total_commission:.2f}")
        print(f"{'NET IMPACT:':<97} ${total_loss - total_commission:.2f}")
        print("="*160)
        
        # Loss pattern analysis
        self.analyze_loss_patterns(losing_trades)
    
    def analyze_loss_patterns(self, losing_trades):
        """Analyze patterns in losing trades"""
        print("\nLOSS PATTERN ANALYSIS")
        print("-" * 80)
        
        # Group by symbol
        symbol_losses = {}
        side_losses = {'BUY': 0, 'SELL': 0}
        duration_analysis = {'quick': 0, 'medium': 0, 'long': 0}
        
        for trade in losing_trades:
            symbol = trade['symbol']
            if symbol not in symbol_losses:
                symbol_losses[symbol] = {'count': 0, 'total_loss': 0, 'avg_pips': 0}
            
            symbol_losses[symbol]['count'] += 1
            symbol_losses[symbol]['total_loss'] += trade['profit_loss']
            symbol_losses[symbol]['avg_pips'] += abs(trade['pip_movement']) if trade['pip_movement'] != 0 else 0
            
            # Side analysis
            side_losses[trade['side']] += abs(trade['profit_loss'])
            
            # Duration analysis
            if trade['duration_minutes'] < 60:
                duration_analysis['quick'] += 1
            elif trade['duration_minutes'] < 240:
                duration_analysis['medium'] += 1
            else:
                duration_analysis['long'] += 1
        
        # Display symbol analysis
        print("\nLOSSES BY SYMBOL:")
        for symbol, data in symbol_losses.items():
            avg_pips = data['avg_pips'] / data['count'] if data['count'] > 0 else 0
            print(f"  {symbol}: {data['count']} losses, ${data['total_loss']:.2f} total, {avg_pips:.2f} avg pips against")
        
        # Display side analysis
        print(f"\nLOSSES BY DIRECTION:")
        print(f"  BUY losses: ${side_losses['BUY']:.2f}")
        print(f"  SELL losses: ${side_losses['SELL']:.2f}")
        
        # Display duration analysis
        print(f"\nLOSSES BY DURATION:")
        print(f"  Quick losses (<1h): {duration_analysis['quick']} trades")
        print(f"  Medium losses (1-4h): {duration_analysis['medium']} trades")
        print(f"  Long losses (>4h): {duration_analysis['long']} trades")
        
        # Key insights
        print(f"\nKEY INSIGHTS:")
        worst_symbol = max(symbol_losses.items(), key=lambda x: abs(x[1]['total_loss']))
        print(f"  - Worst performing symbol: {worst_symbol[0]} (${worst_symbol[1]['total_loss']:.2f} lost)")
        
        if side_losses['BUY'] > side_losses['SELL']:
            print(f"  - BUY trades losing more than SELL trades")
        else:
            print(f"  - SELL trades losing more than BUY trades")
        
        total_losing_trades = len(losing_trades)
        if duration_analysis['quick'] > total_losing_trades * 0.5:
            print(f"  - Most losses happen quickly (<1 hour) - possible poor entry timing")
        elif duration_analysis['long'] > total_losing_trades * 0.3:
            print(f"  - Many losses are held too long - consider tighter stop losses")
    
    def display_winning_analysis(self, winning_trades):
        """Display analysis of winning trades for comparison"""
        print("\n" + "="*120)
        print("WINNING TRADES ANALYSIS")
        print("="*120)
        
        total_wins = sum(trade['profit_loss'] for trade in winning_trades)
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        
        # Group by symbol
        symbol_wins = {}
        for trade in winning_trades:
            symbol = trade['symbol']
            if symbol not in symbol_wins:
                symbol_wins[symbol] = {'count': 0, 'total_profit': 0}
            symbol_wins[symbol]['count'] += 1
            symbol_wins[symbol]['total_profit'] += trade['profit_loss']
        
        print(f"Total winning trades: {len(winning_trades)}")
        print(f"Total profit: ${total_wins:.2f}")
        print(f"Average win: ${avg_win:.2f}")
        
        print(f"\nWINS BY SYMBOL:")
        for symbol, data in symbol_wins.items():
            print(f"  {symbol}: {data['count']} wins, ${data['total_profit']:.2f} profit")
        print("="*120)

    def display_win_rates_by_pair(self):
        """Display win rates for each currency pair"""
        if not self.closed_deals:
            return
        
        filled_deals = [d for d in self.closed_deals if d['status'] == 'FILLED']
        
        # Symbol breakdown with win/loss tracking
        symbols = {}
        
        for deal in filled_deals:
            symbol = deal['symbol']
            if symbol not in symbols:
                symbols[symbol] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0,
                    'total_loss': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'largest_win': 0,
                    'largest_loss': 0
                }
            
            symbols[symbol]['total_trades'] += 1
            
            if deal['profit_loss'] > 0:
                symbols[symbol]['winning_trades'] += 1
                symbols[symbol]['total_profit'] += deal['profit_loss']
                symbols[symbol]['largest_win'] = max(symbols[symbol]['largest_win'], deal['profit_loss'])
            elif deal['profit_loss'] < 0:
                symbols[symbol]['losing_trades'] += 1
                symbols[symbol]['total_loss'] += abs(deal['profit_loss'])
                symbols[symbol]['largest_loss'] = max(symbols[symbol]['largest_loss'], abs(deal['profit_loss']))
        
        # Calculate averages and win rates
        for symbol, data in symbols.items():
            if data['winning_trades'] > 0:
                data['avg_win'] = data['total_profit'] / data['winning_trades']
            if data['losing_trades'] > 0:
                data['avg_loss'] = data['total_loss'] / data['losing_trades']
            data['win_rate'] = (data['winning_trades'] / data['total_trades']) * 100 if data['total_trades'] > 0 else 0
            data['net_pnl'] = data['total_profit'] - data['total_loss']
        
        print(f"\n" + "="*140)
        print("WIN RATE ANALYSIS BY CURRENCY PAIR")
        print("="*140)
        print(f"{'Symbol':<10} {'Total':<6} {'Wins':<5} {'Losses':<7} {'Win Rate':<9} {'Net P&L':<10} {'Avg Win':<9} {'Avg Loss':<10} {'Best Win':<10} {'Worst Loss':<11}")
        print("-" * 140)
        
        # Sort by win rate (descending)
        sorted_symbols = sorted(symbols.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        
        overall_trades = 0
        overall_wins = 0
        overall_net_pnl = 0
        
        for symbol, data in sorted_symbols:
            win_rate_str = f"{data['win_rate']:.1f}%"
            net_pnl_str = f"${data['net_pnl']:.2f}"
            avg_win_str = f"${data['avg_win']:.2f}" if data['avg_win'] > 0 else "$0.00"
            avg_loss_str = f"${data['avg_loss']:.2f}" if data['avg_loss'] > 0 else "$0.00"
            best_win_str = f"${data['largest_win']:.2f}" if data['largest_win'] > 0 else "$0.00"
            worst_loss_str = f"${data['largest_loss']:.2f}" if data['largest_loss'] > 0 else "$0.00"
            
            print(f"{symbol:<10} {data['total_trades']:<6} {data['winning_trades']:<5} {data['losing_trades']:<7} "
                  f"{win_rate_str:<9} {net_pnl_str:<10} {avg_win_str:<9} {avg_loss_str:<10} {best_win_str:<10} {worst_loss_str:<11}")
            
            overall_trades += data['total_trades']
            overall_wins += data['winning_trades']
            overall_net_pnl += data['net_pnl']
        
        print("-" * 140)
        overall_win_rate = (overall_wins / overall_trades) * 100 if overall_trades > 0 else 0
        print(f"{'OVERALL':<10} {overall_trades:<6} {overall_wins:<5} {overall_trades - overall_wins:<7} "
              f"{overall_win_rate:.1f}%{'':<4} ${overall_net_pnl:.2f}")
        print("="*140)
        
        # Additional insights
        if sorted_symbols:
            best_pair = sorted_symbols[0]
            worst_pair = sorted_symbols[-1]
            
            print(f"\nKEY INSIGHTS:")
            print(f"  🏆 Best performing pair: {best_pair[0]} ({best_pair[1]['win_rate']:.1f}% win rate, ${best_pair[1]['net_pnl']:.2f} net)")
            print(f"  ⚠️  Worst performing pair: {worst_pair[0]} ({worst_pair[1]['win_rate']:.1f}% win rate, ${worst_pair[1]['net_pnl']:.2f} net)")
            print(f"  📊 Overall win rate: {overall_win_rate:.1f}% ({overall_wins}/{overall_trades} trades)")
            
            profitable_pairs = [s for s, d in sorted_symbols if d['net_pnl'] > 0]
            losing_pairs = [s for s, d in sorted_symbols if d['net_pnl'] < 0]
            
            print(f"  💰 Profitable pairs: {len(profitable_pairs)}/{len(sorted_symbols)}")
            print(f"  💸 Losing pairs: {len(losing_pairs)}/{len(sorted_symbols)}")
            
            if profitable_pairs:
                print(f"     Profitable: {', '.join([p[0] for p in profitable_pairs])}")
            if losing_pairs:
                print(f"     Losing: {', '.join([p[0] for p in losing_pairs])}")

    def display_summary(self):
        """Display summary statistics"""
        if not self.closed_deals:
            return
        
        total_deals = len(self.closed_deals)
        filled_deals = [d for d in self.closed_deals if d['status'] == 'FILLED']
        
        # Symbol breakdown
        symbols = {}
        total_volume = 0
        total_pnl = 0
        
        for deal in filled_deals:
            symbol = deal['symbol']
            if symbol not in symbols:
                symbols[symbol] = {'count': 0, 'volume': 0, 'pnl': 0}
            
            symbols[symbol]['count'] += 1
            symbols[symbol]['volume'] += deal['volume_lots']
            symbols[symbol]['pnl'] += deal['profit_loss']
            
            total_volume += deal['volume_lots']
            total_pnl += deal['profit_loss']
        
        print(f"\nSUMMARY STATISTICS")
        print(f"Total Deals: {total_deals}")
        print(f"Filled Deals: {len(filled_deals)}")
        print(f"Total Volume: {total_volume:.2f} lots")
        print(f"Total P&L: ${total_pnl:.2f}")
        
        if symbols:
            print(f"\nBY SYMBOL:")
            for symbol, data in symbols.items():
                print(f"  {symbol}: {data['count']} deals, {data['volume']:.2f} lots, ${data['pnl']:.2f}")
        
        # Display win rates by pair
        self.display_win_rates_by_pair()
    
    def output_json(self):
        """Output trading data in JSON format for API consumption"""
        import json
        
        if not self.closed_deals:
            output = {
                'success': False,
                'error': 'No trading data found',
                'data': {}
            }
            print("❌ NO TRADING DATA FOUND:")
            print("=" * 50)
            print(json.dumps(output, indent=2))
            print("=" * 50)
            # Also save to file for web app
            self.save_to_file(output)
            return
        
        # Calculate summary statistics
        filled_deals = [d for d in self.closed_deals if d['status'] == 'FILLED']
        total_trades = len(filled_deals)
        total_pnl = sum(d['profit_loss'] for d in filled_deals)
        total_volume = sum(d['volume_lots'] for d in filled_deals)
        
        winning_trades = [d for d in filled_deals if d['profit_loss'] > 0]
        losing_trades = [d for d in filled_deals if d['profit_loss'] < 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # Symbol breakdown
        symbols = {}
        for deal in filled_deals:
            symbol = deal['symbol']
            if symbol not in symbols:
                symbols[symbol] = {
                    'totalTrades': 0,
                    'winningTrades': 0,
                    'pnl': 0,
                    'volume': 0,
                    'wins': [],
                    'losses': []
                }
            
            symbols[symbol]['totalTrades'] += 1
            symbols[symbol]['pnl'] += deal['profit_loss']
            symbols[symbol]['volume'] += deal['volume_lots']
            
            if deal['profit_loss'] > 0:
                symbols[symbol]['winningTrades'] += 1
                symbols[symbol]['wins'].append(deal['profit_loss'])
            else:
                symbols[symbol]['losses'].append(deal['profit_loss'])
        
        # Convert to API format
        symbol_performance = []
        for symbol, data in symbols.items():
            win_rate_symbol = (data['winningTrades'] / data['totalTrades'] * 100) if data['totalTrades'] > 0 else 0
            symbol_performance.append({
                'symbol': symbol,
                'pnl': round(data['pnl'], 2),
                'trades': data['totalTrades'],
                'volume': round(data['volume'], 0),
                'winRate': round(win_rate_symbol, 1)
            })
        
        # Recent trades (last 30)
        recent_trades = []
        for deal in sorted(filled_deals, key=lambda x: x['execution_time'], reverse=True)[:30]:
            recent_trades.append({
                'id': deal['deal_id'],
                'time': deal['execution_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': deal['symbol'],
                'side': deal['side'],
                'volume': deal['volume_lots'],
                'entry': deal['entry_price'],
                'exit': deal['close_price'] if deal['close_price'] > 0 else deal['entry_price'],
                'pips': abs(deal['pip_movement']) if deal['pip_movement'] else 0,
                'pnl': deal['profit_loss'],
                'status': deal['status'],
                'duration': deal['duration_minutes']
            })
        
        # P&L History (simplified - by day)
        pnl_history = []
        deals_by_date = {}
        for deal in filled_deals:
            date_str = deal['execution_time'].strftime('%Y-%m-%d')
            if date_str not in deals_by_date:
                deals_by_date[date_str] = 0
            deals_by_date[date_str] += deal['profit_loss']
        
        cumulative = 0
        for date in sorted(deals_by_date.keys()):
            daily = deals_by_date[date]
            cumulative += daily
            pnl_history.append({
                'date': date,
                'daily': round(daily, 2),
                'cumulative': round(cumulative, 2)
            })
        
        # Risk metrics
        profit_factor = 0
        if losing_trades:
            total_wins = sum(d['profit_loss'] for d in winning_trades)
            total_losses = abs(sum(d['profit_loss'] for d in losing_trades))
            profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        max_drawdown = min(d['profit_loss'] for d in filled_deals) if filled_deals else 0
        avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
        
        # Generate insights
        insights = []
        if symbol_performance:
            best_symbol = max(symbol_performance, key=lambda x: x['pnl'])
            worst_symbol = min(symbol_performance, key=lambda x: x['pnl'])
            
            insights.append(f"Best performing pair: {best_symbol['symbol']} (+${best_symbol['pnl']:.2f})")
            if worst_symbol['pnl'] < 0:
                insights.append(f"Worst performing pair: {worst_symbol['symbol']} (${worst_symbol['pnl']:.2f})")
            insights.append(f"Overall win rate: {win_rate:.1f}% ({len(winning_trades)}/{total_trades} trades)")
        
        output = {
            'success': True,
            'summary': {
                'totalPnL': round(total_pnl, 2),
                'totalTrades': total_trades,
                'winRate': round(win_rate, 1),
                'totalVolume': round(total_volume, 0),
                'winningTrades': len(winning_trades),
                'losingTrades': len(losing_trades),
                'lastUpdate': datetime.datetime.now().isoformat()
            },
            'symbolPerformance': symbol_performance,
            'recentTrades': recent_trades,
            'pnlHistory': pnl_history,
            'riskMetrics': {
                'maxDrawdown': round(max_drawdown, 2),
                'avgTradeSize': round(avg_trade_size, 2),
                'profitFactor': round(profit_factor, 2),
                'sharpeRatio': 0  # Would need more data to calculate
            },
            'insights': insights
        }
        
        print("🔥 TRADE MONITOR JSON OUTPUT:")
        print("=" * 50)
        print(json.dumps(output, indent=2))
        print("=" * 50)
        print(f"📊 SUMMARY: {output['summary']['totalTrades']} trades, ${output['summary']['totalPnL']:.2f} P&L, {output['summary']['winRate']:.1f}% win rate")
        print("=" * 50)
        
        # Also save to file for web app
        self.save_to_file(output)
    
    def save_to_file(self, data):
        """Save trading data to file for web app"""
        try:
            # Save to current directory
            with open('trading_data.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            pass  # Ignore file save errors in JSON mode
        
    def connect_sync(self):
        """Synchronous connection method for API usage - returns JSON data"""
        try:
            import time
            from twisted.internet import reactor
            
            # Set up for JSON output
            self.json_output = True
            self.json_data = None
            
            # Set up callbacks
            self.client.setConnectedCallback(self.connected)
            self.client.setDisconnectedCallback(self.disconnected)  
            self.client.setMessageReceivedCallback(self.onMessageReceived)
            
            # Start the service
            self.client.startService()
            
            # Wait for data with timeout
            timeout = 30
            start_time = time.time()
            
            while not self.closed_deals and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                # Process any pending reactor events
                try:
                    reactor.iterate(0.1)
                except:
                    pass
            
            # If we got deals, generate JSON output
            if self.closed_deals:
                # Capture the JSON output
                import io
                import sys
                from contextlib import redirect_stdout
                
                # Temporarily capture stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    self.output_json()
                
                # Parse the JSON from the output
                output = f.getvalue()
                if "🔥 TRADE MONITOR JSON OUTPUT:" in output:
                    # Extract JSON part
                    lines = output.split('\n')
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.strip() == '{':
                            in_json = True
                        if in_json:
                            json_lines.append(line)
                        if line.strip() == '}':
                            break
                    
                    json_str = '\n'.join(json_lines)
                    try:
                        self.json_data = json.loads(json_str)
                    except:
                        pass
            
            # Stop the service
            try:
                self.client.stopService()
                reactor.stop()
            except:
                pass
                
            return self.json_data
            
        except Exception as e:
            logger.error(f"Error in sync connect: {e}")
            return None

def main():
    """Main function with argument parsing support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='cTrader Trade Monitor')
    parser.add_argument('--days', type=int, default=30, help='Number of days to look back (default: 30)')
    parser.add_argument('--json', action='store_true', help='Output data in JSON format for API consumption')
    parser.add_argument('--start-date', type=str, help='Start date in YYYY-MM-DD format (e.g., 2025-06-15)')
    
    args = parser.parse_args()
    
    # Configure logging level based on JSON mode
    if args.json:
        # Suppress all logging in JSON mode except critical errors
        logging.getLogger().setLevel(logging.CRITICAL)
        logger.setLevel(logging.CRITICAL)
    
    if not args.json:
        print("Starting cTrader Trade Monitor...")
        print("=" * 50)
    
    try:
        # Set a timeout to prevent infinite hanging
        def force_exit():
            if not args.json:
                print("\nProgram exceeded timeout. Exiting safely.")
            else:
                output = {
                    'success': False,
                    'error': 'Timeout: Operation exceeded time limit',
                    'data': {}
                }
                print(json.dumps(output))
            reactor.stop()
            import os
            os._exit(1)

        # Shorter timeout for JSON mode (30 seconds), longer for interactive mode (120 seconds)
        timeout_seconds = 30 if args.json else 120
        timer = threading.Timer(timeout_seconds, force_exit)
        timer.start()

        if not args.json:
            print("Connecting to cTrader...")
        
        monitor = TradeMonitor(
            json_output=args.json,
            days_back=args.days,
            start_date=getattr(args, 'start_date', None)
        )
        
    except KeyboardInterrupt:
        if not args.json:
            print("\nManual stop requested. Exiting...")
        reactor.stop()
        sys.exit(0)
    except Exception as e:
        if not args.json:
            print(f"\nFatal error: {e}")
        reactor.stop()
        sys.exit(1)

if __name__ == "__main__":
    main() 