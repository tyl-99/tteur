import pandas as pd
import numpy as np
import itertools
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backtest'))

from backtest.backtest_engine import BacktestEngine
from strategy.eurjpy_strategy import EURJPYSTRATEGY

# Setup logging for autotuner
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def autotune_eurjpy_strategy(num_combinations=10):
    logger.info(f"🚀 Starting autotuning for EUR/JPY strategy with {num_combinations} combinations...")

    # Define parameter ranges for stop-loss and take-profit
    sl_values = np.linspace(40, 60, 5).round(1)  # Example: 5 values from 40 to 60
    tp_values = np.linspace(80, 120, 5).round(1) # Example: 5 values from 80 to 120
    
    best_performance = {
        'final_balance': 0,
        'params': {},
        'total_trades': 0,
        'win_rate': 0.0,
        'overall_rr': 0.0
    }

    # Generate combinations
    combinations = list(itertools.product(sl_values, tp_values))
    
    # Select a subset of combinations if more than requested
    if len(combinations) > num_combinations:
        # For simplicity, taking the first 'num_combinations' evenly spaced elements.
        # In a real scenario, you might want a more sophisticated sampling or random selection.
        indices = np.linspace(0, len(combinations) - 1, num_combinations, dtype=int)
        selected_combinations = [combinations[i] for i in indices]
    else:
        selected_combinations = combinations

    for i, (sl, tp) in enumerate(selected_combinations):
        logger.info(f"\n⚙️ Running combination {i+1}/{len(selected_combinations)}: SL={sl} pips, TP={tp} pips")

        # Create a new strategy instance with current parameters
        strategy_instance = EURJPYSTRATEGY(
            fixed_stop_loss_pips=sl,
            take_profit_pips=tp
        )

        # Initialize and run backtest engine with the specific strategy instance
        engine = BacktestEngine(
            target_pair="EUR/JPY",
            initial_balance=1000,
            strategy_instance=strategy_instance
        )
        results = engine.run_backtest()

        # Evaluate results
        if results.get('final_balance', 0) > best_performance['final_balance']:
            best_performance = {
                'final_balance': results.get('final_balance', 0),
                'params': {'stop_loss': sl, 'take_profit': tp},
                'total_trades': results.get('total_trades', 0),
                'win_rate': results.get('win_rate', 0.0),
                'overall_rr': results.get('overall_rr', 0.0)
            }
            logger.info(f"🏆 New best performance found: Final Balance ${best_performance['final_balance']:.2f} with SL={sl}, TP={tp}")

    logger.info(f"\n✨ Autotuning for EUR/JPY completed!")
    print(f"\n================================================================================")
    print(f"📈 BEST EUR/JPY STRATEGY PARAMETERS")
    print(f"================================================================================")
    print(f"   Final Balance: ${best_performance['final_balance']:.2f}")
    print(f"   Stop Loss: {best_performance['params'].get('stop_loss')} pips")
    print(f"   Take Profit: {best_performance['params'].get('take_profit')} pips")
    print(f"   Total Trades: {best_performance['total_trades']:,}")
    print(f"   Win Rate: {best_performance['win_rate']:.2f}%")
    print(f"   Overall R:R Ratio: {best_performance['overall_rr']:.2f}:1")
    print(f"================================================================================")

if __name__ == "__main__":
    autotune_eurjpy_strategy(num_combinations=10) 