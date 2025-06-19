#!/usr/bin/env python3
"""
Main Backtest Runner for Railway Deployment
Uses environment variables to control pair selection and backtest duration.
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tuning.autotuner import AutoTuner

# Load environment variables
load_dotenv()

# Configure minimal logging (suppress most output)
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

class MainBacktestRunner:
    def __init__(self, target_pair=None, backtest_hours=None):
        # Get configuration from environment variables or args
        self.target_pair = target_pair or os.getenv("BacktestPair", "EUR/USD")
        self.backtest_hours = float(backtest_hours or os.getenv("BacktestHours", "2.0"))
        
        # Strategy class mapping
        self.strategy_mapping = {
            "EUR/USD": "strategy.eurusd_strategy.EURUSDSupplyDemandStrategy",
            "GBP/USD": "strategy.gbpusd_strategy.GBPUSDDemandStrategy", 
            "EUR/GBP": "strategy.eurgbp_strategy.EURGBPSupplyDemandStrategy",
            "USD/JPY": "strategy.usdjpy_strategy.USDJPYStrategy",
            "GBP/JPY": "strategy.gbpjpy_strategy.GBPJPYStrategy",
            "EUR/JPY": "strategy.eurjpy_strategy.EURJPYSupplyDemandStrategy"
        }
        
        print(f"🎯 TARGET PAIR: {self.target_pair}")
        print(f"⏱️  BACKTEST DURATION: {self.backtest_hours} hours")
        print(f"🚀 Starting optimization...")
        print("-" * 50)
        
    def run_backtest(self):
        """Run the backtest with minimal output"""
        try:
            # Create autotuner instance
            autotuner = AutoTuner(
                target_pair=self.target_pair,
                initial_balance=1000,
                num_epochs=10000,  # Will be limited by time
                time_limit_hours=self.backtest_hours
            )
            
            # Override the autotuner's strategy import for the specific pair
            self._setup_strategy_for_pair(autotuner)
            
            # Run optimization with minimal output
            self._run_optimization_quiet(autotuner)
            
            # Print final results
            self._print_final_results(autotuner)
            
        except Exception as e:
            print(f"❌ Error during backtest: {str(e)}")
            sys.exit(1)
    
    def _setup_strategy_for_pair(self, autotuner):
        """Dynamically import and set the correct strategy for the pair"""
        strategy_path = self.strategy_mapping.get(self.target_pair)
        if not strategy_path:
            raise ValueError(f"No strategy found for pair: {self.target_pair}")
        
        # Import the strategy class dynamically
        module_path, class_name = strategy_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        strategy_class = getattr(module, class_name)
        
        # Update autotuner to use the correct strategy
        autotuner.strategy_class = strategy_class
        
    def _run_optimization_quiet(self, autotuner):
        """Run optimization with minimal console output"""
        import time
        import json
        
        combinations = autotuner.generate_combinations()
        total_combinations = len(combinations)
        start_time = time.time()
        results = []
        
        for i, params in enumerate(combinations):
            # Check time limit
            elapsed_seconds = time.time() - start_time
            if elapsed_seconds > autotuner.time_limit_seconds:
                print(f"\n⏳ Time limit reached after {i} epochs")
                break
            
            # Run backtest (suppress internal output)
            result = self._run_quiet_backtest(autotuner, params, i + 1)
            results.append(result)
            
            # Simple progress indicator (only every 10th iteration for cleaner output)
            if i % 10 == 0 or i == total_combinations - 1:
                progress = f"{i + 1}/{total_combinations}"
                elapsed_mins = int(elapsed_seconds // 60)
                print(f"\rProgress: {progress} | Elapsed: {elapsed_mins}m", end="", flush=True)
        
        print()  # New line after progress
        autotuner.tuning_results = results
        autotuner.save_results()
        
    def _run_quiet_backtest(self, autotuner, params, test_id):
        """Run a single backtest with minimal output"""
        import time
        
        start_time = time.time()
        try:
            # Create strategy instance with parameters
            strategy = autotuner.strategy_class()
            for key, value in params.items():
                setattr(strategy, key, value)

            # Import and use backtest engine
            from backtest.backtest_engine import BacktestEngine
            engine = BacktestEngine(autotuner.target_pair, autotuner.initial_balance, strategy=strategy)
            
            # Suppress BacktestEngine output by temporarily redirecting stdout/stderr
            import io
            import contextlib
            
            f = io.StringIO()
            with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                data = engine.load_excel_data()
                if not data or autotuner.target_pair not in data:
                    return autotuner._create_failed_result(test_id, params, "No data", start_time)

                pair_df = data[autotuner.target_pair].copy()
                
                # Find all zones
                all_zones = strategy.find_all_zones(pair_df)
                if not all_zones:
                    return autotuner._create_failed_result(test_id, params, "No zones found", start_time)

                active_trade = None
                all_trades = []
                
                # Simulate trading
                for i in range(1, len(pair_df)):
                    current_bar = pair_df.iloc[i]
                    
                    # Exit check
                    if active_trade is not None:
                        exit_price = None
                        if active_trade['decision'] == "BUY":
                            if current_bar['high'] >= active_trade['take_profit']: 
                                exit_price = active_trade['take_profit']
                            elif current_bar['low'] <= active_trade['stop_loss']: 
                                exit_price = active_trade['stop_loss']
                        else:  # SELL
                            if current_bar['low'] <= active_trade['take_profit']: 
                                exit_price = active_trade['take_profit']
                            elif current_bar['high'] >= active_trade['stop_loss']: 
                                exit_price = active_trade['stop_loss']
                        
                        if exit_price is not None:
                            pnl_mult = 1 if active_trade['decision'] == "BUY" else -1
                            # Calculate P&L properly based on pip movement
                            pip_size = 0.01 if "JPY" in autotuner.target_pair else 0.0001
                            pip_value = 10  # $10 per pip for standard lot
                            price_diff = (exit_price - active_trade['entry_price']) * pnl_mult
                            pip_movement = price_diff / pip_size
                            pnl = pip_movement * pip_value - 1.0
                            all_trades.append({'pnl': pnl})
                            active_trade = None
                        continue

                    # Entry check
                    for zone in all_zones:
                        if zone['is_fresh'] and zone['created_at_index'] < i:
                            for price_point in [current_bar['high'], current_bar['low']]:
                                signal = strategy.check_entry_signal(price_point, zone)
                                if signal:
                                    active_trade = signal
                                    zone['is_fresh'] = False
                                    break
                            if active_trade:
                                break

            if not all_trades:
                return autotuner._create_failed_result(test_id, params, "No trades executed", start_time)
            
            wins = sum(1 for t in all_trades if t['pnl'] > 0)
            total_trades = len(all_trades)
            win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = sum(t['pnl'] for t in all_trades)
            
            return {
                "id": test_id,
                "params": json.dumps(params),
                "win_rate": win_rate,
                "trades": total_trades,
                "pnl": total_pnl,
                "wins": wins,
                "losses": total_trades - wins,
                "status": "OK"
            }
            
        except Exception as e:
            return autotuner._create_failed_result(test_id, params, str(e), start_time)
    
    def _print_final_results(self, autotuner):
        """Print the top 5 results in a clean, readable format"""
        print("\n" + "="*60)
        print(f"🏆 BACKTEST RESULTS FOR {self.target_pair}")
        print("="*60)
        
        if not autotuner.tuning_results:
            print("❌ No results generated")
            return
        
        # Filter successful results with minimum trades
        successful = [r for r in autotuner.tuning_results 
                     if r['status'] == 'OK' and r.get('trades', 0) >= 5]
        
        if not successful:
            print("❌ No successful combinations found (minimum 5 trades required)")
            return
        
        # Sort by win rate, then by total PnL
        top_results = sorted(successful, 
                           key=lambda x: (x.get('win_rate', 0), x.get('pnl', 0)), 
                           reverse=True)[:5]
        
        print(f"📊 Total epochs tested: {len(autotuner.tuning_results)}")
        print(f"✅ Successful combinations: {len(successful)}")
        print(f"⏱️  Test duration: {self.backtest_hours} hours")
        print()
        
        for i, result in enumerate(top_results, 1):
            import json
            params = json.loads(result['params'])
            
            print(f"#{i} BEST COMBINATION")
            print("-" * 30)
            print(f"📈 Win Rate: {result['win_rate']:.2f}%")
            print(f"💰 Total P&L: ${result['pnl']:.2f}")
            print(f"📊 Trades: {result['trades']} ({result.get('wins', 0)}W / {result.get('losses', 0)}L)")
            
            if result['pnl'] > 0:
                losing_pnl = sum(r.get('pnl', 0) for r in autotuner.tuning_results if r.get('pnl', 0) < 0)
                if losing_pnl < 0:
                    print(f"💚 Profit Factor: {abs(result['pnl']) / abs(losing_pnl):.2f}")
            
            print(f"⚙️  Parameters:")
            for param, value in params.items():
                print(f"   • {param}: {value}")
            print()
        
        # Summary stats
        best_result = top_results[0]
        print("🎯 RECOMMENDED PARAMETERS:")
        print("-" * 30)
        best_params = json.loads(best_result['params'])
        for param, value in best_params.items():
            print(f"{param} = {value}")
        
        print(f"\n💡 Expected Performance:")
        print(f"   Win Rate: {best_result['win_rate']:.2f}%")
        print(f"   Profit: ${best_result['pnl']:.2f}")
        print(f"   Trade Count: {best_result['trades']}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Forex Strategy Backtest Runner")
    parser.add_argument("--pair", type=str, help="Currency pair to test (e.g., USD/JPY)")
    parser.add_argument("--hours", type=float, help="Backtest duration in hours")
    
    args = parser.parse_args()
    
    print("🚀 FOREX STRATEGY BACKTEST RUNNER")
    print("=" * 50)
    
    runner = MainBacktestRunner(args.pair, args.hours)
    runner.run_backtest()
    
    print("\n✅ Backtest completed successfully!")

if __name__ == "__main__":
    main() 