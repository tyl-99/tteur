import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import datetime
import sys
import os
# import requests
# from dotenv import load_dotenv

# Ensure the news directory is importable for Gemini post-processing
# sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'news'))

# Load environment variables
# load_dotenv()


class EURUSDSTRATEGY:
    """
    Market Structure Break with Supply/Demand Retest Strategy for EUR/USD (30m)

    Core (unchanged in spirit):
      1) Detect Market Structure Break (MSB): HH for bullish or LL for bearish
      2) Identify the base zone before the impulse (demand for bullish, supply for bearish)
      3) Wait for price to retrace into the zone within a Fibonacci band (default 38.2%–61.8%)
      4) Require 1-candle confirmation (engulfing or V-shaped / shooting-star type)
      5) Risk management with SL beyond zone & TP by fixed R:R (default 1:3)

    What’s improved (without changing the core):
      • Correct indexing for zone “freshness” checks (previous bug with local vs global index).
      • More realistic Fib band by default (0.382–0.618) + require price to be inside the zone.
      • Slightly stricter impulse definition for cleaner zones (still moderate to keep frequency).
      • Sensible session-hours filter ON by default (London/NY).
      • Optional volatility (ATR) filter added (OFF by default; core unchanged if you don’t use it).
      • Safer math guards and messages.

    Parameters you’ll likely tune later (kept simple here):
      - min_structure_move_pips: 6 (keeps frequency reasonable)
      - Fib band: 38.2%–61.8%, enforced inside the zone
      - Confirmation body pct: 0.40 (solid)
      - SL bounds: 22–28 pips (keep 1:3 attainable intraday)
      - Session filter: ON by default for quality
      - News sentiment filter: OFF by default (turn on near events if you want)
    """

    def __init__(self, target_pair="EUR/USD",
                 # Lookback / structure
                 lookback_period=120,
                 min_structure_move_pips=6,
                 swing_point_lookback=2,               # ↑ (was 1) smoother swing points
                 min_candles_between_swing_points=2,   # ↑ (was 1) reduces noise
                 min_swing_point_pips_diff=0,          # keep off unless needed

                 # Fibonacci
                 fib_tolerance=0.28,  # retained for compatibility (not used directly)
                 fib_level_lower_bound=0.382,          # tightened band
                 fib_level_upper_bound=0.618,          # tightened band
                 use_is_in_zone_filter_for_fib=True,   # require price to be in the zone

                 # Zone validation
                 min_zone_size_pips=1,
                 max_zone_size_pips=25,
                 max_base_candles_in_zone=2,           # ↑ allows more valid bases
                 use_max_base_candle_range_filter=True,
                 max_base_candle_range_multiplier=0.5,
                 max_base_candle_wick_pct=1.0,         # allow any by default

                 # Impulse quality (moderately stricter than before)
                 min_impulse_pips_factor=0.5,          # ↑ fraction of min_structure_move_pips
                 min_impulse_candle_range_pips=3,      # ↑ avoid tiny impulses
                 min_impulse_body_to_range_ratio=0.35, # ↑ prefer bodies not all wick

                 # Confirmation
                 min_confirmation_body_pct=0.40,
                 enable_bullish_engulfing=True,
                 enable_v_shaped_reversal=True,
                 v_shaped_lower_wick_ratio=0.05,
                 enable_bearish_engulfing=True,
                 enable_shooting_star=True,
                 shooting_star_upper_wick_ratio=0.05,

                 # Risk Management
                 sl_buffer_pips=5,
                 rr_ratio=3.0,               # default 1:3 as requested
                 sl_min_pips=22,
                 sl_max_pips=28,
                 max_bars_in_trade=6,
                 risk_per_trade=0.0035,
                 default_volume=0.01,        # will be used if sizing isn’t integrated

                 # Filters
                 session_hours_utc: Optional[List[str]] = ("07:00-11:00", "13:30-16:00"),
                 enable_session_hours_filter: bool = True,     # ON by default for EUR/USD quality
                 enable_zone_freshness_check: bool = True,     # ON by default boosts win rate
                 # enable_news_sentiment_filter: bool = False,   # OFF by default for speed
                 enable_volatility_filter: bool = False,       # optional; OFF by default
                 atr_period: int = 14,
                 min_atr_pips: float = 3.0,                    # if vol filter on, avoid dead markets
                 profile: Optional[str] = None
                 ):
        # Pair / pip size
        self.target_pair = target_pair
        self.pip_size = 0.0001

        # Structure
        self.lookback_period = lookback_period
        self.min_structure_move_pips = min_structure_move_pips
        self.swing_point_lookback = swing_point_lookback
        self.min_candles_between_swing_points = min_candles_between_swing_points
        self.min_swing_point_pips_diff = min_swing_point_pips_diff

        # Fibonacci
        self.fib_tolerance = fib_tolerance
        self.fib_level_lower_bound = fib_level_lower_bound
        self.fib_level_upper_bound = fib_level_upper_bound
        self.use_is_in_zone_filter_for_fib = use_is_in_zone_filter_for_fib

        # Zone validation
        self.min_zone_size_pips = min_zone_size_pips
        self.max_zone_size_pips = max_zone_size_pips
        self.max_base_candles_in_zone = max_base_candles_in_zone
        self.use_max_base_candle_range_filter = use_max_base_candle_range_filter
        self.max_base_candle_range_multiplier = max_base_candle_range_multiplier
        self.max_base_candle_wick_pct = max_base_candle_wick_pct

        # Impulse quality
        self.min_impulse_pips_factor = min_impulse_pips_factor
        self.min_impulse_candle_range_pips = min_impulse_candle_range_pips
        self.min_impulse_body_to_range_ratio = min_impulse_body_to_range_ratio

        # Confirmation
        self.min_confirmation_body_pct = min_confirmation_body_pct
        self.enable_bullish_engulfing = enable_bullish_engulfing
        self.enable_v_shaped_reversal = enable_v_shaped_reversal
        self.v_shaped_lower_wick_ratio = v_shaped_lower_wick_ratio
        self.enable_bearish_engulfing = enable_bearish_engulfing
        self.enable_shooting_star = enable_shooting_star
        self.shooting_star_upper_wick_ratio = shooting_star_upper_wick_ratio

        # Risk
        self.sl_buffer_pips = sl_buffer_pips
        self.rr_ratio = rr_ratio
        self.sl_min_pips = sl_min_pips
        self.sl_max_pips = sl_max_pips
        self.max_bars_in_trade = max_bars_in_trade
        self.risk_per_trade = risk_per_trade
        self.default_volume = default_volume

        # Filters
        self.session_hours_utc = list(session_hours_utc) if session_hours_utc else ["07:00-11:00", "13:30-16:00"]
        self.enable_session_hours_filter = enable_session_hours_filter
        self.enable_zone_freshness_check = enable_zone_freshness_check
        # self.enable_news_sentiment_filter = enable_news_sentiment_filter
        self.enable_volatility_filter = enable_volatility_filter
        self.atr_period = atr_period
        self.min_atr_pips = min_atr_pips

        # Optional profiles to quickly adjust signal frequency without changing core logic
        if isinstance(profile, str) and profile.lower() == "loose":
            # Expand Fibonacci band and do not require price strictly inside the zone
            self.fib_level_lower_bound = 0.236
            self.fib_level_upper_bound = 0.786
            self.use_is_in_zone_filter_for_fib = False

            # Loosen confirmation thresholds
            self.min_confirmation_body_pct = 0.25

            # Allow smaller/softer impulses to qualify
            self.min_impulse_pips_factor = 0.25
            self.min_impulse_candle_range_pips = 1.5
            self.min_impulse_body_to_range_ratio = 0.20

            # Slightly easier structure and zones
            self.min_structure_move_pips = min(self.min_structure_move_pips, 4)
            self.max_base_candles_in_zone = max(self.max_base_candles_in_zone, 3)
            self.max_zone_size_pips = max(self.max_zone_size_pips, 30)

            # Remove timing and freshness constraints to increase frequency
            self.enable_session_hours_filter = False
            self.enable_zone_freshness_check = False

    # =========================
    # Utilities / Filters
    # =========================
    def _is_within_trading_hours(self, current_datetime: pd.Timestamp) -> bool:
        """Check if the current time falls within defined trading session hours (UTC)."""
        if not self.enable_session_hours_filter or not self.session_hours_utc:
            return True

        hhmm = current_datetime.strftime("%H:%M")
        for session in self.session_hours_utc:
            start_str, end_str = session.split("-")
            if start_str <= hhmm <= end_str:
                return True
        return False

    def _atr_pips(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """Compute ATR in pips; return None if not enough data."""
        if len(df) < period + 1:
            return None
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]

        tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
        atr = pd.Series(tr).rolling(window=period).mean().iloc[-1]
        if pd.isna(atr):
            return None
        return float(atr / self.pip_size)

    def _calculate_fibonacci_levels(self, high_price: float, low_price: float, direction: str) -> Dict[str, float]:
        """Calculate Fib retracement levels for readability (not strictly required for the band test)."""
        price_range = high_price - low_price
        if direction == "bullish":
            return {
                "0%": high_price,
                "23.6%": high_price - (price_range * 0.236),
                "38.2%": high_price - (price_range * 0.382),
                "50%": high_price - (price_range * 0.5),
                "61.8%": high_price - (price_range * 0.618),
                "100%": low_price
            }
        else:
            return {
                "0%": low_price,
                "23.6%": low_price + (price_range * 0.236),
                "38.2%": low_price + (price_range * 0.382),
                "50%": low_price + (price_range * 0.5),
                "61.8%": low_price + (price_range * 0.618),
                "100%": high_price
            }

    # =========================
    # Structure & Zones
    # =========================
    def _identify_market_structure_break(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Identify market structure breaks (HH for bullish, LL for bearish)."""
        if len(df) < self.lookback_period:
            return None

        recent_data = df.iloc[-self.lookback_period:].copy().reset_index(drop=True)
        base_offset = len(df) - self.lookback_period  # map recent_data index -> global df index

        # Find local highs and lows
        highs, lows = [], []
        for i in range(self.swing_point_lookback, len(recent_data) - self.swing_point_lookback):
            window_prev = recent_data.iloc[i - self.swing_point_lookback:i]
            window_next = recent_data.iloc[i + 1:i + 1 + self.swing_point_lookback]

            is_swing_high = (recent_data.iloc[i]['high'] >= window_prev['high'].max() and
                             recent_data.iloc[i]['high'] >= window_next['high'].max())
            is_swing_low = (recent_data.iloc[i]['low'] <= window_prev['low'].min() and
                            recent_data.iloc[i]['low'] <= window_next['low'].min())

            if is_swing_high:
                highs.append({'index': i, 'price': recent_data.iloc[i]['high']})
            if is_swing_low:
                lows.append({'index': i, 'price': recent_data.iloc[i]['low']})

        if len(highs) < 2 and len(lows) < 2:
            return None

        # (Optional) filter swings further if min_swing_point_pips_diff > 0
        def _filter_swings(swings: List[Dict[str, Any]], is_high: bool) -> List[Dict[str, Any]]:
            if self.min_swing_point_pips_diff <= 0:
                return swings
            filt = []
            for s in swings:
                left = max(0, s['index'] - self.min_candles_between_swing_points)
                right = s['index']
                seg = recent_data.iloc[left:right]
                if seg.empty:
                    continue
                if is_high:
                    cond_price = seg['low'].min() + self.min_swing_point_pips_diff * self.pip_size
                    if s['price'] > cond_price:
                        filt.append(s)
                else:
                    cond_price = seg['high'].max() - self.min_swing_point_pips_diff * self.pip_size
                    if s['price'] < cond_price:
                        filt.append(s)
            return filt

        highs = _filter_swings(highs, is_high=True)
        lows = _filter_swings(lows, is_high=False)

        # Check for Higher High (bullish structure break)
        if len(highs) >= 2:
            latest_high, previous_high = highs[-1], highs[-2]
            if (latest_high['price'] > previous_high['price'] and
                (latest_high['price'] - previous_high['price']) / self.pip_size >= self.min_structure_move_pips):
                demand_zone = self._find_demand_zone(
                    recent_data, previous_high['index'], latest_high['index'], base_offset
                )
                if demand_zone:
                    return {
                        'type': 'bullish_break',
                        'break_high': latest_high['price'],
                        'previous_high': previous_high['price'],
                        'zone': demand_zone,
                        'break_index': latest_high['index'] + base_offset,
                        'creation_price': df.iloc[demand_zone['index']]['close']
                    }

        # Check for Lower Low (bearish structure break)
        if len(lows) >= 2:
            latest_low, previous_low = lows[-1], lows[-2]
            if (latest_low['price'] < previous_low['price'] and
                (previous_low['price'] - latest_low['price']) / self.pip_size >= self.min_structure_move_pips):
                supply_zone = self._find_supply_zone(
                    recent_data, previous_low['index'], latest_low['index'], base_offset
                )
                if supply_zone:
                    return {
                        'type': 'bearish_break',
                        'break_low': latest_low['price'],
                        'previous_low': previous_low['price'],
                        'zone': supply_zone,
                        'break_index': latest_low['index'] + base_offset,
                        'creation_price': df.iloc[supply_zone['index']]['close']
                    }

        return None

    def _find_demand_zone(self, recent_df: pd.DataFrame, start_idx: int, end_idx: int, offset: int) -> Optional[Dict[str, Any]]:
        """Find demand zone (base before bullish impulse) within recent_df; store global index using offset."""
        for i in range(end_idx - 1, start_idx, -1):
            for base_len in range(1, min(self.max_base_candles_in_zone + 1, i - start_idx)):
                base_start = i - base_len
                base_candles = recent_df.iloc[base_start:i]

                if self.use_max_base_candle_range_filter:
                    max_base_range = (self.max_zone_size_pips * self.max_base_candle_range_multiplier) * self.pip_size
                    if not all((c['high'] - c['low']) < max_base_range for _, c in base_candles.iterrows()):
                        continue

                if self.max_base_candle_wick_pct < 1.0:
                    wick_too_large = False
                    for _, c in base_candles.iterrows():
                        total_range = c['high'] - c['low']
                        if total_range <= 0:
                            continue
                        upper_wick = c['high'] - max(c['open'], c['close'])
                        lower_wick = min(c['open'], c['close']) - c['low']
                        if (upper_wick / total_range > self.max_base_candle_wick_pct) or \
                           (lower_wick / total_range > self.max_base_candle_wick_pct):
                            wick_too_large = True
                            break
                    if wick_too_large:
                        continue

                # Impulse validation
                impulse_candle = recent_df.iloc[i]
                base_high = base_candles['high'].max()
                base_low = base_candles['low'].min()

                impulse_strength_pips = (impulse_candle['close'] - base_high) / self.pip_size
                min_required_impulse_pips = self.min_structure_move_pips * self.min_impulse_pips_factor

                impulse_range_pips = (impulse_candle['high'] - impulse_candle['low']) / self.pip_size
                impulse_body = abs(impulse_candle['close'] - impulse_candle['open'])
                impulse_total_range = impulse_candle['high'] - impulse_candle['low']
                body_to_range = (impulse_body / impulse_total_range) if impulse_total_range > 0 else 0

                if (impulse_candle['close'] > base_high and
                    impulse_strength_pips >= min_required_impulse_pips and
                    impulse_range_pips >= self.min_impulse_candle_range_pips and
                    body_to_range >= self.min_impulse_body_to_range_ratio):

                    zone_high = base_high
                    zone_low = base_low
                    zone_size_pips = (zone_high - zone_low) / self.pip_size
                    if self.min_zone_size_pips <= zone_size_pips <= self.max_zone_size_pips:
                        return {
                            'high': zone_high,
                            'low': zone_low,
                            'size_pips': zone_size_pips,
                            'index': offset + i,  # global index in full df
                            'type': 'demand'
                        }
        return None

    def _find_supply_zone(self, recent_df: pd.DataFrame, start_idx: int, end_idx: int, offset: int) -> Optional[Dict[str, Any]]:
        """Find supply zone (base before bearish impulse) within recent_df; store global index using offset."""
        for i in range(end_idx - 1, start_idx, -1):
            for base_len in range(1, min(self.max_base_candles_in_zone + 1, i - start_idx)):
                base_start = i - base_len
                base_candles = recent_df.iloc[base_start:i]

                if self.use_max_base_candle_range_filter:
                    max_base_range = (self.max_zone_size_pips * self.max_base_candle_range_multiplier) * self.pip_size
                    if not all((c['high'] - c['low']) < max_base_range for _, c in base_candles.iterrows()):
                        continue

                if self.max_base_candle_wick_pct < 1.0:
                    wick_too_large = False
                    for _, c in base_candles.iterrows():
                        total_range = c['high'] - c['low']
                        if total_range <= 0:
                            continue
                        upper_wick = c['high'] - max(c['open'], c['close'])
                        lower_wick = min(c['open'], c['close']) - c['low']
                        if (upper_wick / total_range > self.max_base_candle_wick_pct) or \
                           (lower_wick / total_range > self.max_base_candle_wick_pct):
                            wick_too_large = True
                            break
                    if wick_too_large:
                        continue

                impulse_candle = recent_df.iloc[i]
                base_high = base_candles['high'].max()
                base_low = base_candles['low'].min()

                impulse_strength_pips = (base_low - impulse_candle['close']) / self.pip_size
                min_required_impulse_pips = self.min_structure_move_pips * self.min_impulse_pips_factor

                impulse_range_pips = (impulse_candle['high'] - impulse_candle['low']) / self.pip_size
                impulse_body = abs(impulse_candle['close'] - impulse_candle['open'])
                impulse_total_range = impulse_candle['high'] - impulse_candle['low']
                body_to_range = (impulse_body / impulse_total_range) if impulse_total_range > 0 else 0

                if (impulse_candle['close'] < base_low and
                    impulse_strength_pips >= min_required_impulse_pips and
                    impulse_range_pips >= self.min_impulse_candle_range_pips and
                    body_to_range >= self.min_impulse_body_to_range_ratio):

                    zone_high = base_high
                    zone_low = base_low
                    zone_size_pips = (zone_high - zone_low) / self.pip_size
                    if self.min_zone_size_pips <= zone_size_pips <= self.max_zone_size_pips:
                        return {
                            'high': zone_high,
                            'low': zone_low,
                            'size_pips': zone_size_pips,
                            'index': offset + i,  # global index in full df
                            'type': 'supply'
                        }
        return None

    def _is_zone_fresh(self, zone: Dict[str, Any], current_df: pd.DataFrame) -> bool:
        """Check if zone is untested since creation (if enabled)."""
        if not self.enable_zone_freshness_check:
            return True

        zidx = zone['index']
        if zidx >= len(current_df) - 1:
            return True

        check_df = current_df.iloc[zidx + 1:].copy()
        if check_df.empty:
            return True

        if zone['type'] == 'demand':
            # If price traded below zone low at any time after creation → not fresh
            if (check_df['low'] < zone['low']).any():
                return False
        elif zone['type'] == 'supply':
            # If price traded above zone high at any time after creation → not fresh
            if (check_df['high'] > zone['high']).any():
                return False
        return True

    # =========================
    # Entry Filters
    # =========================
    def _check_fibonacci_retracement(self, current_price: float, structure_break: Dict[str, Any]) -> bool:
        """Check if current price lies inside the configurable Fib band (default 38.2–61.8) and, optionally, inside the zone."""
        lb = float(self.fib_level_lower_bound)
        ub = float(self.fib_level_upper_bound)
        lb, ub = min(lb, ub), max(lb, ub)

        if structure_break['type'] == 'bullish_break':
            high_price = structure_break['break_high']
            low_price = structure_break['zone']['low']  # start of impulse
            # For bullish: band is between high - ub*range and high - lb*range
            up_ok = (current_price >= (high_price - (high_price - low_price) * ub)) and \
                    (current_price <= (high_price - (high_price - low_price) * lb))
            if self.use_is_in_zone_filter_for_fib:
                in_zone = structure_break['zone']['low'] <= current_price <= structure_break['zone']['high']
                return up_ok and in_zone
            return up_ok

        elif structure_break['type'] == 'bearish_break':
            low_price = structure_break['break_low']
            high_price = structure_break['zone']['high']  # start of impulse
            # For bearish: band is between low + lb*range and low + ub*range
            down_ok = (current_price <= (low_price + (high_price - low_price) * ub)) and \
                      (current_price >= (low_price + (high_price - low_price) * lb))
            if self.use_is_in_zone_filter_for_fib:
                in_zone = structure_break['zone']['low'] <= current_price <= structure_break['zone']['high']
                return down_ok and in_zone
            return down_ok

        return False

    def _check_confirmation_signal(self, df: pd.DataFrame, trade_type: str) -> bool:
        """Check engulfing / V reversal (BUY) or engulfing / shooting-star (SELL)."""
        if len(df) < 3:
            return False

        c = df.iloc[-1]
        p = df.iloc[-2]
        current_body = abs(c['close'] - c['open'])
        current_total = c['high'] - c['low']
        body_pct = (current_body / current_total) if current_total > 0 else 0

        if trade_type == "BUY":
            if self.enable_bullish_engulfing:
                be = (p['close'] < p['open'] and
                      c['close'] > c['open'] and
                      c['open'] < p['close'] and
                      c['close'] > p['open'] and
                      body_pct >= self.min_confirmation_body_pct)
                if be:
                    return True

            if self.enable_v_shaped_reversal:
                lower_wick = (c['open'] - c['low']) if (c['close'] > c['open']) else (c['close'] - c['low'])
                v = (c['close'] > c['open'] and
                     current_total > 0 and
                     (lower_wick / current_total) >= self.v_shaped_lower_wick_ratio and
                     body_pct >= self.min_confirmation_body_pct)
                if v:
                    return True
            return False

        elif trade_type == "SELL":
            if self.enable_bearish_engulfing:
                be = (p['close'] > p['open'] and
                      c['close'] < c['open'] and
                      c['open'] > p['close'] and
                      c['close'] < p['open'] and
                      body_pct >= self.min_confirmation_body_pct)
                if be:
                    return True

            if self.enable_shooting_star:
                upper_wick = (c['high'] - c['open']) if (c['close'] < c['open']) else (c['high'] - c['close'])
                ss = (c['close'] < c['open'] and
                      current_total > 0 and
                      (upper_wick / current_total) >= self.shooting_star_upper_wick_ratio and
                      body_pct >= self.min_confirmation_body_pct)
                if ss:
                    return True
            return False

        return False

    # =========================
    # Main Signal Logic
    # =========================
    def analyze_trade_signal(self, df: pd.DataFrame, current_index: int, pair: str) -> Dict[str, Any]:
        """
        Analyze and produce trade decision at a given index.

        Expected df columns: ['timestamp','open','high','low','close', ...]
        Timestamp assumed UTC.
        """
        if current_index < 0 or current_index >= len(df):
            return {"decision": "NO TRADE", "reason": "Invalid current_index"}

        current_data = df.iloc[:current_index + 1].copy()
        if len(current_data) < self.lookback_period + 10:
            return {"decision": "NO TRADE", "reason": "Insufficient data"}

        current_price = float(current_data.iloc[-1]['close'])
        current_datetime = current_data.iloc[-1]['timestamp']

        # Session hours filter
        if not self._is_within_trading_hours(current_datetime):
            return {"decision": "NO TRADE", "reason": "Outside of trading hours"}

        # Volatility filter (optional)
        if self.enable_volatility_filter:
            atr_pips = self._atr_pips(current_data, self.atr_period)
            if atr_pips is None or atr_pips < self.min_atr_pips:
                return {"decision": "NO TRADE", "reason": "Low volatility (ATR filter)"}

        # 1) Market structure break
        structure_break = self._identify_market_structure_break(current_data)
        if not structure_break:
            return {"decision": "NO TRADE", "reason": "No valid market structure break found"}

        zone = structure_break['zone']

        # 2) Zone freshness
        if not self._is_zone_fresh(zone, current_data):
            return {"decision": "NO TRADE", "reason": "Zone is no longer fresh"}

        # 3) Fib band test (within zone if configured)
        if not self._check_fibonacci_retracement(current_price, structure_break):
            return {"decision": "NO TRADE", "reason": "Price not in Fib band / zone"}

        # 4) Distance checks (kept permissive; confluence already strong)
        if structure_break['type'] == 'bullish_break':
            distance_to_zone_entry = (current_price - zone['low']) / self.pip_size
            if distance_to_zone_entry < 0 or distance_to_zone_entry > 100:
                return {"decision": "NO TRADE", "reason": "Price not within acceptable distance to demand zone entry"}
        else:
            distance_to_zone_entry = (zone['high'] - current_price) / self.pip_size
            if distance_to_zone_entry < 0 or distance_to_zone_entry > 100:
                return {"decision": "NO TRADE", "reason": "Price not within acceptable distance to supply zone entry"}

        # 5) Confirmation candle
        trade_direction = "BUY" if structure_break['type'] == 'bullish_break' else "SELL"
        if not self._check_confirmation_signal(current_data, trade_direction):
            return {"decision": "NO TRADE", "reason": f"No {trade_direction.lower()} confirmation signal"}

        # 6) Optional news sentiment alignment
        # news_sentiment = "N/A (Filter Disabled)"
        # if self.enable_news_sentiment_filter:
        #     news_sentiment = self._get_news_sentiment(current_datetime)
        #     print(f"📰 News Sentiment: {news_sentiment}")
        #     if trade_direction == "BUY" and news_sentiment == "Bearish":
        #         print("❌ BUY filtered out by bearish news sentiment")
        #         return {"decision": "NO TRADE", "reason": "Buy filtered out by bearish news"}
        #     if trade_direction == "SELL" and news_sentiment == "Bullish":
        #         print("❌ SELL filtered out by bullish news sentiment")
        #         return {"decision": "NO TRADE", "reason": "Sell filtered out by bullish news"}

        # 7) Finalize SL/TP using 1:3 R:R (with SL bounded)
        entry_price = current_price
        if trade_direction == "BUY":
            stop_loss_candidate = zone['low'] - (self.sl_buffer_pips * self.pip_size)
            min_sl_price = entry_price - (self.sl_max_pips * self.pip_size)
            max_sl_price = entry_price - (self.sl_min_pips * self.pip_size)
            stop_loss = max(min_sl_price, min(max_sl_price, stop_loss_candidate))
            risk_pips = max(1e-6, (entry_price - stop_loss) / self.pip_size)
            take_profit = entry_price + (risk_pips * self.rr_ratio * self.pip_size)
            print(f"📈 BUY @ {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}  Price: {entry_price:.5f}")
        else:
            stop_loss_candidate = zone['high'] + (self.sl_buffer_pips * self.pip_size)
            min_sl_price = entry_price + (self.sl_max_pips * self.pip_size)
            max_sl_price = entry_price + (self.sl_min_pips * self.pip_size)
            stop_loss = min(max_sl_price, max(min_sl_price, stop_loss_candidate))
            risk_pips = max(1e-6, (stop_loss - entry_price) / self.pip_size)
            take_profit = entry_price - (risk_pips * self.rr_ratio * self.pip_size)
            print(f"📉 SELL @ {current_datetime.strftime('%Y-%m-%d %H:%M:%S')} Price: {entry_price:.5f}")

        print(f"📊 SL: {stop_loss:.5f} | TP: {take_profit:.5f} | Risk: {risk_pips:.1f} pips | R:R={self.rr_ratio:.1f}")

        return {
            "decision": trade_direction,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "volume": self.default_volume,
            "reason": (
                f"{'Bullish' if trade_direction=='BUY' else 'Bearish'} structure break retest at "
                f"{'demand' if trade_direction=='BUY' else 'supply'} zone within Fib {int(self.fib_level_lower_bound*100)}–{int(self.fib_level_upper_bound*100)} band; "
                f"confirmation present"
            ),
            "meta": {
                "zone_high": zone['high'],
                "zone_low": zone['low'],
                "zone_size_pips": zone['size_pips'],
                "risk_pips": risk_pips,
                "rr_ratio": self.rr_ratio,
                "break_index": structure_break['break_index'],
                "creation_price": structure_break['creation_price'],
                "max_bars_in_trade": self.max_bars_in_trade,
                "risk_per_trade": self.risk_per_trade,
                # "news_sentiment": news_sentiment # Removed as news filter is disabled
            }
        }
