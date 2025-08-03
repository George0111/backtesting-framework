import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
from datetime import datetime

def create_trade_visualization(asset_data, trades_by_symbol, results_dir):
    """
    Creates an enhanced interactive HTML visualization of trades for each asset.
    
    Args:
        asset_data (dict): Dictionary of DataFrames with OHLCV data for each asset
        trades_by_symbol (dict): Dictionary of trade information by symbol
        results_dir (str): Directory to save the visualization
    
    Returns:
        str: Path to the created HTML file
    """
    # Create a list of all symbols for the dropdown
    symbols = list(asset_data.keys())
    
    if not symbols:
        print("No asset data available for visualization")
        return
    
    # Create the HTML file with Plotly
    html_file = os.path.join(results_dir, "trade_visualization.html")
    
    # Prepare the data for JavaScript
    js_data = {}
    
    for symbol, df in asset_data.items():
        # Ensure we have the right column names
        ohlc_columns = {}
        for std_col, possible_cols in [
            ('Open', ['Open', 'open']),
            ('High', ['High', 'high']),
            ('Low', ['Low', 'low']),
            ('Close', ['Close', 'close']),
            ('Volume', ['Volume', 'volume'])
        ]:
            for col in possible_cols:
                if col in df.columns:
                    ohlc_columns[std_col] = col
                    break
        
        # Skip if we don't have all required columns
        if len(ohlc_columns) < 4:  # Need at least OHLC
            print(f"Skipping {symbol}: missing required columns")
            continue
        
        # Convert the DataFrame to a format suitable for Plotly
        df_dict = {
            'dates': df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'open': df[ohlc_columns.get('Open')].tolist(),
            'high': df[ohlc_columns.get('High')].tolist(),
            'low': df[ohlc_columns.get('Low')].tolist(),
            'close': df[ohlc_columns.get('Close')].tolist(),
        }
        
        # Add volume if available
        if 'Volume' in ohlc_columns:
            df_dict['volume'] = df[ohlc_columns.get('Volume')].tolist()
        
        # Add trade information if available
        trades = trades_by_symbol.get(symbol, [])
        
        buy_dates = []
        buy_prices = []
        buy_sizes = []
        buy_values = []
        sell_dates = []
        sell_prices = []
        sell_sizes = []
        sell_values = []
        
        # Process trades to calculate holdings and P&L
        holdings = []
        current_position = 0
        position_value = 0
        cost_basis = 0
        
        # Initialize holdings with zeros for all dates
        holdings_dict = {date: 0 for date in df.index.strftime('%Y-%m-%d %H:%M:%S').tolist()}
        position_value_dict = {date: 0 for date in df.index.strftime('%Y-%m-%d %H:%M:%S').tolist()}
        unrealized_pl_dict = {date: 0 for date in df.index.strftime('%Y-%m-%d %H:%M:%S').tolist()}
        realized_pl = 0
        realized_pl_dict = {date: 0 for date in df.index.strftime('%Y-%m-%d %H:%M:%S').tolist()}
        
        # Sort trades by date
        sorted_trades = sorted(trades, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d %H:%M:%S'))
        
        for trade in sorted_trades:
            trade_date = trade['date']
            
            if trade['type'] == 'buy':
                buy_dates.append(trade_date)
                buy_prices.append(trade['price'])
                buy_sizes.append(trade['size'])
                buy_values.append(trade['value'])
                
                # Update position
                current_position += trade['size']
                position_value += trade['value']
                cost_basis = position_value / current_position if current_position > 0 else 0
                
            elif trade['type'] == 'sell':
                sell_dates.append(trade_date)
                sell_prices.append(trade['price'])
                sell_sizes.append(trade['size'])
                sell_values.append(trade['value'])
                
                # Calculate realized P&L for this sale
                if current_position > 0:
                    # Calculate P&L for this sale
                    sale_pl = trade['value'] - (cost_basis * trade['size'])
                    realized_pl += sale_pl
                    realized_pl_dict[trade_date] = realized_pl
                
                # Update position
                current_position -= trade['size']
                position_value = current_position * cost_basis if current_position > 0 else 0
            
            # Update holdings after each trade
            holdings_dict[trade_date] = current_position
            position_value_dict[trade_date] = position_value
        
        # Fill in holdings for all dates (forward fill)
        last_holding = 0
        last_position_value = 0
        last_realized_pl = 0
        
        for date in sorted(holdings_dict.keys()):
            if holdings_dict[date] != 0:
                last_holding = holdings_dict[date]
            else:
                holdings_dict[date] = last_holding
            
            if position_value_dict[date] != 0:
                last_position_value = position_value_dict[date]
            else:
                position_value_dict[date] = last_position_value
            
            if realized_pl_dict[date] != 0:
                last_realized_pl = realized_pl_dict[date]
            else:
                realized_pl_dict[date] = last_realized_pl
            
            # Calculate unrealized P&L
            close_price = df.loc[date][ohlc_columns.get('Close')] if date in df.index.strftime('%Y-%m-%d %H:%M:%S').tolist() else 0
            current_value = holdings_dict[date] * close_price
            unrealized_pl_dict[date] = current_value - position_value_dict[date] if holdings_dict[date] > 0 else 0
        
        # Convert dictionaries to lists for JavaScript
        holdings_dates = sorted(holdings_dict.keys())
        holdings_values = [holdings_dict[date] for date in holdings_dates]
        position_values = [position_value_dict[date] for date in holdings_dates]
        unrealized_pl = [unrealized_pl_dict[date] for date in holdings_dates]
        realized_pl_values = [realized_pl_dict[date] for date in holdings_dates]
        
        # Calculate cumulative returns
        returns = []
        if len(df) > 0:
            price_series = df[ohlc_columns.get('Close')]
            pct_change = price_series.pct_change().fillna(0)
            
            # Calculate returns based on holdings
            weighted_returns = []
            for i, date in enumerate(holdings_dates):
                if i > 0:  # Skip first day
                    # Find the closest date in the price series
                    if date in pct_change.index.strftime('%Y-%m-%d %H:%M:%S').tolist():
                        date_idx = pct_change.index.strftime('%Y-%m-%d %H:%M:%S').tolist().index(date)
                        daily_return = pct_change.iloc[date_idx]
                        # Weight by position size
                        weighted_return = daily_return * holdings_values[i-1]  # Use previous day's holdings
                        weighted_returns.append(weighted_return)
                    else:
                        weighted_returns.append(0)
                else:
                    weighted_returns.append(0)
            
            # Calculate cumulative returns
            cum_returns = np.cumprod(1 + np.array(weighted_returns)) - 1
            returns = cum_returns.tolist()
        
        # Add all data to the dictionary
        df_dict['trades'] = {
            'buy_dates': buy_dates,
            'buy_prices': buy_prices,
            'buy_sizes': buy_sizes,
            'buy_values': buy_values,
            'sell_dates': sell_dates,
            'sell_prices': sell_prices,
            'sell_sizes': sell_sizes,
            'sell_values': sell_values
        }
        
        df_dict['holdings'] = {
            'dates': holdings_dates,
            'values': holdings_values,
            'position_values': position_values,
            'unrealized_pl': unrealized_pl,
            'realized_pl': realized_pl_values,
            'returns': returns
        }
        
        js_data[symbol] = df_dict
    
    # Create the HTML file with embedded JavaScript
    with open(html_file, 'w') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Advanced Trade Visualization</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                }}
                .controls {{
                    margin: 20px 0;
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    flex-wrap: wrap;
                }}
                select, button {{
                    padding: 8px 12px;
                    border-radius: 4px;
                    border: 1px solid #ddd;
                }}
                button {{
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    cursor: pointer;
                }}
                button:hover {{
                    background-color: #45a049;
                }}
                .chart-container {{
                    height: 800px;
                    margin-bottom: 20px;
                }}
                .dashboard {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                .metric-card {{
                    background-color: #fff;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 15px;
                    text-align: center;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .metric-title {{
                    color: #666;
                    font-size: 14px;
                }}
                .positive {{
                    color: #4CAF50;
                }}
                .negative {{
                    color: #f44336;
                }}
                .tab-container {{
                    margin-top: 20px;
                }}
                .tab-buttons {{
                    display: flex;
                    gap: 5px;
                    margin-bottom: 10px;
                }}
                .tab-button {{
                    padding: 8px 16px;
                    background-color: #ddd;
                    border: none;
                    border-radius: 4px 4px 0 0;
                    cursor: pointer;
                }}
                .tab-button.active {{
                    background-color: #4CAF50;
                    color: white;
                }}
                .tab-content {{
                    display: none;
                }}
                .tab-content.active {{
                    display: block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Advanced Trade Visualization</h1>
                <div class="controls">
                    <select id="symbol-selector">
                        {' '.join([f'<option value="{symbol}">{symbol}</option>' for symbol in symbols])}
                    </select>
                    <button id="toggle-view">Toggle Chart/Dashboard View</button>
                </div>
                
                <div id="metrics-dashboard" class="dashboard">
                    <div class="metric-card">
                        <div class="metric-title">Current Position</div>
                        <div id="current-position" class="metric-value">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Position Value</div>
                        <div id="position-value" class="metric-value">$0.00</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Unrealized P&L</div>
                        <div id="unrealized-pl" class="metric-value">$0.00</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Realized P&L</div>
                        <div id="realized-pl" class="metric-value">$0.00</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Total Trades</div>
                        <div id="total-trades" class="metric-value">0</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Average Buy Price</div>
                        <div id="avg-buy-price" class="metric-value">$0.00</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Average Sell Price</div>
                        <div id="avg-sell-price" class="metric-value">$0.00</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Cumulative Return</div>
                        <div id="cumulative-return" class="metric-value">0.00%</div>
                    </div>
                </div>
                
                <div class="tab-container">
                    <div class="tab-buttons">
                        <button class="tab-button active" data-tab="price-chart">Price & Trades</button>
                        <button class="tab-button" data-tab="holdings-chart">Holdings & P&L</button>
                        <button class="tab-button" data-tab="returns-chart">Cumulative Returns</button>
                    </div>
                    
                    <div id="price-chart" class="tab-content active chart-container"></div>
                    <div id="holdings-chart" class="tab-content chart-container"></div>
                    <div id="returns-chart" class="tab-content chart-container"></div>
                </div>
                
                <div id="trade-table-container" style="margin-top: 20px;">
                    <h2>Trade History</h2>
                    <table id="trade-table" style="width:100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Date</th>
                                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Type</th>
                                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Price</th>
                                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Size</th>
                                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Value</th>
                            </tr>
                        </thead>
                        <tbody id="trade-table-body">
                            <!-- Trade rows will be added here -->
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script>
                // Store all data
                const allData = {json.dumps(js_data)};
                let currentView = 'chart'; // 'chart' or 'dashboard'
                
                // Function to format currency
                function formatCurrency(value) {{
                    return new Intl.NumberFormat('en-US', {{ 
                        style: 'currency', 
                        currency: 'USD',
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }}).format(value);
                }}
                
                // Function to format percentage
                function formatPercent(value) {{
                    return new Intl.NumberFormat('en-US', {{ 
                        style: 'percent', 
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }}).format(value);
                }}
                
                // Function to update the dashboard metrics
                function updateDashboard(symbol) {{
                    const data = allData[symbol];
                    if (!data || !data.holdings) return;
                    
                    const holdings = data.holdings;
                    const trades = data.trades;
                    
                    // Get the most recent values
                    const currentPosition = holdings.values[holdings.values.length - 1];
                    const positionValue = holdings.position_values[holdings.position_values.length - 1];
                    const unrealizedPL = holdings.unrealized_pl[holdings.unrealized_pl.length - 1];
                    const realizedPL = holdings.realized_pl[holdings.realized_pl.length - 1];
                    const totalTrades = (trades.buy_dates.length + trades.sell_dates.length);
                    
                    // Calculate average prices
                    let avgBuyPrice = 0;
                    let avgSellPrice = 0;
                    
                    if (trades.buy_dates.length > 0) {{
                        const totalBuyValue = trades.buy_values.reduce((a, b) => a + b, 0);
                        const totalBuySize = trades.buy_sizes.reduce((a, b) => a + b, 0);
                        avgBuyPrice = totalBuyValue / totalBuySize;
                    }}
                    
                    if (trades.sell_dates.length > 0) {{
                        const totalSellValue = trades.sell_values.reduce((a, b) => a + b, 0);
                        const totalSellSize = trades.sell_sizes.reduce((a, b) => a + b, 0);
                        avgSellPrice = totalSellValue / totalSellSize;
                    }}
                    
                    // Calculate cumulative return
                    const cumulativeReturn = holdings.returns.length > 0 ? 
                        holdings.returns[holdings.returns.length - 1] : 0;
                    
                    // Update the dashboard
                    document.getElementById('current-position').textContent = currentPosition.toFixed(2);
                    document.getElementById('position-value').textContent = formatCurrency(positionValue);
                    
                    const unrealizedElement = document.getElementById('unrealized-pl');
                    unrealizedElement.textContent = formatCurrency(unrealizedPL);
                    unrealizedElement.className = 'metric-value ' + (unrealizedPL >= 0 ? 'positive' : 'negative');
                    
                    const realizedElement = document.getElementById('realized-pl');
                    realizedElement.textContent = formatCurrency(realizedPL);
                    realizedElement.className = 'metric-value ' + (realizedPL >= 0 ? 'positive' : 'negative');
                    
                    document.getElementById('total-trades').textContent = totalTrades;
                    document.getElementById('avg-buy-price').textContent = formatCurrency(avgBuyPrice);
                    document.getElementById('avg-sell-price').textContent = formatCurrency(avgSellPrice);
                    
                    const returnElement = document.getElementById('cumulative-return');
                    returnElement.textContent = formatPercent(cumulativeReturn);
                    returnElement.className = 'metric-value ' + (cumulativeReturn >= 0 ? 'positive' : 'negative');
                }}
                
                // Function to update the trade table
                function updateTradeTable(symbol) {{
                    const data = allData[symbol];
                    if (!data || !data.trades) return;
                    
                    const trades = data.trades;
                    const tableBody = document.getElementById('trade-table-body');
                    tableBody.innerHTML = '';
                    
                    // Combine buy and sell trades and sort by date
                    const allTrades = [];
                    
                    for (let i = 0; i < trades.buy_dates.length; i++) {{
                        allTrades.push({{
                            date: trades.buy_dates[i],
                            type: 'Buy',
                            price: trades.buy_prices[i],
                            size: trades.buy_sizes[i],
                            value: trades.buy_values[i]
                        }});
                    }}
                    
                    for (let i = 0; i < trades.sell_dates.length; i++) {{
                        allTrades.push({{
                            date: trades.sell_dates[i],
                            type: 'Sell',
                            price: trades.sell_prices[i],
                            size: trades.sell_sizes[i],
                            value: trades.sell_values[i]
                        }});
                    }}
                    
                    // Sort by date
                    allTrades.sort((a, b) => new Date(a.date) - new Date(b.date));
                    
                    // Add rows to the table
                    for (const trade of allTrades) {{
                        const row = document.createElement('tr');
                        
                        const dateCell = document.createElement('td');
                        dateCell.textContent = trade.date;
                        dateCell.style.padding = '8px';
                        dateCell.style.border = '1px solid #ddd';
                        row.appendChild(dateCell);
                        
                        const typeCell = document.createElement('td');
                        typeCell.textContent = trade.type;
                        typeCell.style.padding = '8px';
                        typeCell.style.border = '1px solid #ddd';
                        typeCell.style.color = trade.type === 'Buy' ? '#4CAF50' : '#f44336';
                        typeCell.style.fontWeight = 'bold';
                        row.appendChild(typeCell);
                        
                        const priceCell = document.createElement('td');
                        priceCell.textContent = formatCurrency(trade.price);
                        priceCell.style.padding = '8px';
                        priceCell.style.border = '1px solid #ddd';
                        row.appendChild(priceCell);
                        
                        const sizeCell = document.createElement('td');
                        sizeCell.textContent = trade.size.toFixed(2);
                        sizeCell.style.padding = '8px';
                        sizeCell.style.border = '1px solid #ddd';
                        row.appendChild(sizeCell);
                        
                        const valueCell = document.createElement('td');
                        valueCell.textContent = formatCurrency(trade.value);
                        valueCell.style.padding = '8px';
                        valueCell.style.border = '1px solid #ddd';
                        row.appendChild(valueCell);
                        
                        tableBody.appendChild(row);
                    }}
                }}
                
                // Function to create the price chart
                function createPriceChart(symbol) {{
                    const data = allData[symbol];
                    if (!data) {{
                        console.error('No data for symbol:', symbol);
                        return;
                    }}
                    
                    // Create candlestick chart
                    const traces = [{{
                        type: 'candlestick',
                        x: data.dates,
                        open: data.open,
                        high: data.high,
                        low: data.low,
                        close: data.close,
                        name: symbol,
                        increasing: {{line: {{color: '#26a69a'}}, fillcolor: '#26a69a'}},
                        decreasing: {{line: {{color: '#ef5350'}}, fillcolor: '#ef5350'}}
                    }}];
                    
                    // Add volume if available
                    if (data.volume) {{
                        traces.push({{
                            type: 'bar',
                            x: data.dates,
                            y: data.volume,
                            name: 'Volume',
                            yaxis: 'y2',
                            marker: {{
                                color: '#7E7E7E',
                                opacity: 0.5
                            }}
                        }});
                    }}
                    
                    // Add buy markers
                    if (data.trades && data.trades.buy_dates.length > 0) {{
                        traces.push({{
                            type: 'scatter',
                            x: data.trades.buy_dates,
                            y: data.trades.buy_prices,
                            mode: 'markers',
                            name: 'Buy',
                            text: data.trades.buy_sizes.map((size, i) => 
                                `Buy: ${{formatCurrency(data.trades.buy_prices[i])}}\\nSize: ${{size.toFixed(2)}}\\nValue: ${{formatCurrency(data.trades.buy_values[i])}}`
                            ),
                            hoverinfo: 'text',
                            marker: {{
                                color: 'green',
                                size: 10,
                                symbol: 'triangle-up',
                                line: {{
                                    color: 'white',
                                    width: 1
                                }}
                            }}
                        }});
                    }}
                    
                    // Add sell markers
                    if (data.trades && data.trades.sell_dates.length > 0) {{
                        traces.push({{
                            type: 'scatter',
                            x: data.trades.sell_dates,
                            y: data.trades.sell_prices,
                            mode: 'markers',
                            name: 'Sell',
                            text: data.trades.sell_sizes.map((size, i) => 
                                `Sell: ${{formatCurrency(data.trades.sell_prices[i])}}\\nSize: ${{size.toFixed(2)}}\\nValue: ${{formatCurrency(data.trades.sell_values[i])}}`
                            ),
                            hoverinfo: 'text',
                            marker: {{
                                color: 'red',
                                size: 10,
                                symbol: 'triangle-down',
                                line: {{
                                    color: 'white',
                                    width: 1
                                }}
                            }}
                        }});
                    }}
                    
                    // Define layout
                    const layout = {{
                        title: `${{symbol}} Price Chart with Trades`,
                        dragmode: 'zoom',
                        showlegend: true,
                        xaxis: {{
                            rangeslider: {{
                                visible: false
                            }}
                        }},
                        yaxis: {{
                            title: 'Price',
                            autorange: true,
                            domain: [0.2, 1]
                        }},
                        yaxis2: {{
                            title: 'Volume',
                            autorange: true,
                            domain: [0, 0.2],
                            showticklabels: false
                        }},
                        margin: {{
                            l: 50,
                            r: 50,
                            b: 50,
                            t: 50,
                            pad: 4
                        }}
                    }};
                    
                    // Create the plot
                    Plotly.newPlot('price-chart', traces, layout);
                }}
                
                // Function to create the holdings chart
                function createHoldingsChart(symbol) {{
                    const data = allData[symbol];
                    if (!data || !data.holdings) return;
                    
                    const holdings = data.holdings;
                    
                    // Create holdings chart
                    const traces = [
                        {{
                            type: 'scatter',
                            x: holdings.dates,
                            y: holdings.values,
                            name: 'Position Size',
                            line: {{ color: '#2196F3', width: 2 }}
                        }},
                        {{
                            type: 'scatter',
                            x: holdings.dates,
                            y: holdings.position_values,
                            name: 'Position Value',
                            yaxis: 'y2',
                            line: {{ color: '#4CAF50', width: 2 }}
                        }},
                        {{
                            type: 'scatter',
                            x: holdings.dates,
                            y: holdings.unrealized_pl,
                            name: 'Unrealized P&L',
                            yaxis: 'y3',
                            line: {{ color: '#FFC107', width: 2 }}
                        }},
                        {{
                            type: 'scatter',
                            x: holdings.dates,
                            y: holdings.realized_pl,
                            name: 'Realized P&L',
                            yaxis: 'y3',
                            line: {{ color: '#9C27B0', width: 2 }}
                        }}
                    ];
                    
                    // Define layout
                    const layout = {{
                        title: `${{symbol}} Holdings and P&L`,
                        dragmode: 'zoom',
                        showlegend: true,
                        grid: {{
                            rows: 3,
                            columns: 1,
                            pattern: 'independent',
                            roworder: 'top to bottom'
                        }},
                        xaxis: {{ title: 'Date' }},
                        yaxis: {{ 
                            title: 'Position Size',
                            domain: [0.7, 1]
                        }},
                        yaxis2: {{ 
                            title: 'Position Value ($)',
                            domain: [0.35, 0.65]
                        }},
                        yaxis3: {{ 
                            title: 'P&L ($)',
                            domain: [0, 0.3]
                        }},
                        margin: {{
                            l: 50,
                            r: 50,
                            b: 50,
                            t: 50,
                            pad: 4
                        }}
                    }};
                    
                    // Create the plot
                    Plotly.newPlot('holdings-chart', traces, layout);
                }}
                
                // Function to create the returns chart
                function createReturnsChart(symbol) {{
                    const data = allData[symbol];
                    if (!data || !data.holdings) return;
                    
                    const holdings = data.holdings;
                    
                    // Create returns chart
                    const traces = [
                        {{
                            type: 'scatter',
                            x: holdings.dates,
                            y: holdings.returns,
                            name: 'Cumulative Return',
                            line: {{ color: '#2196F3', width: 2 }}
                        }}
                    ];
                    
                    // Define layout
                    const layout = {{
                        title: `${{symbol}} Cumulative Returns`,
                        dragmode: 'zoom',
                        showlegend: true,
                        xaxis: {{ title: 'Date' }},
                        yaxis: {{ 
                            title: 'Return (%)',
                            tickformat: '.1%'
                        }},
                        margin: {{
                            l: 50,
                            r: 50,
                            b: 50,
                            t: 50,
                            pad: 4
                        }}
                    }};
                    
                    // Create the plot
                    Plotly.newPlot('returns-chart', traces, layout);
                }}
                
                // Function to update all charts
                function updateCharts(symbol) {{
                    createPriceChart(symbol);
                    createHoldingsChart(symbol);
                    createReturnsChart(symbol);
                    updateDashboard(symbol);
                    updateTradeTable(symbol);
                }}
                
                // Initialize with the first symbol
                document.addEventListener('DOMContentLoaded', function() {{
                    const symbolSelector = document.getElementById('symbol-selector');
                    updateCharts(symbolSelector.value);
                    
                    // Add event listener for dropdown changes
                    symbolSelector.addEventListener('change', function() {{
                        updateCharts(this.value);
                    }});
                    
                    // Add event listener for toggle button
                    document.getElementById('toggle-view').addEventListener('click', function() {{
                        currentView = currentView === 'chart' ? 'dashboard' : 'chart';
                        document.getElementById('metrics-dashboard').style.display = 
                            currentView === 'dashboard' ? 'grid' : 'none';
                        document.getElementById('chart-container').style.display = 
                            currentView === 'chart' ? 'block' : 'none';
                    }});
                    
                    // Tab switching
                    const tabButtons = document.querySelectorAll('.tab-button');
                    const tabContents = document.querySelectorAll('.tab-content');
                    
                    tabButtons.forEach(button => {{
                        button.addEventListener('click', () => {{
                            // Remove active class from all buttons and contents
                            tabButtons.forEach(btn => btn.classList.remove('active'));
                            tabContents.forEach(content => content.classList.remove('active'));
                            
                            // Add active class to clicked button and corresponding content
                            button.classList.add('active');
                            const tabId = button.getAttribute('data-tab');
                            document.getElementById(tabId).classList.add('active');
                        }});
                    }});
                }});
            </script>
        </body>
        </html>
        """)
    
    print(f"Interactive trade visualization saved to {html_file}")
    return html_file