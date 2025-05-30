import json
import numpy as np

class Strategy:
    def __init__(self):
        pass

    @staticmethod
    def strategy(df, pair, news) -> str:
    
        # Calculate EMA50 and EMA200
        ema50_series = df['close'].ewm(span=50, adjust=False).mean()
        ema200_series = df['close'].ewm(span=200, adjust=False).mean()
        ema50 = ema50_series.iloc[-1]
        ema200 = ema200_series.iloc[-1]

        # Check EMA slope to confirm trend direction
        ema50_slope = ema50_series.iloc[-1] - ema50_series.iloc[-5]
        ema200_slope = ema200_series.iloc[-1] - ema200_series.iloc[-5]

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

        # Convert timestamps to string for JSON
        df_copy = df.copy()
        df_copy['timestamp'] = df_copy['timestamp'].astype(str)
        candle_data = df_copy.tail(100).to_dict(orient='records')

        analysis = {
            'ema50': float(round(ema50, 5)),
            'ema200': float(round(ema200, 5)),
            'ema50_slope': float(round(ema50_slope, 5)),
            'ema200_slope': float(round(ema200_slope, 5)),
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
            'pair': pair,
            'recent_candles': candle_data
        }

        analysis_bundle = json.dumps(analysis)

        prompt = f"""
        You are an advanced Forex trading analyst. Use the strategy below to analyze {pair} 30-minute chart data and return only the **highest-probability trade setup**, if any. Be strict—only recommend a trade if all conditions align strongly.

        📈 Strategy Summary (for {pair} 30min):
        **This is USD Account**
        ✅ Long Trade (Buy):
        1. EMA 50 > EMA 200 AND both EMAs sloping upward (check ema50_slope > 0 and ema200_slope > 0).
        2. Price must bounce from around 0.5 or 0.618 Fibonacci retracement level.
        3. RSI < 30 and turning upward.
        4. Bullish candle closes above retracement level with volume spike.
        5. No nearby resistance.

        🔻 Short Trade (Sell):
        1. EMA 50 < EMA 200 AND both EMAs sloping downward (check ema50_slope < 0 and ema200_slope < 0).
        2. Price must reject from 0.5 or 0.618 retracement level.
        3. RSI > 70 and turning downward.
        4. Bearish candle closes below retracement level with volume spike.
        5. No nearby support.

        💵 Risk Management:
        - Account size: $1000
        - Risk per trade: $50
        - Target R:R = 1:3
        - SL = Based on technical level
        - Use formula: lot_size = 30 / (SL_pips * pip_value)

        📐 Pip Rules:
        - EUR/USD, GBP/USD, EUR/GBP: pip = 0.0001, value = $10
        - USD/JPY, EUR/JPY, GBP/JPY: pip = 0.01, values accordingly

        🎯 Objective:
        - Use strict filtering. If the setup is not strong, return "NO TRADE".
        - Your answer M UST STRICTLY be a clean JSON only in this format:
        - Your response only have JSON ONLY!!! NO OTHER THINGS
        
        ```json
        {{
        "volume": float,
        "decision": "BUY" or "SELL" or "NO TRADE",
        "entry_price": float,
        "stop_loss": float,
        "take_profit": float,
        "reason": "Short justification",
        "winrate": "Confidence %",
        "volume calculation": "Explain how volume was calculated"
        }}

        Forex News for today : {news}
        
        Data: {analysis_bundle}
        """

        return prompt


    
