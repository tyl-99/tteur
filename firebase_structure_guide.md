# 🔥 Firebase Structure for cTrader Trading Bot

## 📄 **FIRESTORE DATABASE STRUCTURE**

### **Collection: `trades`**
**Document ID**: Auto-generated  
**Purpose**: Store individual trade records
```json
{
  "trade_id": "auto-generated-id",
  "timestamp": "2024-01-15T10:30:45Z",
  "symbol": "EUR/USD",
  "decision": "BUY",
  "status": "completed", // pending, completed, failed, cancelled
  
  // Position Details
  "position_id": 12345678,
  "order_id": 87654321,
  "volume_lots": 0.15,
  "volume_units": 15000,
  
  // Price Levels  
  "entry_price": 1.08457,
  "exit_price": 1.08612,
  "stop_loss": 1.08200,
  "take_profit": 1.08900,
  
  // Risk Management
  "risk_reward_ratio": 2.85,
  "potential_loss_usd": 50.00,
  "potential_win_usd": 142.50,
  "actual_pnl_usd": 142.50,
  
  // Strategy Analysis
  "strategy_name": "EURUSDSupplyDemandStrategy",
  "trade_reason": "Strong demand zone rejection with bullish confirmation...",
  "winrate": "55%+",
  "confidence_level": "high",
  
  // Calculations
  "risk_pips": 25.7,
  "reward_pips": 44.3,
  "pip_value": 10.0,
  "volume_calculation": "0.15 lots for $50 risk",
  "loss_calculation": "25.7 pips × $10.0/pip × 0.15 lots",
  "win_calculation": "44.3 pips × $10.0/pip × 0.15 lots",
  
  // Execution Details
  "execution_time_ms": 245,
  "slippage_pips": 0.2,
  "spread_pips": 1.1,
  
  // Session Info
  "trading_session": "london_open",
  "session_date": "2024-01-15",
  "bot_version": "v2.1"
}
```

### **Collection: `account`**
**Document ID**: `current_balance`, `daily_summary`, `monthly_summary`
```json
// Document: current_balance
{
  "balance": 5247.83,
  "currency": "USD",
  "equity": 5289.45,
  "margin_used": 156.78,
  "free_margin": 5132.67,
  "margin_level": 3372.45,
  "last_updated": "2024-01-15T15:30:00Z"
}

// Document: daily_summary_2024-01-15
{
  "date": "2024-01-15",
  "starting_balance": 5100.00,
  "ending_balance": 5247.83,
  "daily_pnl": 147.83,
  "total_trades": 8,
  "winning_trades": 5,
  "losing_trades": 3,
  "win_rate": 62.5,
  "total_volume_lots": 1.25,
  "max_drawdown": 87.45,
  "biggest_win": 142.50,
  "biggest_loss": -50.00
}
```

### **Collection: `strategies`**
**Document ID**: Strategy name (e.g., `EURUSDSupplyDemandStrategy`)
```json
{
  "strategy_name": "EURUSDSupplyDemandStrategy",
  "symbol": "EUR/USD",
  "settings": {
    "timeframe": "M30",
    "lookback_periods": 100,
    "min_rr_ratio": 2.5,
    "max_risk_per_trade": 50.0,
    "confidence_threshold": 0.75
  },
  "performance": {
    "total_trades": 156,
    "win_rate": 58.33,
    "avg_rr_ratio": 2.87,
    "total_pnl": 2456.78,
    "max_consecutive_wins": 7,
    "max_consecutive_losses": 4
  },
  "last_updated": "2024-01-15T12:00:00Z",
  "active": true
}
```

### **Collection: `sessions`**
**Document ID**: Date + Session (e.g., `2024-01-15_session`)
```json
{
  "session_id": "2024-01-15_session",
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T14:00:00Z",
  "pairs_analyzed": ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "GBP/JPY", "EUR/GBP"],
  "trades_executed": 3,
  "errors_encountered": ["TRADING_BAD_STOPS", "API_TIMEOUT"],
  "total_runtime_minutes": 300,
  "pairs_skipped": 1,
  "notifications_sent": 3,
  "bot_version": "v2.1"
}
```

### **Collection: `market_data`**
**Document ID**: Symbol + Date (e.g., `EUR_USD_2024-01-15`)
```json
{
  "symbol": "EUR/USD",
  "date": "2024-01-15",
  "timeframe": "M30",
  "candles_count": 48,
  "price_range": {
    "high": 1.08789,
    "low": 1.08234,
    "open": 1.08456,
    "close": 1.08612
  },
  "volatility": "medium",
  "trend_direction": "bullish",
  "key_levels": {
    "support": [1.08200, 1.08100],
    "resistance": [1.08900, 1.09000]
  },
  "data_source": "ctrader_api"
}
```

---

## 📁 **FIREBASE STORAGE STRUCTURE**

