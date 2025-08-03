#!/usr/bin/env python3
"""
Compare Strategy Results

This script loads the results from two strategy backtest runs and presents
a side-by-side comparison of key performance metrics in a table format.
Includes benchmark performance for better context.
"""

import os
import sys
import pandas as pd
import numpy as np
import argparse
import glob
from tabulate import tabulate
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def find_latest_results(base_dir, strategy_names=None, timestamp=None):
    """
    Find the latest results directories for the specified strategies.
    
    Args:
        base_dir: Base directory where results are stored
        strategy_names: List of strategy names to find
        timestamp: Specific timestamp to look for (if comparing runs from same batch)
        
    Returns:
        Dictionary mapping strategy names to their results directories
    """
    if strategy_names is None:
        strategy_names = ["CryptoMomentum", "CryptoMomentumEqual"]
    
    result_dirs = {}
    
    if timestamp:
        # Look for specific timestamp
        for strategy in strategy_names:
            pattern = os.path.join(base_dir, f"{strategy}_{timestamp}*")
            matching_dirs = glob.glob(pattern)
            if matching_dirs:
                result_dirs[strategy] = max(matching_dirs, key=os.path.getmtime)
                print(f"Found {strategy} results with timestamp {timestamp}: {result_dirs[strategy]}")
            else:
                print(f"No results found for {strategy} with timestamp {timestamp}")
    else:
        # Find latest for each strategy
        for strategy in strategy_names:
            pattern = os.path.join(base_dir, f"{strategy}_*")
            matching_dirs = glob.glob(pattern)
            if matching_dirs:
                result_dirs[strategy] = max(matching_dirs, key=os.path.getmtime)
                # Extract the timestamp from the directory name for logging
                dir_name = os.path.basename(result_dirs[strategy])
                timestamp_part = dir_name.replace(f"{strategy}_", "")
                print(f"Found latest {strategy} results (timestamp: {timestamp_part}): {result_dirs[strategy]}")
            else:
                print(f"No results found for {strategy}")
    
    return result_dirs

def calculate_metrics_from_returns(returns_series, strategy_name):
    """
    Calculate performance metrics from a returns series.
    
    Args:
        returns_series: Series of returns
        strategy_name: Name of the strategy (for logging)
        
    Returns:
        Dictionary of performance metrics
    """
    metrics = {}
    
    # Convert to cumulative returns
    cumulative_returns = (1 + returns_series).cumprod()
    
    # Calculate key metrics
    initial_value = 1.0  # Starting value for normalized returns
    final_value = cumulative_returns.iloc[-1]
    total_return_pct = (final_value / initial_value - 1) * 100
    
    # Calculate CAGR
    start_date = returns_series.index[0]
    end_date = returns_series.index[-1]
    years = (end_date - start_date).days / 365.25
    cagr = (final_value / initial_value) ** (1 / years) - 1
    
    # Calculate volatility (annualized)
    volatility = returns_series.std() * np.sqrt(252)  # Assuming 252 trading days per year
    
    # Calculate Sharpe ratio (assuming risk-free rate of 0)
    sharpe = (returns_series.mean() * 252) / (returns_series.std() * np.sqrt(252)) if volatility > 0 else 0
    
    # Calculate maximum drawdown
    peak = cumulative_returns.cummax()
    drawdown = (cumulative_returns / peak - 1) * 100
    max_drawdown = drawdown.min()
    
    # Store metrics
    metrics['Total Return (%)'] = total_return_pct
    metrics['CAGR (%)'] = cagr * 100
    metrics['Volatility (%)'] = volatility * 100
    metrics['Sharpe Ratio'] = sharpe
    metrics['Max Drawdown (%)'] = max_drawdown
    metrics['Duration (years)'] = years
    
    print(f"Calculated metrics for {strategy_name} from returns data")
    return metrics

