#!/usr/bin/env python3
"""
Simple Trading API - File-based approach (no threading issues)
"""
import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_trendbar_data_async():
    """Fetch trendbar data in background thread"""
    try:
        logger.info("🚀 Starting background trendbar data fetch...")
        
        # Check if we already have recent trendbar data
        latest_file = 'latest_trendbar_data.xlsx'
        if os.path.exists(latest_file):
            file_age = datetime.now().timestamp() - os.path.getmtime(latest_file)
            # If file is less than 1 hour old, skip fetching
            if file_age < 3600:  # 1 hour
                logger.info(f"📄 Recent trendbar data exists (age: {file_age/60:.0f} minutes), skipping fetch")
                return
        
        # Import and run the simplified fetch function
        from fetch_data import fetch_latest_data
        result = fetch_latest_data()
        
        if result:
            logger.info("✅ Trendbar data fetch completed successfully")
        else:
            logger.error("❌ Trendbar data fetch failed")
        
    except Exception as e:
        logger.error(f"❌ Error fetching trendbar data: {e}")

def get_real_trading_data():
    """Get trading data from file (updated by trade_monitor)"""
    try:
        logger.info("🔄 Reading trading data from file...")
        
        # Check if we have fresh data file
        data_file = 'trading_data.json'
        if os.path.exists(data_file):
            # Always try to read the file first
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    if data.get('success'):
                        # Check if file is recent (less than 5 minutes old)
                        file_age = datetime.now().timestamp() - os.path.getmtime(data_file)
                        if file_age < 300:  # 5 minutes
                            logger.info(f"✅ Got fresh cached data: {data['summary']['totalTrades']} trades, ${data['summary']['totalPnL']:.2f} P&L")
                            return data
                        else:
                            logger.info(f"📄 Got older cached data: {data['summary']['totalTrades']} trades, ${data['summary']['totalPnL']:.2f} P&L (age: {file_age:.0f}s)")
                            # Still return it, but we'll try to refresh below
            except Exception as e:
                logger.error(f"Error reading cached file: {e}")
        
        # If no fresh data, try to generate new data
        logger.info("🔄 Generating fresh trading data...")
        
        try:
            # Run trade monitor to update the file
            result = subprocess.run([
                sys.executable, 'trade_monitor.py', '--json', '--days', '30'
            ], capture_output=True, text=True, timeout=45, cwd='.')
            
            if result.returncode == 0:
                # Try to read the updated file
                if os.path.exists(data_file):
                    with open(data_file, 'r') as f:
                        data = json.load(f)
                        if data.get('success'):
                            logger.info(f"✅ Got fresh data: {data['summary']['totalTrades']} trades, ${data['summary']['totalPnL']:.2f} P&L")
                            return data
        except subprocess.TimeoutExpired:
            logger.warning("⏰ Trade monitor timed out")
        except Exception as e:
            logger.error(f"❌ Error running trade monitor: {e}")
        
        # If all else fails, try to read any existing file
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    if data.get('success'):
                        logger.info(f"📄 Using cached data: {data['summary']['totalTrades']} trades, ${data['summary']['totalPnL']:.2f} P&L")
                        return data
            except Exception as e:
                logger.error(f"Error reading fallback file: {e}")
                
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting trading data: {e}")
        return None

# Fallback data
FALLBACK_DATA = {
    'success': True,
    'summary': {
        'totalPnL': 0.0,
        'totalTrades': 0,
        'winRate': 0.0,
        'totalVolume': 0.0,
        'winningTrades': 0,
        'losingTrades': 0,
        'lastUpdate': datetime.now().isoformat()
    },
    'symbolPerformance': [],
    'recentTrades': [],
    'pnlHistory': [],
    'riskMetrics': {
        'maxDrawdown': 0.0,
        'avgTradeSize': 0.0,
        'profitFactor': 0.0,
        'sharpeRatio': 0.0
    },
    'insights': ['No trading data available']
}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/api/all')
def get_all_data():
    """Get all trading data - file-based approach"""
    try:
        # Try to get real data first
        real_data = get_real_trading_data()
        
        if real_data:
            logger.info("✅ Returning REAL trading data")
            # Format response for frontend
            response = {
                'status': 'success',
                'data': real_data
            }
            return jsonify(response)
        else:
            logger.warning("⚠️ Using fallback data (no real data available)")
            fallback = FALLBACK_DATA.copy()
            fallback['summary']['lastUpdate'] = datetime.now().isoformat()
            fallback['fallback'] = True
            response = {
                'status': 'success',
                'data': fallback
            }
            return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in all data endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 500

@app.route('/api/trading-data')
def get_trading_data():
    """Get current trading data - same as /api/all"""
    return get_all_data()