### **Root Folder Structure:**
```
my-trader-9e446.appspot.com/
├── logs/
│   ├── daily/
│   │   ├── forex_trading_2024-01-15.log
│   │   ├── forex_trading_2024-01-16.log
│   │   └── ...
│   ├── monthly/
│   │   ├── january_2024_complete.log
│   │   └── ...
│   └── error_logs/
│       ├── errors_2024-01-15.log
│       └── ...
│
├── reports/
│   ├── trade_reports/
│   │   ├── EUR_USD/
│   │   │   ├── DETAILED_TRADES_EUR_USD_20240115_143022.xlsx
│   │   │   └── ...
│   │   ├── GBP_USD/
│   │   │   ├── DETAILED_TRADES_GBP_USD_20240115_143022.xlsx
│   │   │   └── ...
│   │   └── ...
│   ├── daily_summaries/
│   │   ├── daily_summary_2024-01-15.xlsx
│   │   └── ...
│   └── monthly_reports/
│       ├── january_2024_performance.xlsx
│       └── ...
│
├── backups/
│   ├── candle_data/
│   │   ├── EUR_USD_2024-01-15.csv
│   │   ├── GBP_USD_2024-01-15.csv
│   │   └── ...
│   ├── database_backups/
│   │   ├── firestore_backup_2024-01-15.json
│   │   └── ...
│   └── configurations/
│       ├── strategy_settings_2024-01-15.json
│       └── ...
│
├── charts/
│   ├── technical_analysis/
│   │   ├── EUR_USD_analysis_2024-01-15.png
│   │   └── ...
│   └── performance_charts/
│       ├── monthly_performance_jan_2024.png
│       └── ...
│
└── notifications/
    ├── pushover_logs/
    │   ├── notifications_2024-01-15.json
    │   └── ...
    └── trade_alerts/
        ├── successful_trades_2024-01-15.json
        └── ...
```

---

## 🔧 **INTEGRATION POINTS IN YOUR cTrader.py**

### **1. Trade Execution (`onOrderSent`)**
```python
# Save trade when order is sent
firebase_trade = {
    "symbol": self.current_pair,
    "decision": self.pending_order["decision"],
    "volume_lots": self.pending_order["volume"] / 100000,
    "entry_price": self.pending_order["entry_price"],
    "stop_loss": self.pending_order["stop_loss"],
    "take_profit": self.pending_order["take_profit"],
    "risk_reward_ratio": self.pending_order["risk_reward_ratio"],
    "potential_loss_usd": self.pending_order["potential_loss_usd"],
    "potential_win_usd": self.pending_order["potential_win_usd"],
    "trade_reason": self.pending_order["reason"],
    "status": "pending"
}
self.firebase.save_trade(firebase_trade)
```

### **2. Position Close (`onPositionClosed`)**
```python
# Update trade with final results
completed_trade = {
    "status": "completed",
    "exit_price": closing_price,
    "actual_pnl_usd": actual_profit_loss,
    "execution_time_ms": execution_time
}
self.firebase.update_trade(trade_id, completed_trade)
```

### **3. Daily Backup (`move_to_next_pair` - last pair)**
```python
if self.pairIndex == len(self.pairs) - 1:
    # End of session - trigger backups
    self.firebase.daily_backup()
    self.firebase.upload_trade_reports()
```

### **4. Error Logging**
```python
# In onError method
self.firebase.log_error({
    "error_type": error_type,
    "pair": self.current_pair,
    "timestamp": datetime.now(),
    "details": str(failure)
})
```

---

## 📊 **QUERY EXAMPLES**

### **Get Recent Trades**
```python
# Last 10 trades for EUR/USD
trades = firebase.get_trades("EUR/USD", limit=10)

# Today's winning trades
today_winners = firebase.get_winning_trades(date="2024-01-15")

# This month's performance by strategy
strategy_performance = firebase.get_strategy_performance("EURUSDSupplyDemandStrategy", month="2024-01")
```

### **Performance Analytics**
```python
# Calculate win rate for last 30 days
win_rate = firebase.calculate_win_rate(days=30)

# Get best performing pair this month
best_pair = firebase.get_best_pair(month="2024-01")

# Risk analysis - trades exceeding risk limits
high_risk_trades = firebase.get_high_risk_trades(risk_threshold=75.0)
```

---

## 🎯 **BACKUP SCHEDULE**

- **Real-time**: Every trade → Firestore
- **Hourly**: Error logs → Storage  
- **Daily**: Trading logs → Storage
- **Daily**: Trade reports → Storage
- **Weekly**: Candle data → Storage
- **Monthly**: Complete database backup → Storage

This structure gives you:
✅ **Complete trade tracking**
✅ **Performance analytics** 
✅ **Automatic backups**
✅ **Error monitoring**
✅ **Historical data preservation**
✅ **Scalable for multiple bots** 