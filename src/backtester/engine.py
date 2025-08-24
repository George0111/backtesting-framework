import backtrader as bt
import pandas as pd
import os
import numpy as np
import warnings
from . import utils
from .analysis import metrics
import quantstats as qs
import matplotlib
# Set the backend to 'Agg' which is a non-interactive backend
# This must be done before importing pyplot
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Suppress FutureWarnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)

def run_backtest(strategy_class, symbols, start_date, end_date, starting_cash, data_dir, results_dir, benchmark, strategy_params=None):
    """
    Runs a backtest using the specified strategy and parameters.

    Args:
        strategy_class (bt.Strategy): The strategy class to be tested.
        symbols (list): A list of ticker symbols to include in the backtest.
        start_date (str): The start date for the backtest (YYYY-MM-DD).
        end_date (str): The end date for the backtest (YYYY-MM-DD).
        starting_cash (float): The initial portfolio value.
        data_dir (str): The directory where data CSV files are stored.
        results_dir (str): The directory to save results (plots, reports).
        strategy_params (dict, optional): A dictionary of parameters for the strategy.

    Returns:
        The final portfolio value.
    """
    # Disable plotting by setting the maximum size to 0
    cerebro = bt.Cerebro(stdstats=False, maxcpus=1)

    # Add strategy with parameters
    if strategy_params:
        cerebro.addstrategy(strategy_class, **strategy_params)
    else:
        cerebro.addstrategy(strategy_class)

    # Add data feeds
    start_dt = pd.Timestamp(start_date, tz='UTC')
    end_dt = pd.Timestamp(end_date, tz='UTC')
    
    # Store dataframes for individual asset analysis
    asset_data = {}

    for symbol in symbols:
        try:
            data_path = os.path.join(data_dir)
            df = utils.fetch_data(data_path, symbol, start_dt, end_dt)
            data_feed = bt.feeds.PandasData(dataname=df, name=symbol)
            cerebro.adddata(data_feed, name=symbol)
            print(f"Successfully loaded data for {symbol}")
            
            # Store the dataframe for later analysis
            asset_data[symbol] = df
        except FileNotFoundError as e:
            print(f"Warning: Could not load data for {symbol}. Error: {e}")
            continue

    # Configure broker with realistic transaction costs
    cerebro.broker.setcash(starting_cash)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% commission
    cerebro.broker.set_slippage_perc(0.0)          # 0% slippage for preliminary testing
    
    # Add custom observer to track all orders and trades
    class OrderObserver(bt.observer.Observer):
        lines = ('buy', 'sell',)
        
        def next(self):
            self.lines.buy[0] = float('nan')
            self.lines.sell[0] = float('nan')
            
            for order in self._owner._orderspending:
                if order.status == order.Completed:
                    if order.isbuy():
                        self.lines.buy[0] = order.executed.price
                    else:
                        self.lines.sell[0] = order.executed.price
    
    # Add the custom observer
    cerebro.addobserver(OrderObserver)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    
    # Add a custom analyzer to track all trades with timestamps
    class TradeRecorder(bt.Analyzer):
        def __init__(self):
            self.trades = {}
            self.orders = []
            
        def notify_order(self, order):
            if order.status == order.Completed:
                # Record the order details
                self.orders.append({
                    'datetime': self.strategy.datetime.datetime(),
                    'data': order.data._name,
                    'type': 'buy' if order.isbuy() else 'sell',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value,
                    'commission': order.executed.comm
                })
    
    # Add the trade recorder
    cerebro.addanalyzer(TradeRecorder, _name='traderecorder')

    # Run backtest
    print(f"\nStarting Portfolio Value: {cerebro.broker.getvalue():,.2f}")
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f"Ending Portfolio Value:   {final_value:,.2f}\n")

    strat = results[0]
    pyfoliozer = strat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()
    
    # Get trade analyzer results
    trade_analyzer = strat.analyzers.getbyname('tradeanalyzer')
    trade_analysis = trade_analyzer.get_analysis()
    
    # Get trade recorder results
    trade_recorder = strat.analyzers.getbyname('traderecorder')
    orders = trade_recorder.orders
    
    # Organize trades by symbol
    trades_by_symbol = {}
    for order in orders:
        symbol = order['data']
        if symbol not in trades_by_symbol:
            trades_by_symbol[symbol] = []
        
        trades_by_symbol[symbol].append({
            'date': order['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
            'type': order['type'],
            'price': order['price'],
            'size': order['size'],
            'value': order['value']
        })
    
    # Save trade information to CSV
    trades_df = pd.DataFrame(orders)
    trades_df.to_csv(os.path.join(results_dir, "trades.csv"), index=False)
    
    # Print trade summary
    print("\n--- Trade Summary ---")
    for symbol, trades in trades_by_symbol.items():
        buy_trades = [t for t in trades if t['type'] == 'buy']
        sell_trades = [t for t in trades if t['type'] == 'sell']
        
        print(f"{symbol}:")
        print(f"  Total Trades: {len(trades)}")
        print(f"  Buy Trades: {len(buy_trades)}")
        print(f"  Sell Trades: {len(sell_trades)}")
        
        if buy_trades:
            buy_values = [t['value'] for t in buy_trades]
            print(f"  Total Buy Value: ${sum(buy_values):,.2f}")
            print(f"  Average Buy Price: ${sum(t['price'] * t['size'] for t in buy_trades) / sum(t['size'] for t in buy_trades):,.2f}")
        
        if sell_trades:
            sell_values = [t['value'] for t in sell_trades]
            print(f"  Total Sell Value: ${sum(sell_values):,.2f}")
            print(f"  Average Sell Price: ${sum(t['price'] * t['size'] for t in sell_trades) / sum(t['size'] for t in sell_trades):,.2f}")
        
        print("")
    
    # Get drawdown analyzer results directly from backtrader
    drawdown_analyzer = strat.analyzers.getbyname('drawdown')
    max_drawdown_bt = drawdown_analyzer.get_analysis().get('max', {}).get('drawdown', 0) / 100.0
    
    # Get benchmark data
    benchmark_returns = utils.get_benchmark(benchmark, start_dt, end_dt, data_dir)
    print(benchmark_returns.head(), benchmark_returns.tail())
    # Convert both indices to timezone-naive
    returns.index = returns.index.tz_localize(None)
    if benchmark_returns.index.tzinfo is not None:
        benchmark_returns.index = benchmark_returns.index.tz_localize(None)
    
    # Align both Series/DataFrame to the same dates
    returns, benchmark_returns = returns.align(benchmark_returns, join='inner')  


    # Check for extreme negative returns that might cause issues
    if returns.min() <= -1:
        print("Warning: Returns contain values <= -1, which can cause issues with calculations.")
        # Clip extreme negative values to prevent calculation issues
        returns = returns.clip(lower=-0.99)
    
    # Save returns data
    returns.to_csv(os.path.join(results_dir, "returns.csv"))
    if benchmark_returns is not None:
        benchmark_returns.to_csv(os.path.join(results_dir, "benchmark_returns.csv"))
    
    # Create a better drawdown calculation function
    def calculate_drawdowns(returns):
        """Calculate drawdowns more accurately."""
        # Ensure returns are greater than -1 (prevent division by zero issues)
        returns = returns.clip(lower=-0.99)
        
        # Calculate cumulative returns
        cum_returns = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cum_returns.cummax()
        
        # Calculate drawdown
        drawdown = (cum_returns - running_max) / running_max
        
        # Ensure drawdown values are between -1 and 0
        drawdown = np.maximum(drawdown, -1.0)
        
        return drawdown
    
    # Calculate drawdowns using both methods
    drawdowns_manual = calculate_drawdowns(returns)
    max_drawdown_manual = drawdowns_manual.min()
    
    # Use the backtrader analyzer value if available, otherwise use our calculation
    max_drawdown = max_drawdown_bt if max_drawdown_bt > 0 else max_drawdown_manual
    
    # Print both values for comparison
    print(f"Max Drawdown (Backtrader): {max_drawdown_bt:.4f}")
    print(f"Max Drawdown (Manual calc): {max_drawdown_manual:.4f}")
    
    # --- Individual Asset Analysis ---
    print("\n--- Individual Asset Analysis ---")
    
    # Calculate returns for each asset
    asset_returns = {}
    asset_metrics = {}
    
    for symbol, df in asset_data.items():
        # Calculate daily returns
        if 'Close' in df.columns:
            price_col = 'Close'
        elif 'close' in df.columns:
            price_col = 'close'
        else:
            print(f"Warning: Could not find price column for {symbol}")
            continue
        
        # Resample to daily if using intraday data
        if len(df) > (end_dt - start_dt).days * 2:  # Heuristic to detect intraday data
            daily_df = df[price_col].resample('D').last().dropna()
        else:
            daily_df = df[price_col]
        
        # Calculate returns
        asset_return = daily_df.pct_change().dropna()
        asset_returns[symbol] = asset_return
        
        # Calculate metrics
        try:
            total_return = (daily_df.iloc[-1] / daily_df.iloc[0] - 1) * 100
            annualized_return = qs.stats.cagr(asset_return)
            volatility = qs.stats.volatility(asset_return) * 100
            sharpe = qs.stats.sharpe(asset_return)
            max_dd = qs.stats.max_drawdown(asset_return) * 100
            
            asset_metrics[symbol] = {
                'Total Return (%)': total_return,
                'CAGR (%)': annualized_return * 100,
                'Volatility (%)': volatility,
                'Sharpe Ratio': sharpe,
                'Max Drawdown (%)': max_dd
            }
            
            print(f"{symbol}:")
            print(f"  Total Return: {total_return:.2f}%")
            print(f"  CAGR: {annualized_return:.2f}")
            print(f"  Volatility: {volatility:.2f}%")
            print(f"  Sharpe Ratio: {sharpe:.2f}")
            print(f"  Max Drawdown: {max_dd:.2f}%")
        except Exception as e:
            print(f"Error calculating metrics for {symbol}: {e}")
    
    # Create a DataFrame of asset metrics for easier comparison
    metrics_df = pd.DataFrame(asset_metrics).T
    metrics_df.to_csv(os.path.join(results_dir, "asset_metrics.csv"))
    
    # Plot asset returns comparison
    plt.figure(figsize=(12, 8))
    for symbol, asset_return in asset_returns.items():
        cum_return = (1 + asset_return).cumprod()
        plt.plot(cum_return.index, cum_return, label=symbol)
    
    plt.title('Cumulative Returns by Asset')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(results_dir, "asset_returns_comparison.png"))
    plt.close()  # Close the figure to free memory
    
    # Plot asset metrics comparison
    plt.figure(figsize=(14, 10))
    
    # Plot total returns
    plt.subplot(2, 2, 1)
    metrics_df['Total Return (%)'].sort_values().plot(kind='bar', color='skyblue')
    plt.title('Total Return by Asset (%)')
    plt.xticks(rotation=45)
    plt.grid(axis='y')
    
    # Plot Sharpe ratios
    plt.subplot(2, 2, 2)
    metrics_df['Sharpe Ratio'].sort_values().plot(kind='bar', color='lightgreen')
    plt.title('Sharpe Ratio by Asset')
    plt.xticks(rotation=45)
    plt.grid(axis='y')
    
    # Plot volatility
    plt.subplot(2, 2, 3)
    metrics_df['Volatility (%)'].sort_values().plot(kind='bar', color='salmon')
    plt.title('Volatility by Asset (%)')
    plt.xticks(rotation=45)
    plt.grid(axis='y')
    
    # Plot max drawdown
    plt.subplot(2, 2, 4)
    metrics_df['Max Drawdown (%)'].sort_values().plot(kind='bar', color='orange')
    plt.title('Max Drawdown by Asset (%)')
    plt.xticks(rotation=45)
    plt.grid(axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "asset_metrics_comparison.png"))
    plt.close()  # Close the figure to free memory
    
    # Create correlation heatmap of asset returns
    plt.figure(figsize=(12, 10))
    returns_df = pd.DataFrame({symbol: returns for symbol, returns in asset_returns.items()})
    correlation = returns_df.corr()
    sns.heatmap(correlation, annot=True, cmap='coolwarm', linewidths=0.5)
    plt.title('Asset Return Correlations')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "asset_correlations.png"))
    plt.close()  # Close the figure to free memory
    
    # Configure QuantStats to use non-interactive backend
    qs.extend_pandas()
    
    # Generate basic metrics report
    try:
        # Simple metrics first
        print("\nBasic metrics:")
        print(f"Sharpe Ratio: {qs.stats.sharpe(returns)}")
        print(f"CAGR: {qs.stats.cagr(returns)}")
        print(f"Max Drawdown: {max_drawdown:.4f}")  # Use the better of the two calculations
        
        # Try plotting basic charts with explicit non-interactive mode
        with plt.style.context('default'):
            # Returns plot
            qs.plots.returns(returns, savefig=os.path.join(results_dir, "returns.png"), show=False)
            plt.close()
            
            # Yearly returns plot
            qs.plots.yearly_returns(returns, savefig=os.path.join(results_dir, "yearly_returns.png"), show=False)
            plt.close()
            
            # Drawdowns plot
            qs.plots.drawdown(returns, savefig=os.path.join(results_dir, "drawdowns.png"), show=False)
            plt.close()
        
        # Create a simple HTML report with asset analysis
        with open(os.path.join(results_dir, "basic_report.html"), 'w') as f:
            f.write(f"""
            <html>
            <head>
                <title>{strategy_class.__name__} Strategy Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
                    th {{ background-color: #f2f2f2; text-align: center; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .section {{ margin-top: 30px; }}
                    .asset-charts {{ display: flex; flex-wrap: wrap; justify-content: space-around; }}
                    .asset-charts img {{ margin: 10px; max-width: 45%; }}
                    .button {{ 
                        display: inline-block;
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 15px;
                        text-align: center;
                        text-decoration: none;
                        font-size: 16px;
                        margin: 4px 2px;
                        cursor: pointer;
                        border-radius: 5px;
                    }}
                </style>
            </head>
            <body>
                <h1>{strategy_class.__name__} Strategy Report</h1>
                
                <div class="section">
                    <h2>Backtest Summary</h2>
                    <p>Start Date: {start_date}</p>
                    <p>End Date: {end_date}</p>
                    <p>Starting Cash: ${starting_cash:,.2f}</p>
                    <p>Ending Cash: ${final_value:,.2f}</p>
                    <p>Total Return: {(final_value / starting_cash - 1) * 100:.2f}%</p>
                    <p>Sharpe Ratio: {qs.stats.sharpe(returns):.4f}</p>
                    <p>CAGR: {qs.stats.cagr(returns):.4f}</p>
                    <p>Max Drawdown: {max_drawdown * 100:.2f}%</p>
                    <p>Sortino Ratio: {qs.stats.sortino(returns):.4f}</p>
                    <p>Calmar Ratio: {qs.stats.calmar(returns):.4f}</p>
                    <a href="quantstats_report.html" class="button">View Detailed Performance Report</a>
                </div>
                
                <div class="section">
                    <h2>Portfolio Performance</h2>
                    <img src="returns.png" alt="Returns" />
                    <img src="yearly_returns.png" alt="Yearly Returns" />
                    <img src="drawdowns.png" alt="Drawdowns" />
                </div>
                
                <div class="section">
                    <h2>Trade Summary</h2>
                    <table>
                        <tr>
                            <th>Asset</th>
                            <th>Total Trades</th>
                            <th>Buy Trades</th>
                            <th>Sell Trades</th>
                        </tr>
            """)
            
            # Add rows for each asset's trade summary
            for symbol, trades in trades_by_symbol.items():
                buy_trades = [t for t in trades if t['type'] == 'buy']
                sell_trades = [t for t in trades if t['type'] == 'sell']
                
                f.write(f"""
                        <tr>
                            <td>{symbol}</td>
                            <td>{len(trades)}</td>
                            <td>{len(buy_trades)}</td>
                            <td>{len(sell_trades)}</td>
                        </tr>
                """)
            
            f.write("""
                    </table>
                </div>
            """)
            
            f.write(f"""
                <div class="section">
                    <h2>Individual Asset Analysis</h2>
                    <table>
                        <tr>
                            <th>Asset</th>
                            <th>Total Return (%)</th>
                            <th>CAGR (%)</th>
                            <th>Volatility (%)</th>
                            <th>Sharpe Ratio</th>
                            <th>Max Drawdown (%)</th>
                        </tr>
            """)
            
            # Add rows for each asset
            for symbol, metrics in asset_metrics.items():
                f.write(f"""
                        <tr>
                            <td>{symbol}</td>
                            <td>{metrics['Total Return (%)']:.2f}</td>
                            <td>{metrics['CAGR (%)']:.2f}</td>
                            <td>{metrics['Volatility (%)']:.2f}</td>
                            <td>{metrics['Sharpe Ratio']:.2f}</td>
                            <td>{metrics['Max Drawdown (%)']:.2f}</td>
                        </tr>
                """)
            
            f.write(f"""
                    </table>
                </div>
                
                <div class="section">
                    <h2>Asset Comparison Charts</h2>
                    <div class="asset-charts">
                        <img src="asset_returns_comparison.png" alt="Asset Returns Comparison" />
                        <img src="asset_metrics_comparison.png" alt="Asset Metrics Comparison" />
                        <img src="asset_correlations.png" alt="Asset Correlations" />
                    </div>
                </div>
            </body>
            </html>
            """)
        
        # Try the full quantstats report with error handling
        try:
            # Use the display=False parameter to prevent interactive display
            qs.reports.html(
                returns,
                benchmark=benchmark_returns,
                output=os.path.join(results_dir, "quantstats_report.html"),
                title=f"{strategy_class.__name__} Strategy Report",
                display=False
            )
            print(f"QuantStats report saved to {os.path.join(results_dir, 'quantstats_report.html')}")
        except Exception as e:
            print(f"Error generating QuantStats report: {e}")
            print("Basic report was generated as an alternative.")
    except Exception as e:
        print(f"Error in generating reports: {e}")
    
    # Create a note about skipped Backtrader plot
    with open(os.path.join(results_dir, f"plot_{strategy_class.__name__}_info.txt"), 'w') as f:
        f.write("Backtrader plot was skipped to improve performance.\n")
        f.write("Please use the static visualization files for analysis.")

    return final_value