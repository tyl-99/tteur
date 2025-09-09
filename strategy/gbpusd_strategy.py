import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class GBPUSDSTRATEGY:
    """
    GBP/USD H4 Simple EMA Crossover Strategy
    
    Clean and simple strategy using EMA 34/55 crossover signals
    - Buy when EMA 34 crosses above EMA 55
    - Sell when EMA 34 crosses below EMA 55
    - Fixed 45-pip stop loss with 2:1 risk/reward
    """
    
    def __init__(self, target_pair="GBP/USD"):
        self.target_pair = target_pair
        
        # --- EMA PARAMETERS ---
        self.ema_fast = 34   # Fast EMA
        self.ema_slow = 55   # Slow EMA
        
        # --- RISK MANAGEMENT ---
        self.fixed_risk_amount = 100.0      # Risk $100 per trade
        self.risk_reward_ratio = 2.0        # 2:1 R:R ratio
        self.base_stop_loss_pips = 45       # Fixed 45-pip stop loss for GBP/USD
        self.pip_value_per_lot = 10.0       # GBP/USD pip value
        self.min_position_size = 0.01       # Minimum position size
        self.max_position_size = 2.0        # Maximum position size
        self.pip_size = 0.0001              # GBP/USD pip size
    
    def calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_position_size(self, risk_pips):
        """Calculate position size based on fixed risk amount"""
        if risk_pips <= 0:
            return self.min_position_size
            
        # Position size = Risk Amount / (Risk Pips * Pip Value)
        position_size = self.fixed_risk_amount / (risk_pips * self.pip_value_per_lot)
        
        # Clamp to min/max limits
        return max(self.min_position_size, min(self.max_position_size, position_size))
    
    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Optional[Dict[str, Any]]:
        """
        Main analysis method for EMA crossover strategy
        """
        if len(df) < self.ema_slow:
            return {"decision": "NO TRADE", "reason": "Insufficient data"}
        
        current_price = df['close'].iloc[-1]
        current_timestamp = df.index[-1]
        
        # Calculate EMAs
        ema_34 = self.calculate_ema(df['close'], self.ema_fast)
        ema_55 = self.calculate_ema(df['close'], self.ema_slow)
        
        current_ema_34 = ema_34.iloc[-1]
        current_ema_55 = ema_55.iloc[-1]
        prev_ema_34 = ema_34.iloc[-2]
        prev_ema_55 = ema_55.iloc[-2]
        
        # Simple crossover signals
        buy_crossover = (current_ema_34 > current_ema_55 and prev_ema_34 <= prev_ema_55)
        sell_crossover = (current_ema_34 < current_ema_55 and prev_ema_34 >= prev_ema_55)
        
        if buy_crossover:
            # Buy setup
            entry_price = current_price
            stop_loss = entry_price - (self.base_stop_loss_pips * self.pip_size)
            take_profit = entry_price + (self.base_stop_loss_pips * self.risk_reward_ratio * self.pip_size)
            
            risk_pips = self.base_stop_loss_pips
            volume = self.calculate_position_size(risk_pips)
            
            return {
                "decision": "BUY",
                "volume": volume,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": 0.8,
                "signal_reason": f"EMA 34 crossed above EMA 55 at {current_price:.5f}",
                "meta": {
                    "strategy": "ema_crossover",
                    "ema_34": current_ema_34,
                    "ema_55": current_ema_55,
                    "risk_pips": risk_pips,
                    "target_pips": risk_pips * self.risk_reward_ratio
                }
            }
        elif sell_crossover:
            # Sell setup
            entry_price = current_price
            stop_loss = entry_price + (self.base_stop_loss_pips * self.pip_size)
            take_profit = entry_price - (self.base_stop_loss_pips * self.risk_reward_ratio * self.pip_size)
            
            risk_pips = self.base_stop_loss_pips
            volume = self.calculate_position_size(risk_pips)
            
            return {
                "decision": "SELL",
                "volume": volume,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": 0.8,
                "signal_reason": f"EMA 34 crossed below EMA 55 at {current_price:.5f}",
                "meta": {
                    "strategy": "ema_crossover",
                    "ema_34": current_ema_34,
                    "ema_55": current_ema_55,
                    "risk_pips": risk_pips,
                    "target_pips": risk_pips * self.risk_reward_ratio
                }
            }
        
        return {"decision": "NO TRADE", "reason": "No EMA crossover signal"}