import pandas as pd
import numpy as np
import datetime
import os
import logging
import json
import random
from typing import Dict, List, Any, Optional
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtest_engine import BacktestEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoTuner:
    def __init__(self, target_pair="EUR/USD", initial_balance=1000, num_epochs=10000, time_limit_hours=1):
        self.target_pair = target_pair
        self.initial_balance = initial_balance
        self.pair_code = target_pair.replace("/", "_")
        self.num_epochs = num_epochs
        self.time_limit_seconds = time_limit_hours * 3600
        self.tuning_results = []
        self.strategy_class = None  # Will be set dynamically
        self.setup_logging()

        logger.info(f"🎯 SUPPLY/DEMAND TUNER FOR {self.target_pair}")
        logger.info(f"🔥 Testing up to {self.num_epochs} combinations")
        logger.info(f"⏳ Time limit: {time_limit_hours} hour(s)")

    def setup_logging(self):
        os.makedirs('auto_tuning_results', exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.results_path = f"auto_tuning_results/{self.pair_code}_SUPPLY_DEMAND_TUNING_{timestamp}.xlsx"

    def generate_combinations(self) -> List[Dict[str, Any]]:
        print(f"\n🚀 Generating unique combinations for Supply/Demand Strategy...")
        random.seed(42)
        
        param_options = {
            'zone_lookback': [100, 200, 300],
            'base_max_candles': [3, 5, 7],
            'move_min_ratio': [1.5, 2.0, 2.5, 3.0],
            'zone_width_max_pips': [15, 20, 25, 30]
        }
        
        keys, values = zip(*param_options.items())
        from itertools import product
        all_products = [dict(zip(keys, v)) for v in product(*values)]
        
        if len(all_products) > self.num_epochs:
            combinations = random.sample(all_products, self.num_epochs)
        else:
            combinations = all_products
            random.shuffle(combinations)
        
        print(f"✅ Generated {len(combinations)} unique combinations to test.")
        return combinations

    def run_fast_backtest(self, params: Dict, test_id: int) -> Dict:
        start_time = time.time()
        try:
            # Use the dynamically set strategy class or default import
            if self.strategy_class:
                strategy = self.strategy_class()
            else:
                # Fallback to EUR/USD strategy for backward compatibility
                from strategy.eurusd_strategy import EURUSDStrategy
                strategy = EURUSDStrategy()
            
            for key, value in params.items():
                setattr(strategy, key, value)

            engine = BacktestEngine(self.target_pair, self.initial_balance, strategy=strategy)
            
            data = engine.load_excel_data()
            if not data or self.target_pair not in data:
                return self._create_failed_result(test_id, params, "No data", start_time)

            pair_df = data[self.target_pair].copy()
            
            # 1. Find all possible zones once at the start
            all_zones = strategy.find_all_zones(pair_df)
            if not all_zones:
                return self._create_failed_result(test_id, params, "No zones found", start_time)

            active_trade = None
            all_trades = []
            
            # 2. Iterate through each candle to check for entries and exits
            for i in range(1, len(pair_df)):
                current_bar = pair_df.iloc[i]
                
                # Exit check
                if active_trade is not None:
                    exit_price = None
                    if active_trade['decision'] == "BUY":
                        if current_bar['high'] >= active_trade['take_profit']: exit_price = active_trade['take_profit']
                        elif current_bar['low'] <= active_trade['stop_loss']: exit_price = active_trade['stop_loss']
                    else:  # SELL
                        if current_bar['low'] <= active_trade['take_profit']: exit_price = active_trade['take_profit']
                        elif current_bar['high'] >= active_trade['stop_loss']: exit_price = active_trade['stop_loss']
                    
                    if exit_price is not None:
                        pnl_mult = 1 if active_trade['decision'] == "BUY" else -1
                        # Calculate P&L properly based on pip movement
                        pip_size = 0.01 if "JPY" in self.target_pair else 0.0001
                        pip_value = 10  # $10 per pip for standard lot
                        price_diff = (exit_price - active_trade['entry_price']) * pnl_mult
                        pip_movement = price_diff / pip_size
                        pnl = pip_movement * pip_value - 1.0  # PnL calc
                        all_trades.append({'pnl': pnl})
                        active_trade = None
                    continue # Continue to next candle after exit check

                # Entry check
                # Iterate through zones that are "fresh" and have been created in the past
                for zone in all_zones:
                    if zone['is_fresh'] and zone['created_at_index'] < i:
                        # Check both high and low of the current candle for entry
                        for price_point in [current_bar['high'], current_bar['low']]:
                            signal = strategy.check_entry_signal(price_point, zone)
                            if signal:
                                active_trade = signal
                                zone['is_fresh'] = False  # Mark zone as tested
                                break # Exit inner price_point loop
                        if active_trade:
                            break # Exit zone loop

            if not all_trades:
                return self._create_failed_result(test_id, params, "No trades executed", start_time)
            
            wins = sum(1 for t in all_trades if t['pnl'] > 0)
            total_trades = len(all_trades)
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            return {
                "id": test_id,
                "params": json.dumps(params),
                "win_rate": win_rate,
                "trades": total_trades,
                "pnl": sum(t['pnl'] for t in all_trades),
                "status": "OK"
            }
        except Exception as e:
            return self._create_failed_result(test_id, params, str(e), start_time)

    def _create_failed_result(self, test_id: int, params: Dict, error: str, start_time: float) -> Dict:
        return { "id": test_id, "params": json.dumps(params), "status": "Failed", "error": error, "win_rate": 0, "trades": 0 }

    def run_optimization(self):
        print("\n🚀 Starting Supply/Demand optimization...")
        combinations = self.generate_combinations()
        total_combinations = len(combinations)
        start_time = time.time()
        best_win_rate = 0
        results = []

        for i, params in enumerate(combinations):
            elapsed_seconds = time.time() - start_time
            if elapsed_seconds > self.time_limit_seconds:
                print(f"\n⏳ Time limit of {self.time_limit_seconds / 3600:.1f} hours reached. Stopping optimization.")
                break

            result = self.run_fast_backtest(params, i + 1)
            results.append(result)

            if result['status'] == 'OK' and result['trades'] >= 5 and result['win_rate'] > best_win_rate:
                best_win_rate = result['win_rate']
            
            self._print_progress(i + 1, total_combinations, start_time, best_win_rate)
        
        print("\n\n✅ Optimization finished!")
        self.tuning_results = results
        self.save_results()
        self.print_top_results()

    def _print_progress(self, i: int, total: int, start_time: float, best_wr: float):
        elapsed = time.time() - start_time
        avg_time_per_epoch = elapsed / i
        eta = (total - i) * avg_time_per_epoch
        
        elapsed_str = f"{int(elapsed // 60): >2}m {int(elapsed % 60):02}s"
        eta_str = f"{int(eta // 60): >3}m {int(eta % 60):02}s"
        
        progress_bar = f"Epoch {i: >4}/{total} | Elapsed: {elapsed_str} | ETA: {eta_str} | 🏆 Best WR: {best_wr: >6.2f}%"
        print(f"\r{progress_bar}", end="")

    def save_results(self):
        if not self.tuning_results: return
        df = pd.DataFrame(self.tuning_results)
        df.to_excel(self.results_path, index=False)
        print(f"\n💾 Results saved to {self.results_path}")

    def print_top_results(self):
        if not self.tuning_results:
            print("No results to display.")
            return

        successful = [r for r in self.tuning_results if r['status'] == 'OK' and r.get('trades', 0) >= 5]
        if not successful:
            print("\n❌ No combinations found with more than 5 trades.")
            return
            
        print(f"\n🏆 TOP 5 SUPPLY/DEMAND RESULTS (min 5 trades, R:R 1:3):")
        top_5 = sorted(successful, key=lambda x: x.get('win_rate', 0), reverse=True)[:5]
        
        for i, r in enumerate(top_5, 1):
            params = json.loads(r['params'])
            print(f"  #{i}: Win Rate: {r['win_rate']:.2f}% ({r['trades']} trades) | PnL: ${r.get('pnl', 0):.2f} | Params: {params}")

def main():
    try:
        tuner = AutoTuner(target_pair="EUR/USD", initial_balance=1000, num_epochs=20, time_limit_hours=1)
        tuner.run_optimization()
    except Exception as e:
        logger.error(f"An error occurred during the tuning process: {e}", exc_info=True)

if __name__ == "__main__":
    main() 