def load_performance_metrics(results_dir, strategy_name):
    """
    Load performance metrics from a results directory.
    
    Args:
        results_dir: Path to the results directory
        strategy_name: Name of the strategy (for logging)
        
    Returns:
        Dictionary of performance metrics
    """
    metrics = {}
    
    # First, try to calculate metrics from returns.csv (most accurate)
    returns_csv = os.path.join(results_dir, "returns.csv")
    if os.path.exists(returns_csv):
        try:
            returns_df = pd.read_csv(returns_csv, index_col=0, parse_dates=True)
            
            # Get the returns column (usually named 'return' or the first column)
            returns_col = 'return' if 'return' in returns_df.columns else returns_df.columns[0]
            returns_series = returns_df[returns_col]
            
            # Calculate metrics from returns
            metrics = calculate_metrics_from_returns(returns_series, strategy_name)
            
            # Load trade statistics if available
            trades_csv = os.path.join(results_dir, "trades.csv")
            if os.path.exists(trades_csv):
                try:
                    trades_df = pd.read_csv(trades_csv)
                    if not trades_df.empty:
                        # Calculate trade statistics
                        metrics['Total Trades'] = len(trades_df)
                        
                        # Calculate win rate if P/L column exists
                        if 'P/L' in trades_df.columns or 'PnL' in trades_df.columns:
                            pnl_col = 'P/L' if 'P/L' in trades_df.columns else 'PnL'
                            winning_trades = trades_df[trades_df[pnl_col] > 0]
                            metrics['Win Rate (%)'] = (len(winning_trades) / len(trades_df)) * 100
                            
                            # Calculate average profit/loss
                            metrics['Avg Profit/Loss (%)'] = trades_df[pnl_col].mean()
                            
                            # Calculate profit factor
                            gross_profit = winning_trades[pnl_col].sum()
                            losing_trades = trades_df[trades_df[pnl_col] < 0]
                            gross_loss = abs(losing_trades[pnl_col].sum()) if not losing_trades.empty else 1
                            metrics['Profit Factor'] = gross_profit / gross_loss if gross_loss > 0 else gross_profit
                        
                        print(f"Added trade statistics for {strategy_name}")
                except Exception as e:
                    print(f"Error processing trades.csv: {e}")
            
            return metrics
        except Exception as e:
            print(f"Error calculating metrics from returns.csv: {e}")
    
    # If we couldn't calculate from returns.csv, try asset_metrics.csv as fallback
    asset_metrics_csv = os.path.join(results_dir, "asset_metrics.csv")
    if os.path.exists(asset_metrics_csv):
        try:
            # Load the asset metrics file
            metrics_df = pd.read_csv(asset_metrics_csv)
            
            # Check if there's a Portfolio row, otherwise use the first row
            portfolio_row = metrics_df[metrics_df.iloc[:, 0] == 'Portfolio']
            if not portfolio_row.empty:
                row_to_use = portfolio_row.iloc[0]
            else:
                # Use the first row but warn that it might not be strategy performance
                row_to_use = metrics_df.iloc[0]
                print(f"Warning: Using {row_to_use.iloc[0]} metrics for {strategy_name} - may not reflect strategy performance")
            
            # Extract metrics from the row
            for col in metrics_df.columns:
                if col not in ['', 'Unnamed: 0']:  # Skip index columns
                    try:
                        # Convert percentage strings to float values if needed
                        if isinstance(row_to_use[col], str) and '%' in row_to_use[col]:
                            metrics[col] = float(row_to_use[col].replace('%', ''))
                        else:
                            metrics[col] = float(row_to_use[col])
                    except (ValueError, TypeError):
                        # If conversion fails, store as is
                        if pd.notnull(row_to_use[col]):
                            metrics[col] = row_to_use[col]
            
            print(f"Loaded metrics for {strategy_name} from asset_metrics.csv")
        except Exception as e:
            print(f"Error processing asset_metrics.csv: {e}")
    
    return metrics

def load_benchmark_metrics(results_dir):
    """
    Load benchmark performance metrics from a results directory.
    
    Args:
        results_dir: Path to the results directory
        
    Returns:
        Tuple of (benchmark_name, metrics_dict)
    """
    # Try to load benchmark returns
    benchmark_csv = os.path.join(results_dir, "benchmark_returns.csv")
    if os.path.exists(benchmark_csv):
        try:
            benchmark_df = pd.read_csv(benchmark_csv, index_col=0, parse_dates=True)
            
            # Get benchmark name (first column)
            if len(benchmark_df.columns) > 0:
                benchmark_name = benchmark_df.columns[0]
                
                # Extract benchmark returns
                benchmark_returns = benchmark_df[benchmark_name]
                
                # Calculate metrics from returns
                metrics = calculate_metrics_from_returns(benchmark_returns, benchmark_name)
                metrics['Benchmark'] = benchmark_name
                
                print(f"Loaded benchmark metrics for {benchmark_name}")
                return benchmark_name, metrics
        except Exception as e:
            print(f"Error processing benchmark_returns.csv: {e}")
    
    return None, {}

