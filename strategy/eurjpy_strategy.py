import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class EURJPYSTRATEGY:
    """
    EUR/JPY Breakout Trading Strategy.
    This strategy identifies consolidation ranges and enters trades upon a breakout.
    Entry: Price closes above range high (buy) or below range low (sell).
    Exit: Fixed Stop-Loss at 50 pips, Take-Profit at 100 pips.
    """
    
    def __init__(self,
                 range_lookback_candles: int = 12,
                 min_range_pips: float = 40.0,
                 fixed_stop_loss_pips: float = 50.0,
                 take_profit_pips: float = 100.0
                 ):
        self.pip_size = 0.01  # For JPY pairs
        
        # Range parameters
        self.range_lookback_candles = range_lookback_candles
        self.min_range_pips = min_range_pips

        # Fixed Stop Loss and Take Profit
        self.fixed_stop_loss_pips = fixed_stop_loss_pips
        self.take_profit_pips = take_profit_pips

        # Statistics
        self.check_count = 0
        self.filtered_count = 0
        self.passed_count = 0

    def identify_range(self, df: pd.DataFrame):
        """Identify range from the specified lookback period."""
        if len(df) < self.range_lookback_candles + 1:  # Need enough data for lookback
            return False, None, None

        # Use the specified lookback period
        recent_df = df.iloc[-(self.range_lookback_candles + 1):-1] # Exclude current candle
        
        range_high = recent_df['high'].max()
        range_low = recent_df['low'].min()

        # Check if range is wide enough
        range_pips = (range_high - range_low) / self.pip_size
        
        if range_pips >= self.min_range_pips:
            return True, range_high, range_low
        else:
            return False, None, None

    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Dict[str, Any]:
        """
        Very Simple Range Breakout Strategy for EUR/JPY.
        """
        self.check_count += 1

        if len(df) < self.range_lookback_candles + 2:  # Need enough data for range + current candle + previous for indicators if any
            return {"decision": "NO TRADE", "reason": "Insufficient data for range identification"}

        current_bar = df.iloc[-1]

        decision = "NO TRADE"
        reason = "No signal"
        entry_price = current_bar['close']
        stop_loss = 0.0
        take_profit = 0.0
        volume = 0.1  # Fixed volume for now, can be dynamic

        # Identify current range
        range_valid, range_high, range_low = self.identify_range(df)
        
        if not range_valid:
            self.filtered_count += 1
            return {
                "decision": "NO TRADE",
                "entry_price": float(entry_price),
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "volume": float(volume),
                "reason": "No valid range identified or range too narrow"
            }

        # Long breakout conditions
        if current_bar['close'] > range_high:
            decision = "BUY"
            reason = f"BUY: Price {current_bar['close']:.5f} closed above range high {range_high:.5f}"
            entry_price = current_bar['close']
            stop_loss = entry_price - (self.fixed_stop_loss_pips * self.pip_size)
            take_profit = entry_price + (self.take_profit_pips * self.pip_size)
            self.passed_count += 1
            
        # Short breakout conditions
        elif current_bar['close'] < range_low:
            decision = "SELL"
            reason = f"SELL: Price {current_bar['close']:.5f} closed below range low {range_low:.5f}"
            entry_price = current_bar['close']
            stop_loss = entry_price + (self.fixed_stop_loss_pips * self.pip_size)
            take_profit = entry_price - (self.take_profit_pips * self.pip_size)
            self.passed_count += 1
            
        else:
            self.filtered_count += 1
            reason = "No breakout signal within range"

        return {
            "decision": decision,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "volume": float(volume),
            "reason": reason
        }

    def get_statistics(self):
        return {
            'total_checks': self.check_count,
            'filtered_out': self.filtered_count,
            'passed_to_strategy': self.passed_count
        }

    def print_final_stats(self):
        stats = self.get_statistics()
        print(f"\n🎯 RANGE BREAKOUT STRATEGY STATS:")
        print(f"   Total Checks: {stats['total_checks']:,}")
        print(f"   Signals Generated: {stats['passed_to_strategy']:,}")
        print(f"   Current Range: {self.current_range_low:.5f} - {self.current_range_high:.5f}" if self.range_valid else "   No Active Range")