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
        - Risk per trade: $50(TAKE NOTE THIS IS MAXIMUM RISK)
        - Target R:R = 1:3(MUST AT LEAST 1:3 OR MORE RISK REWARD RATIO)
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

    @staticmethod
    def get_strategy(pair):
        pair = pair.upper()
        strategies = {
    "EUR/USD": """
          ✅ Long Trade (Buy):
            1. EMA 50 > EMA 200 with both showing a sharp upward slope.
            2. Price touches 0.5 or 0.618 fib zone with double bottom or bullish engulfing.
            3. RSI < 30 AND bullish divergence within last 5 bars.
            4. Strong bullish candle closes above fib zone with volume > 2x average.
            5. Resistance must be > 30 pips away.

            🔻 Short Trade (Sell):
            1. EMA 50 < EMA 200 with strong downward slope (ema50_slope < 2 * ema200_slope).
            2. Price rejects fib zone with long upper wick + bearish engulfing.
            3. RSI > 70 AND bearish divergence confirmed.
            4. Candle closes below fib with volume spike > 150% of recent average.
            5. Nearest support must be > 30 pips away.
            """,

                "GBP/USD": """
            ✅ Long Trade (Buy):
            1. EMA 50 > EMA 200 and slope > 2x ATR.
            2. Pullback to fib 0.5 or 0.618 with pin bar or bullish engulfing after RSI < 35.
            3. Volume on bounce candle is higher than past 10 bars.
            4. 2nd bullish candle confirms entry with clean close above fib zone.
            5. Resistance at least 25 pips away and price must close above micro-range.

            🔻 Short Trade (Sell):
            1. EMA 50 < EMA 200 and sloping clearly down.
            2. Fib rejection at 0.5 or 0.618 with RSI > 65 and turning down.
            3. Candle has upper wick > body size.
            4. High-volume bearish candle follows confirming momentum.
            5. No support within 25 pips; strong body close confirms breakdown.
            """,

                "USD/JPY": """
            ✅ Long Trade (Buy):
            1. EMA 50 > EMA 200 and slope > 1.5x recent ATR.
            2. Pullback to 0.5 or 0.618 fib during NY session only.
            3. RSI < 30 and price forms bullish engulfing candle.
            4. Volume spike in bullish candle > average of last 20 bars.
            5. Resistance > 35 pips away and recent highs taken out.

            🔻 Short Trade (Sell):
            1. EMA 50 < EMA 200 with strong negative slope.
            2. Price rejects fib zone with long upper wick and RSI > 75.
            3. Bearish engulfing or Marubozu closes below fib level.
            4. Volume must exceed past 15-candle average by 30%.
            5. No support seen in 30 pips.
            """,

                "EUR/JPY": """
            ✅ Long Trade (Buy):
            1. EMA 50 > EMA 200 and both rising (avoid flat EMA50).
            2. RSI < 25 and hidden bullish divergence against price.
            3. Strong lower wick rejection from fib zone (0.5–0.618).
            4. Bullish engulfing candle closes above fib level with volume spike.
            5. No supply zones within 30 pips.

            🔻 Short Trade (Sell):
            1. EMA 50 < EMA 200 and sloping downward.
            2. RSI > 75 and bearish divergence with prior swing high.
            3. Pin bar or engulfing candle rejects fib zone with large upper wick.
            4. Follow-up bearish candle breaks below fib zone.
            5. Demand zone must be far (>30 pips) or broken.
            """,

                "GBP/JPY": """
            ✅ Long Trade (Buy):
            1. EMA 50 > EMA 200, both with strong upward slope.
            2. Fib zone (0.5 or 0.618) touched with RSI < 30 + spike in ATR.
            3. Strong bullish candle with large body and high volume.
            4. No major resistance within 35 pips.
            5. Second bullish candle confirms continuation.

            🔻 Short Trade (Sell):
            1. EMA 50 < EMA 200 and both falling quickly.
            2. Price rejects fib zone with large upper wick and RSI > 70.
            3. High-volume bearish engulfing or breakdown candle.
            4. Clean close below support with no recent bounce levels in 30+ pips.
            5. RSI momentum down + ATR rising.
            """,

                "EUR/GBP": """
            ✅ Long Trade (Buy):
            1. EMA 50 > EMA 200 (slight slope acceptable if RSI and divergence align).
            2. RSI < 30 with hidden bullish divergence.
            3. Candle structure: 2–3 small bullish candles forming a base, then a breakout.
            4. Tick volume rising with breakout candle > prior highs.
            5. Resistance clearly broken and not retested in last 25 bars.

            🔻 Short Trade (Sell):
            1. EMA 50 < EMA 200 (any slope).
            2. RSI > 70 and bearish divergence against price.
            3. 2–3 small candles with lower highs, followed by a large bearish candle.
            4. Volume increasing throughout candle sequence, then breakout.
            5. Support zone clearly broken and momentum confirmed.
            """
            }


        return strategies.get(pair, "No strategy defined for this pair.")


    
