import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class EURUSDSupplyDemandStrategy:
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
        self.zone_lookback = 300         # How far back to look for zones (OPTIMIZED: was 200)
        self.base_max_candles = 5        # Max number of candles in a "base" (OPTIMIZED: unchanged)
        self.move_min_ratio = 2.0        # How strong the move out of the base must be (OPTIMIZED: unchanged)
        self.zone_width_max_pips = 30    # Max width of a zone in pips to be considered valid (OPTIMIZED: was 20)
        self.pip_size = 0.0001
        
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

    def get_statistics(self):
        """Return strategy statistics"""
        return {
            'zones_found': len(self.zones),
            'fresh_zones': sum(1 for z in self.zones if z['is_fresh'])
        }

    def print_final_stats(self):
        """Print final strategy statistics"""
        stats = self.get_statistics()
        print(f"🎯 EUR/USD SUPPLY/DEMAND STRATEGY STATS:")
        print(f"   Total Checks: {stats['check_count']:,}")
        print(f"   Signals Generated: {stats['signal_count']}")
        print(f"   Zones Found: {stats['zone_count']}")
        print(f"   Fresh Zones: {stats['fresh_zones']}") 