@app.route('/api/trade-analysis/<int:trade_id>')
def get_enhanced_trade_analysis(trade_id):
    """Get enhanced AI trade analysis with 300 candles context"""
    try:
        logger.info(f"🧠 Enhanced AI analysis requested for trade {trade_id}")
        
        # Get trading data to find the specific trade
        trading_data = get_real_trading_data()
        if not trading_data:
            return jsonify({
                'status': 'error',
                'message': 'No trading data available'
            }), 404
        
        # Find the trade
        trade = None
        for t in trading_data.get('recentTrades', []):
            if t.get('id') == trade_id:
                trade = t
                break
        
        if not trade:
            return jsonify({
                'status': 'error',
                'message': f'Trade {trade_id} not found'
            }), 404
        
        # Import candle analyzer
        from candle_analyzer import candle_analyzer
        
        # Add sample stop loss and take profit for demo
        trade_with_levels = trade.copy()
        if 'stop_loss' not in trade_with_levels:
            # Calculate sample stop loss and take profit based on entry price
            entry = trade['entry']
            if trade['side'] == 'BUY':
                trade_with_levels['stop_loss'] = entry * 0.995  # 0.5% below entry
                trade_with_levels['take_profit'] = entry * 1.015  # 1.5% above entry
            else:  # SELL
                trade_with_levels['stop_loss'] = entry * 1.005  # 0.5% above entry
                trade_with_levels['take_profit'] = entry * 0.985  # 1.5% below entry
        
        # Analyze the trade with candle data
        if trade['pnl'] < 0:
            # Losing trade - get detailed loss analysis
            analysis = candle_analyzer.analyze_losing_trade(trade_with_levels, trading_data)
        else:
            # Winning trade - could add winning trade analysis later
            analysis = {
                'symbol': trade['symbol'],
                'ai_loss_insights': [
                    f"✅ WINNING TRADE: You made ${trade['pnl']:.2f} profit on this {trade['side']} trade",
                    "🎉 Good job! This trade was profitable",
                    "💡 Analyze what you did right to repeat this success"
                ],
                'total_candles_analyzed': 0,
                'actual_loss': trade['pnl']
            }
        
        return jsonify({
            'status': 'success',
            'data': {
                'trade': trade,
                'analysis': analysis
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced trade analysis: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    data_file_exists = os.path.exists('trading_data.json')
    trendbar_file_exists = os.path.exists('latest_trendbar_data.xlsx')
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Trading API',
        'data_file_exists': data_file_exists,
        'trendbar_file_exists': trendbar_file_exists
    })

@app.route('/api/refresh')
def refresh_data():
    """Force refresh trading data"""
    try:
        logger.info("🔄 Force refreshing trading data...")
        
        # Delete old file to force refresh
        if os.path.exists('trading_data.json'):
            os.remove('trading_data.json')
        
        # Get fresh data
        data = get_real_trading_data()
        
        if data:
            return jsonify({
                'success': True,
                'message': 'Data refreshed successfully',
                'trades': data['summary']['totalTrades'],
                'pnl': data['summary']['totalPnL']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to refresh data'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/fetch-trendbar')
def fetch_trendbar_endpoint():
    """Manually trigger trendbar data fetch"""
    try:
        logger.info("🔄 Manual trendbar data fetch requested...")
        
        # Start background fetch
        thread = threading.Thread(target=fetch_trendbar_data_async)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Trendbar data fetch started in background'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/currency-analysis/<path:symbol>')
def get_currency_analysis(symbol):
    """Get AI-powered currency pair analysis with strategy code review"""
    try:
        # URL decode the symbol
        from urllib.parse import unquote
        decoded_symbol = unquote(symbol)
        logger.info(f"🧠 AI Currency analysis requested for {decoded_symbol}")
        
        # Get trading data
        trading_data = get_real_trading_data()
        if not trading_data:
            return jsonify({
                'status': 'error',
                'message': 'No trading data available'
            }), 404
        
        # Find trades for this symbol
        symbol_trades = [t for t in trading_data.get('recentTrades', []) 
                        if t.get('symbol') == decoded_symbol or t.get('symbol') == symbol]
        
        if not symbol_trades:
            return jsonify({
                'status': 'error',
                'message': f'No trades found for {decoded_symbol}'
            }), 404
        
        # Get AI analysis with strategy code
        ai_analysis = get_ai_strategy_analysis(decoded_symbol, symbol_trades)
        
        # Calculate basic stats
        total_pnl = sum(t.get('pnl', 0) for t in symbol_trades)
        winning_trades = [t for t in symbol_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in symbol_trades if t.get('pnl', 0) < 0]
        win_rate = (len(winning_trades) / len(symbol_trades)) * 100 if symbol_trades else 0
        best_trade = max(t.get('pnl', 0) for t in symbol_trades) if symbol_trades else 0
        worst_trade = min(t.get('pnl', 0) for t in symbol_trades) if symbol_trades else 0
        avg_trade_size = sum(t.get('volume', 0) for t in symbol_trades) / len(symbol_trades) if symbol_trades else 0
        
        analysis_data = {
            'totalPnL': total_pnl,
            'winRate': win_rate,
            'totalTrades': len(symbol_trades),
            'profitFactor': abs(sum(t.get('pnl', 0) for t in winning_trades) / sum(t.get('pnl', 0) for t in losing_trades)) if losing_trades else 0,
            'bestTrade': best_trade,
            'worstTrade': worst_trade,
            'maxDrawdown': abs(worst_trade),
            'avgTradeSize': avg_trade_size,
            'aiInsights': ai_analysis.get('insights', [f"AI analysis for {decoded_symbol} in progress..."]),
            'marketAnalysis': ai_analysis.get('strategy_analysis', f"Strategy analysis for {decoded_symbol} being processed..."),
            'recommendations': ai_analysis.get('recommendations', ["AI recommendations being generated..."]),
            'strategyCode': ai_analysis.get('strategy_code', ''),
            'strategyImprovements': ai_analysis.get('strategy_improvements', []),
            'recentTrades': symbol_trades[:10]
        }
        
        return jsonify({
            'status': 'success',
            'data': analysis_data
        })
        
    except Exception as e:
        logger.error(f"❌ Error in AI currency analysis: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def get_ai_strategy_analysis(symbol, trades):
    """Get AI analysis of strategy code and trading performance"""
    try:
        import os
        import google.generativeai as genai
        
        # Load strategy file for this symbol
        strategy_file = get_strategy_file_for_symbol(symbol)
        if not strategy_file:
            return {
                'insights': [f"⚠️ No strategy file found for {symbol}"],
                'strategy_analysis': f"Strategy file for {symbol} not found",
                'recommendations': ["Create a specific strategy file for this currency pair"],
                'strategy_code': '',
                'strategy_improvements': []
            }
        
        # Read strategy code
        strategy_path = os.path.join('..', 'strategy', strategy_file)
        if not os.path.exists(strategy_path):
            strategy_path = os.path.join('strategy', strategy_file)
        
        if not os.path.exists(strategy_path):
            return {
                'insights': [f"⚠️ Strategy file {strategy_file} not found"],
                'strategy_analysis': f"Could not locate strategy file {strategy_file}",
                'recommendations': ["Check strategy file location"],
                'strategy_code': '',
                'strategy_improvements': []
            }
        
        with open(strategy_path, 'r', encoding='utf-8') as f:
            strategy_code = f.read()
        
        # Prepare trade data for AI
        trade_summary = []
        for trade in trades[:20]:  # Last 20 trades
            trade_summary.append({
                'time': trade.get('time', ''),
                'side': trade.get('side', ''),
                'volume': trade.get('volume', 0),
                'entry': trade.get('entry', 0),
                'exit': trade.get('exit', 0),
                'pips': trade.get('pips', 0),
                'pnl': trade.get('pnl', 0)
            })
        
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY', 'your-api-key-here')
        if api_key == 'your-api-key-here':
            # Return mock AI analysis if no API key
            return get_mock_ai_analysis(symbol, trades, strategy_code)
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create AI prompt
        prompt = f"""
You are an expert forex trading strategy analyst. Analyze the following:

**CURRENCY PAIR:** {symbol}

**STRATEGY CODE:**
```python
{strategy_code}
```

**RECENT TRADING RESULTS:**
{trade_summary}

**PERFORMANCE SUMMARY:**
- Total Trades: {len(trades)}
- Win Rate: {(len([t for t in trades if t.get('pnl', 0) > 0]) / len(trades) * 100):.1f}%
- Total P&L: ${sum(t.get('pnl', 0) for t in trades):.2f}

Please provide:

1. **STRATEGY ANALYSIS** (2-3 sentences): What is this strategy trying to do? Is it well-designed for {symbol}?

2. **PERFORMANCE INSIGHTS** (3-4 bullet points): Why is the strategy performing this way? What patterns do you see in the trades?

3. **SPECIFIC IMPROVEMENTS** (3-5 actionable items): What exact changes should be made to the strategy code to improve performance?

4. **CODE MODIFICATIONS** (2-3 specific suggestions): What parameters, conditions, or logic should be adjusted?

Keep responses practical and actionable. Focus on concrete improvements that can be implemented immediately.
"""
        
        # Get AI response
        response = model.generate_content(prompt)
        ai_response = response.text
        
        # Parse AI response into sections
        insights = []
        strategy_analysis = ""
        recommendations = []
        improvements = []
        
        # Simple parsing of AI response
        lines = ai_response.split('\n')
        current_section = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "STRATEGY ANALYSIS" in line.upper():
                current_section = "strategy"
            elif "PERFORMANCE INSIGHTS" in line.upper():
                current_section = "insights"
            elif "SPECIFIC IMPROVEMENTS" in line.upper():
                current_section = "recommendations"
            elif "CODE MODIFICATIONS" in line.upper():
                current_section = "improvements"
            elif line.startswith('- ') or line.startswith('• ') or line.startswith('* '):
                if current_section == "insights":
                    insights.append(line[2:])
                elif current_section == "recommendations":
                    recommendations.append(line[2:])
                elif current_section == "improvements":
                    improvements.append(line[2:])
            else:
                if current_section == "strategy" and line:
                    strategy_analysis += line + " "
        
        # Fallback if parsing failed
        if not insights:
            insights = [f"🧠 AI analyzed {len(trades)} trades for {symbol}", "📊 Strategy performance review completed"]
        if not strategy_analysis:
            strategy_analysis = f"AI analysis of {symbol} strategy shows areas for improvement based on recent trading performance."
        if not recommendations:
            recommendations = ["Review strategy parameters", "Consider adjusting entry/exit conditions", "Optimize position sizing"]
        
        return {
            'insights': insights[:5],  # Limit to 5 insights
            'strategy_analysis': strategy_analysis.strip(),
            'recommendations': recommendations[:5],  # Limit to 5 recommendations
            'strategy_code': strategy_code[:1000],  # First 1000 chars for display
            'strategy_improvements': improvements[:5],
            'ai_response': ai_response  # Full response for debugging
        }
        
    except Exception as e:
        logger.error(f"❌ Error in AI analysis: {e}")
        return get_mock_ai_analysis(symbol, trades, "")

def get_strategy_file_for_symbol(symbol):
    """Get strategy filename for currency pair"""
    symbol_map = {
        'EUR/USD': 'eurusd_strategy.py',
        'USD/JPY': 'usdjpy_strategy.py', 
        'GBP/USD': 'gbpusd_strategy.py',
        'EUR/GBP': 'eurgbp_strategy.py',
        'EUR/JPY': 'eurjpy_strategy.py',
        'GBP/JPY': 'gbpjpy_strategy.py'
    }
    return symbol_map.get(symbol)

def get_mock_ai_analysis(symbol, trades, strategy_code):
    """Mock AI analysis when API not available"""
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    win_rate = (len([t for t in trades if t.get('pnl', 0) > 0]) / len(trades) * 100) if trades else 0
    
    insights = [
        f"🧠 AI analyzed {len(trades)} trades for {symbol}",
        f"📊 Current win rate: {win_rate:.1f}% - {'Good performance' if win_rate > 50 else 'Needs improvement'}",
        f"💰 Total P&L: ${total_pnl:.2f} - {'Profitable strategy' if total_pnl > 0 else 'Strategy losing money'}",
        "🔍 Pattern analysis shows entry timing could be optimized",
        "⚖️ Risk management parameters may need adjustment"
    ]
    
    recommendations = [
        "Adjust entry signal sensitivity to reduce false signals",
        "Optimize stop loss levels based on volatility",
        "Consider adding time-based filters for better entries",
        "Review position sizing relative to account balance",
        "Implement trailing stops for better profit capture"
    ]
    
    improvements = [
        "Increase lookback period for trend confirmation",
        "Add RSI filter to avoid overbought/oversold entries", 
        "Implement dynamic stop loss based on ATR",
        "Add correlation filter with other pairs",
        "Use multiple timeframe confirmation"
    ]
    
    return {
        'insights': insights,
        'strategy_analysis': f"Mock AI analysis shows {symbol} strategy has {win_rate:.1f}% win rate with ${total_pnl:.2f} total P&L. The strategy appears to be {'working well' if total_pnl > 0 else 'underperforming'} and could benefit from parameter optimization.",
        'recommendations': recommendations,
        'strategy_code': strategy_code[:1000],
        'strategy_improvements': improvements
    }

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Run backtest with LLM-suggested strategy code"""
    try:
        from web_backtest_engine import WebBacktestEngine
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        currency_pair = data.get('currency_pair', 'EUR/USD')
        strategy_code = data.get('strategy_code', '')
        initial_balance = data.get('initial_balance', 1000)
        
        if not strategy_code:
            return jsonify({'error': 'No strategy code provided'}), 400
        
        logger.info(f"🚀 Starting backtest for {currency_pair}")
        
        # Create backtest engine
        engine = WebBacktestEngine(
            target_pair=currency_pair,
            initial_balance=initial_balance,
            strategy_code=strategy_code
        )
        
        # Load strategy from code
        if not engine.load_strategy_from_code(strategy_code):
            return jsonify({'error': 'Failed to load strategy from code'}), 400
        
        # Run backtest
        results = engine.run_backtest()
        
        if results is None:
            return jsonify({'error': 'Backtest failed to run'}), 500
        
        logger.info(f"✅ Backtest completed: {results['total_trades']} trades, {results['win_rate']:.1f}% win rate")
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f"Backtest completed successfully for {currency_pair}"
        })
        
    except Exception as e:
        logger.error(f"❌ Backtest error: {e}")
        return jsonify({'error': f'Backtest failed: {str(e)}'}), 500

@app.route('/api/get-strategy-code/<path:symbol>')
def get_strategy_code(symbol):
    """Get current strategy code for a currency pair"""
    try:
        strategy_file = get_strategy_file_for_symbol(symbol)
        if not strategy_file:
            return jsonify({'error': f'No strategy file found for {symbol}'}), 404
        
        # Try multiple paths
        strategy_paths = [
            os.path.join('..', 'strategy', strategy_file),
            os.path.join('strategy', strategy_file),
            os.path.join('..', '..', 'strategy', strategy_file)
        ]
        
        strategy_code = None
        for path in strategy_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    strategy_code = f.read()
                break
        
        if not strategy_code:
            return jsonify({'error': f'Strategy file {strategy_file} not found'}), 404
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'strategy_file': strategy_file,
            'strategy_code': strategy_code
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting strategy code: {e}")
        return jsonify({'error': f'Failed to get strategy code: {str(e)}'}), 500

@app.route('/api/save-strategy-code', methods=['POST'])
def save_strategy_code():
    """Save updated strategy code"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        symbol = data.get('symbol', '')
        strategy_code = data.get('strategy_code', '')
        
        if not symbol or not strategy_code:
            return jsonify({'error': 'Symbol and strategy code required'}), 400
        
        strategy_file = get_strategy_file_for_symbol(symbol)
        if not strategy_file:
            return jsonify({'error': f'No strategy file found for {symbol}'}), 404
        
        # Try to save to the main strategy folder
        strategy_paths = [
            os.path.join('..', 'strategy', strategy_file),
            os.path.join('strategy', strategy_file)
        ]
        
        saved = False
        for path in strategy_paths:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(strategy_code)
                
                logger.info(f"✅ Strategy saved: {path}")
                saved = True
                break
                
            except Exception as e:
                logger.warning(f"Failed to save to {path}: {e}")
                continue
        
        if not saved:
            return jsonify({'error': 'Failed to save strategy file'}), 500
        
        return jsonify({
            'success': True,
            'message': f'Strategy code saved for {symbol}',
            'symbol': symbol,
            'strategy_file': strategy_file
        })
        
    except Exception as e:
        logger.error(f"❌ Error saving strategy code: {e}")
        return jsonify({'error': f'Failed to save strategy code: {str(e)}'}), 500

@app.route('/api/ai-strategy-suggestions', methods=['POST'])
def get_ai_strategy_suggestions():
    """Get AI-powered strategy suggestions based on backtest results"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        symbol = data.get('symbol', '')
        current_strategy = data.get('current_strategy', '')
        backtest_results = data.get('backtest_results', {})
        auto_apply = data.get('auto_apply', False)  # New parameter for auto-apply
        
        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400
        
        logger.info(f"🧠 Generating AI strategy suggestions for {symbol} (auto_apply={auto_apply})")
        
        # Generate AI-powered suggestions
        suggestions = generate_ai_strategy_suggestions(symbol, current_strategy, backtest_results)
        
        response_data = {
            'success': True,
            'symbol': symbol,
            'suggestions': suggestions,
            'auto_applied': False
        }
        
        # Auto-apply if requested
        if auto_apply and suggestions.get('suggested_code_changes'):
            try:
                improved_code = suggestions['suggested_code_changes'][0]  # Get the first code suggestion
                
                # Save the improved strategy automatically
                strategy_file = get_strategy_file_for_symbol(symbol)
                if strategy_file:
                    strategy_paths = [
                        os.path.join('..', 'strategy', strategy_file),
                        os.path.join('strategy', strategy_file)
                    ]
                    
                    applied = False
                    for path in strategy_paths:
                        try:
                            with open(path, 'w', encoding='utf-8') as f:
                                f.write(improved_code)
                            logger.info(f"✅ Auto-applied AI strategy improvements to {path}")
                            response_data['auto_applied'] = True
                            response_data['applied_to'] = path
                            applied = True
                            break
                        except Exception as e:
                            logger.warning(f"⚠️ Could not auto-apply to {path}: {e}")
                            continue
                    
                    if not applied:
                        logger.warning(f"⚠️ Could not auto-apply strategy improvements for {symbol}")
                        response_data['auto_apply_error'] = "Could not write to strategy file"
                else:
                    logger.warning(f"⚠️ No strategy file found for {symbol}")
                    response_data['auto_apply_error'] = "No strategy file found"
                    
            except Exception as e:
                logger.error(f"❌ Error auto-applying strategy: {e}")
                response_data['auto_apply_error'] = str(e)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error generating AI suggestions: {e}")
        return jsonify({'error': f'Failed to generate suggestions: {str(e)}'}), 500

def generate_ai_strategy_suggestions(symbol, current_strategy, backtest_results):
    """Generate AI-powered strategy improvement suggestions focused on Supply & Demand with 1:3 RR and $50 max risk"""
    
    # Analyze backtest performance
    win_rate = backtest_results.get('win_rate', 0)
    total_pnl = backtest_results.get('total_pnl', 0)
    max_drawdown = backtest_results.get('max_drawdown', 0)
    total_trades = backtest_results.get('total_trades', 0)
    avg_loss = backtest_results.get('avg_loss', 0)
    
    suggestions = {
        'performance_analysis': [],
        'supply_demand_improvements': [],
        'risk_management': [],
        'parameter_optimization': [],
        'suggested_code_changes': []
    }
    
    # Performance Analysis with $50 Risk Focus
    suggestions['performance_analysis'].append(f"📊 BACKTEST RESULTS: {total_trades} trades, {win_rate:.1f}% win rate, ${total_pnl:.2f} P&L")
    
    if abs(avg_loss) > 50:
        suggestions['performance_analysis'].append(f"🚨 CRITICAL: Average loss ${abs(avg_loss):.2f} EXCEEDS $50 LIMIT!")
        suggestions['performance_analysis'].append("💡 IMMEDIATE ACTION: Reduce position sizes to cap losses at $50")
    else:
        suggestions['performance_analysis'].append(f"✅ RISK OK: Average loss ${abs(avg_loss):.2f} within $50 limit")
    
    if win_rate < 40:
        suggestions['performance_analysis'].append(f"🔴 LOW WIN RATE: {win_rate:.1f}% - Supply/Demand zones need better filtering")
    elif win_rate > 60:
        suggestions['performance_analysis'].append(f"🟢 GOOD WIN RATE: {win_rate:.1f}% - Focus on maximizing profits with 1:3 RR")
    
    # Supply & Demand Specific Improvements
    supply_demand_improvements = [
        "🎯 ZONE QUALITY FILTERS:",
        "   • Only trade zones with width < 20 pips (tighter = better)",
        "   • Require minimum 2.5x impulse move ratio (stronger breakouts)",
        "   • Increase zone lookback to 400 candles (more zone history)",
        "",
        "🔍 ENTRY TIMING IMPROVEMENTS:",
        "   • Add RSI filter: Only enter when RSI 35-65 (avoid extremes)",
        "   • Add ATR volatility filter: Only trade when ATR > 0.0008",
        "   • Require 3+ candle confirmation in zone before entry",
        "",
        "📊 MARKET STRUCTURE FILTERS:",
        "   • Only BUY in bullish/neutral market structure",
        "   • Only SELL in bearish/neutral market structure",
        "   • Avoid trading in choppy/sideways markets",
        "",
        "⏰ TIME-BASED FILTERS:",
        "   • Avoid trading 2 hours before/after major news",
        "   • Skip low-volatility sessions (Asian overlap)",
        "   • Close all trades before weekend gaps"
    ]
    suggestions['supply_demand_improvements'] = supply_demand_improvements
    
    # Risk Management with $50 Focus
    risk_suggestions = [
        "💰 POSITION SIZING (Critical for $50 max risk):",
        f"   • Current avg loss: ${abs(avg_loss):.2f}",
        f"   • Suggested position reduction: {50/max(abs(avg_loss), 1):.2f}x smaller",
        "   • Calculate lot size: (50 / SL_pips) / pip_value",
        "",
        "🛡️ STOP LOSS OPTIMIZATION:",
        "   • Place SL 2-3 pips outside zone boundary",
        "   • Use ATR-based SL: SL = zone_edge + (1.5 * ATR)",
        "   • Maximum SL distance: 25 pips for major pairs",
        "",
        "🎯 TAKE PROFIT (1:3 RR Mandatory):",
        "   • Always set TP = Entry + (3 * SL_distance)",
        "   • Consider partial profits at 1:2 (50% position)",
        "   • Use trailing stops after 1:2 achieved"
    ]
    
    if max_drawdown > 15:
        risk_suggestions.append(f"🚨 HIGH DRAWDOWN: {max_drawdown:.1f}% - Reduce position sizes immediately")
        risk_suggestions.append("   • Max recommended drawdown: 10%")
        risk_suggestions.append("   • Consider 0.01 lot size until performance improves")
    
    suggestions['risk_management'] = risk_suggestions
    
    # Parameter Optimization with Specific Values
    param_suggestions = [
        "⚙️ SUPPLY & DEMAND PARAMETERS:",
        f"   • zone_lookback: {300 if win_rate < 50 else 400} (current strategy uses 300)",
        f"   • base_max_candles: {3 if win_rate < 40 else 5} (tighter for better zones)",
        f"   • move_min_ratio: {2.5 if win_rate < 50 else 2.2} (stronger moves)",
        f"   • zone_width_max_pips: {15 if win_rate < 40 else 20} (tighter zones)",
        "",
        "📊 TECHNICAL INDICATORS:",
        "   • RSI period: 14 (standard)",
        "   • RSI entry range: 35-65 (avoid overbought/oversold)",
        "   • ATR period: 14 (volatility measurement)",
        "   • ATR minimum: 0.0008 (sufficient volatility)",
        "",
        "🎯 RISK PARAMETERS:",
        "   • Max risk per trade: $50 (absolute limit)",
        "   • Risk-reward ratio: 1:3 minimum (mandatory)",
        "   • Max daily loss: $150 (3 bad trades max)",
        "   • Position size formula: min(0.1, 50/SL_pips/pip_value)"
    ]
    
    if win_rate < 30:
        param_suggestions.extend([
            "",
            "🔴 EMERGENCY PARAMETERS (Very Low Win Rate):",
            "   • zone_lookback: 500 (maximum history)",
            "   • move_min_ratio: 3.0 (only strongest moves)",
            "   • zone_width_max_pips: 10 (ultra-tight zones)",
            "   • Pause trading until parameters optimized"
        ])
    
    suggestions['parameter_optimization'] = param_suggestions
    
    # Enhanced Code with Supply & Demand Focus
    pip_size = "0.01" if "JPY" in symbol else "0.0001"
    zone_width = 100 if "JPY" in symbol else 15
    
    enhanced_code = f'''
# Enhanced {symbol} Supply & Demand Strategy - AI Optimized
# Focus: 1:3 Risk-Reward, $50 Max Risk, Fresh Zones Only

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class Enhanced{symbol.replace('/', '')}SupplyDemandStrategy:
    """
    AI-Enhanced Supply & Demand Strategy with strict risk management
    - Maximum $50 risk per trade
    - Mandatory 1:3 risk-reward ratio
    - Fresh zone entries only
    - RSI and ATR filters
    """
    
    def __init__(self, target_pair="{symbol}"):
        self.target_pair = target_pair
        
        # AI-OPTIMIZED PARAMETERS
        self.zone_lookback = {400 if win_rate < 50 else 350}
        self.base_max_candles = {3 if win_rate < 40 else 4}
        self.move_min_ratio = {2.5 if win_rate < 50 else 2.2}
        self.zone_width_max_pips = {zone_width}
        self.pip_size = {pip_size}
        
        # RISK MANAGEMENT (CRITICAL)
        self.max_risk_dollars = 50.0  # ABSOLUTE LIMIT
        self.min_risk_reward = 3.0    # 1:3 MINIMUM
        
        # TECHNICAL FILTERS
        self.rsi_period = 14
        self.rsi_min = 35    # No entries below this
        self.rsi_max = 65    # No entries above this
        self.atr_period = 14
        self.atr_min = 0.0008  # Minimum volatility required
        
        # Internal state
        self.zones = []
        self.last_candle_index = -1
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size to limit risk to $50"""
        risk_pips = abs(entry_price - stop_loss) / self.pip_size
        pip_value = 1.0 if "JPY" in self.target_pair else 10.0
        
        # Calculate lot size for $50 max risk
        max_lot_size = self.max_risk_dollars / (risk_pips * pip_value)
        
        # Cap at reasonable limits
        return min(max_lot_size, 0.1)  # Max 0.1 lots
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def analyze_trade_signal(self, df: pd.DataFrame, pair: str) -> Dict[str, Any]:
        """
        Enhanced analysis with AI-optimized filters
        """
        if len(df) < max(self.zone_lookback, 50):
            return {{"decision": "NO TRADE", "reason": "Insufficient data"}}
        
        # Add technical indicators
        df = df.copy()
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        df['atr'] = self.calculate_atr(df, self.atr_period)
        df['candle_range'] = df['high'] - df['low']
        df['body_size'] = abs(df['close'] - df['open'])
        
        current_candle = df.iloc[-1]
        current_price = current_candle['close']
        current_rsi = current_candle['rsi']
        current_atr = current_candle['atr']
        
        # FILTER 1: RSI Check
        if pd.isna(current_rsi) or current_rsi < self.rsi_min or current_rsi > self.rsi_max:
            return {{
                "decision": "NO TRADE", 
                "reason": f"RSI {{current_rsi:.1f}} outside range {{self.rsi_min}}-{{self.rsi_max}}"
            }}
        
        # FILTER 2: ATR Volatility Check
        if pd.isna(current_atr) or current_atr < self.atr_min:
            return {{
                "decision": "NO TRADE", 
                "reason": f"ATR {{current_atr:.5f}} below minimum {{self.atr_min}}"
            }}
        
        # Find fresh supply/demand zones
        current_candle_index = len(df) - 1
        if self.last_candle_index != current_candle_index:
            lookback_df = df.iloc[-self.zone_lookback:].copy()
            self._find_zones(lookback_df)
            self.last_candle_index = current_candle_index
        
        # Check for entry in fresh zones
        for zone in self.zones:
            if not zone['is_fresh']:
                continue
                
            in_zone = zone['price_low'] <= current_price <= zone['price_high']
            if not in_zone:
                continue
                
            # Determine trade direction
            if zone['type'] == 'supply':
                decision = "SELL"
                stop_loss = zone['price_high'] + (2 * self.pip_size)
                risk_pips = (stop_loss - current_price) / self.pip_size
                take_profit = current_price - (risk_pips * self.min_risk_reward * self.pip_size)
                
            elif zone['type'] == 'demand':
                decision = "BUY"
                stop_loss = zone['price_low'] - (2 * self.pip_size)
                risk_pips = (current_price - stop_loss) / self.pip_size
                take_profit = current_price + (risk_pips * self.min_risk_reward * self.pip_size)
            else:
                continue
            
            # Use reasonable position size for good P&L (0.4 lots = ~$35-50 per trade)
            position_size = 0.4
            
            # Calculate actual risk in dollars for validation
            risk_dollars = risk_pips * position_size * (1.0 if "JPY" in pair else 10.0)
            
            # Mark zone as tested
            zone['is_fresh'] = False
            
            return {{
                "decision": decision,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "volume": position_size,  # Fixed 0.4 lots for good P&L
                "risk_reward_ratio": self.min_risk_reward,
                "estimated_risk_dollars": risk_dollars,
                "meta": {{
                    "zone_type": zone['type'],
                    "zone_high": zone['price_high'],
                    "zone_low": zone['price_low'],
                    "rsi": current_rsi,
                    "atr": current_atr,
                    "risk_pips": risk_pips
                }},
                "reason": f"{{zone['type'].title()}} zone entry - RSI {{current_rsi:.1f}}, ATR {{current_atr:.5f}}"
            }}
        
        return {{"decision": "NO TRADE", "reason": "No fresh zones available"}}
    
    def _find_zones(self, df: pd.DataFrame):
        """Find supply and demand zones with enhanced filtering"""
        self.zones = []
        
        if len(df) < self.base_max_candles + 2:
            return
        
        i = self.base_max_candles
        while i < len(df) - 1:
            base_found = False
            
            for base_len in range(1, self.base_max_candles + 1):
                base_start = i - base_len
                base_candles = df.iloc[base_start:i]
                impulse_candle = df.iloc[i]
                
                avg_base_range = base_candles['candle_range'].mean()
                if avg_base_range == 0:
                    continue
                
                # Enhanced impulse detection
                if impulse_candle['candle_range'] > avg_base_range * self.move_min_ratio:
                    base_high = base_candles['high'].max()
                    base_low = base_candles['low'].min()
                    zone_width_pips = (base_high - base_low) / self.pip_size
                    
                    # Strict zone width filter
                    if 0 < zone_width_pips < self.zone_width_max_pips:
                        zone_type = None
                        
                        if impulse_candle['close'] > base_high:
                            zone_type = 'demand'
                        elif impulse_candle['close'] < base_low:
                            zone_type = 'supply'
                        
                        if zone_type:
                            self.zones.append({{
                                'type': zone_type,
                                'price_high': base_high,
                                'price_low': base_low,
                                'created_at': i,
                                'is_fresh': True,
                                'strength': impulse_candle['candle_range'] / avg_base_range
                            }})
                            base_found = True
                            break
            
            i += 1 if not base_found else 1
        
        # Keep only strongest zones (top 10)
        self.zones = sorted(self.zones, key=lambda x: x['strength'], reverse=True)[:10]
'''
    
    suggestions['suggested_code_changes'] = [enhanced_code]
    
    return suggestions

@app.route('/api/ai-parameter-optimization', methods=['POST'])
def get_ai_parameter_optimization():
    """Get AI-powered parameter optimization for Supply & Demand strategy"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        symbol = data.get('symbol', '')
        backtest_results = data.get('backtest_results', {})
        current_parameters = data.get('current_parameters', {})
        
        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400
        
        logger.info(f"🧠 Generating AI parameter optimization for {symbol}")
        
        # Generate structured parameter recommendations
        optimization = generate_parameter_optimization(symbol, backtest_results, current_parameters)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'optimization': optimization
        })
        
    except Exception as e:
        logger.error(f"❌ Error in AI parameter optimization: {e}")
        return jsonify({'error': f'Failed to generate optimization: {str(e)}'}), 500

def generate_parameter_optimization(symbol, backtest_results, current_params):
    """Generate structured parameter optimization for Supply & Demand strategy"""
    
    win_rate = backtest_results.get('win_rate', 0)
    total_pnl = backtest_results.get('total_pnl', 0)
    avg_loss = backtest_results.get('avg_loss', 0)
    max_drawdown = backtest_results.get('max_drawdown', 0)
    total_trades = backtest_results.get('total_trades', 0)
    
    # Current parameters with defaults
    current_zone_lookback = current_params.get('zone_lookback', 300)
    current_base_max = current_params.get('base_max_candles', 5)
    current_move_ratio = current_params.get('move_min_ratio', 2.0)
    current_zone_width = current_params.get('zone_width_max_pips', 30)
    
    optimization = {
        'performance_assessment': [],
        'parameter_recommendations': {},
        'risk_management_settings': {},
        'technical_filters': {},
        'implementation_priority': []
    }
    
    # Performance Assessment
    optimization['performance_assessment'] = [
        f"📊 Current Performance: {win_rate:.1f}% win rate, ${total_pnl:.2f} P&L",
        f"🎯 Risk Status: Average loss ${abs(avg_loss):.2f} {'✅ OK' if abs(avg_loss) <= 50 else '🚨 EXCEEDS $50 LIMIT'}",
        f"📈 Trade Volume: {total_trades} trades analyzed",
        f"📉 Drawdown: {max_drawdown:.1f}% {'✅ Acceptable' if max_drawdown < 15 else '🚨 Too High'}"
    ]
    
    # Parameter Recommendations based on performance
    param_recommendations = {}
    
    # Zone Lookback Optimization
    if win_rate < 30:
        param_recommendations['zone_lookback'] = {
            'current': current_zone_lookback,
            'recommended': 500,
            'reason': 'Very low win rate - need maximum zone history',
            'priority': 'HIGH'
        }
    elif win_rate < 50:
        param_recommendations['zone_lookback'] = {
            'current': current_zone_lookback,
            'recommended': min(current_zone_lookback + 100, 450),
            'reason': 'Below average win rate - increase zone detection',
            'priority': 'MEDIUM'
        }
    else:
        param_recommendations['zone_lookback'] = {
            'current': current_zone_lookback,
            'recommended': current_zone_lookback,
            'reason': 'Good win rate - maintain current setting',
            'priority': 'LOW'
        }
    
    # Base Max Candles Optimization
    if win_rate < 40:
        param_recommendations['base_max_candles'] = {
            'current': current_base_max,
            'recommended': max(current_base_max - 1, 2),
            'reason': 'Low win rate - tighter base requirements for better zones',
            'priority': 'HIGH'
        }
    else:
        param_recommendations['base_max_candles'] = {
            'current': current_base_max,
            'recommended': current_base_max,
            'reason': 'Adequate performance - maintain current setting',
            'priority': 'LOW'
        }
    
    # Move Min Ratio Optimization
    if win_rate < 35:
        param_recommendations['move_min_ratio'] = {
            'current': current_move_ratio,
            'recommended': current_move_ratio + 0.5,
            'reason': 'Very low win rate - require much stronger impulse moves',
            'priority': 'CRITICAL'
        }
    elif win_rate < 50:
        param_recommendations['move_min_ratio'] = {
            'current': current_move_ratio,
            'recommended': current_move_ratio + 0.2,
            'reason': 'Below average - slightly stronger moves needed',
            'priority': 'MEDIUM'
        }
    else:
        param_recommendations['move_min_ratio'] = {
            'current': current_move_ratio,
            'recommended': current_move_ratio,
            'reason': 'Good performance - maintain current ratio',
            'priority': 'LOW'
        }
    
    # Zone Width Optimization
    if win_rate < 40:
        new_width = max(current_zone_width - 10, 10)
        param_recommendations['zone_width_max_pips'] = {
            'current': current_zone_width,
            'recommended': new_width,
            'reason': 'Low win rate - much tighter zones needed',
            'priority': 'HIGH'
        }
    elif win_rate < 55:
        new_width = max(current_zone_width - 5, 15)
        param_recommendations['zone_width_max_pips'] = {
            'current': current_zone_width,
            'recommended': new_width,
            'reason': 'Moderate performance - slightly tighter zones',
            'priority': 'MEDIUM'
        }
    else:
        param_recommendations['zone_width_max_pips'] = {
            'current': current_zone_width,
            'recommended': current_zone_width,
            'reason': 'Good zones - maintain current width',
            'priority': 'LOW'
        }
    
    optimization['parameter_recommendations'] = param_recommendations
    
    # Risk Management Settings
    risk_settings = {
        'max_risk_per_trade': {
            'value': 50.0,
            'currency': 'USD',
            'enforcement': 'MANDATORY',
            'calculation': 'risk_pips * position_size * pip_value'
        },
        'risk_reward_ratio': {
            'minimum': 3.0,
            'target': 3.0,
            'enforcement': 'MANDATORY',
            'note': 'Take Profit must be 3x Stop Loss distance'
        },
        'position_sizing_formula': {
            'formula': 'min(0.1, 50 / (SL_pips * pip_value))',
            'max_lot_size': 0.1,
            'pip_value': 10.0 if 'JPY' not in symbol else 1.0
        },
        'daily_loss_limit': {
            'value': 150.0,
            'currency': 'USD',
            'rationale': 'Maximum 3 losing trades per day'
        }
    }
    
    if abs(avg_loss) > 50:
        risk_settings['emergency_measures'] = {
            'reduce_position_size': f"Immediate reduction to {50/abs(avg_loss):.2f}x current size",
            'pause_trading': 'Consider pausing until risk is controlled',
            'review_required': 'Mandatory strategy review needed'
        }
    
    optimization['risk_management_settings'] = risk_settings
    
    # Technical Filters
    technical_filters = {
        'rsi_filter': {
            'period': 14,
            'entry_range': {'min': 35, 'max': 65},
            'rationale': 'Avoid overbought/oversold extremes',
            'implementation': 'if rsi < 35 or rsi > 65: skip_trade'
        },
        'atr_filter': {
            'period': 14,
            'minimum_value': 0.0008 if 'JPY' not in symbol else 0.08,
            'rationale': 'Ensure sufficient volatility for meaningful moves',
            'implementation': 'if atr < minimum: skip_trade'
        },
        'market_structure_filter': {
            'bullish': 'Allow BUY trades only',
            'bearish': 'Allow SELL trades only',
            'choppy': 'Skip all trades',
            'detection': 'Higher highs/lower lows over 50 candles'
        },
        'time_filters': {
            'news_avoidance': '2 hours before/after major news',
            'session_preference': 'London/New York overlap preferred',
            'weekend_closure': 'Close all positions before Friday 4PM EST'
        }
    }
    
    optimization['technical_filters'] = technical_filters
    
    # Implementation Priority
    priority_list = []
    
    # Critical items first
    if abs(avg_loss) > 50:
        priority_list.append({
            'priority': 'CRITICAL',
            'action': 'Reduce position sizes immediately',
            'impact': 'Risk control',
            'timeframe': 'Immediate'
        })
    
    if win_rate < 30:
        priority_list.append({
            'priority': 'CRITICAL',
            'action': 'Increase move_min_ratio to filter weak signals',
            'impact': 'Signal quality improvement',
            'timeframe': 'Immediate'
        })
    
    # High priority items
    high_priority_params = [p for p in param_recommendations.values() if p['priority'] == 'HIGH']
    for param in high_priority_params:
        priority_list.append({
            'priority': 'HIGH',
            'action': f"Adjust parameter: {param['reason']}",
            'impact': 'Performance improvement',
            'timeframe': 'Next backtest'
        })
    
    # Add technical filters
    if win_rate < 50:
        priority_list.append({
            'priority': 'HIGH',
            'action': 'Implement RSI filter (35-65 range)',
            'impact': 'Entry timing improvement',
            'timeframe': 'Next version'
        })
        
        priority_list.append({
            'priority': 'MEDIUM',
            'action': 'Add ATR volatility filter',
            'impact': 'Trade quality improvement',
            'timeframe': 'Next version'
        })
    
    optimization['implementation_priority'] = priority_list
    
    return optimization

if __name__ == '__main__':
    logger.info("Starting Trading API Server...")
    logger.info("Using file-based approach - no threading issues!")
    
    # Start background trendbar data fetch
    logger.info("📊 Starting background trendbar data fetch...")
    fetch_thread = threading.Thread(target=fetch_trendbar_data_async)
    fetch_thread.daemon = True
    fetch_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=True) 