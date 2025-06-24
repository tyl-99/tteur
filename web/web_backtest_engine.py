import pandas as pd
import numpy as np
import datetime
import os
import logging
import json
from collections import defaultdict
import warnings

# Ignore FutureWarnings from pandas
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Trade:
    def __init__(self, entry_time, pair, direction, entry_price, stop_loss, take_profit, volume, reason):
        self.entry_time = entry_time
        self.pair = pair
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.volume = volume
        self.reason = reason
        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.pips_gained = 0
        self.usd_pnl = 0
        self.duration_hours = 0
        self.is_closed = False
    
    def calculate_pnl(self, exit_price):
        """Calculate P&L for this trade - Enhanced for $35-50 range"""
        pip_size = 0.01 if "JPY" in self.pair else 0.0001
        
        # Enhanced pip values for meaningful P&L ($35-50 range)
        # Standard lot (100,000 units) pip values:
        pip_value = 100.0 if "JPY" in self.pair else 100.0  # $100 per pip for 1.0 lot
        
        if self.direction == "BUY":
            pips = (exit_price - self.entry_price) / pip_size
        else:  # SELL
            pips = (self.entry_price - exit_price) / pip_size
        
        self.pips_gained = pips
        # P&L = pips * pip_value * volume
        # For 0.5 lots and 1 pip move: 1 * 100 * 0.5 = $50
        # For 0.4 lots and 1 pip move: 1 * 100 * 0.4 = $40
        self.usd_pnl = pips * pip_value * self.volume
        return self.usd_pnl
    
    def close_trade(self, exit_time, exit_price, exit_reason):
        """Close the trade and calculate all metrics"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.is_closed = True
        
        # Calculate duration
        if isinstance(self.entry_time, (datetime.datetime, pd.Timestamp)) and \
           isinstance(self.exit_time, (datetime.datetime, pd.Timestamp)):
            duration = self.exit_time - self.entry_time
            self.duration_hours = duration.total_seconds() / 3600
        
        # Calculate P&L
        self.calculate_pnl(exit_price)
        
        return self.usd_pnl

class WebBacktestEngine:
    def __init__(self, target_pair="EUR/USD", initial_balance=1000, strategy_code=None):
        self.target_pair = target_pair
        self.pair_code = target_pair.replace("/", "_").replace("-", "_")
        
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.lowest_balance = initial_balance
        
        self.trades = []
        self.open_trades = []
        
        # Strategy will be created from LLM-suggested code
        self.strategy = None
        self.strategy_code = strategy_code
        
        logger.info(f"💰 Web Backtest Engine: ${initial_balance} initial balance")
        logger.info(f"🎯 TARGET PAIR: {self.target_pair}")
        logger.info(f"🧠 STRATEGY: LLM-Suggested Code")
    
    def load_strategy_from_code(self, strategy_code):
        """Load strategy from LLM-suggested code"""
        try:
            # Create a namespace for the strategy
            namespace = {}
            exec(strategy_code, namespace)
            
            # Find the strategy class
            strategy_class = None
            for name, obj in namespace.items():
                if (isinstance(obj, type) and 
                    hasattr(obj, 'analyze_trade_signal') and 
                    name.endswith('Strategy')):
                    strategy_class = obj
                    break
            
            if strategy_class:
                self.strategy = strategy_class()
                logger.info(f"✅ Strategy loaded: {strategy_class.__name__}")
                return True
            else:
                logger.error("❌ No valid strategy class found in code")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to load strategy from code: {e}")
            return False
    
    def get_pip_size(self, pair):
        """Get pip size for any currency pair"""
        if "JPY" in pair:
            return 0.01
        else:
            return 0.0001
    
    def get_trading_costs(self, pair):
        """Get trading costs for different pairs"""
        costs = {
            "EUR/USD": {"spread": 1.2, "slippage": 0.8},
            "GBP/USD": {"spread": 1.5, "slippage": 1.0},
            "USD/JPY": {"spread": 1.0, "slippage": 0.8},
            "EUR/GBP": {"spread": 1.8, "slippage": 1.2},
            "GBP/JPY": {"spread": 2.0, "slippage": 1.5},
            "EUR/JPY": {"spread": 1.5, "slippage": 1.0},
        }
        return costs.get(pair, {"spread": 1.5, "slippage": 1.0})
    
    def load_trendbar_data(self, file_path='latest_trendbar_data.xlsx'):
        """Load trendbar data from Excel file"""
        try:
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            
            # Find the sheet for our target pair
            sheet_name = self.target_pair.replace('/', '_')
            if sheet_name not in excel_data:
                logger.error(f"❌ Sheet {sheet_name} not found in Excel file")
                logger.error(f"Available sheets: {list(excel_data.keys())}")
                return None
            
            df = excel_data[sheet_name]
            
            # Ensure datetime column
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'Timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Standardize column names
            column_mapping = {
                'Open': 'open',
                'High': 'high', 
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }
            df = df.rename(columns=column_mapping)
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"📊 Loaded {len(df)} candles for {self.target_pair}")
            logger.info(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load trendbar data: {e}")
            return None
    
    def open_trade(self, signal, timestamp, pair, market_price, current_index):
        """Open a new trade based on strategy signal"""
        try:
            # Apply trading costs
            costs = self.get_trading_costs(pair)
            pip_size = self.get_pip_size(pair)
            
            # Adjust entry price for spread and slippage
            if signal["decision"] == "BUY":
                entry_price = market_price + (costs["spread"] + costs["slippage"]) * pip_size
            else:  # SELL
                entry_price = market_price - (costs["spread"] + costs["slippage"]) * pip_size
            
            # Create trade
            trade = Trade(
                entry_time=timestamp,
                pair=pair,
                direction=signal["decision"],
                entry_price=entry_price,
                stop_loss=signal.get("stop_loss", 0),
                take_profit=signal.get("take_profit", 0),
                volume=signal.get("volume", 0.4),  # Default 0.4 lots for $35-50 P&L range
                reason=signal.get("reason", "Strategy signal")
            )
            
            self.open_trades.append(trade)
            logger.info(f"🔵 OPENED {trade.direction} {trade.pair} at {trade.entry_price:.5f}")
            
            return trade
            
        except Exception as e:
            logger.error(f"❌ Failed to open trade: {e}")
            return None
    
    def check_trade_exits(self, timestamp, bar_data, pair, current_index):
        """Check if any open trades should be closed"""
        trades_to_close = []
        
        for trade in self.open_trades:
            if trade.pair != pair:
                continue
            
            current_price = bar_data['close']
            high_price = bar_data['high']
            low_price = bar_data['low']
            
            exit_price = None
            exit_reason = None
            
            # Check stop loss and take profit
            if trade.direction == "BUY":
                if low_price <= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "Stop Loss"
                elif high_price >= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = "Take Profit"
            else:  # SELL
                if high_price >= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "Stop Loss"
                elif low_price <= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = "Take Profit"
            
            if exit_price:
                trades_to_close.append((trade, timestamp, exit_price, exit_reason))
        
        # Close trades
        for trade, exit_time, exit_price, exit_reason in trades_to_close:
            self.close_trade(trade, exit_time, exit_price, exit_reason)
    
    def close_trade(self, trade, exit_time, exit_price, exit_reason):
        """Close a trade and update balance"""
        try:
            # Apply exit costs
            costs = self.get_trading_costs(trade.pair)
            pip_size = self.get_pip_size(trade.pair)
            
            # Adjust exit price for spread and slippage
            if trade.direction == "BUY":
                exit_price = exit_price - (costs["spread"] + costs["slippage"]) * pip_size
            else:  # SELL
                exit_price = exit_price + (costs["spread"] + costs["slippage"]) * pip_size
            
            # Close the trade
            pnl = trade.close_trade(exit_time, exit_price, exit_reason)
            
            # Update balance
            self.current_balance += pnl
            self.peak_balance = max(self.peak_balance, self.current_balance)
            self.lowest_balance = min(self.lowest_balance, self.current_balance)
            
            # Move to closed trades
            self.trades.append(trade)
            self.open_trades.remove(trade)
            
            logger.info(f"🔴 CLOSED {trade.direction} {trade.pair} at {trade.exit_price:.5f} | "
                       f"P&L: ${pnl:.2f} | Reason: {exit_reason}")
            
        except Exception as e:
            logger.error(f"❌ Failed to close trade: {e}")
    
    def run_backtest(self):
        """Run the backtest with LLM-suggested strategy"""
        if not self.strategy:
            logger.error("❌ No strategy loaded")
            return None
        
        # Load trendbar data
        df = self.load_trendbar_data()
        if df is None:
            logger.error("❌ Failed to load trendbar data")
            return None
        
        logger.info(f"🚀 Starting backtest for {self.target_pair}")
        logger.info(f"📊 Processing {len(df)} candles...")
        
        # Process each candle
        for i in range(len(df)):
            current_bar = df.iloc[i]
            timestamp = current_bar['timestamp']
            
            # Check for trade exits first
            self.check_trade_exits(timestamp, current_bar, self.target_pair, i)
            
            # Check for new trade signals (only if no open trades for this pair)
            if len(self.open_trades) == 0:
                try:
                    # Get data up to current point for strategy analysis
                    strategy_data = df.iloc[:i+1].copy()
                    
                    # Call strategy
                    signal = self.strategy.analyze_trade_signal(strategy_data, self.target_pair)
                    
                    if signal and signal.get("decision") in ["BUY", "SELL"]:
                        self.open_trade(signal, timestamp, self.target_pair, current_bar['close'], i)
                        
                except Exception as e:
                    logger.error(f"❌ Strategy error at index {i}: {e}")
                    continue
        
        # Close any remaining open trades
        for trade in self.open_trades[:]:
            final_bar = df.iloc[-1]
            self.close_trade(trade, final_bar['timestamp'], final_bar['close'], "End of Data")
        
        return self.get_results()
    
    def get_results(self):
        """Get backtest results"""
        if not self.trades:
            return {
                'target_pair': self.target_pair,
                'initial_balance': self.initial_balance,
                'final_balance': self.current_balance,
                'total_pnl': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'peak_balance': self.peak_balance,
                'lowest_balance': self.lowest_balance,
                'trades': []
            }
        
        winning_trades = [t for t in self.trades if t.usd_pnl > 0]
        losing_trades = [t for t in self.trades if t.usd_pnl <= 0]
        
        total_pnl = sum(t.usd_pnl for t in self.trades)
        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
        
        max_drawdown = ((self.peak_balance - self.lowest_balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0
        
        # Convert trades to dict for JSON serialization
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'entry_time': trade.entry_time.isoformat() if hasattr(trade.entry_time, 'isoformat') else str(trade.entry_time),
                'exit_time': trade.exit_time.isoformat() if hasattr(trade.exit_time, 'isoformat') else str(trade.exit_time),
                'pair': trade.pair,
                'direction': trade.direction,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'pips_gained': trade.pips_gained,
                'usd_pnl': trade.usd_pnl,
                'duration_hours': trade.duration_hours,
                'exit_reason': trade.exit_reason,
                'reason': trade.reason
            })
        
        results = {
            'target_pair': self.target_pair,
            'initial_balance': self.initial_balance,
            'final_balance': self.current_balance,
            'total_pnl': total_pnl,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'peak_balance': self.peak_balance,
            'lowest_balance': self.lowest_balance,
            'trades': trades_data
        }
        
        logger.info(f"📊 BACKTEST RESULTS:")
        logger.info(f"   Total Trades: {len(self.trades)}")
        logger.info(f"   Win Rate: {win_rate:.1f}%")
        logger.info(f"   Total P&L: ${total_pnl:.2f}")
        logger.info(f"   Final Balance: ${self.current_balance:.2f}")
        logger.info(f"   Max Drawdown: {max_drawdown:.1f}%")
        
        return results 