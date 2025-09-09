import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EURGBPSTRATEGY:
    """
    EUR/GBP H4 Double Moving Average Crossover Strategy
    
    This strategy focuses on: 
    - 34-period SMA and 55-period SMA crossovers
    - Trend confirmation by sloping averages
    - Fixed 30-pip Stop Loss with 2:1 Reward-to-Risk
    """
    
    def __init__(self, target_pair="EUR/GBP"):
        self.target_pair = target_pair
        
        # --- STRATEGY PARAMETERS ---
        self.sma_fast_period = 34
        self.sma_slow_period = 55
        self.sma_slope_period = 5 # Period to check SMA slope
        self.min_slope = 0.00001 # Minimum slope to consider 'sloping upwards/downwards'
        
        # --- RISK MANAGEMENT ---
        self.fixed_risk_amount = 100.0     # Risk $100 per trade
        self.fixed_stop_loss_pips = 30     # Reverted to fixed SL of 30 pips
        self.min_risk_reward_ratio = 2.0   # 2:1 R:R ratio
        self.pip_value_per_lot = 10.0      # Standardized EUR/GBP pip value to $10.0
        self.pip_size = 0.0001             # Standard pip size for EUR/GBP
        self.min_position_size = 0.01      # Minimum trade volume
        self.max_position_size = 2.0       # Maximum trade volume

    def calculate_sma(self, df, period):
        """Calculate Simple Moving Average"""
        return df['close'].rolling(window=period).mean()

    def calculate_position_size(self, risk_pips):
        """Calculate position size based on fixed risk amount"""
        if risk_pips <= 0:
            return self.min_position_size
        
        position_size = self.fixed_risk_amount / (risk_pips * self.pip_value_per_lot)
        return max(self.min_position_size, min(self.max_position_size, position_size))

    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Optional[Dict[str, Any]]:
        """
        Main analysis method for EUR/GBP Double Moving Average Crossover strategy
        """
        if len(df) < self.sma_slow_period + self.sma_slope_period:
            return {"decision": "NO TRADE", "reason": "Insufficient data for SMAs"}

        # Calculate SMAs
        sma_fast = self.calculate_sma(df, self.sma_fast_period)
        sma_slow = self.calculate_sma(df, self.sma_slow_period)

        if sma_fast.isnull().iloc[-1] or sma_slow.isnull().iloc[-1]:
            return {"decision": "NO TRADE", "reason": "SMA values not yet available"}

        # Get current and previous SMA values
        current_sma_fast = sma_fast.iloc[-1]
        current_sma_slow = sma_slow.iloc[-1]
        prev_sma_fast = sma_fast.iloc[-2]
        prev_sma_slow = sma_slow.iloc[-2]
        
        current_price = df['close'].iloc[-1]
        
        # Check SMA slopes
        fast_slope = (current_sma_fast - sma_fast.iloc[-self.sma_slope_period]) / (self.sma_slope_period * self.pip_size)
        slow_slope = (current_sma_slow - sma_slow.iloc[-self.sma_slope_period]) / (self.sma_slope_period * self.pip_size)
        
        # Buy Setup
        if prev_sma_fast <= prev_sma_slow and current_sma_fast > current_sma_slow: # Crossover
            if fast_slope > self.min_slope and slow_slope > self.min_slope: # Both sloping upwards
                
                entry_price = current_price
                stop_loss = entry_price - (self.fixed_stop_loss_pips * self.pip_size)
                take_profit = entry_price + (self.fixed_stop_loss_pips * self.min_risk_reward_ratio * self.pip_size)
                
                risk_pips = self.fixed_stop_loss_pips
                volume = self.calculate_position_size(risk_pips)
                
                # Calculate actual reward pips based on the fixed SL and desired R:R
                reward_pips = risk_pips * self.min_risk_reward_ratio
                
                logger.info(f"[BUY Signal] Entry: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                logger.info(f"[BUY Signal] Risk pips: {risk_pips:.2f}, Reward pips: {reward_pips:.2f}, R:R: {self.min_risk_reward_ratio:.2f}")

                return {
                    "decision": "BUY",
                    "entry_price": entry_price,
                    "volume": volume,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "confidence": 0.8,
                    "signal_reason": f"34-SMA crossed above 55-SMA, both sloping up. Fast Slope: {fast_slope:.2f}, Slow Slope: {slow_slope:.2f}",
                    "meta": {
                        "strategy": "double_ma_crossover",
                        "sma_fast": current_sma_fast,
                        "sma_slow": current_sma_slow,
                        "fast_slope": fast_slope,
                        "slow_slope": slow_slope,
                        "risk_pips": risk_pips,
                        "reward_pips": reward_pips,
                        "risk_reward_ratio": self.min_risk_reward_ratio
                    }
                }
        
        # Sell Setup
        elif prev_sma_fast >= prev_sma_slow and current_sma_fast < current_sma_slow: # Crossover
            if fast_slope < -self.min_slope and slow_slope < -self.min_slope: # Both sloping downwards
                
                entry_price = current_price
                stop_loss = entry_price + (self.fixed_stop_loss_pips * self.pip_size)
                take_profit = entry_price - (self.fixed_stop_loss_pips * self.min_risk_reward_ratio * self.pip_size)
                
                risk_pips = self.fixed_stop_loss_pips
                volume = self.calculate_position_size(risk_pips)
                
                # Calculate actual reward pips based on the fixed SL and desired R:R
                reward_pips = risk_pips * self.min_risk_reward_ratio
                
                logger.info(f"[SELL Signal] Entry: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                logger.info(f"[SELL Signal] Risk pips: {risk_pips:.2f}, Reward pips: {reward_pips:.2f}, R:R: {self.min_risk_reward_ratio:.2f}")

                return {
                    "decision": "SELL",
                    "entry_price": entry_price,
                    "volume": volume,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "confidence": 0.8,
                    "signal_reason": f"34-SMA crossed below 55-SMA, both sloping down. Fast Slope: {fast_slope:.2f}, Slow Slope: {slow_slope:.2f}",
                    "meta": {
                        "strategy": "double_ma_crossover",
                        "sma_fast": current_sma_fast,
                        "sma_slow": current_sma_slow,
                        "fast_slope": fast_slope,
                        "slow_slope": slow_slope,
                        "risk_pips": risk_pips,
                        "reward_pips": risk_pips * self.min_risk_reward_ratio,
                        "risk_reward_ratio": self.min_risk_reward_ratio
                    }
                }

        return {"decision": "NO TRADE", "reason": "No valid SMA crossover signal"}