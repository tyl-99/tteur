import json
import numpy as np

class Strategy:
    def __init__(self):
        pass

    @staticmethod
    def strategy(df, pair) -> str:

        # Calculate EMA50 and EMA200
        ema50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]

        # Calculate RSI(14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_last = rsi.iloc[-1]

        # Recent swing high and low (last 20 bars)
        recent_high = df['high'].rolling(window=20).max().iloc[-1]
        recent_low = df['low'].rolling(window=20).min().iloc[-1]

        # Fibonacci retracement levels
        fib_50 = recent_high - 0.5 * (recent_high - recent_low)
        fib_618 = recent_high - 0.618 * (recent_high - recent_low)

        analysis = {
            'ema50': float(round(ema50, 5)),
            'ema200': float(round(ema200, 5)),
            'rsi': float(round(rsi_last, 2)),
            'recent_high': float(round(recent_high, 5)),
            'recent_low': float(round(recent_low, 5)),
            'fib_50': float(round(fib_50, 5)),
            'fib_618': float(round(fib_618, 5)),
            'last_candle': {
                'open': float(df['open'].iloc[-1]),
                'close': float(df['close'].iloc[-1]),
                'high': float(df['high'].iloc[-1]),
                'low': float(df['low'].iloc[-1]),
                'volume': float(df['volume'].iloc[-1])
            },
            'pair': pair
        }
        
                    
        analysis_bundle = json.dumps(analysis)
        prompt = f"""
        You are an advanced Forex trading analyst. Use the strategy below to analyze {pair} 30-minute chart data and return only the **highest-probability trade setup**, if any. Be strict—only recommend a trade if all conditions align strongly.

        📈 Strategy Summary (for {pair} 30min):
        **This is USD Account**
        ✅ Long Trade (Buy):
        1. Trend must be bullish: EMA 50 is clearly above EMA 200 and both EMAs sloping upward.
        2. A recent swing low and high must allow for drawing a Fibonacci retracement.
        3. Price must retrace to **around the 0.5 or 0.618 Fibonacci level**, then bounce up.
        4. RSI (14) should dip below 30 and start rising (oversold recovery).
        5. A **bullish candle must close clearly above** the retracement level with volume confirmation (if available).
        6. Confirm no major resistance directly overhead.

        🔻 Short Trade (Sell):
        1. Trend must be bearish: EMA 50 is below EMA 200 and both sloping downward.
        2. Identify recent swing high and low for Fibonacci.
        3. Price must pull back to the **0.5 or 0.618 level**, then reject downward.
        4. RSI (14) should go above 70 and turn downward (overbought condition).
        5. A **bearish candle must close clearly below** the retracement level with increasing volume.
        6. Confirm no major support just below.

        💵 Risk Management:
        - Account size: $1000  
        - Max risk per trade: $50  
        - Risk/reward: 1:3  
        - Automatically calculate stop-loss and take-profit based on that ratio.
        - Also calculate the volume in **lots** so that if SL is hit, loss = $30.

        📐 Pip Rules (for correct lot size):
        - Assume 1 lot = 100,000 units
        - Pip size for EUR/USD, GBP/USD, EUR/GBP = **0.0001**
        - Pip size for JPY pairs = **0.01**
        - Pip value (1 lot) for:
        - EUR/USD = $10  
        - GBP/USD = $10  
        - EUR/GBP = $12.5  
        - USD/JPY = $9.13  
        - EUR/JPY = $9.28  
        - GBP/JPY = $9.10

        ✅ To calculate lot size:
        1. First, calculate stop-loss in **pips** (based on entry vs SL).
        2. Use formula: `lot_size = 30 / (stop_loss_pips * pip_value)`
        3. Final answer must include `volume` in **lots**, e.g., 0.12

        🎯 Objective:
        - Use strict filtering. If the setup is not strong, return "NO TRADE".
        - Your answer must be a clean JSON only in this format:

        ```json
        {{
        "volume": float,
        "decision": "BUY" or "SELL" or "NO TRADE",
        "entry_price": float,
        "stop_loss": float,
        "take_profit": float,
        "reason": "Very short and precise justification — e.g. 'EMA trend bullish, RSI recovering from 29, Fib 0.618 bounce confirmed'"
        }}

        Data: {analysis_bundle}
        """
        
        return prompt
