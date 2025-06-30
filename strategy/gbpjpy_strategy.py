import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class GBPJPYStrategy:
    """
    A Supply and Demand strategy for EUR/JPY aiming for a high R:R.

    Logic:
    1. Identifies Supply and Demand zones based on strong price moves away from a consolidated base.
       - Supply: A sharp drop after a base (Rally-Base-Drop or Drop-Base-Drop).
       - Demand: A sharp rally after a base (Drop-Base-Rally or Rally-Base-Rally).
    2. Enters a trade when price returns to a 'fresh' (untested) zone.
    3. The Stop Loss is placed just outside the zone.
    4. Enforces a strict 1:3 Risk-to-Reward ratio.
    """

    def __init__(self, target_pair="GBP/JPY"):
        self.target_pair = target_pair
        
        # --- OPTIMIZED STRATEGY PARAMETERS (From AutoTuner Results) ---
        # Best Result: 67.71% Win Rate, 96 trades, $16,811 PnL
        self.zone_lookback = 300         # How far back to look for zones
        self.base_max_candles = 5        # Max number of candles in a "base"
        self.move_min_ratio = 1.5        # How strong the move out of the base must be
        self.zone_width_max_pips = 30    # Max width of a zone in pips
        self.pip_size = 0.01
        
        # --- TREND FILTERING PARAMETERS ---
        self.trend_sma_period = 50       # SMA period for trend detection
        self.trend_buffer_pips = 12      # Buffer around SMA for trend neutrality (slightly larger for GBP/JPY volatility)
        
        # --- PA FILTER SETTINGS (LESS STRICT) ---
        self.min_rejection_pips = 5      # Minimum rejection wick size for GBP/JPY (higher volatility)
        self.rsi_oversold = 30           # RSI level for oversold
        self.rsi_overbought = 70         # RSI level for overbought
        self.min_confluences = 1         # Minimum PA confluences required
        
        # --- Internal State ---
        self.zones = [] # Stores {'type', 'price_high', 'price_low', 'created_at', 'is_fresh'}
        self.last_candle_index = -1

    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50  # Default if not enough data
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(0, delta) for delta in deltas]
        losses = [max(0, -delta) for delta in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _check_pa_confluence(self, df: pd.DataFrame, index: int, zone: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check price action confluence for a trade signal
        Only called when strategy wants to trade!
        """
        if index < 100:  # Need enough history
            return {"confluences": 0, "signals": [], "trade_allowed": False}
        
        # Get current candle data
        current_candle = df.iloc[index]
        prev_candle = df.iloc[index - 1] if index > 0 else current_candle
        
        # Initialize confluence tracking
        confluences = 0
        signals = []
        
        # 1. CANDLESTICK PATTERN ANALYSIS
        body_size = abs(current_candle['close'] - current_candle['open'])
        candle_range = current_candle['high'] - current_candle['low']
        upper_wick = current_candle['high'] - max(current_candle['open'], current_candle['close'])
        lower_wick = min(current_candle['open'], current_candle['close']) - current_candle['low']
        
        pattern = "NONE"
        
        # Pin Bar Detection
        if candle_range > 0:
            upper_wick_pct = upper_wick / candle_range
            lower_wick_pct = lower_wick / candle_range
            body_pct = body_size / candle_range
            
            if (upper_wick_pct >= 0.6 and body_pct <= 0.3 and 
                upper_wick >= body_size * 2 and zone['type'] == 'supply'):
                pattern = "BEARISH_PIN"
                confluences += 1
                signals.append(f"Bearish Pin Bar")
                
            elif (lower_wick_pct >= 0.6 and body_pct <= 0.3 and 
                  lower_wick >= body_size * 2 and zone['type'] == 'demand'):
                pattern = "BULLISH_PIN"
                confluences += 1
                signals.append(f"Bullish Pin Bar")

        # Doji Detection (Indecision at key zone)
        if candle_range > 0 and (body_size / candle_range) < 0.1:
            pattern = "DOJI"
            confluences += 1
            signals.append("Doji (Indecision)")
        
        # Engulfing Pattern Detection
        prev_body = abs(prev_candle['close'] - prev_candle['open'])
        if (body_size > prev_body * 1.2 and 
            ((current_candle['close'] > current_candle['open'] and zone['type'] == 'demand') or
             (current_candle['close'] < current_candle['open'] and zone['type'] == 'supply'))):
            if zone['type'] == 'demand':
                pattern = "BULLISH_ENGULFING"
                confluences += 1
                signals.append(f"Bullish Engulfing")
            else:
                pattern = "BEARISH_ENGULFING"
                confluences += 1
                signals.append(f"Bearish Engulfing")
        
        # Morning/Evening Star Detection (3-candle pattern)
        if index >= 2:
            c1 = df.iloc[index - 2]
            c2 = df.iloc[index - 1]
            c3 = current_candle

            c1_body = abs(c1['open'] - c1['close'])
            c2_body = abs(c2['open'] - c2['close'])
            avg_body = df['close'].iloc[max(0, index-22):index-2].sub(df['open'].iloc[max(0, index-22):index-2]).abs().mean()

            # Morning Star (Bullish Reversal)
            if (zone['type'] == 'demand' and
                c1['close'] < c1['open'] and c1_body > avg_body and  # C1 is a strong bearish candle
                c2_body < c1_body * 0.3 and                           # C2 is a small, indecisive candle
                c3['close'] > c3['open'] and                          # C3 is a bullish candle
                c3['close'] > (c1['open'] + c1['close']) / 2):        # C3 confirms by closing past midpoint of C1
                pattern = "MORNING_STAR"
                confluences += 1
                signals.append("Morning Star")

            # Evening Star (Bearish Reversal)
            elif (zone['type'] == 'supply' and
                  c1['close'] > c1['open'] and c1_body > avg_body and  # C1 is a strong bullish candle
                  c2_body < c1_body * 0.3 and                           # C2 is a small, indecisive candle
                  c3['close'] < c3['open'] and                          # C3 is a bearish candle
                  c3['close'] < (c1['open'] + c1['close']) / 2):        # C3 confirms by closing past midpoint of C1
                pattern = "EVENING_STAR"
                confluences += 1
                signals.append("Evening Star")
        
        # 2. REJECTION WICK ANALYSIS
        rejection_wick_pips = 0
        if zone['type'] == 'supply' and upper_wick > 0:
            rejection_wick_pips = upper_wick / self.pip_size
            if rejection_wick_pips >= self.min_rejection_pips:
                confluences += 1
                signals.append(f"Strong Rejection: {rejection_wick_pips:.1f} pips")
        elif zone['type'] == 'demand' and lower_wick > 0:
            rejection_wick_pips = lower_wick / self.pip_size
            if rejection_wick_pips >= self.min_rejection_pips:
                confluences += 1
                signals.append(f"Strong Rejection: {rejection_wick_pips:.1f} pips")
        
        # 3. RSI MOMENTUM CONFIRMATION
        if index >= 14:  # Need enough data for RSI
            closes = df['close'].iloc[index-13:index+1].values
            rsi = self._calculate_rsi(closes, 14)
            
            if zone['type'] == 'demand' and rsi <= self.rsi_oversold:  # Oversold for BUY
                confluences += 1
                signals.append(f"RSI Oversold: {rsi:.1f}")
            elif zone['type'] == 'supply' and rsi >= self.rsi_overbought:  # Overbought for SELL
                confluences += 1
                signals.append(f"RSI Overbought: {rsi:.1f}")
        
        return {
            "confluences": confluences,
            "signals": signals,
            "trade_allowed": confluences >= self.min_confluences,
            "pattern": pattern,
            "rejection_wick_pips": rejection_wick_pips
        }

    def _is_strong_move(self, candles: pd.DataFrame) -> bool:
        """Check if the move away from the base is significant."""
        if len(candles) < 2:
            return False
        
        first_candle = candles.iloc[0]
        last_candle = candles.iloc[-1]
        
        move_size = abs(last_candle['close'] - first_candle['open'])
        avg_body_size = candles['body_size'].mean()

        return move_size > avg_body_size * self.move_min_ratio

    def _find_zones(self, df: pd.DataFrame):
        """Identifies and stores Supply and Demand zones based on explosive moves from a base."""
        self.zones = []
        df['body_size'] = abs(df['open'] - df['close'])
        df['candle_range'] = df['high'] - df['low']

        i = self.base_max_candles
        while i < len(df) - 1:
            base_found = False
            for base_len in range(1, self.base_max_candles + 1):
                base_start = i - base_len
                base_candles = df.iloc[base_start:i]
                
                # Condition 1: Base candles must have small ranges
                avg_base_range = base_candles['candle_range'].mean()
                
                # Condition 2: Find the explosive move candle after the base
                impulse_candle = df.iloc[i]

                # Condition 3: Explosive move must be much larger than base candles
                if impulse_candle['candle_range'] > avg_base_range * self.move_min_ratio:
                    base_high = base_candles['high'].max()
                    base_low = base_candles['low'].min()
                    zone_width_pips = (base_high - base_low) / self.pip_size

                    if zone_width_pips > 0 and zone_width_pips < self.zone_width_max_pips:
                        # Explosive move upwards creates a DEMAND zone
                        if impulse_candle['close'] > base_high and self._should_create_zone('demand', df, i):
                            trend = self._get_trend_direction(df, i)
                            self.zones.append({
                                'type': 'demand', 
                                'price_high': base_high, 
                                'price_low': base_low,
                                'created_at': i, 'is_fresh': True,
                                'trend_at_creation': trend
                            })
                            base_found = True
                            break 
                        
                        # Explosive move downwards creates a SUPPLY zone
                        elif impulse_candle['close'] < base_low and self._should_create_zone('supply', df, i):
                            trend = self._get_trend_direction(df, i)
                            self.zones.append({
                                'type': 'supply', 
                                'price_high': base_high, 
                                'price_low': base_low,
                                'created_at': i, 'is_fresh': True,
                                'trend_at_creation': trend
                            })
                            base_found = True
                            break
            
            if base_found:
                i += 1 # Move to the next candle after the impulse
            else:
                i += 1
        
        # Remove overlapping zones, keeping the most recent one
        if self.zones:
            self.zones = sorted(self.zones, key=lambda x: x['created_at'], reverse=True)
            unique_zones = []
            seen_ranges = []
            for zone in self.zones:
                is_overlap = False
                for seen_high, seen_low in seen_ranges:
                    if not (zone['price_high'] < seen_low or zone['price_low'] > seen_high):
                        is_overlap = True
                        break
                if not is_overlap:
                    unique_zones.append(zone)
                    seen_ranges.append((zone['price_high'], zone['price_low']))
            self.zones = unique_zones

    def find_all_zones(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Scans the entire DataFrame and identifies all historical Supply and Demand zones.
        This should be called once at the start of a backtest.
        """
        all_zones = []
        df['body_size'] = abs(df['open'] - df['close'])
        df['candle_range'] = df['high'] - df['low']

        i = self.base_max_candles
        while i < len(df) - 1:
            base_found = False
            # Look for a base of 1 to base_max_candles
            for base_len in range(1, self.base_max_candles + 1):
                base_start = i - base_len
                base_candles = df.iloc[base_start:i]
                impulse_candle = df.iloc[i]
                
                # Condition 1: Base candles should be relatively small
                avg_base_range = base_candles['candle_range'].mean()
                if avg_base_range == 0: continue # Avoid division by zero

                # Condition 2: Impulse candle must be significantly larger than base candles
                if impulse_candle['candle_range'] > avg_base_range * self.move_min_ratio:
                    base_high = base_candles['high'].max()
                    base_low = base_candles['low'].min()
                    zone_width_pips = (base_high - base_low) / self.pip_size

                    # Condition 3: Zone width must be within a reasonable limit
                    if 0 < zone_width_pips < self.zone_width_max_pips:
                        zone_type = None
                        if impulse_candle['close'] > base_high: # Explosive move up creates Demand
                            zone_type = 'demand'
                        elif impulse_candle['close'] < base_low: # Explosive move down creates Supply
                            zone_type = 'supply'
                        
                        # 🚨 TREND FILTERING: Only create zones aligned with trend
                        if zone_type and self._should_create_zone(zone_type, df, i):
                            trend = self._get_trend_direction(df, i)
                            all_zones.append({
                                'type': zone_type, 
                                'price_high': base_high, 
                                'price_low': base_low,
                                'created_at_index': i,
                                'is_fresh': True,
                                'trend_at_creation': trend  # Track trend when zone was created
                            })
                            base_found = True
                            break # Move to the next candle after finding a valid zone from this base
            
            if base_found:
                i += base_len # Skip past the candles that formed the zone
            else:
                i += 1
        
        # Filter out overlapping zones, keeping the one created last (most recent)
        if not all_zones:
            return []
            
        all_zones = sorted(all_zones, key=lambda x: x['created_at_index'], reverse=True)
        unique_zones = []
        seen_ranges = []
        for zone in all_zones:
            is_overlap = any(not (zone['price_high'] < seen_low or zone['price_low'] > seen_high) for seen_high, seen_low in seen_ranges)
            if not is_overlap:
                unique_zones.append(zone)
                seen_ranges.append((zone['price_high'], zone['price_low']))
        
        return sorted(unique_zones, key=lambda x: x['created_at_index'])

    def check_entry_signal(self, current_price: float, zone: Dict[str, Any], df: pd.DataFrame = None, current_index: int = None) -> Optional[Dict[str, Any]]:
        """
        Checks if the current price provides an entry signal for a given fresh zone.
        NOW WITH PRICE ACTION FILTERING!
        """
        decision = "NO TRADE"
        sl = 0
        tp = 0

        in_supply_zone = zone['type'] == 'supply' and zone['price_low'] <= current_price <= zone['price_high']
        in_demand_zone = zone['type'] == 'demand' and zone['price_low'] <= current_price <= zone['price_high']

        if in_supply_zone:
            decision = "SELL"
            sl = zone['price_high'] + (2 * self.pip_size)
            risk_pips = (sl - current_price) / self.pip_size
            tp = current_price - (risk_pips * 3 * self.pip_size)

        elif in_demand_zone:
            decision = "BUY"
            sl = zone['price_low'] - (2 * self.pip_size)
            risk_pips = (current_price - sl) / self.pip_size
            tp = current_price + (risk_pips * 3 * self.pip_size)

        # ✅ STRATEGY WANTS TO TRADE - NOW CHECK PA CONFLUENCE!
        if decision in ["BUY", "SELL"] and df is not None and current_index is not None:
            pa_result = self._check_pa_confluence(df, current_index, zone)
            
            if pa_result['trade_allowed']:
                # PA APPROVED - Execute trade with enhanced metadata
                return {
                    "decision": decision,
                    "entry_price": current_price,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "zone": zone,
                    "meta": {
                        "pa_confluences": pa_result['confluences'],
                        "pa_signals": pa_result['signals'],
                        "candlestick_pattern": pa_result['pattern'],
                        "rejection_wick_pips": pa_result['rejection_wick_pips'],
                        "pa_enhanced": True
                    },
                    "note": f"PA APPROVED: {pa_result['confluences']}/4 confluences"
                }
            else:
                # PA REJECTED - Block trade
                return {
                    "decision": "NO TRADE",
                    "reason": f"PA BLOCKED: Only {pa_result['confluences']}/4 confluences (need {self.min_confluences})",
                    "meta": {
                        "pa_confluences": pa_result['confluences'],
                        "pa_signals": pa_result['signals'],
                        "candlestick_pattern": pa_result['pattern'],
                        "pa_enhanced": True,
                        "strategy_wanted": decision
                    }
                }
        
        # Original strategy logic (fallback for compatibility)
        elif decision != "NO TRADE":
            return {
                "decision": decision,
                "entry_price": current_price,
                "stop_loss": sl,
                "take_profit": tp,
                "zone": zone,
                "note": "Original strategy - no PA data available"
            }
        
        return None

    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Dict[str, Any]:
        """
        Analyzes the market data for the target pair to find trading opportunities.
        """
        current_candle_index = len(df) - 1
        
        # Only recalculate zones if it's a new candle
        if self.last_candle_index != current_candle_index:
            lookback_df = df.iloc[-self.zone_lookback:].copy()
            self._find_zones(lookback_df)
            self.last_candle_index = current_candle_index

        current_price = df['close'].iloc[-1]
        
        for zone in self.zones:
            if not zone['is_fresh']:
                continue

            # Check for entry
            in_supply_zone = zone['type'] == 'supply' and current_price >= zone['price_low'] and current_price <= zone['price_high']
            in_demand_zone = zone['type'] == 'demand' and current_price >= zone['price_low'] and current_price <= zone['price_high']
            
            sl = 0
            tp = 0
            decision = "NO TRADE"
            
            if in_supply_zone:
                zone['is_fresh'] = False # Mark as tested
                decision = "SELL"
                sl_pips = (zone['price_high'] - current_price) / self.pip_size + 2 # SL 2 pips above zone high
                sl = zone['price_high'] + (2 * self.pip_size)
                tp = current_price - (sl_pips * 3 * self.pip_size)
                
            elif in_demand_zone:
                zone['is_fresh'] = False # Mark as tested
                decision = "BUY"
                sl_pips = (current_price - zone['price_low']) / self.pip_size + 2 # SL 2 pips below zone low
                sl = zone['price_low'] - (2 * self.pip_size)
                tp = current_price + (sl_pips * 3 * self.pip_size)

            if decision != "NO TRADE":
                return {
                    "decision": decision,
                    "entry_price": current_price,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "meta": { "zone_type": zone['type'], "zone_high": zone['price_high'], "zone_low": zone['price_low']}
                }
                
        return {"decision": "NO TRADE"}

    def _calculate_sma(self, prices, period):
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0  # Return last price if not enough data
        return sum(prices[-period:]) / period

    def _get_trend_direction(self, df: pd.DataFrame, index: int) -> str:
        """
        Determine trend direction using SMA
        Returns: 'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if index < self.trend_sma_period:
            return 'NEUTRAL'  # Not enough data for trend analysis
            
        # Calculate SMA up to current index
        closes = df['close'].iloc[max(0, index - self.trend_sma_period + 1):index + 1].values
        sma = self._calculate_sma(closes, self.trend_sma_period)
        current_price = df.iloc[index]['close']
        
        # Create buffer zone around SMA
        upper_buffer = sma + (self.trend_buffer_pips * self.pip_size)
        lower_buffer = sma - (self.trend_buffer_pips * self.pip_size)
        
        if current_price > upper_buffer:
            return 'BULLISH'
        elif current_price < lower_buffer:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def _should_create_zone(self, zone_type: str, df: pd.DataFrame, index: int) -> bool:
        """
        Determine if a zone should be created based on trend filtering
        """
        trend = self._get_trend_direction(df, index)
        
        # Only create demand zones in bullish or neutral trends
        if zone_type == 'demand':
            return trend in ['BULLISH', 'NEUTRAL']
        
        # Only create supply zones in bearish or neutral trends
        elif zone_type == 'supply':
            return trend in ['BEARISH', 'NEUTRAL']
        
        return False 