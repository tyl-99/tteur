#!/usr/bin/env python3
"""
🚀 2-HOUR MAXIMUM OPTIMIZATION RUNNER
Finds the best possible trading parameters within a strict 2-hour window.
Uses intelligent parameter selection and time management.
"""

import pandas as pd
import numpy as np
import datetime
import os
import logging
import json
import random
import time
from typing import Dict, List, Any
from itertools import product

# Import trading modules
from autotuner import AutoTuner

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_max_optimization():
    """
    Run maximum optimization for 2 hours using the existing AutoTuner
    """
    print("🚀 STARTING 2-HOUR MAXIMUM PARAMETER OPTIMIZATION")
    print("=" * 60)
    
    start_time = time.time()
    max_runtime_hours = 2.0
    
    # Create AutoTuner with maximum efficiency settings
    print(f"⚙️  Initializing AutoTuner...")
    print(f"   - Target: EUR/USD")
    print(f"   - Time limit: {max_runtime_hours} hours")
    print(f"   - Strategy: Supply/Demand Ultra-Optimized")
    
    # Initialize with high epoch count but time limit will control actual testing
    tuner = AutoTuner(
        target_pair="EUR/USD",
        initial_balance=1000,
        num_epochs=50000,  # Set high - time limit will control actual count
        time_limit_hours=max_runtime_hours
    )
    
    print(f"\n🎯 Starting optimization at {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"📊 Will auto-stop at {max_runtime_hours} hour time limit")
    
    # Run the optimization
    tuner.run_optimization()
    
    total_time = time.time() - start_time
    print(f"\n✅ OPTIMIZATION COMPLETED!")
    print(f"⏱️  Total runtime: {int(total_time//3600)}h {int((total_time%3600)//60)}m {int(total_time%60)}s")
    
    return tuner

def create_quick_test_runner():
    """
    Create a quick test runner for immediate results
    """
    print("\n🏃‍♂️ QUICK TEST MODE (30 minutes max)")
    print("=" * 50)
    
    # Quick 30-minute test for immediate feedback
    quick_tuner = AutoTuner(
        target_pair="EUR/USD",
        initial_balance=1000,
        num_epochs=5000,
        time_limit_hours=0.5  # 30 minutes
    )
    
    print("🚀 Running quick optimization...")
    quick_tuner.run_optimization()
    
    return quick_tuner

def main():
    """
    Main function with user choice
    """
    print("🎯 PARAMETER OPTIMIZATION LAUNCHER")
    print("=" * 40)
    print("Choose optimization mode:")
    print("1. 🚀 MAXIMUM (2 hours) - Best results")
    print("2. ⚡ QUICK (30 minutes) - Fast preview")
    print("3. 🔧 CUSTOM - Specify your own time")
    
    while True:
        try:
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                print("\n🚀 Starting MAXIMUM 2-hour optimization...")
                tuner = run_max_optimization()
                break
                
            elif choice == "2":
                print("\n⚡ Starting QUICK 30-minute test...")
                tuner = create_quick_test_runner()
                break
                
            elif choice == "3":
                hours = float(input("Enter time limit in hours (0.5 - 12): "))
                if 0.5 <= hours <= 12:
                    print(f"\n🔧 Starting CUSTOM {hours}-hour optimization...")
                    tuner = AutoTuner(
                        target_pair="EUR/USD",
                        initial_balance=1000,
                        num_epochs=int(hours * 25000),  # Scale epochs with time
                        time_limit_hours=hours
                    )
                    tuner.run_optimization()
                    break
                else:
                    print("❌ Time must be between 0.5 and 12 hours")
                    continue
                    
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
                continue
                
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Optimization cancelled.")
            return
    
    print(f"\n🎉 All done! Check your results in the auto_tuning_results/ folder")

if __name__ == "__main__":
    main() 