def compare_strategies(result_dirs):
    """
    Compare performance metrics between strategies and benchmark.
    
    Args:
        result_dirs: Dictionary mapping strategy names to their results directories
        
    Returns:
        DataFrame with comparison of metrics
    """
    all_metrics = {}
    benchmark_metrics = {}
    
    # Load strategy metrics
    for strategy, results_dir in result_dirs.items():
        metrics = load_performance_metrics(results_dir, strategy)
        if metrics:
            all_metrics[strategy] = metrics
        else:
            print(f"Warning: No metrics found for {strategy} in {results_dir}")
    
    # Load benchmark metrics from the first result directory
    if result_dirs:
        first_strategy = list(result_dirs.keys())[0]
        benchmark_name, benchmark_data = load_benchmark_metrics(result_dirs[first_strategy])
        if benchmark_name and benchmark_data:
            benchmark_metrics[benchmark_name] = benchmark_data
    
    # Create a DataFrame with all metrics
    comparison_data = {}
    
    # Define the metrics we want to include in the comparison
    key_metrics = [
        'Total Return (%)', 
        'CAGR (%)', 
        'Volatility (%)', 
        'Sharpe Ratio', 
        'Max Drawdown (%)',
        'Total Trades',
        'Win Rate (%)',
        'Duration (years)'
    ]
    
    # Add strategy metrics
    for strategy, metrics in all_metrics.items():
        strategy_data = {}
        for metric in key_metrics:
            if metric in metrics:
                strategy_data[metric] = metrics[metric]
            else:
                strategy_data[metric] = np.nan
        comparison_data[strategy] = strategy_data
    
    # Add benchmark metrics
    for benchmark, metrics in benchmark_metrics.items():
        benchmark_data = {}
        for metric in key_metrics:
            if metric in metrics:
                benchmark_data[metric] = metrics[metric]
            else:
                benchmark_data[metric] = np.nan
        comparison_data[benchmark] = benchmark_data
    
    # Convert to DataFrame
    comparison_df = pd.DataFrame(comparison_data)
    
    return comparison_df

def load_returns_data(results_dir):
    """
    Load returns data from a results directory.
    
    Args:
        results_dir: Path to the results directory
        
    Returns:
        DataFrame with returns data
    """
    # Try to load returns.csv
    returns_csv = os.path.join(results_dir, "returns.csv")
    if os.path.exists(returns_csv):
        try:
            returns_df = pd.read_csv(returns_csv, index_col=0, parse_dates=True)
            
            # Get the returns column (usually named 'return' or the first column)
            returns_col = 'return' if 'return' in returns_df.columns else returns_df.columns[0]
            
            # Create a new DataFrame with just the strategy returns
            strategy_returns = pd.DataFrame({
                'Returns': returns_df[returns_col]
            })
            
            return strategy_returns
        except Exception as e:
            print(f"Error loading returns data: {e}")
    
    return None

