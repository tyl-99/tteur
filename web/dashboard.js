// Trading Dashboard JavaScript
class TradingDashboard {
    constructor() {
        this.charts = {};
        this.tradingData = null;
        this.wsConnection = null;
        this.updateInterval = null;
        this.tradesDisplayCount = 30;
        this.tradesFilter = 'all';
        
        this.init();
    }

    async init() {
        this.showLoading(true);
        
        try {
            console.log('🚀 Initializing dashboard...');
            await this.loadTradingData();
            console.log('📈 Initializing charts...');
            this.initializeCharts();
            console.log('📋 Populating trades table...');
            this.populateTradesTable();
            console.log('📊 Updating metrics...');
            this.updateMetrics();
            console.log('🔍 Loading detailed analysis...');
            await this.loadDetailedAnalysis();
            console.log('🎛️ Setting up event listeners...');
            this.setupEventListeners();
            console.log('⏰ Starting real-time updates...');
            this.startRealTimeUpdates();
            console.log('✅ Dashboard initialization complete!');
        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            this.showError('Failed to load trading data');
        } finally {
            this.showLoading(false);
        }
    }

    // Load trading data from API
    async loadTradingData() {
        try {
            console.log('🔄 Loading trading data from API...');
            const response = await fetch('/api/all');
            console.log('📡 API Response status:', response.status, response.statusText);
            
            if (response.ok) {
                const result = await response.json();
                console.log('📊 API Response data:', result);
                
                if (result.status === 'success') {
                    this.tradingData = result.data;
                    console.log('✅ Successfully loaded REAL trading data:', {
                        totalPnL: this.tradingData.summary.totalPnL,
                        totalTrades: this.tradingData.summary.totalTrades,
                        recentTrades: this.tradingData.recentTrades.length
                    });
                    return;
                } else {
                    console.warn('⚠️ API returned non-success status:', result.status);
                }
            } else {
                console.error('❌ API response not OK:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('❌ Failed to load real data, using mock data:', error);
        }

        // Fallback to mock data
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        this.tradingData = {
            summary: {
                totalPnL: 201.75,
                totalTrades: 23,
                winRate: 39.1,
                totalVolume: 928,
                winningTrades: 9,
                losingTrades: 14
            },
            symbolPerformance: [
                { symbol: 'EUR/USD', pnl: 195.18, trades: 3, volume: 170 },
                { symbol: 'USD/JPY', pnl: 123.10, trades: 10, volume: 326 },
                { symbol: 'GBP/USD', pnl: 30.18, trades: 2, volume: 72 },
                { symbol: 'GBP/JPY', pnl: 19.68, trades: 3, volume: 136 },
                { symbol: 'EUR/GBP', pnl: -37.26, trades: 1, volume: 36 },
                { symbol: 'EUR/JPY', pnl: -129.13, trades: 4, volume: 188 }
            ],
            recentTrades: [
                {
                    id: 261823085,
                    time: '2025-06-20 08:30:15',
                    symbol: 'EUR/USD',
                    side: 'BUY',
                    volume: 46.0,
                    entry: 1.08245,
                    exit: 1.08579,
                    pips: 33.4,
                    pnl: 155.94,
                    status: 'FILLED'
                },
                {
                    id: 261822681,
                    time: '2025-06-20 07:45:22',
                    symbol: 'USD/JPY',
                    side: 'BUY',
                    volume: 61.0,
                    entry: 157.234,
                    exit: 157.479,
                    pips: 24.5,
                    pnl: 103.23,
                    status: 'FILLED'
                },
                {
                    id: 261821565,
                    time: '2025-06-20 06:15:33',
                    symbol: 'GBP/USD',
                    side: 'BUY',
                    volume: 33.0,
                    entry: 1.26845,
                    exit: 1.27083,
                    pips: 23.8,
                    pnl: 78.54,
                    status: 'FILLED'
                },
                {
                    id: 261820123,
                    time: '2025-06-20 05:30:41',
                    symbol: 'USD/JPY',
                    side: 'BUY',
                    volume: 26.0,
                    entry: 157.156,
                    exit: 157.446,
                    pips: 29.0,
                    pnl: 52.13,
                    status: 'FILLED'
                },
                {
                    id: 261819876,
                    time: '2025-06-20 04:22:18',
                    symbol: 'USD/JPY',
                    side: 'SELL',
                    volume: 39.0,
                    entry: 157.892,
                    exit: 157.643,
                    pips: 24.9,
                    pnl: 49.71,
                    status: 'FILLED'
                },
                {
                    id: 261818654,
                    time: '2025-06-20 03:45:55',
                    symbol: 'GBP/USD',
                    side: 'SELL',
                    volume: 39.0,
                    entry: 1.26982,
                    exit: 1.27106,
                    pips: -12.4,
                    pnl: -48.36,
                    status: 'FILLED'
                },
                {
                    id: 261817432,
                    time: '2025-06-20 02:18:27',
                    symbol: 'EUR/JPY',
                    side: 'SELL',
                    volume: 49.0,
                    entry: 169.234,
                    exit: 169.583,
                    pips: -34.9,
                    pnl: -49.49,
                    status: 'FILLED'
                }
            ],
            pnlHistory: [
                { date: '2025-06-15', cumulative: -45.23, daily: -45.23 },
                { date: '2025-06-16', cumulative: 12.45, daily: 57.68 },
                { date: '2025-06-17', cumulative: 89.12, daily: 76.67 },
                { date: '2025-06-18', cumulative: 156.78, daily: 67.66 },
                { date: '2025-06-19', cumulative: 178.34, daily: 21.56 },
                { date: '2025-06-20', cumulative: 201.75, daily: 23.41 }
            ]
        };
    }



    initializeCharts() {
        this.initPnLChart();
        this.initSymbolChart();
    }

    initPnLChart() {
        const ctx = document.getElementById('pnlChart').getContext('2d');
        
        this.charts.pnl = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.tradingData.pnlHistory.map(item => {
                    const date = new Date(item.date);
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                }),
                datasets: [
                    {
                        label: 'Cumulative P&L',
                        data: this.tradingData.pnlHistory.map(item => item.cumulative),
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#00ff88',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    },
                    {
                        label: 'Daily P&L',
                        data: this.tradingData.pnlHistory.map(item => item.daily),
                        borderColor: '#ff8c00',
                        backgroundColor: 'rgba(255, 140, 0, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: '#ff8c00',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12,
                                weight: 'bold'
                            },
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#ff8c00',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#b0b0b0',
                            font: {
                                size: 11
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#b0b0b0',
                            font: {
                                size: 11
                            },
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    point: {
                        hoverBorderWidth: 3
                    }
                }
            }
        });
    }

    initSymbolChart() {
        const ctx = document.getElementById('symbolChart').getContext('2d');
        
        const symbolData = this.tradingData.symbolPerformance;
        const profitableSymbols = symbolData.filter(s => s.pnl > 0);
        const losingSymbols = symbolData.filter(s => s.pnl < 0);
        
        this.charts.symbol = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: symbolData.map(s => s.symbol),
                datasets: [{
                    data: symbolData.map(s => Math.abs(s.pnl)),
                    backgroundColor: [
                        '#00ff88', // EUR/USD - Green (profit)
                        '#00d4ff', // USD/JPY - Blue (profit)
                        '#ffb347', // GBP/USD - Orange (profit)
                        '#667eea', // GBP/JPY - Purple (profit)
                        '#ff6b6b', // EUR/GBP - Red (loss)
                        '#ff4757'  // EUR/JPY - Dark red (loss)
                    ],
                    borderColor: '#1a1a1a',
                    borderWidth: 3,
                    hoverBorderWidth: 4,
                    hoverBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        align: 'center',
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 11,
                                weight: 'bold',
                                family: 'Arial, sans-serif'
                            },
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            boxWidth: 15,
                            boxHeight: 15,
                            textAlign: 'center',
                            generateLabels: function(chart) {
                                const data = chart.data;
                                return data.labels.map((label, i) => {
                                    const value = symbolData[i].pnl;
                                    const isProfit = value >= 0;
                                    return {
                                        text: `${label}: ${isProfit ? '+' : ''}$${value.toFixed(2)}`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        strokeStyle: data.datasets[0].backgroundColor[i],
                                        fontColor: '#ffffff',
                                        color: '#ffffff',
                                        pointStyle: 'circle'
                                    };
                                });
                            }
                        },
                        maxWidth: 400,
                        display: true
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#00d4ff',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const symbol = symbolData[context.dataIndex];
                                return [
                                    `P&L: $${symbol.pnl.toFixed(2)}`,
                                    `Trades: ${symbol.trades}`,
                                    `Volume: ${symbol.volume} lots`,
                                    `Click for detailed analysis`
                                ];
                            }
                        }
                    }
                },
                cutout: '60%',
                elements: {
                    arc: {
                        borderRadius: 4
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const symbol = symbolData[index].symbol;
                        this.showCurrencyAnalysis(symbol);
                    }
                }
            }
        });
    }

    populateTradesTable() {
        const tbody = document.getElementById('tradesTableBody');
        tbody.innerHTML = '';

        // Apply filtering
        let filteredTrades = this.tradingData.recentTrades;
        if (this.tradesFilter) {
            switch (this.tradesFilter) {
                case 'profit':
                    filteredTrades = filteredTrades.filter(t => t.pnl >= 0);
                    break;
                case 'loss':
                    filteredTrades = filteredTrades.filter(t => t.pnl < 0);
                    break;
                case 'major-loss':
                    filteredTrades = filteredTrades.filter(t => t.pnl < -50);
                    break;
            }
        }

        // Show specified number of trades
        const count = this.tradesDisplayCount || 30;
        const tradesToShow = filteredTrades.slice(0, count);

        tradesToShow.forEach(trade => {
            const row = document.createElement('tr');
            
            // Enhanced PnL styling with green/red colors
            const pnlClass = trade.pnl >= 0 ? 'trade-profit' : 'trade-loss';
            const pnlColor = trade.pnl >= 0 ? '#00ff88' : '#ff4757';
            const statusClass = trade.status.toLowerCase();
            
            // Format pips to 3 decimal places with proper sign
            const pipsFormatted = trade.pips >= 0 ? `+${trade.pips.toFixed(3)}` : trade.pips.toFixed(3);
            
            // Generate AI analysis for each trade
            const aiAnalysis = this.generateTradeAnalysis(trade);
            
            // AI analysis button for all trades
            const aiAnalysisButton = `<button class="btn-ai-analysis" onclick="window.tradingDashboard.showTradeAnalysis(${trade.id})" title="AI Analysis">
                <i class="fas fa-brain"></i>
            </button>`;
            
            row.innerHTML = `
                <td>${this.formatDateTime(trade.time)}</td>
                <td><strong>${trade.symbol}</strong></td>
                <td><span class="trade-side trade-side-${trade.side.toLowerCase()}">${trade.side}</span></td>
                <td>${trade.volume.toFixed(1)}</td>
                <td>${trade.entry.toFixed(5)}</td>
                <td>${trade.exit.toFixed(5)}</td>
                <td style="color: ${trade.pips >= 0 ? '#00ff88' : '#ff4757'}; font-weight: bold;">${pipsFormatted}</td>
                <td style="color: ${pnlColor}; font-weight: bold;" class="${pnlClass}">$${trade.pnl.toFixed(2)}</td>
                <td>${aiAnalysisButton}</td>
            `;
            
            // Add hover effect and click handler for all trades
            row.style.cursor = 'pointer';
            row.addEventListener('click', () => this.showTradeAnalysis(trade.id));
            row.addEventListener('mouseenter', () => {
                row.style.backgroundColor = 'rgba(0, 255, 136, 0.1)';
            });
            row.addEventListener('mouseleave', () => {
                row.style.backgroundColor = '';
            });
            
            // Store AI analysis data for modal
            row.dataset.aiAnalysis = aiAnalysis;
            
            tbody.appendChild(row);
        });

        // Add customization controls
        this.addTableCustomizationControls();
    }

    generateTradeAnalysis(trade) {
        const isProfit = trade.pnl >= 0;
        const pipsMove = Math.abs(trade.pips);
        const symbol = trade.symbol;
        const side = trade.side;
        
        let analysis = "";
        
        if (isProfit) {
            analysis = `<div class="analysis-section">
                <h5 style="color: #00ff88;"><i class="fas fa-check-circle"></i> Winning Trade Analysis</h5>
                <ul>
                    <li><strong>Market Direction:</strong> Successfully predicted ${side === 'BUY' ? 'upward' : 'downward'} movement in ${symbol}</li>
                    <li><strong>Pip Movement:</strong> Captured ${pipsMove.toFixed(3)} pips in favorable direction</li>
                    <li><strong>Entry Timing:</strong> Good entry point with ${trade.pnl >= 50 ? 'excellent' : 'decent'} profit capture</li>
                    <li><strong>Risk Management:</strong> ${trade.pnl > 100 ? 'Strong position sizing and exit strategy' : 'Moderate profit taking'}</li>
                    <li><strong>Recommendation:</strong> ${trade.pips > 20 ? 'Consider similar setups for this pair' : 'Monitor for larger moves'}</li>
                </ul>
            </div>`;
        } else {
            const lossCategory = Math.abs(trade.pnl) > 50 ? 'Major Loss' : Math.abs(trade.pnl) > 20 ? 'Moderate Loss' : 'Minor Loss';
            
            analysis = `<div class="analysis-section">
                <h5 style="color: #ff4757;"><i class="fas fa-exclamation-triangle"></i> Loss Analysis - ${lossCategory}</h5>
                <ul>
                    <li><strong>Market Direction:</strong> ${symbol} moved ${pipsMove.toFixed(3)} pips against ${side} position</li>
                    <li><strong>Entry Issues:</strong> ${pipsMove > 30 ? 'Poor entry timing - market was trending opposite' : 'Entry timing was reasonable but market reversed'}</li>
                    <li><strong>Risk Management:</strong> ${Math.abs(trade.pnl) > 50 ? 'Consider tighter stop losses' : 'Loss was within acceptable range'}</li>
                    <li><strong>Market Conditions:</strong> ${this.getMarketConditionAnalysis(symbol, trade.pips)}</li>
                    <li><strong>Recommendation:</strong> ${this.getTradeRecommendation(trade)}</li>
                </ul>
                <div class="improvement-suggestions">
                    <h6><i class="fas fa-lightbulb"></i> Improvement Suggestions:</h6>
                    <ul>
                        ${pipsMove > 20 ? '<li>Consider using smaller position sizes in volatile conditions</li>' : ''}
                        ${Math.abs(trade.pnl) > 30 ? '<li>Implement tighter stop-loss levels</li>' : ''}
                        <li>Wait for stronger confirmation signals before entering ${side} positions on ${symbol}</li>
                        <li>Monitor key support/resistance levels more closely</li>
                    </ul>
                </div>
            </div>`;
        }
        
        return analysis;
    }

    getMarketConditionAnalysis(symbol, pips) {
        const volatility = Math.abs(pips);
        if (volatility > 30) {
            return `High volatility detected in ${symbol} - consider reducing position sizes`;
        } else if (volatility > 15) {
            return `Moderate volatility in ${symbol} - normal market conditions`;
        } else {
            return `Low volatility in ${symbol} - tight range trading`;
        }
    }

    getTradeRecommendation(trade) {
        const loss = Math.abs(trade.pnl);
        const pips = Math.abs(trade.pips);
        
        if (loss > 50 && pips > 25) {
            return `Avoid ${trade.side} trades on ${trade.symbol} until trend confirmation`;
        } else if (loss > 30) {
            return `Use smaller position sizes for ${trade.symbol} trades`;
        } else {
            return `Minor loss - continue monitoring ${trade.symbol} for better entry opportunities`;
        }
    }

    addTableCustomizationControls() {
        const existingControls = document.getElementById('tableCustomization');
        if (existingControls) return; // Already added

        const tableContainer = document.querySelector('.trades-table-container');
        if (!tableContainer) return;

        const controlsHTML = `
            <div id="tableCustomization" class="table-controls">
                <div class="control-group">
                    <label>Show trades:</label>
                    <select id="tradesCount" onchange="window.tradingDashboard.updateTradesCount(this.value)">
                        <option value="10">10 trades</option>
                        <option value="20">20 trades</option>
                        <option value="30" selected>30 trades</option>
                        <option value="50">50 trades</option>
                        <option value="100">100 trades</option>
                    </select>
                </div>
                <div class="control-group">
                    <label>Filter by:</label>
                    <select id="tradesFilter" onchange="window.tradingDashboard.filterTrades(this.value)">
                        <option value="all">All trades</option>
                        <option value="profit">Winning trades</option>
                        <option value="loss">Losing trades</option>
                        <option value="major-loss">Major losses only</option>
                    </select>
                </div>
                <div class="control-group">
                    <button class="btn-refresh" onclick="window.tradingDashboard.refreshTradesTable()">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                </div>
            </div>
        `;

        tableContainer.insertAdjacentHTML('beforebegin', controlsHTML);
    }

    updateTradesCount(count) {
        this.tradesDisplayCount = parseInt(count);
        this.populateTradesTable();
    }

    filterTrades(filter) {
        this.tradesFilter = filter;
        this.populateTradesTable();
    }

    refreshTradesTable() {
        this.showNotification('Refreshing trades data...', 'info');
        this.populateTradesTable();
    }

    async showTradeAnalysis(tradeId) {
        try {
            this.showLoading(true);
            
            // Always try to get enhanced AI analysis from API first
            const response = await fetch(`/api/trade-analysis/${tradeId}`);
            const result = await response.json();
            
            if (result.status === 'success') {
                this.displayEnhancedTradeAnalysisModal(result.data);
            } else {
                // Fallback to local analysis
                const trade = this.tradingData.recentTrades.find(t => t.id === tradeId);
                if (trade) {
                    const analysis = this.generateTradeAnalysis(trade);
                    this.displayTradeAnalysisModal({ trade, analysis });
                } else {
                    this.showNotification('Failed to load trade analysis', 'error');
                }
            }
        } catch (error) {
            console.error('Error fetching trade analysis:', error);
            // Fallback to local analysis
            const trade = this.tradingData.recentTrades.find(t => t.id === tradeId);
            if (trade) {
                const analysis = this.generateTradeAnalysis(trade);
                this.displayTradeAnalysisModal({ trade, analysis });
            } else {
                this.showNotification('Error loading trade analysis', 'error');
            }
        } finally {
            this.showLoading(false);
        }
    }

    displayTradeAnalysisModal(data) {
        const trade = data.trade;
        const analysis = data.analysis;
        
        // Create modal HTML
        const modalHTML = `
            <div class="modal-overlay" id="tradeAnalysisModal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3><i class="fas fa-brain"></i> AI Trade Analysis</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="trade-details">
                            <h4>Trade Details</h4>
                            <div class="trade-info-grid">
                                <div class="trade-info-item">
                                    <span class="label">Symbol:</span>
                                    <span class="value">${trade.symbol}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Side:</span>
                                    <span class="value trade-side-${trade.side.toLowerCase()}">${trade.side}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Volume:</span>
                                    <span class="value">${trade.volume} lots</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Entry:</span>
                                    <span class="value">${trade.entry.toFixed(5)}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Exit:</span>
                                    <span class="value">${trade.exit.toFixed(5)}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Pips:</span>
                                    <span class="value ${trade.pips >= 0 ? 'trade-profit' : 'trade-loss'}" style="color: ${trade.pips >= 0 ? '#00ff88' : '#ff4757'}; font-weight: bold;">${trade.pips >= 0 ? '+' : ''}${trade.pips.toFixed(3)}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">P&L:</span>
                                    <span class="value ${trade.pnl >= 0 ? 'trade-profit' : 'trade-loss'}" style="color: ${trade.pnl >= 0 ? '#00ff88' : '#ff4757'}; font-weight: bold;">$${trade.pnl.toFixed(2)}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Duration:</span>
                                    <span class="value">${trade.duration} minutes</span>
                                </div>
                            </div>
                        </div>
                        <div class="ai-analysis">
                            <h4><i class="fas fa-robot"></i> AI Analysis</h4>
                            <div class="analysis-content">
                                ${analysis}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal with animation
        setTimeout(() => {
            document.getElementById('tradeAnalysisModal').classList.add('show');
        }, 10);
    }

    displayEnhancedTradeAnalysisModal(data) {
        const trade = data.trade;
        const analysis = data.analysis;
        
        // Create enhanced modal HTML with candle analysis
        const modalHTML = `
            <div class="modal-overlay" id="enhancedTradeAnalysisModal">
                <div class="modal-content enhanced-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-brain"></i> Enhanced AI Trade Analysis (300 Candles Context)</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="trade-details">
                            <h4>Trade Details</h4>
                            <div class="trade-info-grid">
                                <div class="trade-info-item">
                                    <span class="label">Symbol:</span>
                                    <span class="value">${trade.symbol}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Side:</span>
                                    <span class="value trade-side-${trade.side.toLowerCase()}">${trade.side}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Volume:</span>
                                    <span class="value">${trade.volume} lots</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Entry:</span>
                                    <span class="value">${trade.entry.toFixed(5)}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">Exit:</span>
                                    <span class="value">${trade.exit.toFixed(5)}</span>
                                </div>
                                <div class="trade-info-item">
                                    <span class="label">P&L:</span>
                                    <span class="value ${trade.pnl >= 0 ? 'trade-profit' : 'trade-loss'}" style="color: ${trade.pnl >= 0 ? '#00ff88' : '#ff4757'}; font-weight: bold;">${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}</span>
                                </div>
                                ${analysis.stop_loss ? `
                                <div class="trade-info-item">
                                    <span class="label">Stop Loss:</span>
                                    <span class="value">${analysis.stop_loss.toFixed(5)}</span>
                                </div>` : ''}
                                ${analysis.take_profit ? `
                                <div class="trade-info-item">
                                    <span class="label">Take Profit:</span>
                                    <span class="value">${analysis.take_profit.toFixed(5)}</span>
                                </div>` : ''}
                            </div>
                        </div>
                        
                        ${analysis.strategy_analysis?.strategy_available ? `
                        <div class="strategy-analysis-section">
                            <h4><i class="fas fa-cog"></i> Strategy Analysis</h4>
                            <div class="strategy-info">
                                <div class="strategy-item">
                                    <span class="label">Strategy Type:</span>
                                    <span class="value strategy-type">${analysis.strategy_analysis.strategy_type}</span>
                                </div>
                                ${analysis.strategy_analysis.strategy_parameters ? `
                                <div class="strategy-parameters">
                                    <h5>Strategy Parameters:</h5>
                                    <div class="parameters-grid">
                                        ${Object.entries(analysis.strategy_analysis.strategy_parameters).map(([key, value]) => `
                                            <div class="param-item">
                                                <span class="param-label">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                                                <span class="param-value">${value}</span>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>` : ''}
                                ${analysis.strategy_analysis.strategy_logic ? `
                                <div class="strategy-logic">
                                    <h5>Strategy Logic:</h5>
                                    <ul class="logic-list">
                                        ${analysis.strategy_analysis.strategy_logic.map(logic => `
                                            <li class="logic-item">${logic}</li>
                                        `).join('')}
                                    </ul>
                                </div>` : ''}
                                ${analysis.strategy_analysis.trade_compliance ? `
                                <div class="trade-compliance">
                                    <h5>Trade Compliance Check:</h5>
                                    <div class="compliance-grid">
                                        <div class="compliance-item">
                                            <span class="label">Risk/Reward Ratio:</span>
                                            <span class="value compliance-${analysis.strategy_analysis.trade_compliance.proper_risk_reward?.toLowerCase()}">${analysis.strategy_analysis.trade_compliance.proper_risk_reward || 'Unknown'}</span>
                                        </div>
                                        <div class="compliance-item">
                                            <span class="label">Zone Quality:</span>
                                            <span class="value compliance-${analysis.strategy_analysis.trade_compliance.zone_quality?.toLowerCase()}">${analysis.strategy_analysis.trade_compliance.zone_quality || 'Unknown'}</span>
                                        </div>
                                    </div>
                                </div>` : ''}
                                ${analysis.strategy_analysis.strategy_violations?.length > 0 ? `
                                <div class="strategy-violations">
                                    <h5>Strategy Violations:</h5>
                                    <div class="violations-list">
                                        ${analysis.strategy_analysis.strategy_violations.map(violation => `
                                            <div class="violation-item ${violation.includes('🔴') ? 'violation-error' : 'violation-warning'}">
                                                ${violation}
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>` : ''}
                            </div>
                        </div>` : ''}

                        <div class="candle-analysis-section">
                            <h4><i class="fas fa-chart-candlestick"></i> Candle Data Analysis</h4>
                            <div class="analysis-stats">
                                <div class="stat-item">
                                    <span class="stat-label">Total Candles Analyzed:</span>
                                    <span class="stat-value">${analysis.total_candles_analyzed || 0}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Pre-Entry Candles:</span>
                                    <span class="stat-value">${analysis.pre_entry_candles || 0}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Trade Duration (Candles):</span>
                                    <span class="stat-value">${analysis.trade_duration_candles || 0}</span>
                                </div>
                            </div>
                        </div>

                        ${analysis.market_conditions ? `
                        <div class="market-conditions-section">
                            <h4><i class="fas fa-chart-line"></i> Market Conditions (300 Candles Before Entry)</h4>
                            <div class="conditions-grid">
                                <div class="condition-item">
                                    <span class="label">Trend Direction:</span>
                                    <span class="value trend-${analysis.market_conditions.trend_direction?.toLowerCase()}">${analysis.market_conditions.trend_direction || 'Unknown'}</span>
                                </div>
                                <div class="condition-item">
                                    <span class="label">RSI at Entry:</span>
                                    <span class="value">${analysis.market_conditions.rsi_at_entry?.toFixed(1) || 'N/A'}</span>
                                </div>
                                <div class="condition-item">
                                    <span class="label">Market Structure:</span>
                                    <span class="value">${analysis.market_conditions.market_structure || 'Unknown'}</span>
                                </div>
                                <div class="condition-item">
                                    <span class="label">Distance to Recent High:</span>
                                    <span class="value">${analysis.market_conditions.distance_to_high_pct?.toFixed(2) || 'N/A'}%</span>
                                </div>
                                <div class="condition-item">
                                    <span class="label">Distance to Recent Low:</span>
                                    <span class="value">${analysis.market_conditions.distance_to_low_pct?.toFixed(2) || 'N/A'}%</span>
                                </div>
                            </div>
                        </div>` : ''}

                        ${analysis.failure_analysis ? `
                        <div class="failure-analysis-section">
                            <h4><i class="fas fa-exclamation-triangle"></i> Trade Execution Analysis</h4>
                            <div class="failure-grid">
                                <div class="failure-item">
                                    <span class="label">Max Drawdown:</span>
                                    <span class="value ${analysis.failure_analysis.max_drawdown_pct > 2 ? 'text-danger' : ''}">${analysis.failure_analysis.max_drawdown_pct?.toFixed(2) || 'N/A'}%</span>
                                </div>
                                <div class="failure-item">
                                    <span class="label">Max Favorable Move:</span>
                                    <span class="value">${analysis.failure_analysis.max_favorable_pct?.toFixed(2) || 'N/A'}%</span>
                                </div>
                                <div class="failure-item">
                                    <span class="label">Trade Went Favorable First:</span>
                                    <span class="value">${analysis.failure_analysis.trade_went_favorable_first ? 'Yes' : 'No'}</span>
                                </div>
                                <div class="failure-item">
                                    <span class="label">Exit Reason:</span>
                                    <span class="value">${analysis.failure_analysis.final_exit_reason || 'Unknown'}</span>
                                </div>
                            </div>
                        </div>` : ''}
                        
                        <div class="ai-insights-section">
                            <h4><i class="fas fa-robot"></i> AI Loss Analysis & Insights</h4>
                            <div class="insights-list">
                                ${analysis.ai_loss_insights?.map(insight => `
                                    <div class="insight-item ${insight.includes('🔴') ? 'insight-error' : insight.includes('⚠️') ? 'insight-warning' : insight.includes('✅') ? 'insight-success' : 'insight-info'}">
                                        <span class="insight-text">${insight}</span>
                                    </div>
                                `).join('') || '<div class="insight-item">No insights available</div>'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal with animation
        setTimeout(() => {
            document.getElementById('enhancedTradeAnalysisModal').classList.add('show');
        }, 10);
    }

    updateMetrics() {
        const data = this.tradingData.summary;
        
        // Update metric values with animation
        this.animateValue('totalPnL', 0, data.totalPnL, 1000, (value) => `$${value.toFixed(2)}`);
        this.animateValue('totalTrades', 0, data.totalTrades, 800);
        this.animateValue('winRate', 0, data.winRate, 1200, (value) => `${value.toFixed(1)}%`);
        this.animateValue('totalVolume', 0, data.totalVolume, 900);
        
        // Update change indicators
        this.updateChangeIndicators();
    }

    updateChangeIndicators() {
        // Simulate real-time changes
        const indicators = [
            { id: 'totalPnL', change: 12.3, positive: true },
            { id: 'winRate', change: -2.1, positive: false },
            { id: 'totalVolume', change: 0, neutral: true }
        ];
        
        // This would be updated with real data in production
    }

    animateValue(elementId, start, end, duration, formatter = null) {
        const element = document.getElementById(elementId);
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function
            const easeOutCubic = 1 - Math.pow(1 - progress, 3);
            const current = start + (end - start) * easeOutCubic;
            
            element.textContent = formatter ? formatter(current) : Math.round(current);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    setupEventListeners() {
        // Sidebar toggle
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('show');
                mainContent.classList.toggle('sidebar-collapsed');
            });
        }

        // Navigation links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remove active class from all nav items
                document.querySelectorAll('.nav-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Add active class to clicked item
                e.target.closest('.nav-item').classList.add('active');
                
                // Handle navigation (for now just show notification)
                const section = e.target.closest('.nav-link').getAttribute('href').replace('#', '');
                this.showNotification(`Navigated to ${section.charAt(0).toUpperCase() + section.slice(1)}`, 'info');
            });
        });

        // Chart period buttons
        document.querySelectorAll('.btn-chart').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.btn-chart').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.updateChartPeriod(e.target.dataset.period);
            });
        });

        // Refresh button
        document.getElementById('refreshTrades').addEventListener('click', () => {
            this.refreshData();
        });

        // Refresh analysis button
        const refreshAnalysisBtn = document.getElementById('refreshAnalysis');
        if (refreshAnalysisBtn) {
            refreshAnalysisBtn.addEventListener('click', async () => {
                await this.loadDetailedAnalysis();
            });
        }

        // Window resize handler
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => {
                chart.resize();
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshData();
                        break;
                    case 'f':
                        e.preventDefault();
                        this.toggleFullscreen();
                        break;
                }
            }
        });
    }

    updateChartPeriod(period) {
        // In production, this would fetch data for the selected period
        console.log(`Updating charts for period: ${period}`);
        
        // Show loading state
        this.showLoading(true);
        
        // Simulate data fetch
        setTimeout(() => {
            // Update chart data based on period
            this.showLoading(false);
        }, 500);
    }

    async refreshData() {
        const refreshBtn = document.getElementById('refreshTrades');
        const icon = refreshBtn.querySelector('i');
        
        // Add spinning animation
        icon.classList.add('fa-spin');
        refreshBtn.disabled = true;
        
        try {
            await this.loadTradingData();
            this.updateMetrics();
            this.populateTradesTable();
            this.updateCharts();
            
            // Show success feedback
            this.showNotification('Data refreshed successfully', 'success');
        } catch (error) {
            console.error('Refresh failed:', error);
            this.showNotification('Failed to refresh data', 'error');
        } finally {
            // Remove spinning animation
            icon.classList.remove('fa-spin');
            refreshBtn.disabled = false;
        }
    }

    updateCharts() {
        // Update P&L chart
        if (this.charts.pnl) {
            this.charts.pnl.data.datasets[0].data = this.tradingData.pnlHistory.map(item => item.cumulative);
            this.charts.pnl.data.datasets[1].data = this.tradingData.pnlHistory.map(item => item.daily);
            this.charts.pnl.update('active');
        }

        // Update symbol chart
        if (this.charts.symbol) {
            this.charts.symbol.data.datasets[0].data = this.tradingData.symbolPerformance.map(s => Math.abs(s.pnl));
            this.charts.symbol.update('active');
        }
    }

    startRealTimeUpdates() {
        // Update timestamp every second
        setInterval(() => {
            document.getElementById('lastUpdate').textContent = this.formatDateTime(new Date());
        }, 1000);

        // Simulate real-time data updates every 30 seconds
        this.updateInterval = setInterval(() => {
            this.simulateRealTimeUpdate();
        }, 30000);
    }

    simulateRealTimeUpdate() {
        // In production, this would receive real-time data via WebSocket
        // For demo, we'll simulate small changes
        
        const variation = (Math.random() - 0.5) * 10; // Random change between -5 and +5
        this.tradingData.summary.totalPnL += variation;
        
        // Update display
        document.getElementById('totalPnL').textContent = `$${this.tradingData.summary.totalPnL.toFixed(2)}`;
        
        // Add subtle pulse animation
        const element = document.getElementById('totalPnL');
        element.style.transform = 'scale(1.05)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    formatDateTime(dateTime) {
        const date = new Date(dateTime);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    async showCurrencyAnalysis(symbol) {
        try {
            this.showLoading(true);
            
            // Encode the symbol to handle forward slashes
            const encodedSymbol = encodeURIComponent(symbol);
            console.log(`Fetching analysis for: ${symbol} (encoded: ${encodedSymbol})`);
            
            const response = await fetch(`/api/currency-analysis/${encodedSymbol}`);
            
            // Check if response is OK first
            if (!response.ok) {
                console.error(`HTTP Error: ${response.status} ${response.statusText}`);
                this.showNotification(`Server error loading ${symbol} analysis: ${response.status}`, 'error');
                return;
            }
            
            // Check content type to make sure it's JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.error('Response is not JSON:', contentType);
                const text = await response.text();
                console.error('Response text:', text.substring(0, 200));
                this.showNotification(`Invalid response format for ${symbol} analysis`, 'error');
                return;
            }
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.displayCurrencyAnalysisModal(symbol, result.data);
            } else {
                console.error('API Error:', result);
                this.showNotification(`Failed to load analysis for ${symbol}: ${result.message || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error fetching currency analysis:', error);
            this.showNotification(`Error loading ${symbol} analysis: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    displayCurrencyAnalysisModal(symbol, data) {
        // Validate data before displaying
        if (!data) {
            this.showNotification(`No data available for ${symbol}`, 'error');
            return;
        }
        
        // Set default values for missing data
        const safeData = {
            totalPnL: data.totalPnL || 0,
            winRate: data.winRate || 0,
            totalTrades: data.totalTrades || 0,
            profitFactor: data.profitFactor || 0,
            bestTrade: data.bestTrade || 0,
            worstTrade: data.worstTrade || 0,
            maxDrawdown: data.maxDrawdown || 0,
            avgTradeSize: data.avgTradeSize || 0,
            aiInsights: data.aiInsights || [`AI analysis for ${symbol} is being generated...`],
            marketAnalysis: data.marketAnalysis || `AI strategy analysis for ${symbol} is being processed...`,
            recommendations: data.recommendations || [`AI recommendations for ${symbol} being generated...`],
            strategyCode: data.strategyCode || '',
            strategyImprovements: data.strategyImprovements || [],
            recentTrades: data.recentTrades || []
        };
        
        // Create comprehensive currency analysis modal
        const modalHTML = `
            <div class="modal-overlay" id="currencyAnalysisModal">
                <div class="modal-content currency-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-chart-line"></i> ${symbol} Detailed Analysis</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <!-- Performance Overview -->
                        <div class="currency-section">
                            <h4><i class="fas fa-trophy"></i> Performance Overview</h4>
                            <div class="currency-metrics-grid">
                                <div class="metric-card ${safeData.totalPnL >= 0 ? 'positive' : 'negative'}">
                                    <div class="metric-value">$${safeData.totalPnL.toFixed(2)}</div>
                                    <div class="metric-label">Total P&L</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-value">${safeData.winRate.toFixed(1)}%</div>
                                    <div class="metric-label">Win Rate</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-value">${safeData.totalTrades}</div>
                                    <div class="metric-label">Total Trades</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-value">${safeData.profitFactor.toFixed(2)}</div>
                                    <div class="metric-label">Profit Factor</div>
                                </div>
                            </div>
                        </div>

                        <!-- Risk Analysis -->
                        <div class="currency-section">
                            <h4><i class="fas fa-shield-alt"></i> Risk Analysis</h4>
                            <div class="risk-metrics">
                                <div class="risk-item">
                                    <span class="risk-label">Best Trade:</span>
                                    <span class="risk-value positive">$${safeData.bestTrade.toFixed(2)}</span>
                                </div>
                                <div class="risk-item">
                                    <span class="risk-label">Worst Trade:</span>
                                    <span class="risk-value negative">$${safeData.worstTrade.toFixed(2)}</span>
                                </div>
                                <div class="risk-item">
                                    <span class="risk-label">Max Drawdown:</span>
                                    <span class="risk-value negative">$${safeData.maxDrawdown.toFixed(2)}</span>
                                </div>
                                <div class="risk-item">
                                    <span class="risk-label">Avg Trade Size:</span>
                                    <span class="risk-value">${safeData.avgTradeSize.toFixed(1)} lots</span>
                                </div>
                            </div>
                        </div>

                        <!-- AI Strategy Analysis -->
                        <div class="currency-section">
                            <h4><i class="fas fa-brain"></i> AI Strategy Analysis</h4>
                            <div class="strategy-analysis-content">
                                <div class="strategy-overview">
                                    <h5><i class="fas fa-code"></i> Strategy Overview</h5>
                                    <p>${safeData.marketAnalysis}</p>
                                </div>
                                
                                ${safeData.strategyCode ? `
                                <div class="strategy-code-preview">
                                    <h5><i class="fas fa-file-code"></i> Current Strategy Code (Preview)</h5>
                                    <div class="code-preview">
                                        <pre><code>${safeData.strategyCode}</code></pre>
                                        <div class="code-note">📝 Showing first 1000 characters of strategy file</div>
                                    </div>
                                </div>
                                ` : ''}
                            </div>
                        </div>

                        <!-- AI Performance Insights -->
                        <div class="currency-section">
                            <h4><i class="fas fa-chart-line"></i> AI Performance Insights</h4>
                            <div class="ai-insights-list">
                                ${safeData.aiInsights.map(insight => `
                                    <div class="insight-item">
                                        <i class="fas fa-lightbulb"></i>
                                        <span>${insight}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <!-- AI Strategy Improvements -->
                        ${safeData.strategyImprovements && safeData.strategyImprovements.length > 0 ? `
                        <div class="currency-section">
                            <h4><i class="fas fa-tools"></i> AI Strategy Improvements</h4>
                            <div class="improvements-list">
                                ${safeData.strategyImprovements.map(improvement => `
                                    <div class="improvement-item">
                                        <i class="fas fa-wrench"></i>
                                        <span>${improvement}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}

                        <!-- AI Recommendations -->
                        <div class="currency-section">
                            <h4><i class="fas fa-bullhorn"></i> AI Recommendations</h4>
                            <div class="recommendations-list">
                                ${safeData.recommendations.map(rec => `
                                    <div class="recommendation-item">
                                        <i class="fas fa-arrow-right"></i>
                                        <span>${rec}</span>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="action-buttons">
                                <button class="btn-primary" onclick="tradingDashboard.openStrategyEditor('${symbol}')">
                                    <i class="fas fa-edit"></i> Edit Strategy
                                </button>
                                <button class="btn-secondary" onclick="tradingDashboard.runBacktest('${symbol}')">
                                    <i class="fas fa-play"></i> Run Backtest
                                </button>
                                <button class="btn-ai" onclick="tradingDashboard.getAIStrategySuggestions('${symbol}', {
                                    win_rate: ${safeData.winRate},
                                    total_pnl: ${safeData.totalPnL},
                                    max_drawdown: ${safeData.maxDrawdown},
                                    total_trades: ${safeData.totalTrades}
                                })">
                                    🧠 AI Suggestions
                                </button>
                                <button class="btn-ai-auto" onclick="tradingDashboard.getAIStrategySuggestions('${symbol}', {
                                    win_rate: ${safeData.winRate},
                                    total_pnl: ${safeData.totalPnL},
                                    max_drawdown: ${safeData.maxDrawdown},
                                    total_trades: ${safeData.totalTrades}
                                }, true)">
                                    ⚡ Auto-Apply AI Fix
                                </button>
                            </div>
                        </div>

                        <!-- Recent Trades -->
                        ${safeData.recentTrades && safeData.recentTrades.length > 0 ? `
                        <div class="currency-section">
                            <h4><i class="fas fa-history"></i> Recent Trades</h4>
                            <div class="recent-trades-table">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Time</th>
                                            <th>Side</th>
                                            <th>Entry</th>
                                            <th>Exit</th>
                                            <th>Pips</th>
                                            <th>P&L</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${safeData.recentTrades.map(trade => `
                                            <tr>
                                                <td>${this.formatDateTime(trade.time)}</td>
                                                <td><span class="trade-side-${trade.side.toLowerCase()}">${trade.side}</span></td>
                                                <td>${trade.entry.toFixed(5)}</td>
                                                <td>${trade.exit.toFixed(5)}</td>
                                                <td>${trade.pips > 0 ? '+' : ''}${trade.pips.toFixed(1)}</td>
                                                <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">$${trade.pnl.toFixed(2)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">
                            Close Analysis
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal with animation
        setTimeout(() => {
            document.getElementById('currencyAnalysisModal').classList.add('show');
        }, 10);
    }

    async loadDetailedAnalysis() {
        // Placeholder for detailed analysis loading
        // This prevents the init function from failing
        console.log('📊 Detailed analysis loading (placeholder)');
        return Promise.resolve();
    }

    openStrategyEditor(symbol) {
        // Open strategy editor for the specific currency pair
        this.showNotification(`Loading strategy editor for ${symbol}...`, 'info');
        this.showStrategyEditorModal(symbol);
    }
    
    async showStrategyEditorModal(symbol) {
        try {
            // Get current strategy code
            const response = await fetch(`/api/get-strategy-code/${encodeURIComponent(symbol)}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showNotification(`Error: ${data.error}`, 'error');
                return;
            }
            
            const modalHTML = `
                <div class="modal-overlay" id="strategyEditorModal">
                    <div class="modal-content" style="max-width: 1000px; max-height: 90vh;">
                        <div class="modal-header">
                            <h2>💻 Strategy Editor - ${symbol}</h2>
                            <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                        </div>
                        <div class="modal-body" style="overflow-y: auto;">
                            <div class="strategy-editor-container">
                                <div class="editor-info">
                                    <p><strong>File:</strong> ${data.strategy_file}</p>
                                    <p><strong>Currency Pair:</strong> ${symbol}</p>
                                </div>
                                
                                <div class="editor-wrapper">
                                    <textarea id="strategyCodeEditor" 
                                              style="width: 100%; height: 400px; font-family: 'Courier New', monospace; font-size: 12px; border: 1px solid #444; background: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 4px;"
                                              placeholder="Loading strategy code...">${data.strategy_code}</textarea>
                                </div>
                                
                                <div class="editor-actions" style="margin-top: 1rem; display: flex; gap: 1rem; justify-content: space-between;">
                                    <div>
                                        <button class="btn-primary" onclick="tradingDashboard.saveStrategyCode('${symbol}')">
                                            💾 Save Strategy
                                        </button>
                                        <button class="btn-secondary" onclick="tradingDashboard.resetStrategyCode('${symbol}')">
                                            🔄 Reset
                                        </button>
                                    </div>
                                    <div>
                                        <button class="btn-success" onclick="tradingDashboard.runBacktestFromEditor('${symbol}')">
                                            🚀 Run Backtest
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Show modal with animation
            setTimeout(() => {
                document.getElementById('strategyEditorModal').classList.add('show');
            }, 10);
            
        } catch (error) {
            console.error('Error loading strategy editor:', error);
            this.showNotification('Failed to load strategy editor', 'error');
        }
    }
    
    async saveStrategyCode(symbol) {
        try {
            const codeEditor = document.getElementById('strategyCodeEditor');
            if (!codeEditor) {
                this.showNotification('Editor not found', 'error');
                return;
            }
            
            const strategyCode = codeEditor.value;
            if (!strategyCode.trim()) {
                this.showNotification('Strategy code cannot be empty', 'error');
                return;
            }
            
            this.showNotification('Saving strategy...', 'info');
            
            const response = await fetch('/api/save-strategy-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: symbol,
                    strategy_code: strategyCode
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Strategy saved successfully for ${symbol}!`, 'success');
            } else {
                this.showNotification(`Error: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error saving strategy:', error);
            this.showNotification('Failed to save strategy', 'error');
        }
    }
    
    async resetStrategyCode(symbol) {
        if (confirm('Are you sure you want to reset the strategy code? This will reload the original code.')) {
            // Reload the strategy editor modal
            document.getElementById('strategyEditorModal').remove();
            this.showStrategyEditorModal(symbol);
        }
    }
    
    async runBacktestFromEditor(symbol) {
        const codeEditor = document.getElementById('strategyCodeEditor');
        if (!codeEditor) {
            this.showNotification('Editor not found', 'error');
            return;
        }
        
        const strategyCode = codeEditor.value;
        this.runBacktest(symbol, strategyCode);
    }
    
    async runBacktest(symbol, strategyCode = null) {
        try {
            // If no strategy code provided, get it from the server
            if (!strategyCode) {
                const response = await fetch(`/api/get-strategy-code/${encodeURIComponent(symbol)}`);
                const data = await response.json();
                
                if (!data.success) {
                    this.showNotification(`Error getting strategy: ${data.error}`, 'error');
                    return;
                }
                
                strategyCode = data.strategy_code;
            }
            
            this.showNotification(`Starting backtest for ${symbol}...`, 'info');
            
            // Show backtest modal with loading state
            this.showBacktestModal(symbol, null, true);
            
            // Run backtest
            const response = await fetch('/api/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    currency_pair: symbol,
                    strategy_code: strategyCode,
                    initial_balance: 1000
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Backtest completed for ${symbol}!`, 'success');
                this.showBacktestModal(symbol, data.results, false);
            } else {
                this.showNotification(`Backtest failed: ${data.error}`, 'error');
                this.showBacktestModal(symbol, null, false, data.error);
            }
            
        } catch (error) {
            console.error('Error running backtest:', error);
            this.showNotification('Failed to run backtest', 'error');
            this.showBacktestModal(symbol, null, false, 'Network error occurred');
        }
    }
    
    showBacktestModal(symbol, results, isLoading, errorMessage = null) {
        // Remove existing modal if present
        const existingModal = document.getElementById('backtestModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        let modalContent = '';
        
        if (isLoading) {
            modalContent = `
                <div class="loading-state" style="text-align: center; padding: 2rem;">
                    <div class="loading-spinner" style="margin: 0 auto 1rem;"></div>
                    <h3>🚀 Running Backtest for ${symbol}</h3>
                    <p>Testing strategy against historical data...</p>
                    <p style="color: #888; font-size: 0.9rem;">This may take a few moments</p>
                </div>
            `;
        } else if (errorMessage) {
            modalContent = `
                <div class="error-state" style="text-align: center; padding: 2rem;">
                    <h3 style="color: var(--danger);">❌ Backtest Failed</h3>
                    <p>${errorMessage}</p>
                    <button class="btn-primary" onclick="tradingDashboard.runBacktest('${symbol}')">
                        🔄 Try Again
                    </button>
                </div>
            `;
        } else if (results) {
            modalContent = `
                <div class="backtest-results">
                    <div class="results-summary" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
                        <div class="metric-card">
                            <h4>💰 Final Balance</h4>
                            <div class="metric-value ${results.total_pnl >= 0 ? 'positive' : 'negative'}">
                                $${results.final_balance.toFixed(2)}
                            </div>
                            <div class="metric-change">
                                ${results.total_pnl >= 0 ? '+' : ''}$${results.total_pnl.toFixed(2)}
                            </div>
                        </div>
                        
                        <div class="metric-card">
                            <h4>📊 Win Rate</h4>
                            <div class="metric-value ${results.win_rate >= 50 ? 'positive' : 'negative'}">
                                ${results.win_rate.toFixed(1)}%
                            </div>
                            <div class="metric-change">
                                ${results.winning_trades}W / ${results.losing_trades}L
                            </div>
                        </div>
                        
                        <div class="metric-card">
                            <h4>📈 Total Trades</h4>
                            <div class="metric-value">
                                ${results.total_trades}
                            </div>
                            <div class="metric-change">
                                ${results.total_trades > 0 ? 'Strategy active' : 'No trades'}
                            </div>
                        </div>
                        
                        <div class="metric-card">
                            <h4>📉 Max Drawdown</h4>
                            <div class="metric-value ${results.max_drawdown > 20 ? 'negative' : results.max_drawdown > 10 ? 'warning' : 'positive'}">
                                ${results.max_drawdown.toFixed(1)}%
                            </div>
                            <div class="metric-change">
                                Peak: $${results.peak_balance.toFixed(2)}
                            </div>
                        </div>
                    </div>
                    
                    ${results.trades && results.trades.length > 0 ? `
                        <div class="trades-table-container">
                            <h4>📋 Trade History (Last 10 Trades)</h4>
                            <div class="table-wrapper" style="max-height: 300px; overflow-y: auto;">
                                <table class="trades-table">
                                    <thead>
                                        <tr>
                                            <th>Entry Time</th>
                                            <th>Direction</th>
                                            <th>Entry</th>
                                            <th>Exit</th>
                                            <th>Pips</th>
                                            <th>P&L</th>
                                            <th>Exit Reason</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${results.trades.slice(-10).reverse().map(trade => `
                                            <tr>
                                                <td>${this.formatDateTime(trade.entry_time)}</td>
                                                <td><span class="trade-side-${trade.direction.toLowerCase()}">${trade.direction}</span></td>
                                                <td>${trade.entry_price.toFixed(5)}</td>
                                                <td>${trade.exit_price.toFixed(5)}</td>
                                                <td>${trade.pips_gained > 0 ? '+' : ''}${trade.pips_gained.toFixed(1)}</td>
                                                <td class="${trade.usd_pnl >= 0 ? 'positive' : 'negative'}">$${trade.usd_pnl.toFixed(2)}</td>
                                                <td>${trade.exit_reason}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ` : `
                        <div class="no-trades" style="text-align: center; padding: 2rem; color: #888;">
                            <h4>📭 No Trades Generated</h4>
                            <p>The strategy did not generate any trades during the backtest period.</p>
                            <p>Consider adjusting strategy parameters or checking entry conditions.</p>
                        </div>
                    `}
                    
                    <div class="backtest-actions" style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                        <button class="btn-primary" onclick="tradingDashboard.openStrategyEditor('${symbol}')">
                            ✏️ Edit Strategy
                        </button>
                        <button class="btn-ai" onclick="tradingDashboard.getAIStrategySuggestions('${symbol}', ${JSON.stringify(results).replace(/"/g, '&quot;')})">
                            🧠 AI Suggestions
                        </button>
                        <button class="btn-secondary" onclick="tradingDashboard.getParameterOptimization('${symbol}', ${JSON.stringify(results).replace(/"/g, '&quot;')})">
                            ⚙️ Parameter Optimization
                        </button>
                        <button class="btn-ai-auto" onclick="tradingDashboard.getAIStrategySuggestions('${symbol}', ${JSON.stringify(results).replace(/"/g, '&quot;')}, true)">
                            ⚡ Auto-Apply AI Fix
                        </button>
                        <button class="btn-secondary" onclick="tradingDashboard.runBacktest('${symbol}')">
                            🔄 Run Again
                        </button>
                    </div>
                </div>
            `;
        }
        
        const modalHTML = `
            <div class="modal-overlay" id="backtestModal">
                <div class="modal-content" style="max-width: 1000px; max-height: 90vh;">
                    <div class="modal-header">
                        <h2>🧪 Backtest Results - ${symbol}</h2>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body" style="overflow-y: auto;">
                        ${modalContent}
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal with animation
        setTimeout(() => {
            document.getElementById('backtestModal').classList.add('show');
        }, 10);
    }

    async getAIStrategySuggestions(symbol, backtestResults, autoApply = false) {
        try {
            const action = autoApply ? 'Generating and auto-applying AI improvements...' : 'Generating AI strategy suggestions...';
            this.showNotification(`🧠 ${action}`, 'info');
            
            // Get current strategy code
            const strategyResponse = await fetch(`/api/get-strategy-code/${encodeURIComponent(symbol)}`);
            const strategyData = await strategyResponse.json();
            
            if (!strategyData.success) {
                this.showNotification('Failed to load current strategy', 'error');
                return;
            }
            
            // Get AI suggestions with optional auto-apply
            const response = await fetch('/api/ai-strategy-suggestions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: symbol,
                    current_strategy: strategyData.strategy_code,
                    backtest_results: backtestResults,
                    auto_apply: autoApply
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Handle auto-apply results
                if (autoApply) {
                    if (data.auto_applied) {
                        this.showNotification(`🎉 AI improvements auto-applied to ${data.applied_to}!`, 'success');
                        this.showAISuggestionsModal(symbol, data.suggestions, true);
                        
                        // Ask if user wants to run backtest with new strategy
                        setTimeout(() => {
                            if (confirm('AI strategy auto-applied! Would you like to run a backtest with the enhanced strategy?')) {
                                this.runBacktest(symbol);
                            }
                        }, 1000);
                    } else {
                        const errorMsg = data.auto_apply_error || 'Unknown error';
                        this.showNotification(`⚠️ Auto-apply failed: ${errorMsg}`, 'warning');
                        this.showAISuggestionsModal(symbol, data.suggestions, false);
                    }
                } else {
                    this.showAISuggestionsModal(symbol, data.suggestions);
                    this.showNotification('🧠 AI suggestions generated!', 'success');
                }
            } else {
                this.showNotification(`Failed to generate suggestions: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error getting AI suggestions:', error);
            this.showNotification('Failed to get AI suggestions', 'error');
        }
    }
    
    showAISuggestionsModal(symbol, suggestions, autoApplied = false) {
        // Remove existing modal if present
        const existingModal = document.getElementById('aiSuggestionsModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modalHTML = `
            <div class="modal-overlay" id="aiSuggestionsModal">
                <div class="modal-content" style="max-width: 1200px; max-height: 90vh;">
                    <div class="modal-header">
                        <h2>🧠 AI Strategy Suggestions - ${symbol} ${autoApplied ? '✅ (Auto-Applied)' : ''}</h2>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body" style="overflow-y: auto;">
                        <div class="ai-suggestions-container">
                            
                            <!-- Performance Analysis -->
                            <div class="suggestion-section">
                                <h3>📊 Performance Analysis</h3>
                                <div class="suggestion-list">
                                    ${suggestions.performance_analysis.map(item => `<div class="suggestion-item">${item}</div>`).join('')}
                                </div>
                            </div>
                            
                            <!-- Supply & Demand Improvements -->
                            <div class="suggestion-section">
                                <h3>🎯 Supply & Demand Improvements</h3>
                                <div class="suggestion-list">
                                    ${(suggestions.supply_demand_improvements || suggestions.technical_improvements || []).map(item => `<div class="suggestion-item">${item}</div>`).join('')}
                                </div>
                            </div>
                            
                            <!-- Risk Management (1:3 RR & $50 Max Risk) -->
                            <div class="suggestion-section">
                                <h3>🛡️ Risk Management ($50 Max Risk)</h3>
                                <div class="suggestion-list">
                                    ${suggestions.risk_management.map(item => `<div class="suggestion-item">${item}</div>`).join('')}
                                </div>
                            </div>
                            
                            <!-- Parameter Optimization -->
                            <div class="suggestion-section">
                                <h3>⚙️ Parameter Optimization</h3>
                                <div class="suggestion-list">
                                    ${(suggestions.parameter_optimization || suggestions.entry_exit_optimization || []).map(item => `<div class="suggestion-item">${item}</div>`).join('')}
                                </div>
                            </div>
                            
                            <!-- Suggested Code -->
                            <div class="suggestion-section">
                                <h3>💻 Enhanced Strategy Code</h3>
                                <div class="code-suggestion">
                                    <pre><code class="language-python">${suggestions.suggested_code_changes[0]}</code></pre>
                                    <div class="code-actions" style="margin-top: 1rem;">
                                        ${autoApplied ? 
                                            `<div class="auto-applied-notice" style="background: rgba(46, 204, 113, 0.1); border: 1px solid #2ecc71; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
                                                <strong>✅ Strategy Auto-Applied!</strong><br>
                                                The enhanced strategy has been automatically saved and is ready to use.
                                            </div>
                                            <button class="btn-primary" onclick="tradingDashboard.runBacktest('${symbol}')">
                                                🚀 Test Enhanced Strategy
                                            </button>` :
                                            `<button class="btn-primary" onclick="tradingDashboard.applyAIStrategy('${symbol}', \`${suggestions.suggested_code_changes[0].replace(/`/g, '\\`')}\`)">
                                                ✨ Apply AI-Enhanced Strategy
                                            </button>`
                                        }
                                        <button class="btn-secondary" onclick="navigator.clipboard.writeText(\`${suggestions.suggested_code_changes[0].replace(/`/g, '\\`')}\`)">
                                            📋 Copy Code
                                        </button>
                                    </div>
                                </div>
                            </div>
                            
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal with animation
        setTimeout(() => {
            document.getElementById('aiSuggestionsModal').classList.add('show');
        }, 10);
    }
    
    async getParameterOptimization(symbol, backtestResults) {
        try {
            this.showNotification('⚙️ Generating parameter optimization...', 'info');
            
            // Extract current parameters from backtest results or use defaults
            const currentParameters = {
                zone_lookback: 300,
                base_max_candles: 5,
                move_min_ratio: 2.0,
                zone_width_max_pips: 30
            };
            
            const response = await fetch('/api/ai-parameter-optimization', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: symbol,
                    backtest_results: backtestResults,
                    current_parameters: currentParameters
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showParameterOptimizationModal(symbol, data.optimization);
                this.showNotification('⚙️ Parameter optimization generated!', 'success');
            } else {
                this.showNotification(`Failed to generate optimization: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error getting parameter optimization:', error);
            this.showNotification('Failed to get parameter optimization', 'error');
        }
    }
    
    showParameterOptimizationModal(symbol, optimization) {
        // Remove existing modal if present
        const existingModal = document.getElementById('parameterOptimizationModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modalHTML = `
            <div class="modal-overlay" id="parameterOptimizationModal">
                <div class="modal-content" style="max-width: 1200px; max-height: 90vh;">
                    <div class="modal-header">
                        <h2>⚙️ Parameter Optimization - ${symbol}</h2>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body" style="overflow-y: auto;">
                        <div class="parameter-optimization-container">
                            
                            <!-- Performance Assessment -->
                            <div class="optimization-section">
                                <h3>📊 Performance Assessment</h3>
                                <div class="assessment-list">
                                    ${optimization.performance_assessment.map(item => `<div class="assessment-item">${item}</div>`).join('')}
                                </div>
                            </div>
                            
                            <!-- Parameter Recommendations -->
                            <div class="optimization-section">
                                <h3>🎯 Parameter Recommendations</h3>
                                <div class="parameter-grid">
                                    ${Object.entries(optimization.parameter_recommendations).map(([param, details]) => `
                                        <div class="parameter-card priority-${details.priority.toLowerCase()}">
                                            <div class="parameter-header">
                                                <h4>${param.replace(/_/g, ' ').toUpperCase()}</h4>
                                                <span class="priority-badge ${details.priority.toLowerCase()}">${details.priority}</span>
                                            </div>
                                            <div class="parameter-values">
                                                <div class="current-value">Current: <strong>${details.current}</strong></div>
                                                <div class="recommended-value">Recommended: <strong>${details.recommended}</strong></div>
                                            </div>
                                            <div class="parameter-reason">${details.reason}</div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                            
                            <!-- Risk Management Settings -->
                            <div class="optimization-section">
                                <h3>🛡️ Risk Management Settings</h3>
                                <div class="risk-settings">
                                    <div class="risk-card">
                                        <h4>💰 Maximum Risk Per Trade</h4>
                                        <div class="risk-value">$${optimization.risk_management_settings.max_risk_per_trade.value} ${optimization.risk_management_settings.max_risk_per_trade.currency}</div>
                                        <div class="risk-enforcement">${optimization.risk_management_settings.max_risk_per_trade.enforcement}</div>
                                        <div class="risk-calculation">${optimization.risk_management_settings.max_risk_per_trade.calculation}</div>
                                    </div>
                                    <div class="risk-card">
                                        <h4>🎯 Risk-Reward Ratio</h4>
                                        <div class="risk-value">1:${optimization.risk_management_settings.risk_reward_ratio.minimum}</div>
                                        <div class="risk-enforcement">${optimization.risk_management_settings.risk_reward_ratio.enforcement}</div>
                                        <div class="risk-note">${optimization.risk_management_settings.risk_reward_ratio.note}</div>
                                    </div>
                                    <div class="risk-card">
                                        <h4>📊 Position Sizing</h4>
                                        <div class="risk-formula">${optimization.risk_management_settings.position_sizing_formula.formula}</div>
                                        <div class="risk-limits">Max: ${optimization.risk_management_settings.position_sizing_formula.max_lot_size} lots</div>
                                        <div class="risk-pip-value">Pip Value: $${optimization.risk_management_settings.position_sizing_formula.pip_value}</div>
                                    </div>
                                </div>
                                ${optimization.risk_management_settings.emergency_measures ? `
                                    <div class="emergency-measures">
                                        <h4>🚨 Emergency Measures Required</h4>
                                        <div class="emergency-item">${optimization.risk_management_settings.emergency_measures.reduce_position_size}</div>
                                        <div class="emergency-item">${optimization.risk_management_settings.emergency_measures.pause_trading}</div>
                                        <div class="emergency-item">${optimization.risk_management_settings.emergency_measures.review_required}</div>
                                    </div>
                                ` : ''}
                            </div>
                            
                            <!-- Technical Filters -->
                            <div class="optimization-section">
                                <h3>📊 Technical Filters</h3>
                                <div class="filters-grid">
                                    <div class="filter-card">
                                        <h4>📈 RSI Filter</h4>
                                        <div class="filter-setting">Period: ${optimization.technical_filters.rsi_filter.period}</div>
                                        <div class="filter-setting">Range: ${optimization.technical_filters.rsi_filter.entry_range.min}-${optimization.technical_filters.rsi_filter.entry_range.max}</div>
                                        <div class="filter-rationale">${optimization.technical_filters.rsi_filter.rationale}</div>
                                        <code class="filter-code">${optimization.technical_filters.rsi_filter.implementation}</code>
                                    </div>
                                    <div class="filter-card">
                                        <h4>⚡ ATR Filter</h4>
                                        <div class="filter-setting">Period: ${optimization.technical_filters.atr_filter.period}</div>
                                        <div class="filter-setting">Minimum: ${optimization.technical_filters.atr_filter.minimum_value}</div>
                                        <div class="filter-rationale">${optimization.technical_filters.atr_filter.rationale}</div>
                                        <code class="filter-code">${optimization.technical_filters.atr_filter.implementation}</code>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Implementation Priority -->
                            <div class="optimization-section">
                                <h3>🚀 Implementation Priority</h3>
                                <div class="priority-list">
                                    ${optimization.implementation_priority.map(item => `
                                        <div class="priority-item priority-${item.priority.toLowerCase()}">
                                            <div class="priority-header">
                                                <span class="priority-badge ${item.priority.toLowerCase()}">${item.priority}</span>
                                                <span class="priority-timeframe">${item.timeframe}</span>
                                            </div>
                                            <div class="priority-action">${item.action}</div>
                                            <div class="priority-impact">Impact: ${item.impact}</div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                            
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal with animation
        setTimeout(() => {
            document.getElementById('parameterOptimizationModal').classList.add('show');
        }, 10);
    }

    async applyAIStrategy(symbol, enhancedCode) {
        try {
            this.showNotification('📝 Applying AI-enhanced strategy...', 'info');
            
            // Save the enhanced strategy
            const response = await fetch('/api/save-strategy-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: symbol,
                    strategy_code: enhancedCode
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('✅ AI-enhanced strategy applied!', 'success');
                
                // Close suggestions modal
                const modal = document.getElementById('aiSuggestionsModal');
                if (modal) modal.remove();
                
                // Ask if user wants to run backtest with new strategy
                if (confirm('Strategy updated! Would you like to run a backtest with the AI-enhanced strategy?')) {
                    await this.runBacktest(symbol);
                }
            } else {
                this.showNotification(`Failed to apply strategy: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error applying AI strategy:', error);
            this.showNotification('Failed to apply AI strategy', 'error');
        }
    }

    destroy() {
        // Cleanup
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.wsConnection) {
            this.wsConnection.close();
        }
        
        Object.values(this.charts).forEach(chart => {
            chart.destroy();
        });
    }
}

// Additional CSS for notifications (injected dynamically)
const notificationStyles = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(10px);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        border-left: 4px solid var(--accent-primary);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        z-index: 1001;
        transform: translateX(400px);
        opacity: 0;
        transition: all 0.3s ease;
        min-width: 300px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    
    .notification.show {
        transform: translateX(0);
        opacity: 1;
    }
    
    .notification-success {
        border-left-color: var(--success);
    }
    
    .notification-error {
        border-left-color: var(--danger);
    }
    
    .notification-info {
        border-left-color: var(--accent-primary);
    }
    
    .notification i {
        font-size: 1.2rem;
    }
    
    .notification-success i {
        color: var(--success);
    }
    
    .notification-error i {
        color: var(--danger);
    }
    
    .notification-info i {
        color: var(--accent-primary);
    }
    
    .trade-side-buy {
        color: var(--success);
        font-weight: 600;
    }
    
    .trade-side-sell {
        color: var(--danger);
        font-weight: 600;
    }
`;

// Inject notification styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.tradingDashboard = new TradingDashboard();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Pause updates when tab is not visible
        if (window.tradingDashboard && window.tradingDashboard.updateInterval) {
            clearInterval(window.tradingDashboard.updateInterval);
        }
    } else {
        // Resume updates when tab becomes visible
        if (window.tradingDashboard) {
            window.tradingDashboard.startRealTimeUpdates();
        }
    }
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.tradingDashboard) {
        window.tradingDashboard.destroy();
    }
}); 