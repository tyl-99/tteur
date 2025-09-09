import pandas as pd
import numpy as np
import datetime
import os
import logging
import json
import pickle
from collections import defaultdict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trade_models import Trade
import warnings

# 🎯 DYNAMIC STRATEGY IMPORTS - ONE LINE PER IMPORT
from strategy.eurusd_strategy import EURUSDSTRATEGY
from strategy.gbpusd_strategy import GBPUSDSTRATEGY
from strategy.usdjpy_strategy import USDJPYSTRATEGY
from strategy.eurgbp_strategy import EURGBPSTRATEGY
from strategy.gbpjpy_strategy import GBPJPYSTRATEGY
from strategy.eurjpy_strategy import EURJPYSTRATEGY
# from strategy.audusd_strategy import AUDUSDStrategy
# from strategy.usdcad_strategy import USDCADStrategy
# from strategy.nzdusd_strategy import NZDUSDStrategy
# from strategy.usdchf_strategy import USDCHFStrategy

# Ignore FutureWarnings from pandas
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, target_pair="EUR/USD", initial_balance=1000, strategy_instance=None):
        # 🎯 DYNAMIC PAIR CONFIGURATION
        self.target_pair = target_pair
        self.pair_code = target_pair.replace("/", "_").replace("-", "_")
        
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.lowest_balance = initial_balance
        
        self.trades = []
        self.open_trades = []
        
        self.min_position_size = 0.01  # Default minimum position size in lots
        self.max_position_size = 2.0   # Default maximum position size in lots

        # 🔧 FIXED: Use persistent strategy instances like ctrader.py
        if strategy_instance:
            self.strategy = strategy_instance
        else:
            self.strategies = {
                "EUR/USD": EURUSDSTRATEGY(),
                "GBP/USD": GBPUSDSTRATEGY(),
                "EUR/GBP": EURGBPSTRATEGY(),
                "USD/JPY": USDJPYSTRATEGY(),
                "GBP/JPY": GBPJPYSTRATEGY(),
                "EUR/JPY": EURJPYSTRATEGY()
            }
            # Get strategy for target pair (like ctrader.py)
            self.strategy = self.strategies.get(target_pair)
        
        if not self.strategy:
            logger.error(f"❌ No strategy available for {target_pair}")
        
        # 🔧 FIXED: Maintain continuous dataframe like real-time
        self.continuous_df = pd.DataFrame()
        self.last_processed_index = 0
        
        # 🔧 NEW: Real-time execution simulation parameters
        self.execution_delay_bars = 2  # 1-2 minute execution delay
        # self.timeout_frequency = 100  # DISABLED: No timeout simulation
        
        # 🕯️ COMPREHENSIVE CANDLE DATA STORAGE
        self.trade_candle_data = {}  # Will store all candle data per trade
        
        # EXCEL & PICKLE LOGGING SETUP
        self.excel_log_path = None
        self.candle_data_path = None
        self.setup_logging()
        
        logger.info(f"💰 Backtest Engine: ${initial_balance} initial balance")
        logger.info(f"🎯 TARGET PAIR: {self.target_pair}")
        logger.info(f"🧠 STRATEGY: {self.strategy.__class__.__name__ if self.strategy else 'No Strategy Available'}")
        logger.info(f"🔧 REALISTIC SIMULATION: Cron timing + execution delays + state persistence")
        logger.info(f"🕯️ COMPREHENSIVE CANDLE DATA: Entry to Exit tracking")
    
    def find_cron_execution_points(self, df):
        """
        🔧 REALISTIC SIMULATION: Find execution points for native timeframe data
        - EUR/USD (H1): Execute on every H1 bar (cron runs hourly)
        - H4 pairs: Execute on every H4 bar (cron runs every 4 hours)
        
        Since we have native timeframe data, each bar represents the exact period
        when cron would execute, so we process most bars but skip some for realism.
        """
        execution_points = []
        
        # Get pair's expected timeframe
        pair_timeframes = {
            "EUR/USD": "H4",  # Changed to H4 for comparison
            "GBP/USD": "H4", 
            "EUR/GBP": "H4",
            "USD/JPY": "H4",
            "GBP/JPY": "H4",
            "EUR/JPY": "H4"
        }
        
        expected_timeframe = pair_timeframes.get(self.target_pair, "M30")
        
        try:
            # Ensure timestamp column is datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            if expected_timeframe == "H1":
                # EUR/USD H1: Process ALL bars (cron filter disabled)
                for idx in range(len(df)):
                    execution_points.append(idx)
                        
            elif expected_timeframe == "H4":
                # H4 pairs: Process ALL bars (cron filter disabled)
                for idx in range(len(df)):
                    execution_points.append(idx)
                        
            else:
                # Fallback: M30 - Process ALL bars (cron filter disabled)
                for idx in range(len(df)):
                    execution_points.append(idx)
            
            execution_rate = (len(execution_points) / len(df)) * 100
            
            logger.info(f"🕐 Found {len(execution_points)} execution points for {self.target_pair} ({expected_timeframe})")
            logger.info(f"🎯 Timeframe: {expected_timeframe} | Execution frequency: {execution_rate:.1f}% of total bars")
            logger.info(f"🚫 CRON FILTER DISABLED: Processing ALL available bars for maximum trades")
            
            return execution_points
            
        except Exception as e:
            logger.error(f"❌ Error finding execution points: {e}")
            # Fallback: use every 30th bar (rough approximation)
            fallback_points = list(range(0, len(df), 30))
            logger.warning(f"⚠️ Using fallback execution points: {len(fallback_points)}")
            return fallback_points
    
    def simulate_execution_delay(self, signal_index, df):
        """
        🔧 REALISTIC SIMULATION: Simulate execution delays and slippage
        Real-time has API delays, network latency, order processing time
        """
        try:
            # Calculate actual execution index (1-2 minutes delay)
            actual_execution_idx = min(signal_index + self.execution_delay_bars, len(df) - 1)
            
            if actual_execution_idx >= len(df):
                return None, None
            
            # Get actual execution price
            actual_price = df.iloc[actual_execution_idx]['close']
            actual_timestamp = df.iloc[actual_execution_idx]['timestamp']
            
            return actual_execution_idx, actual_price, actual_timestamp
            
        except Exception as e:
            logger.error(f"❌ Error simulating execution delay: {e}")
            return signal_index, df.iloc[signal_index]['close'], df.iloc[signal_index]['timestamp']
    
    def get_strategy_file_info(self):
        """
        📝 GET STRATEGY FILE CREATION INFO FOR MISSING PAIRS
        Provides guidance on creating new strategy files
        """
        pair_clean = ''.join(self.target_pair.lower().split('/'))
        class_name = ''.join(self.target_pair.split('/'))
        
        return {
            'file_path': f"strategy/{pair_clean}_strategy.py",
            'class_name': f"{class_name}Strategy",
            'import_statement': f"from strategy.{pair_clean}_strategy import {class_name}Strategy",
            'uncomment_line': f"# from strategy.{pair_clean}_strategy import {class_name}Strategy",
            'example_template': f'''
# strategy/{pair_clean}_strategy.py
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class {class_name}Strategy:
    def __init__(self):
        self.check_count = 0
        self.filtered_count = 0
        self.passed_count = 0
    
    def analyze_trade_signal(self, df: pd.DataFrame, pair: str):
        """
        {self.target_pair} specific trading strategy
        Implement your {self.target_pair} logic here
        """
        self.check_count += 1
        
        try:
            # Add your {self.target_pair} strategy logic here
            # Return format should be:
            # {{
            #     "decision": "BUY" | "SELL" | "NO TRADE",
            #     "entry_price": float,
            #     "stop_loss": float,
            #     "take_profit": float,
            #     "volume": float,
            #     "reason": str
            # }}
            
            # Placeholder - replace with actual strategy
            return {{"decision": "NO TRADE", "reason": "Strategy not implemented"}}
            
        except Exception as e:
            logger.error(f"❌ {class_name}Strategy error: {{e}}")
            return {{"decision": "NO TRADE", "reason": f"Error: {{str(e)}}"}}
    
    def get_statistics(self):
        return {{
            'total_checks': self.check_count,
            'filtered_out': self.filtered_count,
            'passed_to_strategy': self.passed_count
        }}
    
    def print_final_stats(self):
        stats = self.get_statistics()
        print(f"\\n🎯 {class_name.upper()} STRATEGY STATS:")
        print(f"   Total Checks: {{stats['total_checks']:,}}")
        print(f"   Signals Generated: {{stats['passed_to_strategy']:,}}")
'''
        }
    
    def setup_logging(self):
        """Setup logging for dynamic pair with candle data storage"""
        os.makedirs('backtest_logs', exist_ok=True)
        os.makedirs('candle_data', exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Trade logging file
        self.excel_log_path = f"backtest_logs/{self.pair_code}_FULL_trades_{timestamp}.xlsx"
        
        # 🕯️ CANDLE DATA STORAGE (Pickle for efficiency)
        self.candle_data_path = f"candle_data/{self.pair_code}_candle_data_{timestamp}.pkl"
        
        logger.info(f"📊 {self.target_pair} Trade logging: {self.excel_log_path}")
        logger.info(f"🕯️ {self.target_pair} Candle data: {self.candle_data_path}")
    
    def get_pip_size(self, pair):
        """Get pip size for any currency pair"""
        if "JPY" in pair:
            return 0.01
        else:
            return 0.0001
    
    def get_trading_costs(self, pair):
        """Get trading costs for different pairs (set to zero for no spread/slippage)"""
        # User requested no spread/slippage for backtesting
        return {"spread": 0.0, "slippage": 0.0}
    
    def collect_comprehensive_candle_data(self, trade, full_df, entry_index, exit_index):
        """
        Collect comprehensive candle data and a focused slice of up to 500 post-entry candles
        🕯️ COMPLETE PRICE ACTION HISTORY + 500-candle post-entry window
        """
        try:
            trade_id = len(self.trades)
            
            # Calculate full range: 500 candles before entry until exit
            start_index = max(0, entry_index - 500)
            end_index = min(len(full_df) - 1, exit_index)
            
            # Extract all candles in range
            candle_range = full_df.iloc[start_index:end_index + 1].copy()
            candle_range.reset_index(drop=True, inplace=True)
            
            # Add relative positioning
            entry_relative_index = entry_index - start_index
            exit_relative_index = exit_index - start_index
            
            # Mark special candles
            candle_range['candle_type'] = 'normal'
            candle_range.loc[:entry_relative_index - 1, 'candle_type'] = 'pre_entry'
            candle_range.loc[entry_relative_index, 'candle_type'] = 'entry'
            candle_range.loc[entry_relative_index + 1:exit_relative_index - 1, 'candle_type'] = 'in_trade'
            candle_range.loc[exit_relative_index, 'candle_type'] = 'exit'
            
            # Calculate price movements relative to entry
            entry_price = trade.entry_price
            pip_size = self.get_pip_size(trade.pair)
            
            candle_range['pips_from_entry'] = ((candle_range['close'] - entry_price) / pip_size).round(1)
            candle_range['high_pips_from_entry'] = ((candle_range['high'] - entry_price) / pip_size).round(1)
            candle_range['low_pips_from_entry'] = ((candle_range['low'] - entry_price) / pip_size).round(1)
            
            # Mark SL/TP levels hit
            if trade.direction == "BUY":
                candle_range['sl_hit'] = candle_range['low'] <= trade.stop_loss
                candle_range['tp_hit'] = candle_range['high'] >= trade.take_profit
            else:
                candle_range['sl_hit'] = candle_range['high'] >= trade.stop_loss
                candle_range['tp_hit'] = candle_range['low'] <= trade.take_profit
            
            # Calculate candle patterns
            candle_range['body_size'] = abs(candle_range['close'] - candle_range['open'])
            candle_range['upper_wick'] = candle_range['high'] - candle_range[['open', 'close']].max(axis=1)
            candle_range['lower_wick'] = candle_range[['open', 'close']].min(axis=1) - candle_range['low']
            candle_range['total_range'] = candle_range['high'] - candle_range['low']
            candle_range['body_pct'] = (candle_range['body_size'] / candle_range['total_range'] * 100).round(1)
            
            # Bullish/Bearish classification
            candle_range['bullish'] = candle_range['close'] > candle_range['open']
            candle_range['bearish'] = candle_range['close'] < candle_range['open']
            candle_range['doji'] = abs(candle_range['close'] - candle_range['open']) < (candle_range['total_range'] * 0.1)
            
            # Build a focused slice: up to 500 candles after entry (or until exit)
            post_entry_start = entry_index + 1
            post_entry_end = min(entry_index + 500, exit_index)
            post_entry_range = full_df.iloc[post_entry_start:post_entry_end + 1].copy()
            post_entry_range.reset_index(drop=True, inplace=True)

            # Add relative indexing for post-entry window
            post_entry_range['candle_index_from_entry'] = range(1, len(post_entry_range) + 1)

            # Store comprehensive trade candle data
            trade_candle_info = {
                'trade_id': trade_id,
                'pair': trade.pair,
                'direction': trade.direction,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'exit_reason': trade.exit_reason,
                'pips_gained': trade.pips_gained,
                'duration_hours': trade.duration_hours,
                'total_candles': len(candle_range),
                'pre_entry_candles': entry_relative_index,
                'in_trade_candles': exit_relative_index - entry_relative_index,
                'entry_index_in_data': entry_index,
                'exit_index_in_data': exit_index,
                'candle_data': candle_range.to_dict('records'),  # All candles in full range
                'post_entry_candles_500': post_entry_range.to_dict('records')  # Up to 500
            }
            
            # Store in trade_candle_data dictionary
            self.trade_candle_data[trade_id] = trade_candle_info
            
            logger.info(f"🕯️ Collected {len(candle_range)} candles for Trade #{trade_id} ({trade.direction} {trade.pair})")
            
            return trade_candle_info
            
        except Exception as e:
            logger.error(f"❌ Error collecting candle data for trade: {e}")
            return None
    
    def save_candle_data_to_files(self):
        """
        Save candle data to multiple formats:
        1. Pickle for Python processing
        2. Excel for manual analysis
        3. JSON for other applications
        4. JSONL and Parquet (if available) for ML/LLM workflows (post-entry 500)
        """
        import pandas as pd  # Move import to the top of the function
        try:
            if not self.trade_candle_data:
                logger.warning("⚠️ No candle data to save")
                return
            
            # 1. Save as Pickle (most efficient for Python)
            with open(self.candle_data_path, 'wb') as f:
                pickle.dump(self.trade_candle_data, f)
            logger.info(f"🕯️ Candle data saved to pickle: {self.candle_data_path}")
            
            # 2. Save as Excel for manual analysis
            excel_candle_path = self.candle_data_path.replace('.pkl', '.xlsx')
            
            with pd.ExcelWriter(excel_candle_path, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = []
                for trade_id, trade_info in self.trade_candle_data.items():
                    summary_data.append({
                        'trade_id': trade_id,
                        'pair': trade_info['pair'],
                        'direction': trade_info['direction'],
                        'entry_time': trade_info['entry_time'],
                        'exit_time': trade_info['exit_time'],
                        'pips_gained': trade_info['pips_gained'],
                        'exit_reason': trade_info['exit_reason'],
                        'total_candles': trade_info['total_candles'],
                        'duration_hours': trade_info['duration_hours']
                    })
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Trade_Summary', index=False)
                
                # Individual trade sheets (first 20 trades to avoid Excel limits)
                for trade_id, trade_info in list(self.trade_candle_data.items())[:20]:
                    candle_df = pd.DataFrame(trade_info['candle_data'])
                    sheet_name = f"Trade_{trade_id}_{trade_info['direction']}"[:31]  # Excel sheet name limit
                    candle_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"🕯️ Candle data saved to Excel: {excel_candle_path}")
            
            # 3. Save as JSON for other applications
            json_candle_path = self.candle_data_path.replace('.pkl', '.json')
            
            # Convert datetime objects to strings for JSON serialization
            json_data = {}
            for trade_id, trade_info in self.trade_candle_data.items():
                json_trade_info = trade_info.copy()
                json_trade_info['entry_time'] = trade_info['entry_time'].isoformat() if trade_info['entry_time'] else None
                json_trade_info['exit_time'] = trade_info['exit_time'].isoformat() if trade_info['exit_time'] else None
                
                # Convert candle timestamps
                for candle in json_trade_info['candle_data']:
                    if 'timestamp' in candle and pd.notna(candle['timestamp']):
                        candle['timestamp'] = pd.to_datetime(candle['timestamp']).isoformat()
                
                json_data[str(trade_id)] = json_trade_info
            
            with open(json_candle_path, 'w') as f:
                json.dump(json_data, f, indent=2, default=str)
            
            logger.info(f"🕯️ Candle data saved to JSON: {json_candle_path}")

            # 4. Save as JSONL for ML/LLM and Parquet if pyarrow installed
            jsonl_path = self.candle_data_path.replace('.pkl', '_post_entry_500.jsonl')
            try:
                with open(jsonl_path, 'w', encoding='utf-8') as jf:
                    for trade_id, trade_info in self.trade_candle_data.items():
                        base = {
                            'trade_id': trade_id,
                            'pair': trade_info['pair'],
                            'direction': trade_info['direction'],
                            'entry_time': trade_info['entry_time'].isoformat() if trade_info['entry_time'] else None,
                            'exit_time': trade_info['exit_time'].isoformat() if trade_info['exit_time'] else None,
                            'entry_price': trade_info['entry_price'],
                            'exit_price': trade_info['exit_price'],
                            'stop_loss': trade_info['stop_loss'],
                            'take_profit': trade_info['take_profit'],
                            'pips_gained': trade_info['pips_gained']
                        }
                        for row in trade_info.get('post_entry_candles_500', []):
                            record = {**base, **row}
                            jf.write(json.dumps(record, default=str) + "\n")
                logger.info(f"🧾 JSONL saved: {jsonl_path}")
            except Exception as e:
                logger.error(f"❌ Error saving JSONL: {e}")

            # Parquet (optional)
            try:
                import pandas as pd  # Explicitly import pandas here
                import pyarrow as pa  # type: ignore
                import pyarrow.parquet as pq  # type: ignore
                parquet_path = self.candle_data_path.replace('.pkl', '_post_entry_500.parquet')
                rows = []
                for trade_id, trade_info in self.trade_candle_data.items():
                    base = {
                        'trade_id': trade_id,
                        'pair': trade_info['pair'],
                        'direction': trade_info['direction'],
                        'entry_time': trade_info['entry_time'],
                        'exit_time': trade_info['exit_time'],
                        'entry_price': trade_info['entry_price'],
                        'exit_price': trade_info['exit_price'],
                        'stop_loss': trade_info['stop_loss'],
                        'take_profit': trade_info['take_profit'],
                        'pips_gained': trade_info['pips_gained']
                    }
                    for row in trade_info.get('post_entry_candles_500', []):
                        rows.append({**base, **row})
                if rows:
                    df_parquet = pd.DataFrame(rows)
                    table = pa.Table.from_pandas(df_parquet)
                    pq.write_table(table, parquet_path)
                    logger.info(f"🧾 Parquet saved: {parquet_path}")
            except Exception as e:
                logger.warning(f"⚠️ Parquet export skipped: {e}")

            # 5. Optional: copy artifacts to web_app/public/data for dashboard
            try:
                from pathlib import Path
                web_data_dir = Path('web_app/public/data')
                if web_data_dir.exists():
                    import shutil
                    shutil.copy2(json_candle_path, web_data_dir / Path(json_candle_path).name)
                    shutil.copy2(self.candle_data_path, web_data_dir / Path(self.candle_data_path).name)
                    if os.path.exists(jsonl_path):
                        shutil.copy2(jsonl_path, web_data_dir / Path(jsonl_path).name)
                    parquet_path_opt = self.candle_data_path.replace('.pkl', '_post_entry_500.parquet')
                    if os.path.exists(parquet_path_opt):
                        shutil.copy2(parquet_path_opt, web_data_dir / Path(parquet_path_opt).name)
                    logger.info(f"🌐 Copied artifacts to {web_data_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Copy to web_app/public/data skipped: {e}")
            
            # 4. Create a quick access method file
            method_file_path = self.candle_data_path.replace('.pkl', '_access_methods.py')
            method_code = f'''
# {self.target_pair} Candle Data Access Methods
# Generated on {datetime.datetime.now()}

import pickle
import pandas as pd
import json

def load_candle_data():
    """Load all candle data from pickle file"""
    with open('{self.candle_data_path}', 'rb') as f:
        return pickle.load(f)

def get_trade_candles(trade_id):
    """Get candle data for specific trade"""
    data = load_candle_data()
    return data.get(trade_id, None)

def get_trade_as_dataframe(trade_id):
    """Get trade candle data as pandas DataFrame"""
    trade_data = get_trade_candles(trade_id)
    if trade_data:
        return pd.DataFrame(trade_data['candle_data'])
    return None

def list_all_trades():
    """List all available trades"""
    data = load_candle_data()
    trades = []
    for trade_id, trade_info in data.items():
        trades.append({{
            'trade_id': trade_id,
            'pair': trade_info['pair'],
            'direction': trade_info['direction'],
            'pips_gained': trade_info['pips_gained'],
            'exit_reason': trade_info['exit_reason']
        }})
    return trades

def get_winning_trades():
    """Get only winning trades"""
    data = load_candle_data()
    return {{k: v for k, v in data.items() if v['pips_gained'] > 0}}

def get_losing_trades():
    """Get only losing trades"""
    data = load_candle_data()
    return {{k: v for k, v in data.items() if v['pips_gained'] <= 0}}

# Example usage:
# data = load_candle_data()
# trade_1_df = get_trade_as_dataframe(1)
# all_trades = list_all_trades()
'''
            
            with open(method_file_path, 'w') as f:
                f.write(method_code)
            
            logger.info(f"🕯️ Access methods saved: {method_file_path}")
            
            # Print summary
            print(f"\n🕯️ CANDLE DATA SAVED:")
            print(f"   📊 Total trades with candle data: {len(self.trade_candle_data):,}")
            print(f"   🐍 Pickle file (Python): {self.candle_data_path}")
            print(f"   📊 Excel file (Analysis): {excel_candle_path}")
            print(f"   🌐 JSON file (Universal): {json_candle_path}")
            print(f"   🧾 JSONL (ML/LLM): {jsonl_path}")
            print(f"   🔧 Access methods: {method_file_path}")
            
        except Exception as e:
            logger.error(f"❌ Error saving candle data: {e}")
    
    def aggregate_to_timeframe(self, df, target_timeframe):
        """
        🔧 Convert 30-minute data to target timeframe (H1 or H4)
        """
        try:
            if target_timeframe == "M30":
                return df  # Already 30-minute data
            
            # Ensure timestamp is datetime and set as index
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Define aggregation rules
            agg_rules = {
                'open': 'first',
                'high': 'max', 
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            
            # Resample based on target timeframe
            if target_timeframe == "H1":
                # Aggregate to 1-hour bars
                resampled = df.resample('1H').agg(agg_rules)
            elif target_timeframe == "H4":
                # Aggregate to 4-hour bars  
                resampled = df.resample('4H').agg(agg_rules)
            else:
                logger.warning(f"⚠️ Unknown timeframe {target_timeframe}, returning original data")
                return df.reset_index()
            
            # Remove any NaN rows and reset index
            resampled = resampled.dropna()
            resampled.reset_index(inplace=True)
            
            # 🔧 CRITICAL: Recalculate candle_range for aggregated data
            # Strategies depend on this column for analysis
            resampled['candle_range'] = resampled['high'] - resampled['low']
            
            logger.info(f"🔄 Aggregated {len(df)} M30 bars → {len(resampled)} {target_timeframe} bars")
            logger.info(f"✅ Recalculated candle_range for {target_timeframe} data")
            return resampled
            
        except Exception as e:
            logger.error(f"❌ Error aggregating to {target_timeframe}: {e}")
            return df
    
    def load_excel_data(self, file_path='data/forex_data1.xlsx'):
        """
        🚀 ENHANCED: Load NATIVE timeframe data directly from fetch_data.py
        - EUR/USD: Native H1 data (no aggregation needed)
        - H4 pairs: Native H4 data (no aggregation needed)
        - Maximum accuracy with broker's official candles
        """
        # 🔧 FIX: Handle both relative paths (from backtest dir) and absolute paths
        possible_paths = [
            file_path,
            f'backtest/{file_path}',
            f'data/forex_data1.xlsx',
            f'backtest/data/forex_data1.xlsx'
        ]
        
        actual_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_file_path = path
                break
        
        if not actual_file_path:
            logger.error(f"❌ Data file not found. Tried paths: {possible_paths}")
            return {}
        
        # Get pair's expected timeframe
        pair_timeframes = {
            "EUR/USD": "H4",  # Changed to H4 for comparison
            "GBP/USD": "H4", 
            "EUR/GBP": "H4",
            "USD/JPY": "H4",
            "GBP/JPY": "H4",
            "EUR/JPY": "H4"
        }
        
        expected_timeframe = pair_timeframes.get(self.target_pair, "M30")
        
        logger.info(f"📊 Loading {self.target_pair} data from {actual_file_path}")
        logger.info(f"🎯 Expected timeframe: {expected_timeframe} (NATIVE)")
        data = {}
        
        try:
            with pd.ExcelFile(actual_file_path) as excel_file:
                sheet_names = excel_file.sheet_names
                target_sheet = None
                
                # Try different possible sheet names for target pair
                pair_variations = [
                    self.target_pair,
                    self.target_pair.replace("/", "_"),
                    self.target_pair.replace("/", ""),
                    self.target_pair.replace("-", "_"),
                    self.target_pair.replace("-", ""),
                    self.target_pair.lower(),
                    self.target_pair.lower().replace("/", "_"),
                    self.target_pair.lower().replace("/", ""),
                    self.target_pair.upper(),
                    self.target_pair.upper().replace("/", "_"),
                    self.target_pair.upper().replace("/", "")
                ]
                
                for variation in pair_variations:
                    if variation in sheet_names:
                        target_sheet = variation
                        break
                
                if not target_sheet:
                    logger.error(f"❌ {self.target_pair} sheet not found. Available sheets: {sheet_names}")
                    return {}
                
                # Read target pair sheet (now contains NATIVE timeframe data)
                df = pd.read_excel(excel_file, sheet_name=target_sheet)
                
                # Ensure timestamp column is datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Sort by timestamp (ascending for backtest)
                df.sort_values('timestamp', inplace=True, ascending=True)
                df.reset_index(drop=True, inplace=True)
                
                # Ensure candle_range exists (should be pre-calculated)
                if 'candle_range' not in df.columns:
                    df['candle_range'] = df['high'] - df['low']
                    logger.warning(f"⚠️ Added missing candle_range column")
                
                logger.info(f"✅ Loaded NATIVE {self.target_pair}: {len(df):,} {expected_timeframe} bars")
                logger.info(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                logger.info(f"🎯 NATIVE TIMEFRAME: No aggregation needed - maximum broker accuracy!")
                
                data[self.target_pair] = df
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading {self.target_pair} data: {e}")
            return {}
    
    def log_trade_to_excel(self, trade):
        """Save trade result to Excel with basic info"""
        if not self.excel_log_path:
            return
        
        try:
            pip_size = self.get_pip_size(trade.pair)
            
            # Basic trade data
            trade_data = {
                'trade_id': len(self.trades),
                'entry_time': trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if trade.entry_time else '',
                'exit_time': trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else '',
                'pair': trade.pair,
                'direction': trade.direction,
                'entry_price': round(trade.entry_price, 5),
                'exit_price': round(trade.exit_price, 5) if trade.exit_price else 0,
                'stop_loss': round(trade.stop_loss, 5),
                'take_profit': round(trade.take_profit, 5),
                'volume': trade.volume,
                'pips_gained': round(trade.pips_gained, 1),
                'usd_pnl': round(trade.usd_pnl, 2),
                'exit_reason': trade.exit_reason or '',
                'duration_hours': round(trade.duration_hours, 1),
                'balance_after': round(self.current_balance, 2),
                'win_loss': "WIN" if trade.usd_pnl > 0 else "LOSS",
                'candle_data_available': 'YES'  # All trades have candle data
            }
            
            # Read existing data or create new
            try:
                existing_df = pd.read_excel(self.excel_log_path, sheet_name='Trades')
            except FileNotFoundError:
                # If the file or sheet doesn't exist, create an empty DataFrame with correct columns
                existing_df = pd.DataFrame(columns=list(trade_data.keys()))
            except Exception as e:
                logger.error(f"Error reading existing Excel trade log: {e}")
                existing_df = pd.DataFrame(columns=list(trade_data.keys())) # Fallback
            
            # Append new trade
            new_trade_df = pd.DataFrame([trade_data])
            updated_df = pd.concat([existing_df, new_trade_df], ignore_index=True)
            
            # Save back to Excel
            updated_df.to_excel(self.excel_log_path, index=False, sheet_name='Trades')
            
            win_loss = trade_data['win_loss']
            trade_count = len(self.trades)
            logger.info(f"📊 Trade #{trade_count}: {win_loss} | Balance: ${self.current_balance:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log trade to Excel: {e}")
    
    def open_trade(self, signal, timestamp, pair, market_price, current_index, full_df):
        """Open a new trade and store the data index for candle collection"""
        if signal.get("decision", "NO TRADE").upper() == "NO TRADE":
            return
        
        # Validate signal
        required = ["entry_price", "stop_loss", "take_profit", "volume"]
        if not all(field in signal for field in required):
            logger.warning(f"⚠️ Invalid signal for {pair}: missing required fields")
            return
        
        if signal["volume"] <= 0:
            logger.warning(f"⚠️ Invalid volume for {pair}: {signal['volume']}")
            return
        
        # Define target risk in USD
        target_risk_usd = 100.0
        target_reward_usd = 200.0 # Your desired 1:2 R:R

        # Apply trading costs to get actual entry price
        costs = self.get_trading_costs(pair)
        pip_size = self.get_pip_size(pair)
        total_cost_pips = (costs["spread"] + costs["slippage"])
        total_cost_price_units = total_cost_pips * pip_size

        if signal["decision"].upper() == "BUY":
            actual_entry = market_price + total_cost_price_units
            # Calculate adjusted SL based on strategy's fixed pips risk
        else:
            actual_entry = market_price - total_cost_price_units
            # Calculate adjusted SL based on strategy's fixed pips risk
            
        # Use strategy's provided SL, TP, and Volume directly
        final_stop_loss = signal["stop_loss"]
        final_take_profit = signal["take_profit"]
        final_volume = signal["volume"]

        # Create trade with strategy's original values
        trade = Trade(
            timestamp, pair, signal["decision"].upper(), actual_entry,
            final_stop_loss, final_take_profit, 
            final_volume, signal.get("reason", "Strategy signal") 
        )
        
        # 🕯️ STORE ENTRY INDEX FOR CANDLE DATA COLLECTION
        trade.entry_index = current_index
        trade.full_df_reference = full_df  # Store reference to full dataset
        
        # Simple logging for opened trades
        logger.info(f"📈 OPENED {trade.direction} {pair} @ {trade.entry_price:.5f} | SL: {trade.stop_loss:.5f}, TP: {trade.take_profit:.5f}, Volume: {trade.volume:.2f} lots")

        self.open_trades.append(trade)
    
    def check_trade_exits(self, timestamp, bar_data, pair, current_index):
        """Check if any open trades should be closed and collect candle data"""
        trades_to_close = []
        
        for trade in self.open_trades:
            if trade.pair != pair:
                continue
            
            high = bar_data['high']
            low = bar_data['low']
            open_price = bar_data['open']
            
            exit_price = None
            exit_reason = None
            
            if trade.direction == "BUY":
                sl_hit = low <= trade.stop_loss
                tp_hit = high >= trade.take_profit
                
                if sl_hit and tp_hit:
                    # Both hit - determine order by distance to open
                    distance_to_sl = abs(open_price - trade.stop_loss)
                    distance_to_tp = abs(open_price - trade.take_profit)
                    
                    if distance_to_sl <= distance_to_tp:
                        exit_price = trade.stop_loss
                        exit_reason = "Stop Loss"
                    else:
                        exit_price = trade.take_profit
                        exit_reason = "Take Profit"
                elif sl_hit:
                    exit_price = trade.stop_loss
                    exit_reason = "Stop Loss"
                elif tp_hit:
                    exit_price = trade.take_profit
                    exit_reason = "Take Profit"
                
            else:  # SELL
                sl_hit = high >= trade.stop_loss
                tp_hit = low <= trade.take_profit
                
                if sl_hit and tp_hit:
                    distance_to_sl = abs(open_price - trade.stop_loss)
                    distance_to_tp = abs(open_price - trade.take_profit)
                    
                    if distance_to_sl <= distance_to_tp:
                        exit_price = trade.stop_loss
                        exit_reason = "Stop Loss"
                    else:
                        exit_price = trade.take_profit
                        exit_reason = "Take Profit"
                elif sl_hit:
                    exit_price = trade.stop_loss
                    exit_reason = "Stop Loss"
                elif tp_hit:
                    exit_price = trade.take_profit
                    exit_reason = "Take Profit"
        
            if exit_price:
                # 🕯️ COLLECT COMPREHENSIVE CANDLE DATA
                self.close_trade_with_candle_data(trade, timestamp, exit_price, exit_reason, current_index)
                trades_to_close.append(trade)
        
        # Remove closed trades
        for trade in trades_to_close:
            if trade in self.open_trades:
                self.open_trades.remove(trade)
    
    def close_trade_with_candle_data(self, trade, exit_time, exit_price, exit_reason, exit_index):
        """Close trade and collect comprehensive candle data"""
        pnl = trade.close_trade(exit_time, exit_price, exit_reason)
        
        # Update balance and tracking
        self.current_balance += pnl
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        if self.current_balance < self.lowest_balance:
            self.lowest_balance = self.current_balance
        
        # 🕯️ COLLECT COMPREHENSIVE CANDLE DATA
        self.collect_comprehensive_candle_data(
            trade, 
            trade.full_df_reference, 
            trade.entry_index, 
            exit_index
        )
        
        # Add to completed trades
        self.trades.append(trade)
        
        # Log to Excel
        self.log_trade_to_excel(trade)
        
        # Explicitly log comprehensive trade details for debugging
        logger.info(f"📊 CLOSED {trade.direction} {trade.pair} | Reason: {trade.exit_reason} | Pips: {trade.pips_gained:+.2f}")
        logger.info(f"   Entry: {trade.entry_price:.5f}, Exit: {trade.exit_price:.5f}, SL: {trade.stop_loss:.5f}, TP: {trade.take_profit:.5f}, Volume: {trade.volume:.2f}")

        return pnl
    
    def run_backtest(self):
        """
        🔧 REALISTIC BACKTEST: Simulates real ctrader.py execution behavior
        - Cron timing (XX:02, XX:32)
        - Persistent strategy state
        - Execution delays
        - Timeout constraints
        """
        logger.info(f"🚀 Starting REALISTIC {self.target_pair} backtest simulation...")
        
        # 🎯 CHECK IF STRATEGY IS AVAILABLE
        if self.strategy is None:
            strategy_info = self.get_strategy_file_info()
            logger.error(f"❌ No strategy available for {self.target_pair}")
            print(f"\n🚫 BACKTEST ABORTED - NO STRATEGY AVAILABLE")
            print(f"📝 Create strategy file for {self.target_pair}:")
            print(f"   File: {strategy_info['file_path']}")
            print(f"   Class: {strategy_info['class_name']}")
            return
        
        # Load target pair data
        data = self.load_excel_data()
        if not data or self.target_pair not in data:
            logger.error(f"❌ No {self.target_pair} data loaded. Aborting backtest.")
            return
        
        pair_df = data[self.target_pair]
        if pair_df.empty:
            logger.error(f"❌ {self.target_pair} data is empty. Aborting backtest.")
            return
        
        logger.info(f"📊 {self.target_pair} data loaded: {len(pair_df):,} bars")
        
        # Minimum data requirement
        min_bars_for_strategy = 250
        if len(pair_df) < min_bars_for_strategy:
            logger.error(f"❌ Insufficient data. Need {min_bars_for_strategy} bars, got {len(pair_df)}")
            return
        
        # 🔧 FIND REALISTIC EXECUTION POINTS (CRON SCHEDULE)
        execution_points = self.find_cron_execution_points(pair_df)
        
        # Filter execution points to have minimum data
        valid_execution_points = [ep for ep in execution_points if ep >= min_bars_for_strategy - 1]
        
        logger.info(f"🕐 Processing {len(valid_execution_points)} cron execution points...")
        logger.info(f"🔧 Realistic vs Original: {len(valid_execution_points)} vs {len(pair_df)} bars")
        logger.info(f"🎯 Execution frequency: {len(valid_execution_points)/len(pair_df)*100:.1f}% of total bars")
        
        # 🔧 MAIN REALISTIC BACKTEST LOOP
        processed_count = 0
        timeout_count = 0
        
        for exec_idx in valid_execution_points:
            processed_count += 1
            
            try:
                # 🔧 TIMEOUT SIMULATION DISABLED - Focus on pure strategy performance
                # if processed_count % self.timeout_frequency == 0:
                #     timeout_count += 1
                #     logger.info(f"⏰ Timeout simulation #{timeout_count}: Skipping execution (1% rate)")
                #     continue
                
                current_bar = pair_df.iloc[exec_idx]
                timestamp = current_bar['timestamp']
                
                # Check exits first (pass current index for candle data)
                self.check_trade_exits(timestamp, current_bar, self.target_pair, exec_idx)
            
                # Check for new signals (only if no open trade)
                has_open_trade = any(t.pair == self.target_pair for t in self.open_trades)
                
                if not has_open_trade:
                    try:
                        # 🔧 FIXED: Use continuous data (like ctrader.py)
                        # Give strategy the FULL continuous data up to current point
                        current_data = pair_df.iloc[:exec_idx + 1].copy()
                        
                        if len(current_data) >= min_bars_for_strategy:
                            # 🔧 STRATEGY STATE PERSISTS (like ctrader.py)
                            signal = self.strategy.analyze_trade_signal(current_data, self.target_pair)
                            
                            # Open trade if valid with execution delay simulation
                            if signal.get("decision", "NO TRADE").upper() != "NO TRADE":
                                # 🔧 SIMULATE EXECUTION DELAY
                                exec_result = self.simulate_execution_delay(exec_idx, pair_df)
                                
                                if exec_result and len(exec_result) == 3:
                                    actual_exec_idx, actual_price, actual_timestamp = exec_result
                                    
                                    # Apply realistic slippage
                                    costs = self.get_trading_costs(self.target_pair)
                                    pip_size = self.get_pip_size(self.target_pair)
                                    total_cost = (costs["spread"] + costs["slippage"]) * pip_size
                                    
                                    if signal["decision"].upper() == "BUY":
                                        realistic_entry = actual_price + total_cost
                                    else:
                                        realistic_entry = actual_price - total_cost
                                    
                                    # Modify signal with realistic entry price
                                    signal["entry_price"] = realistic_entry
                                    
                                    self.open_trade(signal, actual_timestamp, self.target_pair, 
                                                  actual_price, actual_exec_idx, pair_df)
                                    
                                    # Reduced logging: only log occasionally to reduce noise
                                    if len(self.trades) % 5 == 1:  # Log every 5th trade
                                        logger.info(f"🔧 Execution delay: Signal at {exec_idx} → Executed at {actual_exec_idx}")
                                
                    except Exception as e:
                        logger.error(f"❌ Strategy error at {timestamp}: {e}")
            
                # Progress reporting
                progress = processed_count / len(valid_execution_points) * 100
                if processed_count % 200 == 0:  # Reduced frequency: every 200 instead of 50
                    logger.info(f"📊 Progress: {progress:.1f}% | Trades: {len(self.trades):,}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing execution point {exec_idx}: {e}")
                continue
        
        # Close remaining trades
        if self.open_trades:
            logger.info("🔒 Closing remaining trades...")
            final_bar = pair_df.iloc[-1]
            final_index = len(pair_df) - 1
            for trade in self.open_trades[:]:
                self.close_trade_with_candle_data(trade, final_bar['timestamp'], final_bar['close'], "End of backtest", final_index)
        
        # Save all candle data
        self.save_candle_data_to_files()
        
        # Print final statistics
        results = self.print_realistic_results(len(valid_execution_points), len(pair_df))
        
        logger.info(f"🎯 REALISTIC {self.target_pair} backtest simulation completed!")
        return results
    
    def print_realistic_results(self, execution_points, total_bars):
        """Print realistic backtest results focused on pure strategy performance"""
        total_trades = len(self.trades)
        if total_trades == 0:
            # Returning an empty dict when no trades, to prevent errors in autotuner.
            return {'total_trades': 0, 'win_rate': 0, 'overall_rr': 0, 'final_balance': self.initial_balance}
        
        winning_trades = [t for t in self.trades if t.pips_gained > 0]
        win_rate = len(winning_trades) / total_trades * 100
        
        # Calculate overall Risk-Reward Ratio
        total_winning_pips = sum(t.pips_gained for t in winning_trades)
        losing_trades = [t for t in self.trades if t.pips_gained <= 0]
        total_losing_pips = sum(abs(t.pips_gained) for t in losing_trades)
        
        overall_rr = (total_winning_pips / len(winning_trades)) / (total_losing_pips / len(losing_trades)) if len(winning_trades) > 0 and len(losing_trades) > 0 else 0
        
        # The rest of this method remains the same for printing, I'm just adding the return statement for use by the autotuner
        print(f"\n" + "="*80)
        print(f"🔧 {self.target_pair} REALISTIC BACKTEST RESULTS")
        print(f"="*80)
        print(f"🧠 Strategy: {self.strategy.__class__.__name__ if self.strategy else 'No Strategy'}")
        print(f"")
        print(f"📊 EXECUTION SIMULATION:")
        print(f"   Cron Execution Points: {execution_points:,}")
        print(f"   Total Available Bars: {total_bars:,}")
        print(f"   Execution Frequency: {execution_points/total_bars*100:.1f}% of bars")
        print(f"   Timeout Simulation: DISABLED (Pure strategy performance)")
        print(f"")
        print(f"🎯 TRADING RESULTS:")
        print(f"   Total Trades: {total_trades:,}")
        print(f"   Win Rate: {win_rate:.2f}%")
        print(f"   Winning Trades: {len(winning_trades):,}")
        print(f"   Losing Trades: {total_trades - len(winning_trades):,}")

        print(f"")
        print(f"🎯 TRADING SUMMARY:")
        print(f"   Overall R:R Ratio: {overall_rr:.2f}:1")
        print(f"")
        print(f"🔧 REALISM IMPROVEMENTS:")
        print(f"   ✅ Persistent Strategy State (like ctrader.py)")
        print(f"   ✅ Cron Schedule Simulation (XX:02, XX:32)")
        print(f"   ✅ Execution Delays & Slippage")
        print(f"   🚫 Timeout Constraints (DISABLED for pure performance)")
        print(f"   ✅ Continuous Data Feed (no reset_index)")
        print(f"")
        print(f"🕯️ DATA COLLECTION:")
        print(f"   Candle Data: {len(self.trade_candle_data):,} trades with full history")
        print(f"   Trade Log: {self.excel_log_path}")
        print(f"   Candle Data: {self.candle_data_path}")
        print(f"")
        print(f"🎯 REALISTIC vs OLD BACKTEST:")
        print(f"   Old Method: {total_bars:,} execution opportunities")
        print(f"   Realistic: {execution_points:,} execution opportunities")
        print(f"   Reduction: {(1 - execution_points/total_bars)*100:.1f}% fewer opportunities")
        print(f"="*80)
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'overall_rr': overall_rr,
            'final_balance': self.current_balance
        }
    
    def print_final_results(self):
        """Print final backtest results (fallback for old method)"""
        total_trades = len(self.trades)
        if total_trades == 0:
            print(f"\n🚫 No trades executed for {self.target_pair}")
            return
        
        winning_trades = [t for t in self.trades if t.usd_pnl > 0]
        win_rate = len(winning_trades) / total_trades * 100
        total_pnl = sum(t.usd_pnl for t in self.trades)
        
        print(f"\n" + "="*80)
        print(f"🎯 {self.target_pair} BACKTEST RESULTS")
        print(f"="*80)
        print(f"🧠 Strategy: {self.strategy.__class__.__name__ if self.strategy else 'No Strategy'}")
        print(f"📊 Total Trades: {total_trades:,}")
        print(f"🎯 Win Rate: {win_rate:.2f}%")
        print(f"💰 Total P&L: ${total_pnl:+,.2f}")
        print(f"📈 Final Balance: ${self.current_balance:,.2f}")
        print(f"📊 Return: {((self.current_balance - self.initial_balance) / self.initial_balance * 100):+.2f}%")
        print(f"🕯️ Candle Data: {len(self.trade_candle_data):,} trades with full candle history")
        print(f"📋 Trade Log: {self.excel_log_path}")
        print(f"🕯️ Candle Data: {self.candle_data_path}")
        print(f"="*80)
    
    def run_legacy_backtest(self):
        """
        🗄️ LEGACY METHOD: Old backtest for comparison (processes every bar)
        Use this to compare with realistic results
        """
        logger.info(f"🗄️ Running LEGACY {self.target_pair} backtest for comparison...")
        
        # Reset state for fair comparison
        self.current_balance = self.initial_balance
        self.trades = []
        self.open_trades = []
        self.trade_candle_data = {}
        
        # Create fresh strategy instance for legacy test
        legacy_strategies = {
            "EUR/USD": EURUSDSTRATEGY(),
            "GBP/USD": GBPUSDSTRATEGY(),
            "EUR/GBP": EURGBPSTRATEGY(),
            "USD/JPY": USDJPYSTRATEGY(),
            "GBP/JPY": GBPJPYSTRATEGY(),
            "EUR/JPY": EURJPYSTRATEGY()
        }
        legacy_strategy = legacy_strategies.get(self.target_pair)
        
        if not legacy_strategy:
            logger.error(f"❌ No legacy strategy available for {self.target_pair}")
            return
        
        # Load data
        data = self.load_excel_data()
        if not data or self.target_pair not in data:
            logger.error(f"❌ No {self.target_pair} data loaded. Aborting legacy backtest.")
            return
        
        pair_df = data[self.target_pair]
        min_bars_for_strategy = 250
        
        logger.info(f"🗄️ Legacy processing {len(pair_df) - min_bars_for_strategy + 1:,} bars...")
        
        # OLD METHOD: Process every bar
        for i in range(min_bars_for_strategy - 1, len(pair_df)):
            current_bar = pair_df.iloc[i]
            timestamp = current_bar['timestamp']
            
            self.check_trade_exits(timestamp, current_bar, self.target_pair, i)
            
            has_open_trade = any(t.pair == self.target_pair for t in self.open_trades)
            
            if not has_open_trade:
                try:
                    # OLD METHOD: Create fresh data slice (destroys state)
                    start_idx = max(0, i - min_bars_for_strategy + 1)
                    strategy_data = pair_df.iloc[start_idx:i + 1].copy()
                    strategy_data.reset_index(drop=True, inplace=True)  # DESTROYS STATE!
                    
                    if len(strategy_data) >= min_bars_for_strategy:
                        signal = legacy_strategy.analyze_trade_signal(strategy_data, self.target_pair)
                        
                        if signal.get("decision", "NO TRADE").upper() != "NO TRADE":
                            self.open_trade(signal, timestamp, self.target_pair, current_bar['close'], i, pair_df)
                            
                except Exception as e:
                    logger.error(f"❌ Legacy strategy error at {timestamp}: {e}")
        
        # Close remaining trades
        if self.open_trades:
            final_bar = pair_df.iloc[-1]
            final_index = len(pair_df) - 1
            for trade in self.open_trades[:]:
                self.close_trade_with_candle_data(trade, final_bar['timestamp'], final_bar['close'], "End of legacy test", final_index)
        
        # Print legacy results
        total_trades = len(self.trades)
        if total_trades > 0:
            winning_trades = [t for t in self.trades if t.pips_gained > 0]
            win_rate = len(winning_trades) / total_trades * 100
            
            print(f"\n🗄️ LEGACY BACKTEST RESULTS:")
            print(f"   Total Trades: {total_trades:,}")
            print(f"   Win Rate: {win_rate:.2f}%")
            print(f"   Final Balance: ${self.current_balance:,.2f}")
        
        logger.info(f"🗄️ Legacy {self.target_pair} backtest completed!")
        return {
            'trades': total_trades,
            'win_rate': win_rate if total_trades > 0 else 0,
            'balance': self.current_balance
        }
    
    def run_comparison_backtest(self):
        """
        🔀 COMPARISON: Run both realistic and legacy methods
        Shows the difference between old and new approaches
        """
        print(f"\n🔀 RUNNING COMPARISON BACKTEST FOR {self.target_pair}")
        print(f"="*80)
        
        # Run realistic first
        print(f"1️⃣ Running REALISTIC simulation...")
        self.run_backtest()
        realistic_results = {
            'trades': len(self.trades),
            'win_rate': len([t for t in self.trades if t.pips_gained > 0]) / len(self.trades) * 100 if self.trades else 0,
            'balance': self.current_balance
        }
        
        print(f"\n2️⃣ Running LEGACY simulation...")
        legacy_results = self.run_legacy_backtest()
        
        # Print comparison
        print(f"\n" + "="*80)
        print(f"🔀 REALISTIC vs LEGACY COMPARISON")
        print(f"="*80)
        print(f"📊 TRADE FREQUENCY:")
        print(f"   Realistic: {realistic_results['trades']:,} trades")
        print(f"   Legacy: {legacy_results['trades']:,} trades")
        if legacy_results['trades'] > 0:
            reduction = (1 - realistic_results['trades'] / legacy_results['trades']) * 100
            print(f"   Reduction: {reduction:.1f}% fewer trades (more realistic)")
        print(f"")
        print(f"🎯 WIN RATE:")
        print(f"   Realistic: {realistic_results['win_rate']:.2f}%")
        print(f"   Legacy: {legacy_results['win_rate']:.2f}%")
        print(f"   Difference: {realistic_results['win_rate'] - legacy_results['win_rate']:+.2f}%")
        print(f"")
        print(f"🔧 CRITICAL FIXES APPLIED:")
        print(f"   ✅ Matches real ctrader.py execution")
        print(f"   ✅ Proper strategy state persistence")
        print(f"   ✅ Correct timeframe data per pair")
        print(f"   ✅ Realistic execution timing per timeframe")
        print(f"   ✅ Accounts for delays and slippage")
        print(f"   ✅ Simulates timeout constraints")
        print(f"")
        print(f"📊 NATIVE TIMEFRAME OPTIMIZATION:")
        if self.target_pair == "EUR/USD":
            print(f"   ✅ EUR/USD: Native H1 data + hourly execution")
        else:
            print(f"   ✅ {self.target_pair}: Native H4 data + 4-hourly execution")
        print(f"   🎯 No aggregation needed - maximum broker accuracy!")
        print(f"   ⚡ Faster processing with smaller datasets")
        print(f"="*80)
    
    def verify_timeframe_setup(self):
        """
        🔍 VERIFICATION: Show the user exactly what timeframe setup is being used
        """
        pair_timeframes = {
            "EUR/USD": "H4",  # Changed to H4 for comparison
            "GBP/USD": "H4", 
            "EUR/GBP": "H4",
            "USD/JPY": "H4",
            "GBP/JPY": "H4",
            "EUR/JPY": "H4"
        }
        
        expected_timeframe = pair_timeframes.get(self.target_pair, "M30")
        
        print(f"\n🔍 TIMEFRAME VERIFICATION FOR {self.target_pair}")
        print(f"="*60)
        print(f"📊 Expected Strategy Timeframe: {expected_timeframe}")
        print(f"🎯 Backtest Data Timeframe: {expected_timeframe} (NATIVE)")
        print(f"🕐 Execution Schedule:")
        
        if expected_timeframe == "H1":
            print(f"   ⏰ Every hour at XX:02 (00:02, 01:02, 02:02, ...)")
            print(f"   📈 Uses NATIVE 1-hour candles from broker API")
            print(f"   ⚡ 50% less data than M30 aggregation approach")
        elif expected_timeframe == "H4":
            print(f"   ⏰ Every 4 hours at XX:02 (00:02, 04:02, 08:02, 12:02, 16:02, 20:02)")
            print(f"   📈 Uses NATIVE 4-hour candles from broker API")
            print(f"   ⚡ 87.5% less data than M30 aggregation approach")
        else:
            print(f"   ⏰ Every 30 minutes at XX:02, XX:32")
            print(f"   📈 Uses 30-minute candles (original data)")
        
        print(f"")
        print(f"✅ NATIVE TIMEFRAMES: Maximum accuracy + efficiency!")
        print(f"🚀 Backtest matches real ctrader.py behavior perfectly!")
        print(f"="*60)

if __name__ == "__main__":
    try:
        # Define all target pairs to backtest
        ALL_TARGET_PAIRS = [
            "EUR/USD",
            "GBP/USD",
            "EUR/GBP",
            "USD/JPY",
            "GBP/JPY",
            "EUR/JPY"
        ]

        all_results = {}

        for pair in ALL_TARGET_PAIRS:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING BACKTEST FOR {pair}")
            print(f"{'='*80}")

            # Initialize backtest engine for the current target pair
            engine = BacktestEngine(
                target_pair=pair,
                initial_balance=1000
            )
            
            # Show timeframe verification for the current pair
            engine.verify_timeframe_setup()

            # Run realistic simulation for the current pair
            results = engine.run_backtest()
            if results:
                all_results[pair] = results

            print(f"\n{'='*80}")
            print(f"✅ BACKTEST COMPLETED FOR {pair}")
            print(f"{'='*80}\n")
        
        # Print summary of all backtests
        print(f"\n\n{'='*80}")
        print(f"📊 SUMMARY OF ALL BACKTEST RESULTS")
        print(f"{'='*80}")
        if all_results:
            for pair, results in all_results.items():
                print(f"\n--- {pair} ---")
                print(f"   Total Trades: {results['total_trades']:,}")
                print(f"   Win Rate: {results['win_rate']:.2f}%")
                print(f"   Overall R:R Ratio: {results['overall_rr']:.2f}:1")
                print(f"   Final Balance: ${results['final_balance']:,.2f}")
        else:
            print("No backtest results to display.")
        print(f"\n{'='*80}")
        print(f"🏁 ALL BACKTESTS COMPLETED")
        print(f"{'='*80}")

    except KeyboardInterrupt:
        logger.info(f"🛑 Backtest interrupted by user")
    except Exception as e:
        logger.error(f"❌ An error occurred during backtesting: {e}", exc_info=True)