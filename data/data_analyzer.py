import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class EURUSDDataAnalyzer:
    def __init__(self):
        self.df = None
        self.analysis_results = {}
        
    def load_data(self):
        """Load EUR/USD data from Excel"""
        print("🔍 Loading EUR/USD data...")
        excel_file = pd.ExcelFile('backtest_data/forex_data.xlsx')
        self.df = pd.read_excel(excel_file, sheet_name='EUR_USD')
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        print(f"✅ Loaded {len(self.df):,} bars from {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        
    def analyze_market_structure(self):
        """Analyze the fundamental market structure"""
        print("\n📊 MARKET STRUCTURE ANALYSIS")
        print("=" * 50)
        
        # Basic stats
        total_bars = len(self.df)
        self.df['range'] = self.df['high'] - self.df['low']
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['returns'] = self.df['close'].pct_change()
        
        # Volatility analysis
        daily_volatility = self.df['returns'].std() * 100
        avg_range_pips = (self.df['range'].mean() / 0.0001)
        avg_body_pips = (self.df['body'].mean() / 0.0001)
        
        print(f"Total Bars: {total_bars:,}")
        print(f"Daily Volatility: {daily_volatility:.3f}%")
        print(f"Average Range: {avg_range_pips:.1f} pips")
        print(f"Average Body: {avg_body_pips:.1f} pips")
        
        # Trend analysis with multiple timeframes
        self.df['ema_10'] = self.df['close'].ewm(span=10).mean()
        self.df['ema_20'] = self.df['close'].ewm(span=20).mean()
        self.df['ema_50'] = self.df['close'].ewm(span=50).mean()
        self.df['ema_100'] = self.df['close'].ewm(span=100).mean()
        self.df['ema_200'] = self.df['close'].ewm(span=200).mean()
        
        # Different trend definitions
        strong_uptrend = (self.df['ema_10'] > self.df['ema_20']) & (self.df['ema_20'] > self.df['ema_50']) & (self.df['ema_50'] > self.df['ema_100']) & (self.df['ema_100'] > self.df['ema_200'])
        uptrend = (self.df['ema_20'] > self.df['ema_50']) & (self.df['ema_50'] > self.df['ema_200'])
        downtrend = (self.df['ema_20'] < self.df['ema_50']) & (self.df['ema_50'] < self.df['ema_200'])
        strong_downtrend = (self.df['ema_10'] < self.df['ema_20']) & (self.df['ema_20'] < self.df['ema_50']) & (self.df['ema_50'] < self.df['ema_100']) & (self.df['ema_100'] < self.df['ema_200'])
        
        strong_trend_pct = ((strong_uptrend | strong_downtrend).sum() / total_bars) * 100
        trend_pct = ((uptrend | downtrend).sum() / total_bars) * 100
        ranging_pct = 100 - trend_pct
        
        print(f"Strong Trending: {strong_trend_pct:.1f}%")
        print(f"Trending: {trend_pct:.1f}%")
        print(f"Ranging: {ranging_pct:.1f}%")
        
        self.analysis_results['market_regime'] = 'ranging' if ranging_pct > 40 else 'trending'
        self.analysis_results['volatility'] = 'low' if daily_volatility < 0.08 else 'high'
        
    def test_mean_reversion_patterns(self):
        """Test mean reversion opportunities"""
        print("\n🔄 MEAN REVERSION ANALYSIS")
        print("=" * 50)
        
        # RSI for mean reversion
        self.df['rsi'] = self.calculate_rsi(self.df['close'], 14)
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        self.df['bb_middle'] = self.df['close'].rolling(bb_period).mean()
        bb_std_dev = self.df['close'].rolling(bb_period).std()
        self.df['bb_upper'] = self.df['bb_middle'] + (bb_std_dev * bb_std)
        self.df['bb_lower'] = self.df['bb_middle'] - (bb_std_dev * bb_std)
        
        # Mean reversion signals
        oversold_signals = (self.df['rsi'] < 30) & (self.df['close'] < self.df['bb_lower'])
        overbought_signals = (self.df['rsi'] > 70) & (self.df['close'] > self.df['bb_upper'])
        
        # Test mean reversion success
        reversion_success = []
        for i in range(len(self.df) - 20):
            if oversold_signals.iloc[i]:
                # Check if price goes up in next 10-20 bars
                future_high = self.df['high'].iloc[i+1:i+21].max()
                entry_price = self.df['close'].iloc[i]
                if future_high > entry_price * 1.002:  # 20 pips profit
                    reversion_success.append(True)
                else:
                    reversion_success.append(False)
                    
            elif overbought_signals.iloc[i]:
                # Check if price goes down in next 10-20 bars
                future_low = self.df['low'].iloc[i+1:i+21].min()
                entry_price = self.df['close'].iloc[i]
                if future_low < entry_price * 0.998:  # 20 pips profit
                    reversion_success.append(True)
                else:
                    reversion_success.append(False)
        
        if reversion_success:
            mean_reversion_rate = (sum(reversion_success) / len(reversion_success)) * 100
            print(f"Mean Reversion Success Rate: {mean_reversion_rate:.1f}%")
            print(f"Total Reversion Signals: {len(reversion_success)}")
        else:
            mean_reversion_rate = 0
            print("No clear mean reversion signals found")
            
        self.analysis_results['mean_reversion_rate'] = mean_reversion_rate
        
    def test_momentum_patterns(self):
        """Test momentum/breakout opportunities"""
        print("\n🚀 MOMENTUM ANALYSIS")
        print("=" * 50)
        
        # ATR for volatility
        self.df['atr'] = self.calculate_atr(self.df, 14)
        
        # Momentum indicators
        self.df['macd'], self.df['macd_signal'] = self.calculate_macd(self.df['close'])
        
        # Breakout signals
        lookback = 20
        self.df['resistance'] = self.df['high'].rolling(lookback).max()
        self.df['support'] = self.df['low'].rolling(lookback).min()
        
        breakout_up = self.df['close'] > self.df['resistance'].shift(1)
        breakout_down = self.df['close'] < self.df['support'].shift(1)
        
        # Test breakout success
        breakout_success = []
        for i in range(len(self.df) - 20):
            if breakout_up.iloc[i]:
                # Check if price continues up
                entry_price = self.df['close'].iloc[i]
                future_high = self.df['high'].iloc[i+1:i+21].max()
                if future_high > entry_price * 1.003:  # 30 pips profit
                    breakout_success.append(True)
                else:
                    breakout_success.append(False)
                    
            elif breakout_down.iloc[i]:
                # Check if price continues down
                entry_price = self.df['close'].iloc[i]
                future_low = self.df['low'].iloc[i+1:i+21].min()
                if future_low < entry_price * 0.997:  # 30 pips profit
                    breakout_success.append(True)
                else:
                    breakout_success.append(False)
        
        if breakout_success:
            momentum_rate = (sum(breakout_success) / len(breakout_success)) * 100
            print(f"Breakout Success Rate: {momentum_rate:.1f}%")
            print(f"Total Breakout Signals: {len(breakout_success)}")
        else:
            momentum_rate = 0
            print("No clear breakout signals found")
            
        self.analysis_results['momentum_rate'] = momentum_rate
        
    def test_support_resistance_strategy(self):
        """Test support/resistance bounce strategy"""
        print("\n📈 SUPPORT/RESISTANCE ANALYSIS")
        print("=" * 50)
        
        # Identify key levels
        window = 50
        self.df['pivot_high'] = self.df['high'].rolling(window=window, center=True).max() == self.df['high']
        self.df['pivot_low'] = self.df['low'].rolling(window=window, center=True).min() == self.df['low']
        
        # Find recent support/resistance levels
        recent_highs = self.df[self.df['pivot_high'] == True]['high'].tail(10).values
        recent_lows = self.df[self.df['pivot_low'] == True]['low'].tail(10).values
        
        # Test bounce success
        bounce_success = []
        for i in range(window, len(self.df) - 20):
            current_price = self.df['close'].iloc[i]
            
            # Check if near support (within 10 pips)
            near_support = any(abs(current_price - level) / 0.0001 <= 10 for level in recent_lows)
            # Check if near resistance (within 10 pips)  
            near_resistance = any(abs(current_price - level) / 0.0001 <= 10 for level in recent_highs)
            
            if near_support and self.df['rsi'].iloc[i] < 40:
                # Test bounce up
                future_high = self.df['high'].iloc[i+1:i+21].max()
                if future_high > current_price * 1.002:  # 20 pips profit
                    bounce_success.append(True)
                else:
                    bounce_success.append(False)
                    
            elif near_resistance and self.df['rsi'].iloc[i] > 60:
                # Test bounce down
                future_low = self.df['low'].iloc[i+1:i+21].min()
                if future_low < current_price * 0.998:  # 20 pips profit
                    bounce_success.append(True)
                else:
                    bounce_success.append(False)
        
        if bounce_success:
            sr_bounce_rate = (sum(bounce_success) / len(bounce_success)) * 100
            print(f"S/R Bounce Success Rate: {sr_bounce_rate:.1f}%")
            print(f"Total S/R Signals: {len(bounce_success)}")
        else:
            sr_bounce_rate = 0
            print("No clear S/R bounce signals found")
            
        self.analysis_results['sr_bounce_rate'] = sr_bounce_rate
        
    def test_time_based_patterns(self):
        """Test time-based patterns"""
        print("\n⏰ TIME-BASED ANALYSIS")
        print("=" * 50)
        
        # Add time features
        self.df['hour'] = self.df['timestamp'].dt.hour
        self.df['day_of_week'] = self.df['timestamp'].dt.dayofweek
        
        # Analyze hourly volatility
        hourly_ranges = self.df.groupby('hour')['range'].mean()
        best_hours = hourly_ranges.nlargest(5)
        
        print("Most Volatile Hours (UTC):")
        for hour, avg_range in best_hours.items():
            pips = avg_range / 0.0001
            print(f"  {hour:02d}:00 - {pips:.1f} pips average range")
        
        # Day of week analysis
        daily_ranges = self.df.groupby('day_of_week')['range'].mean()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        print("\nDaily Volatility:")
        for day_num, avg_range in daily_ranges.items():
            if day_num < len(days):
                pips = avg_range / 0.0001
                print(f"  {days[day_num]} - {pips:.1f} pips")
                
        self.analysis_results['best_hours'] = list(best_hours.index)
        
    def test_simple_strategies(self):
        """Test simple, practical strategies"""
        print("\n🎯 SIMPLE STRATEGY TESTING")
        print("=" * 50)
        
        strategies = {
            'RSI_Extreme': self.test_rsi_extreme(),
            'EMA_Cross': self.test_ema_cross(),
            'Bollinger_Squeeze': self.test_bollinger_squeeze(),
            'Range_Trading': self.test_range_trading(),
            'Trend_Following': self.test_trend_following()
        }
        
        # Sort by success rate
        sorted_strategies = sorted(strategies.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        
        print("\n🏆 STRATEGY RANKING:")
        print("-" * 60)
        for i, (name, results) in enumerate(sorted_strategies, 1):
            print(f"{i}. {name:15} | Win Rate: {results['win_rate']:5.1f}% | "
                  f"Trades: {results['total_trades']:3d} | Avg R:R: {results['avg_rr']:4.2f}")
        
        self.analysis_results['best_strategy'] = sorted_strategies[0]
        return sorted_strategies
    
    def test_rsi_extreme(self):
        """Test RSI extreme levels strategy"""
        signals = []
        
        for i in range(50, len(self.df) - 30):
            rsi = self.df['rsi'].iloc[i]
            entry_price = self.df['close'].iloc[i]
            
            if rsi <= 20:  # Extreme oversold
                # Look for exit in next 30 bars
                sl_price = entry_price * 0.9985  # 15 pips SL
                tp_price = entry_price * 1.0045  # 45 pips TP (1:3)
                
                exit_reason, exit_price = self.simulate_trade(i, 'BUY', sl_price, tp_price, 30)
                if exit_reason:
                    pnl = (exit_price - entry_price) / entry_price * 10000  # in pips
                    signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 15 if pnl < 0 else pnl / 15})
                    
            elif rsi >= 80:  # Extreme overbought
                sl_price = entry_price * 1.0015  # 15 pips SL
                tp_price = entry_price * 0.9955  # 45 pips TP (1:3)
                
                exit_reason, exit_price = self.simulate_trade(i, 'SELL', sl_price, tp_price, 30)
                if exit_reason:
                    pnl = (entry_price - exit_price) / entry_price * 10000  # in pips
                    signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 15 if pnl < 0 else pnl / 15})
        
        if signals:
            win_rate = (sum(s['win'] for s in signals) / len(signals)) * 100
            avg_rr = sum(s['rr'] for s in signals) / len(signals)
        else:
            win_rate = 0
            avg_rr = 0
            
        return {'win_rate': win_rate, 'total_trades': len(signals), 'avg_rr': avg_rr}
    
    def test_ema_cross(self):
        """Test EMA crossover strategy"""
        signals = []
        
        for i in range(50, len(self.df) - 30):
            ema_fast = self.df['ema_20'].iloc[i]
            ema_slow = self.df['ema_50'].iloc[i]
            prev_ema_fast = self.df['ema_20'].iloc[i-1]
            prev_ema_slow = self.df['ema_50'].iloc[i-1]
            
            entry_price = self.df['close'].iloc[i]
            
            # Golden cross (bullish)
            if prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow:
                sl_price = entry_price * 0.998   # 20 pips SL
                tp_price = entry_price * 1.006   # 60 pips TP (1:3)
                
                exit_reason, exit_price = self.simulate_trade(i, 'BUY', sl_price, tp_price, 30)
                if exit_reason:
                    pnl = (exit_price - entry_price) / entry_price * 10000
                    signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 20 if pnl < 0 else pnl / 20})
                    
            # Death cross (bearish)
            elif prev_ema_fast >= prev_ema_slow and ema_fast < ema_slow:
                sl_price = entry_price * 1.002   # 20 pips SL
                tp_price = entry_price * 0.994   # 60 pips TP (1:3)
                
                exit_reason, exit_price = self.simulate_trade(i, 'SELL', sl_price, tp_price, 30)
                if exit_reason:
                    pnl = (entry_price - exit_price) / entry_price * 10000
                    signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 20 if pnl < 0 else pnl / 20})
        
        if signals:
            win_rate = (sum(s['win'] for s in signals) / len(signals)) * 100
            avg_rr = sum(s['rr'] for s in signals) / len(signals)
        else:
            win_rate = 0
            avg_rr = 0
            
        return {'win_rate': win_rate, 'total_trades': len(signals), 'avg_rr': avg_rr}
    
    def test_bollinger_squeeze(self):
        """Test Bollinger Band squeeze strategy"""
        signals = []
        
        # Calculate BB width
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / self.df['bb_middle']
        bb_width_ma = self.df['bb_width'].rolling(50).mean()
        
        for i in range(50, len(self.df) - 30):
            current_width = self.df['bb_width'].iloc[i]
            avg_width = bb_width_ma.iloc[i]
            
            # Squeeze condition (low volatility)
            if current_width < avg_width * 0.8:
                entry_price = self.df['close'].iloc[i]
                
                # Wait for breakout in next few bars
                for j in range(i+1, min(i+6, len(self.df))):
                    if self.df['close'].iloc[j] > self.df['bb_upper'].iloc[i]:
                        # Bullish breakout
                        sl_price = entry_price * 0.9985  # 15 pips SL
                        tp_price = entry_price * 1.0045  # 45 pips TP
                        
                        exit_reason, exit_price = self.simulate_trade(j, 'BUY', sl_price, tp_price, 25)
                        if exit_reason:
                            pnl = (exit_price - entry_price) / entry_price * 10000
                            signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 15 if pnl < 0 else pnl / 15})
                        break
                        
                    elif self.df['close'].iloc[j] < self.df['bb_lower'].iloc[i]:
                        # Bearish breakout
                        sl_price = entry_price * 1.0015  # 15 pips SL
                        tp_price = entry_price * 0.9955  # 45 pips TP
                        
                        exit_reason, exit_price = self.simulate_trade(j, 'SELL', sl_price, tp_price, 25)
                        if exit_reason:
                            pnl = (entry_price - exit_price) / entry_price * 10000
                            signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 15 if pnl < 0 else pnl / 15})
                        break
        
        if signals:
            win_rate = (sum(s['win'] for s in signals) / len(signals)) * 100
            avg_rr = sum(s['rr'] for s in signals) / len(signals)
        else:
            win_rate = 0
            avg_rr = 0
            
        return {'win_rate': win_rate, 'total_trades': len(signals), 'avg_rr': avg_rr}
    
    def test_range_trading(self):
        """Test range trading strategy"""
        signals = []
        
        # Identify ranging periods
        for i in range(100, len(self.df) - 30):
            # Check if in range (price oscillating around EMA)
            recent_high = self.df['high'].iloc[i-20:i].max()
            recent_low = self.df['low'].iloc[i-20:i].min()
            range_size = (recent_high - recent_low) / 0.0001  # in pips
            
            # Only trade in moderate ranges (20-80 pips)
            if 20 <= range_size <= 80:
                current_price = self.df['close'].iloc[i]
                mid_range = (recent_high + recent_low) / 2
                
                # Buy near bottom of range
                if current_price <= recent_low + (recent_high - recent_low) * 0.2:
                    sl_price = recent_low - 10 * 0.0001  # 10 pips below range
                    tp_price = recent_high - 5 * 0.0001   # Near top of range
                    
                    exit_reason, exit_price = self.simulate_trade(i, 'BUY', sl_price, tp_price, 30)
                    if exit_reason:
                        pnl = (exit_price - current_price) / current_price * 10000
                        signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 10 if pnl < 0 else pnl / 10})
                        
                # Sell near top of range
                elif current_price >= recent_low + (recent_high - recent_low) * 0.8:
                    sl_price = recent_high + 10 * 0.0001  # 10 pips above range
                    tp_price = recent_low + 5 * 0.0001    # Near bottom of range
                    
                    exit_reason, exit_price = self.simulate_trade(i, 'SELL', sl_price, tp_price, 30)
                    if exit_reason:
                        pnl = (current_price - exit_price) / current_price * 10000
                        signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / 10 if pnl < 0 else pnl / 10})
        
        if signals:
            win_rate = (sum(s['win'] for s in signals) / len(signals)) * 100
            avg_rr = sum(s['rr'] for s in signals) / len(signals)
        else:
            win_rate = 0
            avg_rr = 0
            
        return {'win_rate': win_rate, 'total_trades': len(signals), 'avg_rr': avg_rr}
    
    def test_trend_following(self):
        """Test simple trend following strategy"""
        signals = []
        
        for i in range(100, len(self.df) - 30):
            # Define trend using multiple EMAs
            ema_20 = self.df['ema_20'].iloc[i]
            ema_50 = self.df['ema_50'].iloc[i]
            ema_100 = self.df['ema_100'].iloc[i]
            current_price = self.df['close'].iloc[i]
            rsi = self.df['rsi'].iloc[i]
            
            # Strong uptrend
            if ema_20 > ema_50 > ema_100 and current_price > ema_20 and rsi > 50:
                # Buy on pullback to EMA20
                if abs(current_price - ema_20) / 0.0001 <= 15:  # Within 15 pips
                    sl_price = ema_50 - 10 * 0.0001  # Below EMA50
                    tp_price = current_price + (current_price - sl_price) * 3  # 1:3 RR
                    
                    exit_reason, exit_price = self.simulate_trade(i, 'BUY', sl_price, tp_price, 40)
                    if exit_reason:
                        pnl = (exit_price - current_price) / current_price * 10000
                        sl_pips = (current_price - sl_price) / 0.0001
                        signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / sl_pips if pnl < 0 else pnl / sl_pips})
                        
            # Strong downtrend
            elif ema_20 < ema_50 < ema_100 and current_price < ema_20 and rsi < 50:
                # Sell on pullback to EMA20
                if abs(current_price - ema_20) / 0.0001 <= 15:  # Within 15 pips
                    sl_price = ema_50 + 10 * 0.0001  # Above EMA50
                    tp_price = current_price - (sl_price - current_price) * 3  # 1:3 RR
                    
                    exit_reason, exit_price = self.simulate_trade(i, 'SELL', sl_price, tp_price, 40)
                    if exit_reason:
                        pnl = (current_price - exit_price) / current_price * 10000
                        sl_pips = (sl_price - current_price) / 0.0001
                        signals.append({'win': exit_reason == 'TP', 'pnl': pnl, 'rr': pnl / sl_pips if pnl < 0 else pnl / sl_pips})
        
        if signals:
            win_rate = (sum(s['win'] for s in signals) / len(signals)) * 100
            avg_rr = sum(s['rr'] for s in signals) / len(signals)
        else:
            win_rate = 0
            avg_rr = 0
            
        return {'win_rate': win_rate, 'total_trades': len(signals), 'avg_rr': avg_rr}
    
    def simulate_trade(self, entry_idx, direction, sl_price, tp_price, max_bars):
        """Simulate a trade and return exit reason and price"""
        for j in range(entry_idx + 1, min(entry_idx + max_bars + 1, len(self.df))):
            high = self.df['high'].iloc[j]
            low = self.df['low'].iloc[j]
            
            if direction == 'BUY':
                if high >= tp_price:
                    return 'TP', tp_price
                elif low <= sl_price:
                    return 'SL', sl_price
            else:  # SELL
                if low <= tp_price:
                    return 'TP', tp_price
                elif high >= sl_price:
                    return 'SL', sl_price
        
        # Time exit
        return 'TIME', self.df['close'].iloc[min(entry_idx + max_bars, len(self.df) - 1)]
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df, period=14):
        """Calculate ATR"""
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        return tr.rolling(window=period).mean()
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def generate_strategy_recommendation(self, strategy_results):
        """Generate final strategy recommendation"""
        print("\n🎯 FINAL STRATEGY RECOMMENDATION")
        print("=" * 60)
        
        best_strategy = strategy_results[0]
        strategy_name = best_strategy[0]
        results = best_strategy[1]
        
        print(f"✅ RECOMMENDED STRATEGY: {strategy_name}")
        print(f"📊 Expected Win Rate: {results['win_rate']:.1f}%")
        print(f"📈 Total Test Trades: {results['total_trades']}")
        print(f"⚖️  Average Risk:Reward: 1:{results['avg_rr']:.2f}")
        
        # Market regime assessment
        regime = self.analysis_results.get('market_regime', 'unknown')
        volatility = self.analysis_results.get('volatility', 'unknown')
        
        print(f"\n📋 MARKET CHARACTERISTICS:")
        print(f"   Market Regime: {regime.upper()}")
        print(f"   Volatility: {volatility.upper()}")
        
        if results['win_rate'] >= 50:
            print(f"\n✅ RECOMMENDED: This strategy shows promise for EUR/USD")
            print(f"   Target: Achieve 50%+ win rate with 1:3 risk-reward")
        else:
            print(f"\n⚠️  CAUTION: All tested strategies show <50% win rate")
            print(f"   Recommendation: Consider different market or adjust expectations")
        
        return strategy_name, results
    
    def run_full_analysis(self):
        """Run complete analysis"""
        print("🚀 STARTING COMPREHENSIVE EUR/USD ANALYSIS")
        print("=" * 80)
        
        # Load and analyze
        self.load_data()
        self.analyze_market_structure()
        self.test_mean_reversion_patterns()
        self.test_momentum_patterns()
        self.test_support_resistance_strategy()
        self.test_time_based_patterns()
        
        # Test strategies
        strategy_results = self.test_simple_strategies()
        
        # Final recommendation
        recommended_strategy, results = self.generate_strategy_recommendation(strategy_results)
        
        print(f"\n🎯 ANALYSIS COMPLETE!")
        print(f"Recommended strategy: {recommended_strategy}")
        
        return recommended_strategy, results, strategy_results

if __name__ == "__main__":
    analyzer = EURUSDDataAnalyzer()
    recommended_strategy, results, all_results = analyzer.run_full_analysis() 