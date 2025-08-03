import argparse
import configparser
import os
import sys
from datetime import datetime
import pandas as pd
import itertools

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backtester.engine import run_backtest
from src.backtester.strategies.crypto.CryptoMomentum import CryptoTSMomentum

# A mapping from strategy names to their classes
STRATEGY_MAP = {
    'CryptoTSMomentum': CryptoTSMomentum
}

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run a grid search for crypto backtest parameters.')
    parser.add_argument('--strategy', type=str, default='CryptoTSMomentum',
                        choices=list(STRATEGY_MAP.keys()),
                        help='The strategy to use for the backtest.')
    parser.add_argument('--start_date', type=str, default='2023-01-01',
                        help='Start date for the backtest in YYYY-MM-DD format.')
    parser.add_argument('--end_date', type=str, default='2023-12-31',
                        help='End date for the backtest in YYYY-MM-DD format.')
    parser.add_argument('--timeframe', type=str, default='15mins',
                        choices=['1min', '5mins', '15mins', '1H', '4H', '1D'],
                        help='Timeframe for the data.')
    parser.add_argument('--initial_cash', type=float, default=10000.0,
                        help='Initial cash for the backtest.')
    parser.add_argument('--commission', type=float, default=0.001,
                        help='Commission rate per trade (e.g., 0.001 for 0.1%).')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to a configuration file with strategy parameters.')
    return parser.parse_args()

def load_config(config_path):
    if not config_path or not os.path.exists(config_path):
        return None
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def get_parameter_grid():
    """
    Define the grid of parameters to test.
    Returns a list of dictionaries, each representing a combination of parameters.
    """
    lookback_periods = [24, 48]  # e.g., 6h, 12h on 15min timeframe (reduced for testing)
    holding_periods = [48, 96]    # e.g., 12h, 24h on 15min timeframe (reduced for testing)
    stop_losses = [0.05]          # 5% only (reduced for testing)
    take_profits = [0.1]          # 10% only (reduced for testing)

    # Generate all combinations using itertools.product
    combinations = list(itertools.product(lookback_periods, holding_periods, stop_losses, take_profits))
    param_grid = [
        {
            'lookback_period': combo[0],
            'holding_period': combo[1],
            'stop_loss': combo[2],
            'take_profit': combo[3],
            'log_to_terminal': False
        }
        for combo in combinations
    ]
    return param_grid

def run_grid_search(strategy_class, assets, start_date, end_date, timeframe, initial_cash, commission_rate, param_grid, project_root):
    """
    Run backtests for each combination of parameters in the grid and collect results.
    Returns a DataFrame summarizing the performance metrics for each run.
    """
    results = []
    total_runs = len(param_grid)
    print(f"Starting grid search with {total_runs} parameter combinations...")

    for i, params in enumerate(param_grid, 1):
        # Optionally suppress detailed output to terminal for efficiency
        verbose = False  # Can be toggled or made configurable if needed
        if verbose:
            print(f"Running backtest {i}/{total_runs} with parameters: {params}")
        # Create a unique subfolder for this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        strategy_name = strategy_class.__name__
        results_subfolder = f"{strategy_name}_{timestamp}_{i}"
        unique_results_dir = os.path.join(project_root, 'results', 'grid_search', results_subfolder)
        os.makedirs(unique_results_dir, exist_ok=True)
        if verbose:
            print(f"Saving results to: {unique_results_dir}")

        try:
            # Run the backtest with current parameters
            run_backtest(
                strategy_class=strategy_class,
                symbols=assets,
                start_date=start_date,
                end_date=end_date,
                starting_cash=initial_cash,
                data_dir=os.path.join(project_root, 'data', 'crypto'),
                results_dir=unique_results_dir,
                benchmark='BTC_USDT',
                strategy_params=params
            )
            # Extract metrics from result files if they exist
            metrics = extract_metrics(unique_results_dir, i, params)
            results.append(metrics)
            if verbose:
                print(f"Completed run {i}/{total_runs}:")
                print(f"  Sharpe Ratio: {metrics['sharpe_ratio']}")
                print(f"  Total Return: {metrics['total_return']}%")
                print(f"  Max Drawdown: {metrics['max_drawdown']}%")
                print(f"  Total Trades: {metrics['total_trades']}")
        except Exception as e:
            print(f"Error in run {i}/{total_runs}: {e}")
            results.append({
                'run_id': i,
                'lookback_period': params['lookback_period'],
                'holding_period': params['holding_period'],
                'stop_loss': params['stop_loss'],
                'take_profit': params['take_profit'],
                'sharpe_ratio': 'Error',
                'total_return': 'Error',
                'total_trades': 'Error',
                'max_drawdown': 'Error'
            })

    # Convert results to DataFrame for summary
    results_df = pd.DataFrame(results)
    return results_df

