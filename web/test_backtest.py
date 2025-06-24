#!/usr/bin/env python3
"""
Test script for the web backtest system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_backtest_engine import WebBacktestEngine

# Sample strategy code for testing
SAMPLE_STRATEGY = '''
import pandas as pd
import numpy as np
from typing import Dict, Any

class TestStrategy:
    def __init__(self):
        self.pip_size = 0.0001
        
    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Dict[str, Any]:
        """Simple test strategy - buy when price is above 20-period moving average"""
        try:
            if len(df) < 21:
                return {"decision": "NO TRADE", "reason": "Not enough data"}
            
            # Calculate 20-period moving average
            df['ma20'] = df['close'].rolling(window=20).mean()
            
            current_price = df['close'].iloc[-1]
            current_ma = df['ma20'].iloc[-1]
            
            if pd.isna(current_ma):
                return {"decision": "NO TRADE", "reason": "MA not available"}
            
            # Simple strategy: buy when price is above MA
            if current_price > current_ma:
                stop_loss = current_price - (20 * self.pip_size)  # 20 pip stop loss
                take_profit = current_price + (60 * self.pip_size)  # 60 pip take profit (1:3 R:R)
                
                return {
                    "decision": "BUY",
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "volume": 0.1,
                    "reason": "Price above MA20"
                }
            elif current_price < current_ma:
                stop_loss = current_price + (20 * self.pip_size)  # 20 pip stop loss
                take_profit = current_price - (60 * self.pip_size)  # 60 pip take profit (1:3 R:R)
                
                return {
                    "decision": "SELL",
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "volume": 0.1,
                    "reason": "Price below MA20"
                }
            else:
                return {"decision": "NO TRADE", "reason": "Price at MA level"}
                
        except Exception as e:
            return {"decision": "NO TRADE", "reason": f"Error: {str(e)}"}
'''

def test_backtest_engine():
    """Test the backtest engine with sample strategy"""
    print("🧪 Testing Web Backtest Engine...")
    
    # Create backtest engine
    engine = WebBacktestEngine(
        target_pair="EUR/USD",
        initial_balance=1000,
        strategy_code=SAMPLE_STRATEGY
    )
    
    # Load strategy from code
    print("📝 Loading strategy from code...")
    if not engine.load_strategy_from_code(SAMPLE_STRATEGY):
        print("❌ Failed to load strategy")
        return False
    
    print("✅ Strategy loaded successfully")
    
    # Check if trendbar data exists
    print("📊 Checking trendbar data...")
    df = engine.load_trendbar_data()
    if df is None:
        print("❌ No trendbar data available")
        print("💡 Make sure latest_trendbar_data.xlsx exists in the web folder")
        return False
    
    print(f"✅ Loaded {len(df)} candles")
    print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Run backtest
    print("🚀 Running backtest...")
    results = engine.run_backtest()
    
    if results is None:
        print("❌ Backtest failed")
        return False
    
    # Display results
    print("\n📊 BACKTEST RESULTS:")
    print(f"   Target Pair: {results['target_pair']}")
    print(f"   Initial Balance: ${results['initial_balance']:.2f}")
    print(f"   Final Balance: ${results['final_balance']:.2f}")
    print(f"   Total P&L: ${results['total_pnl']:.2f}")
    print(f"   Total Trades: {results['total_trades']}")
    print(f"   Win Rate: {results['win_rate']:.1f}%")
    print(f"   Max Drawdown: {results['max_drawdown']:.1f}%")
    
    if results['trades']:
        print(f"\n📋 SAMPLE TRADES:")
        for i, trade in enumerate(results['trades'][:3]):  # Show first 3 trades
            print(f"   Trade {i+1}: {trade['direction']} at {trade['entry_price']:.5f} → {trade['exit_price']:.5f} | P&L: ${trade['usd_pnl']:.2f}")
    
    print("\n✅ Backtest completed successfully!")
    return True

if __name__ == "__main__":
    success = test_backtest_engine()
    if success:
        print("\n🎉 All tests passed! The backtest system is working correctly.")
    else:
        print("\n❌ Tests failed. Please check the setup.") 