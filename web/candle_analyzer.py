import pandas as pd
import numpy as np
import datetime
import logging
from typing import Dict, List, Optional, Tuple
import os
import sys
import importlib.util

logger = logging.getLogger(__name__)

class CandleAnalyzer:
    def __init__(self):
        self.candle_data = {}
        self.strategies = {}
        self.load_candle_data()
        self.load_strategies()
    
    def load_candle_data(self):
        """Load candle data from Excel file"""
        try:
            excel_file = 'latest_trendbar_data.xlsx'
            logger.info(f"🔍 Looking for candle data file: {excel_file}")
            logger.info(f"🔍 Current working directory: {os.getcwd()}")
            logger.info(f"🔍 File exists: {os.path.exists(excel_file)}")
            
            if not os.path.exists(excel_file):
                logger.warning(f"📄 Candle data file not found: {excel_file}")
                # Try alternative locations
                alt_paths = [
                    os.path.join(os.getcwd(), excel_file),
                    os.path.join(os.path.dirname(__file__), excel_file),
                    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', excel_file)
                ]
                for alt_path in alt_paths:
                    logger.info(f"🔍 Trying alternative path: {alt_path}")
                    if os.path.exists(alt_path):
                        excel_file = alt_path
                        logger.info(f"✅ Found file at: {excel_file}")
                        break
                else:
                    logger.error(f"❌ Could not find {excel_file} in any location")
                    return
            
            # Load all sheets (currency pairs)
            logger.info(f"📊 Loading Excel file: {excel_file}")
            xl_file = pd.ExcelFile(excel_file, engine='openpyxl')
            logger.info(f"📊 Available sheets: {xl_file.sheet_names}")
            
            for sheet_name in xl_file.sheet_names:
                try:
                    pair = sheet_name.replace('_', '/')
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
                    
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df.sort_values('timestamp')
                        self.candle_data[pair] = df
                        logger.info(f"📊 Loaded {len(df)} candles for {pair}")
                    else:
                        logger.warning(f"⚠️ No timestamp column in sheet {sheet_name}")
                        
                except Exception as sheet_error:
                    logger.error(f"❌ Error loading sheet {sheet_name}: {sheet_error}")
                
        except Exception as e:
            logger.error(f"❌ Error loading candle data: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
    
    def load_strategies(self):
        """Load strategy files for each currency pair"""
        try:
            # Strategy mapping based on ctrader.py
            # Use absolute paths relative to the current working directory
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            strategy_mapping = {
                "EUR/USD": os.path.join(base_path, "strategy", "eurusd_strategy.py"),
                "GBP/USD": os.path.join(base_path, "strategy", "gbpusd_strategy.py"), 
                "EUR/GBP": os.path.join(base_path, "strategy", "eurgbp_strategy.py"),
                "USD/JPY": os.path.join(base_path, "strategy", "usdjpy_strategy.py"),
                "GBP/JPY": os.path.join(base_path, "strategy", "gbpjpy_strategy.py"),
                "EUR/JPY": os.path.join(base_path, "strategy", "eurjpy_strategy.py")
            }
            
            logger.info(f"🔍 Base path for strategies: {base_path}")
            
            for pair, strategy_file in strategy_mapping.items():
                try:
                    logger.info(f"🔍 Looking for strategy file: {strategy_file}")
                    logger.info(f"🔍 Strategy file exists: {os.path.exists(strategy_file)}")
                    
                    if os.path.exists(strategy_file):
                        # Read strategy file content
                        with open(strategy_file, 'r') as f:
                            strategy_content = f.read()
                        
                        self.strategies[pair] = {
                            'file_path': strategy_file,
                            'content': strategy_content,
                            'strategy_type': self.extract_strategy_type(strategy_content),
                            'parameters': self.extract_strategy_parameters(strategy_content),
                            'logic_summary': self.extract_strategy_logic(strategy_content)
                        }
                        logger.info(f"📋 Loaded strategy for {pair}: {self.strategies[pair]['strategy_type']}")
                    else:
                        logger.warning(f"⚠️ Strategy file not found: {strategy_file}")
                        
                except Exception as e:
                    logger.error(f"❌ Error loading strategy for {pair}: {e}")
                    import traceback
                    logger.error(f"❌ Strategy loading traceback: {traceback.format_exc()}")
                    
        except Exception as e:
            logger.error(f"❌ Error loading strategies: {e}")
    
    def extract_strategy_type(self, content: str) -> str:
        """Extract strategy type from content"""
        if "SupplyDemandStrategy" in content:
            return "Supply & Demand"
        elif "DemandStrategy" in content:
            return "Demand Zones"
        elif "Strategy" in content:
            return "Custom Strategy"
        else:
            return "Unknown Strategy"
    
    def extract_strategy_parameters(self, content: str) -> Dict:
        """Extract key strategy parameters"""
        parameters = {}
        
        # Extract common parameters
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if '=' in line and ('self.' in line or '#' not in line):
                try:
                    # Extract parameter assignments
                    if 'self.zone_lookback' in line:
                        parameters['zone_lookback'] = self.extract_number(line)
                    elif 'self.base_max_candles' in line:
                        parameters['base_max_candles'] = self.extract_number(line)
                    elif 'self.move_min_ratio' in line:
                        parameters['move_min_ratio'] = self.extract_number(line)
                    elif 'self.zone_width_max_pips' in line:
                        parameters['zone_width_max_pips'] = self.extract_number(line)
                    elif 'self.pip_size' in line:
                        parameters['pip_size'] = self.extract_number(line)
                    elif 'Risk-to-Reward' in line or 'R:R' in line:
                        parameters['risk_reward_ratio'] = "1:3"
                except:
                    continue
        
        return parameters
    
    def extract_number(self, line: str) -> float:
        """Extract number from a line of code"""
        try:
            # Find the number after the = sign
            parts = line.split('=')
            if len(parts) > 1:
                value_part = parts[1].strip()
                # Remove comments
                if '#' in value_part:
                    value_part = value_part.split('#')[0].strip()
                # Try to convert to float
                return float(value_part)
        except:
            pass
        return 0.0
    
    def extract_strategy_logic(self, content: str) -> List[str]:
        """Extract key strategy logic points"""
        logic_points = []
        
        if "Supply and Demand" in content:
            logic_points.append("🎯 Identifies Supply & Demand zones based on explosive moves from consolidation")
            logic_points.append("📊 Supply zones: Sharp drops after base consolidation")
            logic_points.append("📈 Demand zones: Sharp rallies after base consolidation") 
            logic_points.append("🎪 Enters trades when price returns to 'fresh' untested zones")
            logic_points.append("🛡️ Stop loss placed just outside the zone boundary")
            logic_points.append("💰 Targets 1:3 Risk-to-Reward ratio")
        
        # Extract specific logic from comments
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# ') and ('Logic:' in line or 'Condition' in line or 'Rule' in line):
                logic_points.append(f"📋 {line[2:]}")
        
        return logic_points[:10]  # Limit to 10 key points
    
    def get_candles_for_trade(self, symbol: str, entry_time: str, exit_time: str, pre_candles: int = 300) -> Optional[pd.DataFrame]:
        """Get 300 candles before entry + trade period candles"""
        try:
            if symbol not in self.candle_data:
                logger.warning(f"⚠️ No candle data available for {symbol}")
                return None
            
            df = self.candle_data[symbol].copy()
            entry_dt = pd.to_datetime(entry_time)
            exit_dt = pd.to_datetime(exit_time)
            
            # Find entry candle index
            entry_idx = df[df['timestamp'] <= entry_dt].index.max()
            if pd.isna(entry_idx):
                return None
            
            # Get 300 candles before entry
            start_idx = max(0, entry_idx - pre_candles + 1)
            
            # Find exit candle index
            exit_idx = df[df['timestamp'] <= exit_dt].index.max()
            if pd.isna(exit_idx):
                exit_idx = entry_idx
            
            # Get candles from start to exit
            trade_candles = df.iloc[start_idx:exit_idx + 1].copy()
            trade_candles['is_entry'] = trade_candles.index == entry_idx
            trade_candles['is_exit'] = trade_candles.index == exit_idx
            
            return trade_candles
            
        except Exception as e:
            logger.error(f"❌ Error getting candles: {e}")
            return None
    
    def analyze_losing_trade(self, trade_data: Dict, all_trading_data: Dict = None) -> Dict:
        """Analyze why a trade lost money with 300 candles context AND strategy context"""
        try:
            symbol = trade_data['symbol']
            entry_time = trade_data['time']
            exit_time = trade_data.get('exit_time', entry_time)
            entry_price = trade_data['entry']
            exit_price = trade_data['exit']
            side = trade_data['side']
            pnl = trade_data['pnl']
            stop_loss = trade_data.get('stop_loss')
            take_profit = trade_data.get('take_profit')
            
            # Get 300 candles before entry + trade period
            candles = self.get_candles_for_trade(symbol, entry_time, exit_time)
            if candles is None or len(candles) < 50:
                return self.generate_basic_loss_analysis(trade_data)
            
            # Split into pre-entry (300 candles) and trade period
            pre_entry = candles[~candles['is_entry'] & ~candles['is_exit']].copy()
            trade_period = candles[candles['is_entry'] | candles['is_exit']]
            
            # Analyze market conditions before entry
            market_analysis = self.analyze_pre_entry_market(pre_entry, entry_price, side)
            
            # Analyze what went wrong during trade
            failure_analysis = self.analyze_trade_execution(trade_period, trade_data)
            
            # NEW: Analyze against actual strategy (with full trading data for multiple trades check)
            strategy_analysis = self.analyze_against_strategy(symbol, pre_entry, trade_data, all_trading_data)
            
            # Generate enhanced AI insights with strategy context
            ai_insights = self.generate_enhanced_loss_insights(
                market_analysis, failure_analysis, strategy_analysis, trade_data
            )
            
            return {
                'symbol': symbol,
                'total_candles_analyzed': len(candles),
                'pre_entry_candles': len(pre_entry),
                'trade_duration_candles': len(trade_period),
                'market_conditions': market_analysis,
                'failure_analysis': failure_analysis,
                'strategy_analysis': strategy_analysis,  # NEW
                'ai_loss_insights': ai_insights,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'actual_loss': pnl
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing losing trade: {e}")
            return self.generate_basic_loss_analysis(trade_data)
    
    def check_multiple_trades_violation(self, trade_data: Dict, all_trading_data: Dict) -> List[str]:
        """Check if multiple trades were taken when strategy allows only one"""
        violations = []
        
        try:
            current_trade_time = pd.to_datetime(trade_data['time'])
            current_symbol = trade_data['symbol']
            
            # Get all trades from the trading data
            all_trades = all_trading_data.get('recentTrades', [])
            
            # Find trades that were active at the same time as current trade
            simultaneous_trades = []
            
            for trade in all_trades:
                if trade.get('id') == trade_data.get('id'):
                    continue  # Skip the current trade
                
                trade_time = pd.to_datetime(trade['time'])
                
                # Check if trades were within 1 hour of each other (likely simultaneous)
                time_diff = abs((current_trade_time - trade_time).total_seconds() / 60)  # minutes
                
                if time_diff <= 60:  # Within 1 hour
                    simultaneous_trades.append({
                        'symbol': trade['symbol'],
                        'side': trade['side'],
                        'time': trade['time'],
                        'time_diff_minutes': time_diff
                    })
            
            if len(simultaneous_trades) > 0:
                violations.append("🔴 MULTIPLE TRADES VIOLATION: Strategy allows only ONE trade at a time")
                violations.append(f"🔴 SIMULTANEOUS TRADES: Found {len(simultaneous_trades)} other trades within 1 hour")
                
                for sim_trade in simultaneous_trades[:3]:  # Show max 3 examples
                    violations.append(f"🔴 CONCURRENT TRADE: {sim_trade['side']} {sim_trade['symbol']} ({sim_trade['time_diff_minutes']:.0f} min apart)")
                
                violations.append("🔴 STRATEGY RULE: Wait for current trade to close before opening new ones")
                violations.append("🔴 WHAT YOU DID: Opened multiple positions, violating one-trade-only rule")
            
            return violations
            
        except Exception as e:
            logger.error(f"❌ Error checking multiple trades: {e}")
            return []
    
    def analyze_against_strategy(self, symbol: str, pre_entry: pd.DataFrame, trade_data: Dict, all_trading_data: Dict = None) -> Dict:
        """Simple strategy analysis - no complex violations"""
        try:
            # Just return basic info - no complex analysis that gives wrong data
            return {
                'strategy_available': False,
                'strategy_type': 'BASIC',
                'strategy_parameters': {},
                'strategy_logic': [],
                'trade_compliance': {},
                'strategy_violations': []
            }
            
        except Exception as e:
            logger.error(f"❌ Error in strategy analysis: {e}")
            return {'strategy_available': False, 'error': str(e)}
    
    def check_strategy_compliance(self, strategy: Dict, pre_entry: pd.DataFrame, trade_data: Dict) -> Dict:
        """Check if trade complied with strategy rules"""
        compliance = {
            'followed_entry_rules': 'UNKNOWN',
            'proper_risk_reward': 'UNKNOWN',
            'zone_quality': 'UNKNOWN'
        }
        
        try:
            # Check Risk:Reward ratio
            stop_loss = trade_data.get('stop_loss')
            take_profit = trade_data.get('take_profit')
            entry_price = trade_data['entry']
            
            if stop_loss and take_profit:
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
                rr_ratio = reward / risk if risk > 0 else 0
                
                if rr_ratio >= 2.5:  # Close to 1:3
                    compliance['proper_risk_reward'] = 'YES'
                elif rr_ratio >= 1.5:
                    compliance['proper_risk_reward'] = 'PARTIAL'
                else:
                    compliance['proper_risk_reward'] = 'NO'
            
            # For Supply & Demand strategy, check zone quality
            if strategy['strategy_type'] == "Supply & Demand":
                compliance['zone_quality'] = self.assess_zone_quality(pre_entry, trade_data)
            
            return compliance
            
        except Exception as e:
            logger.error(f"❌ Error checking compliance: {e}")
            return compliance
    
    def check_supply_demand_violations(self, strategy: Dict, pre_entry: pd.DataFrame, trade_data: Dict) -> List[str]:
        """Check for specific Supply & Demand strategy violations"""
        violations = []
        
        try:
            entry_price = trade_data['entry']
            side = trade_data['side']
            entry_time = trade_data['time']
            
            # Check if entry was in a proper zone
            zones = self.find_supply_demand_zones(pre_entry, strategy['parameters'])
            
            entry_in_zone = False
            zone_type_correct = False
            found_zone = None
            
            # Check all zones for entry
            for zone in zones:
                if zone['price_low'] <= entry_price <= zone['price_high']:
                    entry_in_zone = True
                    found_zone = zone
                    if (side == 'SELL' and zone['type'] == 'supply') or (side == 'BUY' and zone['type'] == 'demand'):
                        zone_type_correct = True
                    break
            
            # Primary violation: No zone at all
            if not entry_in_zone:
                violations.append("🔴 STRATEGY VIOLATION: Entry was NOT in a valid Supply/Demand zone")
                # Add more specific explanation
                if len(zones) > 0:
                    closest_zone = min(zones, key=lambda z: min(abs(z['price_high'] - entry_price), abs(z['price_low'] - entry_price)))
                    distance = min(abs(closest_zone['price_high'] - entry_price), abs(closest_zone['price_low'] - entry_price))
                    distance_pips = distance / strategy['parameters'].get('pip_size', 0.0001)
                    violations.append(f"🔴 ZONE DISTANCE: Closest {closest_zone['type']} zone was {distance_pips:.1f} pips away")
                else:
                    violations.append("🔴 NO ZONES FOUND: No valid Supply/Demand zones identified in 300 candles")
            
            # Secondary violation: Wrong zone type
            elif not zone_type_correct:
                violations.append("🔴 STRATEGY VIOLATION: Wrong zone type - SELL should be in Supply zone, BUY in Demand zone")
                if found_zone:
                    violations.append(f"🔴 ZONE TYPE ERROR: You {side} in a {found_zone['type'].upper()} zone")
            
            # Tertiary violation: Zone freshness
            elif entry_in_zone and zone_type_correct:
                # Check if price had been in this zone before (zone was tested)
                zone_tests = self.count_zone_tests(pre_entry, entry_price)
                if zone_tests > 3:
                    violations.append("⚠️ STRATEGY WARNING: Zone was tested multiple times (not fresh)")
                    violations.append(f"⚠️ ZONE TESTS: Price touched this level {zone_tests} times before")
            
            return violations
            
        except Exception as e:
            logger.error(f"❌ Error checking violations: {e}")
            return ["❌ Error checking strategy violations"]
    
    def find_supply_demand_zones(self, df: pd.DataFrame, parameters: Dict) -> List[Dict]:
        """Simplified zone finding based on strategy parameters"""
        zones = []
        
        try:
            if len(df) < 50:
                return zones
            
            # Use strategy parameters
            base_max_candles = parameters.get('base_max_candles', 5)
            move_min_ratio = parameters.get('move_min_ratio', 2.0)
            zone_width_max_pips = parameters.get('zone_width_max_pips', 30)
            pip_size = parameters.get('pip_size', 0.0001)
            
            # Calculate candle ranges
            df_copy = df.copy()
            df_copy['candle_range'] = df_copy['high'] - df_copy['low']
            
            # Look for zones in the last 100 candles
            search_df = df_copy.tail(100)
            
            for i in range(base_max_candles, len(search_df) - 1):
                for base_len in range(1, base_max_candles + 1):
                    base_start = i - base_len
                    base_candles = search_df.iloc[base_start:i]
                    impulse_candle = search_df.iloc[i]
                    
                    avg_base_range = base_candles['candle_range'].mean()
                    if avg_base_range == 0:
                        continue
                    
                    if impulse_candle['candle_range'] > avg_base_range * move_min_ratio:
                        base_high = base_candles['high'].max()
                        base_low = base_candles['low'].min()
                        zone_width_pips = (base_high - base_low) / pip_size
                        
                        if 0 < zone_width_pips < zone_width_max_pips:
                            if impulse_candle['close'] > base_high:
                                zones.append({
                                    'type': 'demand',
                                    'price_high': base_high,
                                    'price_low': base_low
                                })
                            elif impulse_candle['close'] < base_low:
                                zones.append({
                                    'type': 'supply',
                                    'price_high': base_high,
                                    'price_low': base_low
                                })
            
            return zones[-10:]  # Return last 10 zones
            
        except Exception as e:
            logger.error(f"❌ Error finding zones: {e}")
            return []
    
    def count_zone_tests(self, df: pd.DataFrame, entry_price: float) -> int:
        """Count how many times price tested this level"""
        try:
            tolerance = 0.0002  # 2 pips tolerance
            tests = 0
            
            for _, candle in df.iterrows():
                if abs(candle['low'] - entry_price) <= tolerance or abs(candle['high'] - entry_price) <= tolerance:
                    tests += 1
            
            return tests
            
        except:
            return 0
    
    def assess_zone_quality(self, pre_entry: pd.DataFrame, trade_data: Dict) -> str:
        """Assess the quality of the zone for entry"""
        try:
            # Simplified zone quality assessment
            entry_price = trade_data['entry']
            
            # Check volatility around entry
            recent_candles = pre_entry.tail(20)
            avg_range = (recent_candles['high'] - recent_candles['low']).mean()
            
            if avg_range > 0.001:  # High volatility
                return "POOR"
            elif avg_range > 0.0005:
                return "MODERATE"
            else:
                return "GOOD"
                
        except:
            return "UNKNOWN"
    
    def analyze_pre_entry_market(self, pre_entry: pd.DataFrame, entry_price: float, side: str) -> Dict:
        """Analyze market conditions in 300 candles before entry"""
        try:
            if len(pre_entry) < 20:
                return {}
            
            # Calculate key technical levels
            recent_high = pre_entry['high'].tail(50).max()
            recent_low = pre_entry['low'].tail(50).min()
            
            # Moving averages - fix the warning by using .loc
            pre_entry_copy = pre_entry.copy()
            pre_entry_copy.loc[:, 'sma_20'] = pre_entry_copy['close'].rolling(20).mean()
            pre_entry_copy.loc[:, 'sma_50'] = pre_entry_copy['close'].rolling(50).mean()
            
            # RSI
            delta = pre_entry_copy['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            
            # Get latest values before entry
            latest = pre_entry_copy.iloc[-1]
            latest_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            # Trend analysis
            sma_20 = latest['sma_20'] if not pd.isna(latest['sma_20']) else entry_price
            sma_50 = latest['sma_50'] if not pd.isna(latest['sma_50']) else entry_price
            
            trend = "UPTREND" if sma_20 > sma_50 else "DOWNTREND" if sma_20 < sma_50 else "SIDEWAYS"
            
            # Distance to key levels
            dist_to_high = ((recent_high - entry_price) / entry_price) * 100
            dist_to_low = ((entry_price - recent_low) / entry_price) * 100
            
            return {
                'trend_direction': trend,
                'rsi_at_entry': latest_rsi,
                'price_vs_sma20': ((entry_price - sma_20) / sma_20) * 100,
                'price_vs_sma50': ((entry_price - sma_50) / sma_50) * 100,
                'recent_high': recent_high,
                'recent_low': recent_low,
                'distance_to_high_pct': dist_to_high,
                'distance_to_low_pct': dist_to_low,
                'market_structure': self.assess_market_structure(pre_entry_copy),
                'volatility': pre_entry_copy['close'].rolling(20).std().iloc[-1] / latest['close'] * 100
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing pre-entry market: {e}")
            return {}
    
    def assess_market_structure(self, candles: pd.DataFrame) -> str:
        """Assess market structure from candles"""
        try:
            if len(candles) < 50:
                return "INSUFFICIENT_DATA"
            
            # Look at recent 50 candles
            recent = candles.tail(50)
            highs = recent['high'].values
            lows = recent['low'].values
            
            # Count higher highs and lower lows
            higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
            lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
            
            if higher_highs > lower_lows * 1.5:
                return "BULLISH_STRUCTURE"
            elif lower_lows > higher_highs * 1.5:
                return "BEARISH_STRUCTURE"
            else:
                return "CHOPPY_STRUCTURE"
                
        except:
            return "UNKNOWN_STRUCTURE"
    
    def analyze_trade_execution(self, trade_period: pd.DataFrame, trade_data: Dict) -> Dict:
        """Analyze what happened during the trade execution"""
        try:
            side = trade_data['side']
            entry_price = trade_data['entry']
            exit_price = trade_data['exit']
            
            if len(trade_period) < 2:
                return {}
            
            # Find worst price during trade
            if side == "BUY":
                worst_price = trade_period['low'].min()
                best_price = trade_period['high'].max()
                max_drawdown = ((entry_price - worst_price) / entry_price) * 100
                max_favorable = ((best_price - entry_price) / entry_price) * 100
            else:  # SELL
                worst_price = trade_period['high'].max()
                best_price = trade_period['low'].min()
                max_drawdown = ((worst_price - entry_price) / entry_price) * 100
                max_favorable = ((entry_price - best_price) / entry_price) * 100
            
            return {
                'worst_price': worst_price,
                'best_price': best_price,
                'max_drawdown_pct': max_drawdown,
                'max_favorable_pct': max_favorable,
                'trade_went_favorable_first': max_favorable > abs(max_drawdown),
                'final_exit_reason': self.determine_exit_reason(trade_data, max_drawdown),
                'price_volatility_during_trade': trade_period['close'].std() / entry_price * 100
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing trade execution: {e}")
            return {}
    
    def determine_exit_reason(self, trade_data: Dict, max_drawdown: float) -> str:
        """Determine likely reason for exit"""
        pnl = trade_data['pnl']
        
        if pnl < -100:
            return "MAJOR_STOP_LOSS"
        elif pnl < -50:
            return "STOP_LOSS_HIT"
        elif max_drawdown > 2.0:
            return "MANUAL_EXIT_HIGH_DRAWDOWN"
        elif abs(pnl) < 20:
            return "BREAK_EVEN_EXIT"
        else:
            return "REGULAR_LOSS_EXIT"
    
    def generate_enhanced_loss_insights(self, market_analysis: Dict, failure_analysis: Dict, strategy_analysis: Dict, trade_data: Dict) -> List[str]:
        """Generate SIMPLE supply & demand insights - no confusion!"""
        insights = []
        
        try:
            symbol = trade_data['symbol']
            side = trade_data['side']
            pnl = trade_data['pnl']
            
            # Simple Trade Result
            if pnl < 0:
                insights.append(f"❌ LOST ${abs(pnl):.2f} on {side} {symbol}")
            else:
                insights.append(f"✅ WON ${pnl:.2f} on {side} {symbol}")
            
            # Main Problem (only if losing trade)
            if pnl < 0:
                violations = strategy_analysis.get('violations', [])
                if violations and len(violations) > 0:
                    insights.append(f"🔴 MAIN ISSUE: {violations[0]}")
                
                # Zone Quality (simplified)
                zone_quality = strategy_analysis.get('compliance', {}).get('zone_quality', 'UNKNOWN')
                if zone_quality == 'POOR':
                    insights.append("⚠️ ZONE: Was not fresh - only trade fresh zones")
                
                # Market Structure (simplified)
                market_structure = market_analysis.get('market_structure', 'UNKNOWN')
                if market_structure == 'CHOPPY_STRUCTURE':
                    insights.append("⚠️ MARKET: Too choppy - wait for clear trend")
                elif (side == 'BUY' and market_structure == 'BEARISH_STRUCTURE') or (side == 'SELL' and market_structure == 'BULLISH_STRUCTURE'):
                    insights.append("⚠️ TREND: Traded against market direction")
            
            # Simple Fix Suggestions (max 2)
            if pnl < -30:  # Only for significant losses
                insights.append("💡 QUICK FIXES:")
                insights.append("   • Use RSI 35-65 filter")
                insights.append("   • Only trade fresh zones")
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error generating simple insights: {e}")
            return [
                f"Trade: {trade_data.get('side', 'UNKNOWN')} {trade_data.get('symbol', 'UNKNOWN')}",
                f"Result: ${trade_data.get('pnl', 0):.2f}",
                "💡 Use fresh zones + 1:3 RR only"
            ]
    
    def generate_basic_loss_analysis(self, trade_data: Dict) -> Dict:
        """Generate SIMPLE loss analysis when candle data is not available"""
        pnl = trade_data['pnl']
        symbol = trade_data['symbol']
        side = trade_data['side']
        
        return {
            'symbol': symbol,
            'total_candles_analyzed': 0,
            'ai_loss_insights': [
                f"❌ LOST ${abs(pnl):.2f} on {side} {symbol}",
                "💡 Fetch data for detailed analysis",
                "🎯 Use fresh zones + 1:3 RR only"
            ],
            'actual_loss': pnl
        }

# Global analyzer instance
candle_analyzer = CandleAnalyzer() 