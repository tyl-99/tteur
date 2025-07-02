import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class GBPJPYSupplyDemandStrategy:
    """
    Enhanced Supply and Demand strategy for GBP/JPY with comprehensive volume analysis.

    Features:
    1. Volume-confirmed supply/demand zones
    2. Volume spike detection for strong moves
    3. Volume profile analysis (above/below average)
    4. Volume divergence detection
    5. Volume breakout confirmation
    6. Dynamic volume-weighted zone strength
    7. GBP/JPY-specific volatility and volume characteristics
    """

    def __init__(self, target_pair="GBP/JPY"):
        self.target_pair = target_pair
        
        # Zone Detection Parameters (GBP/JPY is highly volatile)
        self.zone_lookback = 300
        self.base_max_candles = 4        # Shorter bases for volatile pair
        self.move_min_ratio = 1.6        # Lower for high volatility
        self.zone_width_max_pips = 50    # Much wider zones for GBP/JPY
        self.pip_size = 0.01             # JPY pip size
        
        # Volume Analysis Parameters
        self.volume_sma_period = 20           # Period for volume moving average
        self.volume_spike_threshold = 1.3     # Even lower threshold for GBP/JPY
        self.high_volume_threshold = 1.7      # 1.7x average = high volume
        self.volume_confirmation_weight = 0.35 # Higher weight for such volatile pair
        self.min_volume_strength = 0.5        # Lower requirement due to volatility
        
        # Internal State
        self.zones = []
        self.last_candle_index = -1
        self.volume_sma = []

    def _calculate_volume_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume-related metrics for the dataframe"""
        df = df.copy()
        
        # Calculate volume SMA
        df['volume_sma'] = df['volume'].rolling(window=self.volume_sma_period, min_periods=1).mean()
        
        # Volume ratio (current volume / average volume)
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Volume spikes (volume significantly above average)
        df['volume_spike'] = df['volume_ratio'] >= self.volume_spike_threshold
        df['high_volume'] = df['volume_ratio'] >= self.high_volume_threshold
        
        # Volume trend (increasing/decreasing volume over last 3 candles)
        df['volume_trend'] = df['volume'].rolling(3).apply(
            lambda x: 1 if x.iloc[-1] > x.iloc[0] else (-1 if x.iloc[-1] < x.iloc[0] else 0)
        )
        
        # Price-Volume relationship
        df['price_change'] = df['close'] - df['open']
        df['price_volume_correlation'] = np.where(
            (df['price_change'] > 0) & (df['volume_ratio'] > 1.1), 1,  # Bullish with volume
            np.where((df['price_change'] < 0) & (df['volume_ratio'] > 1.1), -1, 0)  # Bearish with volume
        )
        
        # GBP/JPY-specific volume analysis
        df['gbpjpy_volatility_adjusted_volume'] = df['volume_ratio'] * (df['high'] - df['low']) / df['close']
        df['gbpjpy_volume_strength'] = np.where(
            df['volume_ratio'] > 1.5, 'strong',
            np.where(df['volume_ratio'] > 1.2, 'medium', 'weak')
        )
        
        return df

    def _calculate_zone_volume_strength(self, df: pd.DataFrame, base_start: int, base_end: int, impulse_idx: int) -> float:
        """Calculate volume strength score for a potential zone"""
        
        if impulse_idx >= len(df) or base_start < 0:
            return 0.0
            
        base_candles = df.iloc[base_start:base_end]
        impulse_candle = df.iloc[impulse_idx]
        
        # 1. Impulse candle volume strength (35% weight)
        impulse_volume_score = min(impulse_candle['volume_ratio'] / self.high_volume_threshold, 1.0) * 0.35
        
        # 2. Volume spike confirmation (25% weight)
        volume_spike_score = 0.25 if impulse_candle['volume_spike'] else 0.0
        
        # 3. Base volume characteristics (20% weight)
        base_avg_volume_ratio = base_candles['volume_ratio'].mean()
        base_volume_score = 0.2 if base_avg_volume_ratio < 1.0 else 0.1  # Prefer low volume bases
        
        # 4. Volatility-adjusted volume (20% weight - unique to GBP/JPY)
        volatility_adj_score = min(impulse_candle['gbpjpy_volatility_adjusted_volume'] * 10, 0.2)
        
        total_score = impulse_volume_score + volume_spike_score + base_volume_score + volatility_adj_score
        return min(total_score, 1.0)

    def _is_strong_move_with_volume(self, base_candles: pd.DataFrame, impulse_candle: pd.Series) -> bool:
        """Check if the move away from base is strong with volume confirmation"""
        
        # Price movement check (adjusted for GBP/JPY volatility)
        move_size = abs(impulse_candle['close'] - base_candles['open'].iloc[0])
        avg_body_size = base_candles['body_size'].mean()
        price_strength = move_size > avg_body_size * self.move_min_ratio
        
        # Volume confirmation check (lower threshold for GBP/JPY)
        volume_confirmation = impulse_candle['volume_ratio'] >= self.volume_spike_threshold
        
        return price_strength and volume_confirmation

    def _find_zones(self, df: pd.DataFrame):
        """Enhanced zone finding with volume analysis"""
        self.zones = []
        
        # Calculate volume metrics
        df_enhanced = self._calculate_volume_metrics(df)
        df_enhanced['body_size'] = abs(df_enhanced['open'] - df_enhanced['close'])
        df_enhanced['candle_range'] = df_enhanced['high'] - df_enhanced['low']

        i = max(self.base_max_candles, self.volume_sma_period)
        while i < len(df_enhanced) - 1:
            best_zone = None
            best_volume_strength = 0
            
            for base_len in range(1, self.base_max_candles + 1):
                base_start = i - base_len
                base_candles = df_enhanced.iloc[base_start:i]
                impulse_candle = df_enhanced.iloc[i]
                
                # Check if it's a strong move with volume
                if not self._is_strong_move_with_volume(base_candles, impulse_candle):
                    continue
                
                # Calculate volume strength
                volume_strength = self._calculate_zone_volume_strength(
                    df_enhanced, base_start, i, i
                )
                
                if volume_strength < self.min_volume_strength:
                    continue
                    
                base_high = base_candles['high'].max()
                base_low = base_candles['low'].min()
                zone_width_pips = (base_high - base_low) / self.pip_size

                if 0 < zone_width_pips < self.zone_width_max_pips:
                    zone_type = None
                    if impulse_candle['close'] > base_high:
                        zone_type = 'demand'
                    elif impulse_candle['close'] < base_low:
                        zone_type = 'supply'
                    
                    if zone_type and volume_strength > best_volume_strength:
                        best_volume_strength = volume_strength
                        best_zone = {
                            'type': zone_type,
                            'price_high': base_high,
                            'price_low': base_low,
                            'created_at': i,
                            'is_fresh': True,
                            'volume_strength': volume_strength,
                            'impulse_volume_ratio': impulse_candle['volume_ratio'],
                            'zone_quality': 'high' if volume_strength > 0.7 else 'medium',
                            'gbpjpy_volume_strength': impulse_candle['gbpjpy_volume_strength'],
                            'volatility_adjusted_volume': impulse_candle['gbpjpy_volatility_adjusted_volume']
                        }
            
            if best_zone:
                self.zones.append(best_zone)
                i += 1
            else:
                i += 1
        
        # Remove overlapping zones, keeping highest volume strength
        if self.zones:
            self.zones = sorted(self.zones, key=lambda x: x['volume_strength'], reverse=True)
            unique_zones = []
            seen_ranges = []
            
            for zone in self.zones:
                is_overlap = False
                for seen_high, seen_low in seen_ranges:
                    if not (zone['price_high'] < seen_low or zone['price_low'] > seen_high):
                        is_overlap = True
                        break
                if not is_overlap:
                    unique_zones.append(zone)
                    seen_ranges.append((zone['price_high'], zone['price_low']))
            
            self.zones = unique_zones

    def _find_technical_take_profit(self, df: pd.DataFrame, current_price: float, trade_direction: str, current_idx: int) -> Dict[str, Any]:
        """Find technically sound take profit levels based on market structure"""
        
        # Look back at significant highs and lows
        lookback_period = min(200, len(df) - 50)  # Look back up to 200 candles
        historical_data = df.iloc[current_idx-lookback_period:current_idx]
        
        if len(historical_data) < 50:
            # Fallback to simple calculation if not enough data
            fallback_pips = 80 if trade_direction == "BUY" else -80  # Wider for GBP/JPY volatility
            return {
                'tp_price': current_price + (fallback_pips * self.pip_size),
                'tp_pips': abs(fallback_pips),
                'tp_reason': 'Insufficient data - fallback TP',
                'confidence': 'low'
            }
        
        # Find significant swing points (local highs/lows)
        swing_highs = []
        swing_lows = []
        
        # Simple swing point detection (look for peaks and valleys)
        for i in range(10, len(historical_data) - 10):
            candle = historical_data.iloc[i]
            
            # Check for swing high (higher than surrounding candles)
            if (candle['high'] > historical_data.iloc[i-5:i+5]['high'].max() * 0.999 and
                candle['high'] > current_price):
                swing_highs.append({
                    'price': candle['high'],
                    'distance_pips': abs(candle['high'] - current_price) / self.pip_size,
                    'index': i
                })
            
            # Check for swing low (lower than surrounding candles)
            if (candle['low'] < historical_data.iloc[i-5:i+5]['low'].min() * 1.001 and
                candle['low'] < current_price):
                swing_lows.append({
                    'price': candle['low'],
                    'distance_pips': abs(candle['low'] - current_price) / self.pip_size,
                    'index': i
                })
        
        # Sort by distance from current price
        swing_highs.sort(key=lambda x: x['distance_pips'])
        swing_lows.sort(key=lambda x: x['distance_pips'])
        
        if trade_direction == "BUY":
            # For BUY trades, target nearest significant resistance (swing high) - NO distance limit
            targets = [h for h in swing_highs if h['price'] > current_price]
            if targets:
                target = targets[0]  # Closest significant high
                return {
                    'tp_price': target['price'] - (4 * self.pip_size),  # Place slightly below resistance (wider for GBP/JPY)
                    'tp_pips': (target['price'] - current_price) / self.pip_size - 4,
                    'tp_reason': f'Previous swing high at {target["price"]:.3f}',
                    'confidence': 'high'
                }
        else:  # SELL trades
            # For SELL trades, target nearest significant support (swing low) - NO distance limit
            targets = [l for l in swing_lows if l['price'] < current_price]
            if targets:
                target = targets[0]  # Closest significant low
                return {
                    'tp_price': target['price'] + (4 * self.pip_size),  # Place slightly above support (wider for GBP/JPY)
                    'tp_pips': (current_price - target['price']) / self.pip_size - 4,
                    'tp_reason': f'Previous swing low at {target["price"]:.3f}',
                    'confidence': 'high'
                }
        
        # Fallback: Use ATR-based target if no swing points found
        recent_data = historical_data.tail(20)
        atr = (recent_data['high'] - recent_data['low']).mean()
        atr_pips = atr / self.pip_size
        target_pips = max(30, min(150, atr_pips * 2))  # 2x ATR, capped between 30-150 pips for GBP/JPY
        
        if trade_direction == "BUY":
            tp_price = current_price + (target_pips * self.pip_size)
        else:
            tp_price = current_price - (target_pips * self.pip_size)
            
        return {
            'tp_price': tp_price,
            'tp_pips': target_pips,
            'tp_reason': f'ATR-based target ({atr_pips:.1f} pips ATR)',
            'confidence': 'medium'
        }

    def _check_volume_breakout_confirmation(self, df: pd.DataFrame, current_idx: int, zone: Dict[str, Any]) -> Dict[str, Any]:
        """Check for volume confirmation on zone entry - different logic for BUY vs SELL"""
        
        if current_idx < self.volume_sma_period:
            return {'confirmed': False, 'volume_ratio': 0, 'volume_trend': 'neutral', 'direction': 'none'}
        
        df_enhanced = self._calculate_volume_metrics(df)
        current_candle = df_enhanced.iloc[current_idx]
        
        # Candle direction analysis
        is_bullish_candle = current_candle['close'] > current_candle['open']
        is_bearish_candle = current_candle['close'] < current_candle['open']
        
        # Base volume requirement (adjusted for GBP/JPY)
        volume_above_threshold = current_candle['volume_ratio'] >= self.volume_spike_threshold
        
        # Direction-specific volume confirmation
        if zone['type'] == 'demand':  # BUY trade
            # Need bullish volume confirmation
            directional_confirmation = (
                is_bullish_candle and  # Must be green candle
                current_candle['price_volume_correlation'] >= 0  # Bullish price-volume
            )
            confirmation_type = 'bullish_volume'
        else:  # zone['type'] == 'supply' - SELL trade
            # Need bearish volume confirmation  
            directional_confirmation = (
                is_bearish_candle and  # Must be red candle
                current_candle['price_volume_correlation'] <= 0  # Bearish price-volume
            )
            confirmation_type = 'bearish_volume'
        
        # Final confirmation requires both volume spike AND directional confirmation
        volume_confirmed = volume_above_threshold and directional_confirmation
        
        # Volume trend analysis
        recent_volume_trend = df_enhanced['volume_trend'].iloc[current_idx-2:current_idx+1].mean()
        if recent_volume_trend > 0.3:
            trend_direction = 'increasing'
        elif recent_volume_trend < -0.3:
            trend_direction = 'decreasing'
        else:
            trend_direction = 'neutral'
        
        return {
            'confirmed': volume_confirmed,
            'volume_ratio': current_candle['volume_ratio'],
            'volume_trend': trend_direction,
            'volume_spike': bool(current_candle['volume_spike']),
            'candle_direction': 'bullish' if is_bullish_candle else 'bearish',
            'directional_confirmation': directional_confirmation,
            'confirmation_type': confirmation_type,
            'price_volume_correlation': current_candle['price_volume_correlation'],
            'gbpjpy_volume_strength': current_candle['gbpjpy_volume_strength'],
            'volatility_adjusted_volume': current_candle['gbpjpy_volatility_adjusted_volume']
        }

    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Dict[str, Any]:
        """Enhanced trade signal analysis with volume confirmation"""
        current_candle_index = len(df) - 1
        
        # Recalculate zones if new candle
        if self.last_candle_index != current_candle_index:
            lookback_df = df.iloc[-self.zone_lookback:].copy()
            self._find_zones(lookback_df)
            self.last_candle_index = current_candle_index

        current_price = df['close'].iloc[-1]
        
        for zone in self.zones:
            if not zone['is_fresh']:
                continue

            # Check for entry
            in_supply_zone = (zone['type'] == 'supply' and 
                            zone['price_low'] <= current_price <= zone['price_high'])
            in_demand_zone = (zone['type'] == 'demand' and 
                            zone['price_low'] <= current_price <= zone['price_high'])
            
            if in_supply_zone or in_demand_zone:
                # Get volume confirmation
                volume_analysis = self._check_volume_breakout_confirmation(
                    df, current_candle_index, zone
                )
                
                # Only trade if volume confirms the move
                if not volume_analysis['confirmed']:
                    continue
                
                zone['is_fresh'] = False  # Mark as tested
                
                # Step 1: Determine trade direction
                if in_supply_zone:
                    decision = "SELL" 
                else:  # in_demand_zone
                    decision = "BUY"
                
                # Step 2: Find technical TP level first
                tp_analysis = self._find_technical_take_profit(df, current_price, decision, current_candle_index)
                tp = tp_analysis['tp_price']
                potential_reward_pips = tp_analysis['tp_pips']
                
                # Step 3: Calculate SL to achieve 1:5 R:R (or best possible)
                zone_quality_multiplier = 0.6 if zone['volume_strength'] > 0.8 else 0.9 if zone['volume_strength'] > 0.6 else 1.0
                min_sl_buffer = 3 * self.pip_size * zone_quality_multiplier  # Minimum buffer beyond zone
                
                # Calculate what SL would give us 1:5 R:R
                target_risk_pips = potential_reward_pips / 5  # Target 1:5 R:R
                
                if decision == "SELL":
                    # Zone invalidation level (absolute maximum SL)
                    max_sl = zone['price_high'] + min_sl_buffer
                    # Ideal SL for 1:5 R:R
                    ideal_sl = current_price + (target_risk_pips * self.pip_size)
                    # Use the tighter (better) of the two
                    sl = min(ideal_sl, max_sl)
                else:  # BUY
                    # Zone invalidation level (absolute maximum SL)
                    max_sl = zone['price_low'] - min_sl_buffer
                    # Ideal SL for 1:5 R:R
                    ideal_sl = current_price - (target_risk_pips * self.pip_size)
                    # Use the tighter (better) of the two
                    sl = max(ideal_sl, max_sl)
                
                # Calculate actual risk and reward
                if decision == "SELL":
                    risk_pips = (sl - current_price) / self.pip_size
                    reward_pips = (current_price - tp) / self.pip_size
                else:  # BUY
                    risk_pips = (current_price - sl) / self.pip_size
                    reward_pips = (tp - current_price) / self.pip_size
                
                # Skip trade if R:R is impossibly poor (less than 1:1)
                if reward_pips <= 0 or risk_pips <= 0 or reward_pips / risk_pips < 1.0:
                    continue

                # Calculate position size based on $30 USD risk
                risk_amount_usd = 30.0
                # For JPY pairs, pip value = $10 * (USD/JPY rate / 100) per lot
                # Using approximate USD/JPY rate of 150 for calculation
                pip_value_usd = 10.0 * (150 / 100)  # Approximately $15 per pip per lot
                position_size = risk_amount_usd / (risk_pips * pip_value_usd)
                adjusted_volume = max(0.01, min(1.0, position_size))  # Min 0.01, Max 1.0 lots
                
                return {
                    "decision": decision,
                    "entry_price": current_price,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "volume": round(adjusted_volume, 2),
                    "volume_calculation": f"Risk: ${risk_amount_usd} ÷ ({risk_pips:.1f} pips × ${pip_value_usd}) = {adjusted_volume:.2f} lots",
                    "meta": {
                        "zone_type": zone['type'],
                        "zone_high": zone['price_high'],
                        "zone_low": zone['price_low'],
                        "volume_strength": zone['volume_strength'],
                        "zone_quality": zone['zone_quality'],
                        "volume_confirmation": volume_analysis,
                        "confidence_level": "high" if zone['volume_strength'] > 0.7 else "medium",
                        "gbpjpy_volume_strength": zone.get('gbpjpy_volume_strength', 'medium'),
                        "volatility_adjusted": True,
                        "tp_analysis": tp_analysis,
                        "risk_pips": round(risk_pips, 1),
                        "reward_pips": round(reward_pips, 1),
                        "target_rr": "1:5",
                        "achieved_rr": f"1:{reward_pips/risk_pips:.1f}",
                        "sl_type": "1:5 R:R target" if sl == (current_price + target_risk_pips * self.pip_size if decision == "SELL" else current_price - target_risk_pips * self.pip_size) else "Zone constraint",
                        "zone_quality_multiplier": zone_quality_multiplier
                    }
                }
                
        return {"decision": "NO TRADE"}

    def get_volume_analysis_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive volume analysis summary"""
        df_enhanced = self._calculate_volume_metrics(df)
        
        recent_data = df_enhanced.tail(20)  # Last 20 candles
        
        return {
            'current_volume_ratio': df_enhanced['volume_ratio'].iloc[-1],
            'avg_volume_ratio_20': recent_data['volume_ratio'].mean(),
            'volume_spikes_recent': int(recent_data['volume_spike'].sum()),
            'volume_trend': 'increasing' if recent_data['volume_trend'].mean() > 0 else 'decreasing',
            'high_volume_candles': int(recent_data['high_volume'].sum()),
            'price_volume_correlation': recent_data['price_volume_correlation'].mean(),
            'gbpjpy_volume_profile': recent_data['gbpjpy_volume_strength'].mode().iloc[0] if len(recent_data) > 0 else 'medium',
            'avg_volatility_adjusted_volume': recent_data['gbpjpy_volatility_adjusted_volume'].mean()
        } 