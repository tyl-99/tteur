import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta
import itertools
import openpyxl

from backtest.backtest_engine_m30 import BacktestEngineM30
from strategy.eurusd_strategy import EURUSDSTRATEGY

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autotuner_log.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Autotuner:
    def __init__(self, target_pair="EUR/USD", start_date: str = None, end_date: str = None):
        self.target_pair = target_pair
        self.results = []
        self.start_date = start_date
        self.end_date = end_date

    def run_tuning(self, num_combinations=10):
        """Run the autotuning process with predefined best parameter combinations."""

        parameter_combinations = [
            {
                'lookback_period': 120,
                'min_structure_move_pips': 6,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 5,
                'rr_ratio': 1.5,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.4,
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 1,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            {
                'lookback_period': 170,
                'min_structure_move_pips': 8,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 8,
                'rr_ratio': 2.7,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 35,
                'min_confirmation_body_pct': 0.35,
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': True,
            },
            {
                'lookback_period': 140,
                'min_structure_move_pips': 7,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 6,
                'rr_ratio': 2.5,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 40,
                'min_confirmation_body_pct': 0.45,
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            {
                'lookback_period': 250,
                'min_structure_move_pips': 12,
                'fib_tolerance': 0.2,
                'sl_buffer_pips': 6,
                'rr_ratio': 2.0,
                'min_zone_size_pips': 2,
                'max_zone_size_pips': 28,
                'min_confirmation_body_pct': 0.5,
                'swing_point_lookback': 3,
                'max_base_candles_in_zone': 1,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            {
                'lookback_period': 180,
                'min_structure_move_pips': 9,
                'fib_tolerance': 0.3,
                'sl_buffer_pips': 8,
                'rr_ratio': 2.8,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 40,
                'min_confirmation_body_pct': 0.38,
                'swing_point_lookback': 3,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            {
                'lookback_period': 210,
                'min_structure_move_pips': 10,
                'fib_tolerance': 0.22,
                'sl_buffer_pips': 8,
                'rr_ratio': 2.8,
                'min_zone_size_pips': 2,
                'max_zone_size_pips': 40,
                'min_confirmation_body_pct': 0.4,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            {
                'lookback_period': 190,
                'min_structure_move_pips': 10,
                'fib_tolerance': 0.3,
                'sl_buffer_pips': 7,
                'rr_ratio': 3.2,
                'min_zone_size_pips': 2,
                'max_zone_size_pips': 50,
                'min_confirmation_body_pct': 0.42,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 3,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            {
                'lookback_period': 200,
                'min_structure_move_pips': 11,
                'fib_tolerance': 0.25,
                'sl_buffer_pips': 6,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 2,
                'max_zone_size_pips': 30,
                'min_confirmation_body_pct': 0.45,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
            },
            # Combination 9 (Loose profile, slightly tighter structure)
            {
                'lookback_period': 100,
                'min_structure_move_pips': 5,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 5,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 30,
                'min_confirmation_body_pct': 0.3,
                'min_impulse_pips_factor': 0.25, # looser
                'min_impulse_candle_range_pips': 1.5, # looser
                'min_impulse_body_to_range_ratio': 0.20, # looser
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 10 (Loose profile, wider Fib band by default, more frequent)
            {
                'lookback_period': 90,
                'min_structure_move_pips': 4,
                'fib_tolerance': 0.28, # overridden by loose profile
                'sl_buffer_pips': 4,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 35,
                'min_confirmation_body_pct': 0.25, # looser
                'min_impulse_pips_factor': 0.25, # looser
                'min_impulse_candle_range_pips': 1.5, # looser
                'min_impulse_body_to_range_ratio': 0.20, # looser
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 3,
                'use_max_base_candle_range_filter': False, # looser
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 11 (Loose profile, stricter confirmation)
            {
                'lookback_period': 150,
                'min_structure_move_pips': 7,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 6,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 28,
                'min_confirmation_body_pct': 0.45, # stricter
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.5,
                'min_impulse_body_to_range_ratio': 0.20,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 1,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': True, # try with freshness check
                'profile': 'loose'
            },
            # Combination 12 (Loose profile, longer lookback)
            {
                'lookback_period': 200,
                'min_structure_move_pips': 6,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 5,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.3,
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.5,
                'min_impulse_body_to_range_ratio': 0.20,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 13 (No loose profile, moderate settings, RR 3.0)
            {
                'lookback_period': 130,
                'min_structure_move_pips': 6,
                'fib_tolerance': 0.30,
                'sl_buffer_pips': 5,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.40,
                'min_impulse_pips_factor': 0.5,
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': True,
            },
            # Combination 14 (Loose profile, very loose structure)
            {
                'lookback_period': 80,
                'min_structure_move_pips': 3,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 4,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 40,
                'min_confirmation_body_pct': 0.2,
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.0, # even looser
                'min_impulse_body_to_range_ratio': 0.15, # even looser
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 4,
                'use_max_base_candle_range_filter': False, # looser
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 15 (Loose profile, higher SL buffer)
            {
                'lookback_period': 110,
                'min_structure_move_pips': 5,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 8,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 30,
                'min_confirmation_body_pct': 0.3,
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.5,
                'min_impulse_body_to_range_ratio': 0.20,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 16 (Loose profile, focus on cleaner impulses)
            {
                'lookback_period': 160,
                'min_structure_move_pips': 6,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 5,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.35,
                'min_impulse_pips_factor': 0.5, # stricter impulse
                'min_impulse_candle_range_pips': 3.0, # stricter
                'min_impulse_body_to_range_ratio': 0.4, # stricter
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 1,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 17 (Loose profile, wider confirmation body)
            {
                'lookback_period': 120,
                'min_structure_move_pips': 6,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 5,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.5, # tighter confirmation
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.5,
                'min_impulse_body_to_range_ratio': 0.20,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            },
            # Combination 18 (No loose profile, very aggressive)
            {
                'lookback_period': 60,
                'min_structure_move_pips': 3,
                'fib_tolerance': 0.382,
                'sl_buffer_pips': 3,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 50,
                'min_confirmation_body_pct': 0.2,
                'min_impulse_pips_factor': 0.2, # even looser
                'min_impulse_candle_range_pips': 0.5, # even looser
                'min_impulse_body_to_range_ratio': 0.1, # even looser
                'swing_point_lookback': 1,
                'max_base_candles_in_zone': 4,
                'use_max_base_candle_range_filter': False,
                'enable_zone_freshness_check': False,
            },
            # Combination 19 (Loose profile, a bit more conservative on structure)
            {
                'lookback_period': 140,
                'min_structure_move_pips': 8,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 6,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.35,
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.5,
                'min_impulse_body_to_range_ratio': 0.20,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 2,
                'use_max_base_candle_range_filter': True,
                'enable_zone_freshness_check': True, # try with freshness
                'profile': 'loose'
            },
            # Combination 20 (Loose profile, wider range on base candles)
            {
                'lookback_period': 120,
                'min_structure_move_pips': 5,
                'fib_tolerance': 0.28,
                'sl_buffer_pips': 5,
                'rr_ratio': 3.0,
                'min_zone_size_pips': 1,
                'max_zone_size_pips': 25,
                'min_confirmation_body_pct': 0.3,
                'min_impulse_pips_factor': 0.25,
                'min_impulse_candle_range_pips': 1.5,
                'min_impulse_body_to_range_ratio': 0.20,
                'swing_point_lookback': 2,
                'max_base_candles_in_zone': 3,
                'use_max_base_candle_range_filter': False, # looser on base candle range
                'enable_zone_freshness_check': False,
                'profile': 'loose'
            }
        ]
        
        logger.info(f"Generated {len(parameter_combinations)} parameter combinations.")
        
        for i, params in enumerate(parameter_combinations):
            logger.info(f"--- Running backtest for combination {i+1}/{len(parameter_combinations)} ---")
            
            # Instantiate strategy with current parameters
            strategy_instance = EURUSDSTRATEGY(
                target_pair=self.target_pair,
                lookback_period=params['lookback_period'],
                min_structure_move_pips=params['min_structure_move_pips'],
                fib_tolerance=params['fib_tolerance'],
                sl_buffer_pips=params['sl_buffer_pips'],
                rr_ratio=params['rr_ratio'],
                min_zone_size_pips=params['min_zone_size_pips'],
                max_zone_size_pips=params['max_zone_size_pips'],
                min_confirmation_body_pct=params['min_confirmation_body_pct'],
                min_impulse_pips_factor=params.get('min_impulse_pips_factor'), # Use .get for optional parameters
                min_impulse_candle_range_pips=params.get('min_impulse_candle_range_pips'), # Use .get for optional parameters
                min_impulse_body_to_range_ratio=params.get('min_impulse_body_to_range_ratio'), # Use .get for optional parameters
                swing_point_lookback=params['swing_point_lookback'],
                max_base_candles_in_zone=params['max_base_candles_in_zone'],
                use_max_base_candle_range_filter=params['use_max_base_candle_range_filter'],
                enable_zone_freshness_check=params['enable_zone_freshness_check'],
                profile=params.get('profile') # Pass profile if it exists in params
            )
            
            # Instantiate backtest engine with specified date range
            backtest_engine = BacktestEngineM30(
                strategy=strategy_instance, 
                target_pair=self.target_pair, 
                start_balance=1000,
                is_autotuning=True, # Set to True for autotuning
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # Run backtest and get results summary
            results_summary = backtest_engine.run_backtest() 
            
            # Store results
            result_entry = {
                'combination_id': i + 1,
                **params,
                'total_trades': results_summary.get('total_trades', 0),
                'win_rate': results_summary.get('win_rate', 0.0),
                'total_pnl': results_summary.get('total_pnl', 0.0),
                'final_balance': results_summary.get('final_balance', 1000.0),
                'max_drawdown': results_summary.get('max_drawdown', 0.0),
                'sharpe_ratio': results_summary.get('sharpe_ratio', 0.0)
            }
            self.results.append(result_entry)
            
        self.report_results()

    def report_results(self):
        """Report and save the autotuning results."""
        results_df = pd.DataFrame(self.results)
        
        # Sort by a key metric, e.g., total_pnl
        results_df = results_df.sort_values(by='total_pnl', ascending=False)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"autotuner_results_{timestamp}.xlsx"
        results_df.to_excel(output_filename, index=False)
        
        logger.info(f"Autotuning completed. Results saved to {output_filename}")
        logger.info("\n--- Top 5 Performing Combinations (PnL & Win Rate) ---")
        for idx, row in results_df.head(5).iterrows():
            logger.info(f"\nCombination ID: {int(row['combination_id'])}")
            logger.info("Metrics:")
            logger.info(f"  Total PnL: {row['total_pnl']:.2f}")
            logger.info(f"  Win Rate: {row['win_rate']:.2f}%")

if __name__ == "__main__":
    # Define the one-year period for backtesting
    end_date_str = datetime.now().strftime("%Y-%m-%d")
    start_date_str = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    autotuner = Autotuner(target_pair="EUR/USD")
    # autotuner.run_tuning() # Commented out to prevent accidental runs 