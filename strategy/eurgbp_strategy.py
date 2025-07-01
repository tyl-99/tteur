import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class EURGBPSupplyDemandStrategy:
    """
    Enhanced Supply and Demand strategy for EUR/GBP with comprehensive volume analysis.

    Features:
    1. Volume-confirmed supply/demand zones
    2. Volume spike detection for strong moves
    3. Volume profile analysis (above/below average)
    4. Volume divergence detection
    5. Volume breakout confirmation
    6. Dynamic volume-weighted zone strength
    """

    def __init__(self, target_pair="EUR/GBP"):
        self.target_pair = target_pair
        
        # Zone Detection Parameters
        self.zone_lookback = 300
        self.base_max_candles = 5
        self.move_min_ratio = 2.0
        self.zone_width_max_pips = 30
        self.pip_size = 0.0001
        
        # Volume Analysis Parameters
        self.volume_sma_period = 20           # Period for volume moving average
        self.volume_spike_threshold = 1.5     # Volume must be 1.5x average for spike
        self.high_volume_threshold = 2.0      # 2x average = high volume
        self.volume_confirmation_weight = 0.3 # Weight of volume in zone strength
        self.min_volume_strength = 0.6        # Minimum volume strength for valid zones
        
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
            (df['price_change'] > 0) & (df['volume_ratio'] > 1.2), 1,  # Bullish with volume
            np.where((df['price_change'] < 0) & (df['volume_ratio'] > 1.2), -1, 0)  # Bearish with volume
        )
        
        return df

    def _calculate_zone_volume_strength(self, df: pd.DataFrame, base_start: int, base_end: int, impulse_idx: int) -> float:
        """Calculate volume strength score for a potential zone"""
        
        if impulse_idx >= len(df) or base_start < 0:
            return 0.0
            
        base_candles = df.iloc[base_start:base_end]
        impulse_candle = df.iloc[impulse_idx]
        
        # 1. Impulse candle volume strength (40% weight)
        impulse_volume_score = min(impulse_candle['volume_ratio'] / self.high_volume_threshold, 1.0) * 0.4
        
        # 2. Volume spike confirmation (20% weight)
        volume_spike_score = 0.2 if impulse_candle['volume_spike'] else 0.0
        
        # 3. Base volume characteristics (20% weight)
        base_avg_volume_ratio = base_candles['volume_ratio'].mean()
        base_volume_score = 0.2 if base_avg_volume_ratio < 1.0 else 0.1  # Prefer low volume bases
        
        # 4. Volume trend confirmation (20% weight)
        if len(base_candles) >= 3:
            volume_trend_score = 0.2 if impulse_candle['volume_trend'] == 1 else 0.1
        else:
            volume_trend_score = 0.1
            
        total_score = impulse_volume_score + volume_spike_score + base_volume_score + volume_trend_score
        return min(total_score, 1.0)

    def _is_strong_move_with_volume(self, base_candles: pd.DataFrame, impulse_candle: pd.Series) -> bool:
        """Check if the move away from base is strong with volume confirmation"""
        
        # Price movement check
        move_size = abs(impulse_candle['close'] - base_candles['open'].iloc[0])
        avg_body_size = base_candles['body_size'].mean()
        price_strength = move_size > avg_body_size * self.move_min_ratio
        
        # Volume confirmation check
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
                            'zone_quality': 'high' if volume_strength > 0.8 else 'medium'
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

    def _check_volume_breakout_confirmation(self, df: pd.DataFrame, current_idx: int, zone: Dict[str, Any]) -> Dict[str, Any]:
        """Check for volume confirmation on zone entry"""
        
        if current_idx < self.volume_sma_period:
            return {'confirmed': False, 'volume_ratio': 0, 'volume_trend': 'neutral'}
        
        df_enhanced = self._calculate_volume_metrics(df)
        current_candle = df_enhanced.iloc[current_idx]
        
        # Volume breakout confirmation
        volume_confirmed = current_candle['volume_ratio'] >= self.volume_spike_threshold
        
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
            'volume_spike': bool(current_candle['volume_spike'])
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
                
                if in_supply_zone:
                    decision = "SELL"
                    sl = zone['price_high'] + (2 * self.pip_size)
                    risk_pips = (sl - current_price) / self.pip_size
                    tp = current_price - (risk_pips * 5 * self.pip_size)  # 1:5 R:R
                else:  # in_demand_zone
                    decision = "BUY"
                    sl = zone['price_low'] - (2 * self.pip_size)
                    risk_pips = (current_price - sl) / self.pip_size
                    tp = current_price + (risk_pips * 5 * self.pip_size)  # 1:5 R:R

                # Calculate position size based on $30 USD risk
                risk_amount_usd = 30.0
                # For EUR/GBP, pip value varies with GBP/USD rate (approximately $13 per pip per lot)
                pip_value_usd = 13.0  # Approximate value - can be adjusted based on current GBP/USD
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
                        "confidence_level": "high" if zone['volume_strength'] > 0.8 else "medium"
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
            'price_volume_correlation': recent_data['price_volume_correlation'].mean()
        } 