#!/usr/bin/env python3
"""
Script to analyze trade rejection errors from forex_trading.log
"""

import re
from datetime import datetime

def analyze_trade_errors():
    """Analyze recent trade errors and rejections"""
    
    error_patterns = [
        'Order failed',
        'failed',
        'error',
        'reject',
        'margin',
        'insufficient',
        'invalid',
        'ERROR'
    ]
    
    recent_errors = []
    
    try:
        with open('forex_trading.log', 'r') as f:
            lines = f.readlines()
        
        # Check last 100 lines for errors
        for line in lines[-100:]:
            for pattern in error_patterns:
                if pattern.lower() in line.lower():
                    recent_errors.append(line.strip())
                    break
        
        print("🔍 RECENT TRADE ERROR ANALYSIS")
        print("=" * 50)
        
        if recent_errors:
            print(f"Found {len(recent_errors)} error-related entries:")
            print()
            
            for i, error in enumerate(recent_errors[-10:], 1):  # Show last 10 errors
                print(f"{i}. {error}")
            print()
            
            # Analyze common error types
            error_types = {}
            for error in recent_errors:
                if "Error processing" in error:
                    pair = error.split("Error processing")[1].split(":")[0].strip()
                    error_types[f"Processing Error - {pair}"] = error_types.get(f"Processing Error - {pair}", 0) + 1
                elif "Order failed" in error:
                    error_types["Order Rejection"] = error_types.get("Order Rejection", 0) + 1
                elif "amendment failed" in error:
                    error_types["SL/TP Amendment Failed"] = error_types.get("SL/TP Amendment Failed", 0) + 1
                
            print("📊 ERROR TYPE SUMMARY:")
            for error_type, count in error_types.items():
                print(f"   • {error_type}: {count} occurrences")
            
        else:
            print("✅ No recent error entries found in the log.")
        
        print()
        print("💡 COMMON CAUSES OF TRADE REJECTIONS:")
        print("   1. 🏦 Insufficient margin/balance")
        print("   2. 📏 Volume too small/large")
        print("   3. 🚫 Maximum positions reached") 
        print("   4. ⏰ Market closed/low liquidity")
        print("   5. 📊 Demo account limitations")
        print("   6. 🔧 API connection issues")
        
    except FileNotFoundError:
        print("❌ forex_trading.log file not found")
    except Exception as e:
        print(f"❌ Error analyzing log: {e}")

if __name__ == "__main__":
    analyze_trade_errors() 