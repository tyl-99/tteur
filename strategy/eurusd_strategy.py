import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class EURUSDSTRATEGY:
    """
    A Supply and Demand strategy for EUR/USD aiming for a high R:R.

    Logic:
    1. Identifies Supply and Demand zones based on strong price moves away from a consolidated base.
       - Supply: A sharp drop after a base (Rally-Base-Drop or Drop-Base-Drop).
       - Demand: A sharp rally after a base (Drop-Base-Rally or Rally-Base-Rally).
    2. Enters a trade when price returns to a 'fresh' (untested) zone.
    3. The Stop Loss is placed just outside the zone.
    4. Enforces a strict 1:3 Risk-to-Reward ratio.
    """

    def __init__(self, target_pair="EUR/USD"):
        self.target_pair = target_pair
        
        # --- OPTIMIZED STRATEGY PARAMETERS (From AutoTuner Results) ---
        # Best Result: 54.95% Win Rate, 111 trades, $6,847 PnL
        self.zone_lookback = 300         # How far back to look for zones (OPTIMIZED: was 200)
        self.base_max_candles = 5        # Max number of candles in a "base" (OPTIMIZED: unchanged)
        self.move_min_ratio = 2.0        # How strong the move out of the base must be (OPTIMIZED: unchanged)
        self.zone_width_max_pips = 30    # Max width of a zone in pips to be considered valid (OPTIMIZED: was 20)
        self.pip_size = 0.0001
        
        # --- LONG WICK FILTER ---
        self.use_wick_filter = True  # Enable long wick filter (50% of candle height)
        self.min_wick_percentage = 0.5  # Minimum wick size as percentage of total candle height
        
        # --- NEW: TREND, ATR AND SESSION FILTERS ---
        self.rr_target = 2.0  # Default RR target (can scale to 2.5 if clean)
        self.buffer_pct = 0.15  # Entry buffer as fraction of zone width
        self.atr_period = 14
        self.atr_min_mult = 0.5  # SL distance >= 0.5 * ATR
        self.atr_max_mult = 1.5  # SL distance <= 1.5 * ATR
        self.use_session_filter = True
        # London/NY core hours in UTC (approx): 7..20
        self.session_hours_utc = set(range(7, 21))
        
        # --- Internal State ---
        self.zones = [] # Stores {'type', 'price_high', 'price_low', 'created_at', 'is_fresh'}
        self.last_candle_index = -1

    def _is_strong_move(self, candles: pd.DataFrame) -> bool:
        """Check if the move away from the base is significant."""
        if len(candles) < 2:
            return False
        
        first_candle = candles.iloc[0]
        last_candle = candles.iloc[-1]
        
        move_size = abs(last_candle['close'] - first_candle['open'])
        avg_body_size = candles['body_size'].mean()

        return move_size > avg_body_size * self.move_min_ratio

    def _check_wick_filter(self, df: pd.DataFrame, trade_direction: str) -> bool:
        """
        Check if the last candle has a long wick in the trade direction.
        BUY: requires long bottom wick (rejection of lower prices)
        SELL: requires long top wick (rejection of higher prices)
        """
        if not self.use_wick_filter:
            return True
        
        if len(df) < 1:
            return False
        
        last_candle = df.iloc[-1]
        high = last_candle['high']
        low = last_candle['low']
        open_price = last_candle['open']
        close = last_candle['close']
        
        total_height = high - low
        if total_height == 0:  # Avoid division by zero
            return False
        
        # Calculate wicks
        top_wick = high - max(open_price, close)
        bottom_wick = min(open_price, close) - low
        
        if trade_direction == "BUY":
            # For BUY signals, need long bottom wick (rejection of lower prices)
            bottom_wick_percentage = bottom_wick / total_height
            return bottom_wick_percentage >= self.min_wick_percentage
        elif trade_direction == "SELL":
            # For SELL signals, need long top wick (rejection of higher prices)
            top_wick_percentage = top_wick / total_height
            return top_wick_percentage >= self.min_wick_percentage
        
        return False

    def _compute_atr(self, df: pd.DataFrame, period: int) -> float:
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            prev_close = close.shift(1)
            tr1 = (high - low).abs()
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/period, adjust=False).mean()
            return float(atr.iloc[-1]) if len(atr) > 0 and pd.notna(atr.iloc[-1]) else None
        except Exception:
            return None

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _compute_h4_trend(self, df: pd.DataFrame) -> str:
        """Return 'up', 'down', or 'unknown' based on H4 EMA200 (fallback to M30 EMA200)."""
        try:
            ts = pd.to_datetime(df['timestamp'], errors='coerce') if 'timestamp' in df.columns else None
            if ts is not None and ts.notna().all():
                tmp = df.copy()
                tmp['timestamp'] = ts
                tmp = tmp.sort_values('timestamp')
                tmp = tmp.set_index('timestamp')
                # Resample to 4H candles using last close
                h4_close = tmp['close'].resample('4H').last().dropna()
                if len(h4_close) >= 210:
                    ema200 = self._ema(h4_close, 200)
                    last_close = float(h4_close.iloc[-1])
                    last_ema = float(ema200.iloc[-1])
                    if last_close > last_ema:
                        return 'up'
                    elif last_close < last_ema:
                        return 'down'
            # Fallback to M30 EMA200 on close
            if len(df) >= 210:
                ema200_m30 = self._ema(df['close'], 200)
                last_close = float(df['close'].iloc[-1])
                last_ema = float(ema200_m30.iloc[-1])
                if last_close > last_ema:
                    return 'up'
                elif last_close < last_ema:
                    return 'down'
        except Exception:
            pass
        return 'unknown'

    def _in_session(self, df: pd.DataFrame) -> bool:
        if not self.use_session_filter:
            return True
        try:
            ts = df['timestamp'].iloc[-1]
            dt = pd.to_datetime(ts, errors='coerce')
            if pd.isna(dt):
                return True  # if unknown, don't block
            return dt.hour in self.session_hours_utc
        except Exception:
            return True

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
                        if impulse_candle['close'] > base_high:
                            self.zones.append({
                                'type': 'demand', 
                                'price_high': base_high, 
                                'price_low': base_low,
                                'created_at': i, 'is_fresh': True
                            })
                            base_found = True
                            break 
                        
                        # Explosive move downwards creates a SUPPLY zone
                        elif impulse_candle['close'] < base_low:
                            self.zones.append({
                                'type': 'supply', 
                                'price_high': base_high, 
                                'price_low': base_low,
                                'created_at': i, 'is_fresh': True
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
                        
                        if zone_type:
                            all_zones.append({
                                'type': zone_type, 
                                'price_high': base_high, 
                                'price_low': base_low,
                                'created_at_index': i,
                                'is_fresh': True
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

    def check_entry_signal(self, current_price: float, zone: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Checks if the current price provides an entry signal for a given fresh zone.
        This is called on each candle against available zones.
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

        if decision != "NO TRADE":
            return {
                "decision": decision,
                "entry_price": current_price,
                "stop_loss": sl,
                "take_profit": tp,
                "meta": { "zone_type": zone['type'], "zone_high": zone['price_high'], "zone_low": zone['price_low']}
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

        # Session gate
        if not self._in_session(df):
            return {"decision": "NO TRADE", "reason": "Out of session"}

        current_price = df['close'].iloc[-1]
        trend = self._compute_h4_trend(df)

        # Precompute ATR and ATR bounds in pips
        atr_value = self._compute_atr(df.iloc[-max(self.atr_period*3, 100):].copy(), self.atr_period)
        atr_pips = (atr_value / self.pip_size) if atr_value else None

        for zone in self.zones:
            if not zone['is_fresh']:
                continue

            in_supply_zone = zone['type'] == 'supply' and zone['price_low'] <= current_price <= zone['price_high']
            in_demand_zone = zone['type'] == 'demand' and zone['price_low'] <= current_price <= zone['price_high']

            # Trend alignment
            if zone['type'] == 'demand' and trend == 'down':
                continue
            if zone['type'] == 'supply' and trend == 'up':
                continue

            # Wick confirmation
            if zone['type'] == 'demand':
                if not self._check_wick_filter(df, "BUY"):
                    continue
                # Entry at zone edge + buffer
                zone_width = zone['price_high'] - zone['price_low']
                entry_price = zone['price_low'] + zone_width * self.buffer_pct
                sl = zone['price_low'] - (2 * self.pip_size)
                risk_pips = (entry_price - sl) / self.pip_size
                
                # ATR bounds
                if atr_pips is not None:
                    if risk_pips < self.atr_min_mult * atr_pips or risk_pips > self.atr_max_mult * atr_pips:
                        continue
                tp = entry_price + (risk_pips * self.rr_target * self.pip_size)
                zone['is_fresh'] = False
                return {
                    "decision": "BUY",
                    "entry_price": float(entry_price),
                    "stop_loss": float(sl),
                    "take_profit": float(tp),
                    "meta": {"zone_type": zone['type'], "zone_high": zone['price_high'], "zone_low": zone['price_low'], "trend": trend, "wick_filter": "on", "atr": atr_value}
                }

            if zone['type'] == 'supply':
                if not self._check_wick_filter(df, "SELL"):
                    continue
                zone_width = zone['price_high'] - zone['price_low']
                entry_price = zone['price_high'] - zone_width * self.buffer_pct
                sl = zone['price_high'] + (2 * self.pip_size)
                risk_pips = (sl - entry_price) / self.pip_size
                if atr_pips is not None:
                    if risk_pips < self.atr_min_mult * atr_pips or risk_pips > self.atr_max_mult * atr_pips:
                        continue
                tp = entry_price - (risk_pips * self.rr_target * self.pip_size)
                zone['is_fresh'] = False
                return {
                    "decision": "SELL",
                    "entry_price": float(entry_price),
                    "stop_loss": float(sl),
                    "take_profit": float(tp),
                    "meta": {"zone_type": zone['type'], "zone_high": zone['price_high'], "zone_low": zone['price_low'], "trend": trend, "wick_filter": "on", "atr": atr_value}
                }

        return {"decision": "NO TRADE", "reason": "No qualified zone"}