def plot_equity_curves(result_dirs, output_file=None, include_benchmark=True):
    """
    Plot equity curves for all strategies and benchmark on the same chart.
    
    Args:
        result_dirs: Dictionary mapping strategy names to their results directories
        output_file: Path to save the plot (optional)
        include_benchmark: Whether to include the benchmark in the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Dictionary to store all series for normalization
    all_series = {}
    benchmark_series = None
    
    # Load returns data for each strategy
    for strategy, results_dir in result_dirs.items():
        returns_df = load_returns_data(results_dir)
        if returns_df is not None and not returns_df.empty:
            # Convert to cumulative returns
            cumulative_returns = (1 + returns_df['Returns']).cumprod()
            all_series[strategy] = cumulative_returns
            
            # Load benchmark if we haven't already
            if include_benchmark and benchmark_series is None:
                benchmark_csv = os.path.join(results_dir, "benchmark_returns.csv")
                if os.path.exists(benchmark_csv):
                    try:
                        benchmark_df = pd.read_csv(benchmark_csv, index_col=0, parse_dates=True)
                        if len(benchmark_df.columns) > 0:
                            benchmark_name = benchmark_df.columns[0]
                            benchmark_returns = benchmark_df[benchmark_name]
                            benchmark_series = (1 + benchmark_returns).cumprod()
                            all_series[benchmark_name] = benchmark_series
                    except Exception as e:
                        print(f"Error loading benchmark data: {e}")
    
    # Normalize all series to start at 100
    for name, series in all_series.items():
        normalized = series / series.iloc[0] * 100
        
        # Use dashed line for benchmark
        if name in ['BTC_USDT', 'BTC-USD', 'ETH_USDT', 'ETH-USD', 'SOL_USDT']:
            normalized.plot(label=name, linestyle='--')
        else:
            normalized.plot(label=name)
    
    plt.title('Equity Curve Comparison (Normalized to 100)')
    plt.xlabel('Date')
    plt.ylabel('Value (Normalized)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Equity curve comparison saved to {output_file}")
    else:
        plt.show()

def plot_drawdowns(result_dirs, output_file=None, include_benchmark=True):
    """
    Plot drawdowns for all strategies and benchmark on the same chart.
    
    Args:
        result_dirs: Dictionary mapping strategy names to their results directories
        output_file: Path to save the plot (optional)
        include_benchmark: Whether to include the benchmark in the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Dictionary to store all drawdown series
    all_drawdowns = {}
    
    # Calculate drawdowns for each strategy
    for strategy, results_dir in result_dirs.items():
        returns_df = load_returns_data(results_dir)
        if returns_df is not None and not returns_df.empty:
            # Convert to cumulative returns
            cumulative_returns = (1 + returns_df['Returns']).cumprod()
            
            # Calculate drawdown
            peak = cumulative_returns.cummax()
            drawdown = (cumulative_returns / peak - 1) * 100
            all_drawdowns[strategy] = drawdown
            
            # Calculate benchmark drawdown if requested
            if include_benchmark:
                benchmark_csv = os.path.join(results_dir, "benchmark_returns.csv")
                if os.path.exists(benchmark_csv):
                    try:
                        benchmark_df = pd.read_csv(benchmark_csv, index_col=0, parse_dates=True)
                        if len(benchmark_df.columns) > 0:
                            benchmark_name = benchmark_df.columns[0]
                            
                            # Only calculate if we haven't already
                            if benchmark_name not in all_drawdowns:
                                benchmark_returns = benchmark_df[benchmark_name]
                                benchmark_cumulative = (1 + benchmark_returns).cumprod()
                                
                                # Calculate drawdown
                                benchmark_peak = benchmark_cumulative.cummax()
                                benchmark_drawdown = (benchmark_cumulative / benchmark_peak - 1) * 100
                                all_drawdowns[benchmark_name] = benchmark_drawdown
                    except Exception as e:
                        print(f"Error calculating benchmark drawdown: {e}")
    
    # Plot all drawdown series
    for name, series in all_drawdowns.items():
        # Use dashed line for benchmark
        if name in ['BTC_USDT', 'BTC-USD', 'ETH_USDT', 'ETH-USD', 'SOL_USDT']:
            series.plot(label=name, linestyle='--')
        else:
            series.plot(label=name)
    
    plt.title('Drawdown Comparison')
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.gca().invert_yaxis()  # Invert y-axis so drawdowns go down
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Drawdown comparison saved to {output_file}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="Compare strategy backtest results")
    parser.add_argument(
        "--results-dir",
        default=os.path.join(project_root, "results"),
        help="Base directory containing results folders"
    )
    parser.add_argument(
        "--timestamp",
        help="Specific timestamp to compare (format: YYYYMMDD_HHMMSS)"
    )
    parser.add_argument(
        "--strategies",
        nargs='+',
        default=["CryptoMomentum", "CryptoMomentumEqual"],
        help="Strategy names to compare"
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(project_root, "results", "comparisons"),
        help="Directory to save comparison results"
    )
    parser.add_argument(
        "--no-benchmark",
        action="store_true",
        help="Exclude benchmark from comparison"
    )
    
    args = parser.parse_args()
    
    # Find results directories
    result_dirs = find_latest_results(
        args.results_dir, 
        strategy_names=args.strategies,
        timestamp=args.timestamp
    )
    
    if not result_dirs:
        print(f"No results found for strategies: {args.strategies}")
        return
    
    print(f"\nFound results directories:")
    for strategy, directory in result_dirs.items():
        print(f"  {strategy}: {directory}")
    
    # Compare strategies
    comparison_df = compare_strategies(result_dirs)
    
    if comparison_df.empty:
        print("No metrics found to compare. Please check the results directories.")
        return
    
    # Format the table for display
    formatted_table = comparison_df.copy()
    
    # Format numeric columns
    for col in formatted_table.columns:
        for idx in formatted_table.index:
            if pd.notnull(formatted_table.loc[idx, col]):
                if 'Return' in idx or 'CAGR' in idx or 'Volatility' in idx or 'Drawdown' in idx or 'Win Rate' in idx:
                    formatted_table.loc[idx, col] = f"{formatted_table.loc[idx, col]:.2f}%"
                elif 'Ratio' in idx or 'Factor' in idx:
                    formatted_table.loc[idx, col] = f"{formatted_table.loc[idx, col]:.2f}"
                elif 'Value' in idx:
                    formatted_table.loc[idx, col] = f"${formatted_table.loc[idx, col]:,.2f}"
                elif 'Trades' in idx:
                    formatted_table.loc[idx, col] = f"{int(formatted_table.loc[idx, col])}"
    
    # Print the comparison table
    print("\n--- Strategy Comparison ---")
    print(tabulate(formatted_table, headers='keys', tablefmt='grid'))
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Save the comparison to CSV
    timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    comparison_csv = os.path.join(args.output_dir, f"strategy_comparison_{timestamp}.csv")
    comparison_df.to_csv(comparison_csv)
    print(f"\nComparison saved to {comparison_csv}")
    
    # Plot equity curves
    equity_plot = os.path.join(args.output_dir, f"equity_comparison_{timestamp}.png")
    plot_equity_curves(result_dirs, equity_plot, not args.no_benchmark)
    
    # Plot drawdowns
    drawdown_plot = os.path.join(args.output_dir, f"drawdown_comparison_{timestamp}.png")
    plot_drawdowns(result_dirs, drawdown_plot, not args.no_benchmark)
    
    # Calculate and print additional comparative metrics
    if len(comparison_df.columns) >= 2:
        print("\n--- Comparative Analysis ---")
        
        # Find the benchmark column if it exists
        benchmark_col = None
        for col in comparison_df.columns:
            if col not in args.strategies:
                benchmark_col = col
                break
        
        # Compare strategies to each other and to benchmark
        for metric in ['Total Return (%)', 'CAGR (%)', 'Sharpe Ratio', 'Max Drawdown (%)']:
            if metric in comparison_df.index:
                print(f"\n{metric}:")
                
                # Compare strategies to each other
                for i, strategy1 in enumerate(args.strategies):
                    for strategy2 in args.strategies[i+1:]:
                        if strategy1 in comparison_df.columns and strategy2 in comparison_df.columns:
                            val1 = comparison_df.loc[metric, strategy1]
                            val2 = comparison_df.loc[metric, strategy2]
                            
                            if pd.notnull(val1) and pd.notnull(val2):
                                diff = val1 - val2
                                pct_diff = (diff / abs(val2)) * 100 if val2 != 0 else float('inf')
                                
                                # Format based on metric
                                if 'Return' in metric or 'CAGR' in metric:
                                    print(f"  {strategy1} vs {strategy2}: {diff:.2f}% difference ({pct_diff:.2f}% relative)")
                                elif 'Drawdown' in metric:
                                    print(f"  {strategy1} vs {strategy2}: {diff:.2f}% difference (smaller is better)")
                                else:
                                    print(f"  {strategy1} vs {strategy2}: {diff:.2f} difference ({pct_diff:.2f}% relative)")
                
                # Compare strategies to benchmark
                if benchmark_col and benchmark_col in comparison_df.columns:
                    benchmark_val = comparison_df.loc[metric, benchmark_col]
                    
                    if pd.notnull(benchmark_val):
                        print(f"\n  Compared to {benchmark_col}:")
                        for strategy in args.strategies:
                            if strategy in comparison_df.columns:
                                strategy_val = comparison_df.loc[metric, strategy]
                                
                                if pd.notnull(strategy_val):
                                    diff = strategy_val - benchmark_val
                                    pct_diff = (diff / abs(benchmark_val)) * 100 if benchmark_val != 0 else float('inf')
                                    
                                    # Format based on metric
                                    if 'Return' in metric or 'CAGR' in metric:
                                        print(f"    {strategy}: {diff:.2f}% above/below benchmark ({pct_diff:.2f}% relative)")
                                    elif 'Drawdown' in metric:
                                        print(f"    {strategy}: {diff:.2f}% difference from benchmark (smaller is better)")
                                    else:
                                        print(f"    {strategy}: {diff:.2f} above/below benchmark ({pct_diff:.2f}% relative)")
    
    print("\nComparison complete!")

if __name__ == "__main__":
    main()