def extract_metrics(results_dir, run_id, params):
    """
    Extract performance metrics from backtest result files in the given directory.
    Returns a dictionary of metrics for the run.
    Note: This is a basic implementation and may need customization based on actual file formats.
    """
    import os
    import pandas as pd
    import glob

    metrics = {
        'run_id': run_id,
        'lookback_period': params['lookback_period'],
        'holding_period': params['holding_period'],
        'stop_loss': params['stop_loss'],
        'take_profit': params['take_profit'],
        'sharpe_ratio': 0.0,
        'total_return': 0.0,
        'total_trades': 0,
        'max_drawdown': 0.0
    }
    
    # Since results_dir is already the unique directory for this run, use it directly
    run_dir = results_dir
    print(f"Looking for result files in: {run_dir}")
    
    # List all files in the run directory for debugging
    if os.path.exists(run_dir):
        print(f"Contents of results directory for run {run_id}:")
        for root, dirs, files in os.walk(run_dir):
            level = root.replace(run_dir, '').count(os.sep)
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                print(f"{subindent}{f}")
                # Try to peek into file contents if it's a potential summary file
                if any(keyword in f.lower() for keyword in ['summary', 'stats', 'report', 'result', 'backtest']) and any(f.endswith(ext) for ext in ['.csv', '.json', '.html', '.txt']):
                    file_path = os.path.join(root, f)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as peek_file:
                            first_lines = peek_file.readlines()[:5]
                            print(f"{subindent}  First few lines of {f}:")
                            for line in first_lines:
                                print(f"{subindent}    {line.strip()}")
                    except Exception as e:
                        print(f"{subindent}  Could not read contents of {f}: {e}")
    else:
        print(f"Results directory not found for run {run_id}: {run_dir}")
        return metrics

    # Search for potential summary files with flexible naming
    summary_data_found = False
    possible_summary_files = glob.glob(os.path.join(run_dir, '**', '*[sS][uU][mM][mM][aA][rR][yY]*'), recursive=True) + \
                             glob.glob(os.path.join(run_dir, '**', '*[sS][tT][aA][tT][sS]*'), recursive=True) + \
                             glob.glob(os.path.join(run_dir, '**', '*[rR][eE][pP][oO][rR][tT]*'), recursive=True) + \
                             glob.glob(os.path.join(run_dir, '**', '*[bB][aA][cC][kK][tT][eE][sS][tT]*'), recursive=True)
    
    # Prioritize specific files that might contain structured metrics
    for summary_file in possible_summary_files:
        file_name = os.path.basename(summary_file).lower()
        if 'asset_metrics' in file_name and summary_file.endswith('.csv'):
            try:
                summary_df = pd.read_csv(summary_file)
                # Try to find columns with relevant names (case insensitive)
                cols = summary_df.columns
                sharpe_col = next((col for col in cols if 'sharpe' in col.lower()), None)
                return_col = next((col for col in cols if 'return' in col.lower() or 'cagr' in col.lower()), None)
                drawdown_col = next((col for col in cols if 'drawdown' in col.lower()), None)
                trades_col = next((col for col in cols if 'trade' in col.lower()), None)
                
                if sharpe_col:
                    metrics['sharpe_ratio'] = summary_df[sharpe_col].iloc[0] if len(summary_df) > 0 else 0.0
                if return_col:
                    metrics['total_return'] = summary_df[return_col].iloc[0] if len(summary_df) > 0 else 0.0
                if drawdown_col:
                    metrics['max_drawdown'] = summary_df[drawdown_col].iloc[0] if len(summary_df) > 0 else 0.0
                if trades_col:
                    metrics['total_trades'] = summary_df[trades_col].iloc[0] if len(summary_df) > 0 else 0
                if any([sharpe_col, return_col, drawdown_col, trades_col]):
                    summary_data_found = True
                    print(f"Summary data extracted from {summary_file}")
                    print(f"Extracted values - Sharpe: {metrics['sharpe_ratio']}, Return: {metrics['total_return']}%, Drawdown: {metrics['max_drawdown']}%, Trades: {metrics['total_trades']}")
                    break
            except Exception as e:
                print(f"Error reading CSV file {summary_file} for run {run_id}: {e}")
        elif summary_file.endswith('.csv'):
            try:
                summary_df = pd.read_csv(summary_file)
                # Try broader search for columns if not already found in asset_metrics.csv
                cols = summary_df.columns
                sharpe_col = next((col for col in cols if 'sharpe' in col.lower()), None)
                return_col = next((col for col in cols if 'return' in col.lower() or 'cagr' in col.lower()), None)
                drawdown_col = next((col for col in cols if 'drawdown' in col.lower()), None)
                trades_col = next((col for col in cols if 'trade' in col.lower()), None)
                
                if sharpe_col:
                    metrics['sharpe_ratio'] = summary_df[sharpe_col].iloc[0] if len(summary_df) > 0 else 0.0
                if return_col:
                    metrics['total_return'] = summary_df[return_col].iloc[0] if len(summary_df) > 0 else 0.0
                if drawdown_col:
                    metrics['max_drawdown'] = summary_df[drawdown_col].iloc[0] if len(summary_df) > 0 else 0.0
                if trades_col:
                    metrics['total_trades'] = summary_df[trades_col].iloc[0] if len(summary_df) > 0 else 0
                if any([sharpe_col, return_col, drawdown_col, trades_col]):
                    summary_data_found = True
                    print(f"Summary data extracted from {summary_file}")
                    print(f"Extracted values - Sharpe: {metrics['sharpe_ratio']}, Return: {metrics['total_return']}%, Drawdown: {metrics['max_drawdown']}%, Trades: {metrics['total_trades']}")
                    break
            except Exception as e:
                print(f"Error reading CSV file {summary_file} for run {run_id}: {e}")
        elif summary_file.endswith('.json'):
            try:
                summary_df = pd.read_json(summary_file, orient='index', typ='series')
                metrics['sharpe_ratio'] = summary_df.get('Sharpe Ratio', summary_df.get('sharpe_ratio', summary_df.get('sharpe', 0.0)))
                metrics['total_return'] = summary_df.get('Return [%]', summary_df.get('return', summary_df.get('total_return', 0.0)))
                metrics['max_drawdown'] = summary_df.get('Max. Drawdown [%]', summary_df.get('max_drawdown', summary_df.get('drawdown', 0.0)))
                metrics['total_trades'] = summary_df.get('# Trades', summary_df.get('trades', summary_df.get('total_trades', 0)))
                summary_data_found = True
                print(f"Summary data extracted from {summary_file}")
                print(f"Extracted values - Sharpe: {metrics['sharpe_ratio']}, Return: {metrics['total_return']}%, Drawdown: {metrics['max_drawdown']}%, Trades: {metrics['total_trades']}")
                break
            except Exception as e:
                print(f"Error reading JSON file {summary_file} for run {run_id}: {e}")
        elif summary_file.endswith('.html') or summary_file.endswith('.txt'):
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Enhanced parsing for common metrics in text or HTML, with more specific patterns tailored to QuantStats output
                    import re
                    # Look for Sharpe Ratio with possible labels, often in a table or with specific formatting
                    sharpe_match = re.search(r'(?:Sharpe Ratio|Sharpe)\s*[:]?\s*([-]?[0-9]+[.]?[0-9]*)', content, re.IGNORECASE)
                    if not sharpe_match:
                        sharpe_match = re.search(r'(?<=Sharpe</td>\s*<td[^>]*>)\s*([-]?[0-9]+[.]?[0-9]*)\s*(?=</td>)', content, re.IGNORECASE)
                    # Look for Cumulative Return or Total Return, often with a percentage
                    return_match = re.search(r'(?:Cumulative Return|Total Return|Return)\s*[:]?\s*([-]?[0-9]+[.]?[0-9]*)(?:%|\s*percent)?', content, re.IGNORECASE)
                    if not return_match:
                        return_match = re.search(r'(?<=Cumulative Return</td>\s*<td[^>]*>)\s*([-]?[0-9]+[.]?[0-9]*)(?:%|\s*percent)?\s*(?=</td>)', content, re.IGNORECASE)
                    # Look for Max Drawdown with percentage context, often negative
                    drawdown_match = re.search(r'(?:Max Drawdown|Maximum Drawdown|Drawdown)\s*[:]?\s*([-]?[0-9]+[.]?[0-9]*)(?:%|\s*percent)?', content, re.IGNORECASE)
                    if not drawdown_match:
                        drawdown_match = re.search(r'(?<=Max Drawdown</td>\s*<td[^>]*>)\s*([-]?[0-9]+[.]?[0-9]*)(?:%|\s*percent)?\s*(?=</td>)', content, re.IGNORECASE)
                    # Look for number of trades, often labeled as # Trades or Total Trades
                    trades_match = re.search(r'(?:# Trades|Number of Trades|Total Trades)\s*[:]?\s*([0-9]+)', content, re.IGNORECASE)
                    if not trades_match:
                        trades_match = re.search(r'(?<=# Trades</td>\s*<td[^>]*>)\s*([0-9]+)\s*(?=</td>)', content, re.IGNORECASE)
                    
                    if sharpe_match:
                        metrics['sharpe_ratio'] = float(sharpe_match.group(1))
                    if return_match:
                        metrics['total_return'] = float(return_match.group(1))
                    if drawdown_match:
                        metrics['max_drawdown'] = float(drawdown_match.group(1)) if float(drawdown_match.group(1)) <= 0 else -float(drawdown_match.group(1))  # Ensure drawdown is negative
                    if trades_match:
                        metrics['total_trades'] = int(trades_match.group(1))
                    if any([sharpe_match, return_match, drawdown_match, trades_match]):
                        summary_data_found = True
                        print(f"Summary data extracted from {summary_file} using text parsing")
                        print(f"Extracted values - Sharpe: {metrics['sharpe_ratio']}, Return: {metrics['total_return']}%, Drawdown: {metrics['max_drawdown']}%, Trades: {metrics['total_trades']}")
                        break
            except Exception as e:
                print(f"Error parsing text/HTML file {summary_file} for run {run_id}: {e}")
    
    if not summary_data_found:
        print(f"No suitable summary file found for run {run_id} in {run_dir}")
        # As a last resort, check if there's a trades file to at least get trade count
        trades_files = glob.glob(os.path.join(run_dir, '**', '*[tT][rR][aA][dD][eE][sS]*.csv'), recursive=True)
        if trades_files:
            try:
                trades_df = pd.read_csv(trades_files[0])
                metrics['total_trades'] = len(trades_df)
                print(f"Trade count extracted from {trades_files[0]}")
            except Exception as e:
                print(f"Error reading trades file for run {run_id}: {e}")
    
    return metrics

    # Check for trades.csv to get total trades
    trades_file = os.path.join(results_dir, 'trades.csv')
    if os.path.exists(trades_file):
        try:
            trades_df = pd.read_csv(trades_file)
            metrics['total_trades'] = len(trades_df)
        except Exception as e:
            print(f"Error reading trades.csv for run {run_id}: {e}")

    # Placeholder for other metrics - in a full implementation, parse files like basic_report.html or returns.csv
    # For now, return placeholder values as actual parsing logic depends on file format and content
    # Future enhancement: Add logic to parse specific files for sharpe_ratio, total_return, max_drawdown
    return metrics

