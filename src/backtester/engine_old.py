import backtrader as bt
import pandas as pd
import os
from . import utils
from .analysis import metrics
import quantstats as qs

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
    cerebro = bt.Cerebro()

    # Add strategy with parameters
    if strategy_params:
        cerebro.addstrategy(strategy_class, **strategy_params)
    else:
        cerebro.addstrategy(strategy_class)

    # Add data feeds
    start_dt = pd.Timestamp(start_date, tz='UTC')
    end_dt = pd.Timestamp(end_date, tz='UTC')

    for symbol in symbols:
        try:
            data_path = os.path.join(data_dir)
            df = utils.fetch_data(data_path, symbol, start_dt, end_dt)
            data_feed = bt.feeds.PandasData(dataname=df, name=symbol)
            cerebro.adddata(data_feed, name=symbol)
            print(f"Successfully loaded data for {symbol}")
        except FileNotFoundError as e:
            print(f"Warning: Could not load data for {symbol}. Error: {e}")
            continue

    # Configure broker
    cerebro.broker.setcash(starting_cash)
    # cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    # Run backtest
    print(f"\nStarting Portfolio Value: {cerebro.broker.getvalue():,.2f}")
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f"Ending Portfolio Value:   {final_value:,.2f}\n")

    
    strat = results[0]
    pyfoliozer = strat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()

    # Get benchmark data
    benchmark_returns = utils.get_benchmark(benchmark, start_dt, end_dt, data_dir)

    # Convert both indices to timezone-naive
    returns.index = returns.index.tz_localize(None)
    benchmark_returns.index = benchmark_returns.index.tz_convert(None)
    returns, benchmark_returns = returns.align(benchmark_returns, join='inner')  # Align both Series/DataFrame to the same dates


    # Check for extreme negative returns that might cause issues
    if returns.min() <= -1:
        print("Warning: Returns contain values <= -1, which can cause issues with calculations.")
        # Clip extreme negative values to prevent calculation issues
        returns = returns.clip(lower=-0.99)

    # ... existing code ...
    
    # Save returns data
    returns.to_csv(os.path.join(results_dir, "returns.csv"))

    if benchmark_returns is not None:
        benchmark_returns.to_csv(os.path.join(results_dir, "benchmark_returns.csv"))
    
    # Create a custom drawdown calculation function
    def calculate_drawdowns(returns):
        """Calculate drawdowns manually."""
        # Ensure returns are greater than -1 (prevent division by zero issues)
        returns = returns.clip(lower=-0.99)
        # Calculate wealth index
        wealth_index = (1 + returns).cumprod()
        # Calculate previous peaks
        previous_peaks = wealth_index.cummax()
        # Calculate drawdowns
        drawdowns = (wealth_index - previous_peaks) / previous_peaks
        return drawdowns
    
    # Calculate drawdowns manually
    drawdowns = calculate_drawdowns(returns)
    max_drawdown = drawdowns.min()
    
    # Generate basic metrics report
    try:
        # Simple metrics first
        print("\nBasic metrics:")
        print(f"Sharpe Ratio: {qs.stats.sharpe(returns)}")
        print(f"CAGR: {qs.stats.cagr(returns)}")
        print(f"Max Drawdown: {max_drawdown:.4f}")  # Use our manual calculation
        
        # Try plotting basic charts
        qs.plots.returns(returns, savefig=os.path.join(results_dir, "returns.png"))
        qs.plots.yearly_returns(returns, savefig=os.path.join(results_dir, "yearly_returns.png"))
        
        # Create a simple HTML report
        with open(os.path.join(results_dir, "basic_report.html"), 'w') as f:
            f.write(f"""
            <html>
            <head><title>{strategy_class.__name__} Strategy Report</title></head>
            <body>
                <h1>{strategy_class.__name__} Strategy Report</h1>
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
                <img src="returns.png" alt="Returns" />
                <img src="yearly_returns.png" alt="Yearly Returns" />
            </body>
            </html>
            """)
        
        # Try the full quantstats report with error handling
        try:
            qs.reports.html(
                returns,
                benchmark=benchmark_returns,
                output=os.path.join(results_dir, "quantstats_report.html"),
                title=f"{strategy_class.__name__} Strategy Report"
            )
            print(f"QuantStats report saved to {os.path.join(results_dir, 'quantstats_report.html')}")
        except Exception as e:
            print(f"Error generating QuantStats report: {e}")
            print("Basic report was generated as an alternative.")
    except Exception as e:
        print(f"Error in generating reports: {e}")
    
    # Save Backtrader plot
    utils.save_backtrader_plot(cerebro, output_dir=results_dir, filename=f"plot_{strategy_class.__name__}.png")


    return final_value
