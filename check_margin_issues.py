#!/usr/bin/env python3
"""
Script to check margin requirements and potential rejection causes
"""

def check_margin_requirements():
    """Calculate margin requirements for typical trade sizes"""
    
    print("🏦 MARGIN REQUIREMENT ANALYSIS")
    print("=" * 50)
    
    # Typical cTrader margin requirements (varies by broker)
    leverage_ratios = {
        "EUR/USD": 30,   # 1:30 for major pairs in EU
        "GBP/USD": 30,
        "USD/JPY": 30,
        "EUR/JPY": 30,
        "GBP/JPY": 30,
        "EUR/GBP": 30
    }
    
    # Current approximate prices
    current_prices = {
        "EUR/USD": 1.0900,
        "GBP/USD": 1.2700,
        "USD/JPY": 150.00,
        "EUR/JPY": 163.50,
        "GBP/JPY": 190.50,
        "EUR/GBP": 0.8580
    }
    
    # Standard lot size (100,000 units of base currency)
    lot_size = 100000
    
    print("📊 MARGIN CALCULATION FOR DIFFERENT POSITION SIZES:")
    print()
    
    for pair, price in current_prices.items():
        leverage = leverage_ratios[pair]
        
        print(f"💱 {pair} (Price: {price})")
        
        # Calculate for different lot sizes
        for lots in [0.01, 0.1, 0.5, 1.0, 2.0]:
            position_value = lots * lot_size * price
            
            # Convert to USD if needed
            if pair == "USD/JPY":
                position_value_usd = position_value / price  # JPY to USD
            elif pair.endswith("JPY"):
                position_value_usd = position_value / price  # JPY to USD  
            elif pair.startswith("USD"):
                position_value_usd = position_value
            else:
                position_value_usd = position_value  # Assume EUR/GBP pairs ~= USD
            
            required_margin = position_value_usd / leverage
            
            print(f"   {lots:4.2f} lots: ${required_margin:8.2f} margin required")
        
        print()
    
    print("🚨 COMMON REJECTION CAUSES:")
    print("   1. 💰 Account balance < required margin")
    print("   2. 📈 Max leverage exceeded")
    print("   3. 🔢 Position too small (min 0.01 lots)")
    print("   4. 📊 Volume not multiple of 1000 units")
    print("   5. ⏰ Market closed or low liquidity")
    print("   6. 🏢 Demo account restrictions")
    
    print()
    print("💡 SOLUTIONS:")
    print("   • Reduce position size")
    print("   • Increase account balance") 
    print("   • Check volume calculation")
    print("   • Verify market hours")
    print("   • Check demo account limits")

def check_volume_calculation():
    """Check if volume calculations are within cTrader limits"""
    
    print("\n" + "=" * 50)
    print("📏 VOLUME CALCULATION CHECK")
    print("=" * 50)
    
    # Simulate volume calculation from your code
    target_risk_usd = 50.0
    
    test_scenarios = [
        {"pair": "EUR/USD", "risk_pips": 20, "pip_value": 10.0},
        {"pair": "USD/JPY", "risk_pips": 30, "pip_value": 10.0},
        {"pair": "GBP/JPY", "risk_pips": 40, "pip_value": 7.0},
    ]
    
    print(f"🎯 Target risk per trade: ${target_risk_usd}")
    print()
    
    for scenario in test_scenarios:
        pair = scenario["pair"]
        risk_pips = scenario["risk_pips"]
        pip_value = scenario["pip_value"]
        
        # Your volume calculation logic
        volume_lots = target_risk_usd / (risk_pips * pip_value)
        volume_lots = max(0.01, min(volume_lots, 2.0))  # Your clamp logic
        
        # Convert to cTrader internal format
        ctrader_volume = volume_lots * 100000
        ctrader_volume = round(ctrader_volume / 1000) * 1000  # Round to 1000s
        ctrader_volume = max(ctrader_volume, 1000)  # Minimum 1000
        final_volume = int(ctrader_volume) * 100  # Final multiplication
        
        print(f"💱 {pair}")
        print(f"   Risk: {risk_pips} pips × ${pip_value}/pip = ${risk_pips * pip_value}/lot")
        print(f"   Calculated: {volume_lots:.3f} lots")
        print(f"   cTrader volume: {final_volume:,} units")
        print(f"   Final lots: {final_volume / 10000000:.3f}")
        
        # Check for potential issues
        if final_volume < 100000:
            print(f"   ⚠️  WARNING: Volume might be too small")
        if final_volume > 200000000:  # 2 lots max
            print(f"   ⚠️  WARNING: Volume exceeds 2 lot limit")
        
        print()

if __name__ == "__main__":
    check_margin_requirements()
    check_volume_calculation() 