def generate_summary_report(results_df, output_dir):
    """
    Generate a summary report of the grid search results and save it.
    """
    summary_path = os.path.join(output_dir, 'grid_search_summary.csv')
    results_df.to_csv(summary_path, index=False)
    print(f"Grid search summary saved to: {summary_path}")

    # Optional: Generate a simple HTML report or other format if needed
    html_path = os.path.join(output_dir, 'grid_search_summary.html')
    with open(html_path, 'w') as f:
        f.write("<html><body>")
        f.write("<h2>Grid Search Summary for CryptoTSMomentum</h2>")
        f.write(results_df.to_html())
        f.write("</body></html>")
    print(f"Grid search HTML report saved to: {html_path}")

    # Print top performers by Sharpe ratio (if available)
    if 'sharpe_ratio' in results_df.columns and results_df['sharpe_ratio'].dtype in ['float64', 'int64']:
        top_performers = results_df.sort_values(by='sharpe_ratio', ascending=False).head(5)
        print("Top 5 parameter combinations by Sharpe Ratio:")
        print(top_performers)

def main():
    args = parse_arguments()
    config = load_config(args.config)
    # Since we're doing a grid search, we'll override individual params with our grid
    strategy_params = {}  # Placeholder, will be overridden by grid search

    # Define BTC_USDT as the only asset for this backtest
    assets = ['BTC_USDT']
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

    # Get parameter grid for search
    param_grid = get_parameter_grid()
    print(f"Parameter grid contains {len(param_grid)} combinations.")

    # Run grid search
    results_df = run_grid_search(
        strategy_class=STRATEGY_MAP[args.strategy],
        assets=assets,
        start_date=start_date,
        end_date=end_date,
        timeframe=args.timeframe,
        initial_cash=args.initial_cash,
        commission_rate=args.commission,
        param_grid=param_grid,
        project_root=project_root
    )

    # Generate summary report
    grid_search_dir = os.path.join(project_root, 'results', 'grid_search')
    os.makedirs(grid_search_dir, exist_ok=True)
    generate_summary_report(results_df, grid_search_dir)

if __name__ == '__main__':
    main()
