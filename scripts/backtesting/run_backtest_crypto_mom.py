import argparse
import configparser
import os
import sys
from datetime import datetime

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backtester.engine import run_backtest
from src.backtester.strategies.crypto.CryptoMomentum import CryptoMomentum, CryptoTSMomentum, CryptoMomentumEqual

# A mapping from strategy names to their classes
STRATEGY_MAP = {
    "CryptoTSMomentum": CryptoTSMomentum,
    "CryptoMomentum": CryptoMomentum,
    "CryptoMomentumEqual": CryptoMomentumEqual,
}

def main():
    # --- Configuration & Argument Parsing ---
    parser = argparse.ArgumentParser(description="Event-Driven Backtesting Engine")
    parser.add_argument(
        "--strategy",
        default="CryptoMomentum",
        choices=STRATEGY_MAP.keys(),
        help="The name of the strategy to run."
    )
    parser.add_argument(
        "--config",
        default=os.path.join(project_root, "config", "crypto.ini"),
        help="Path to the configuration file."
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run both strategies for comparison"
    )
    
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    # --- Setup Paths & Parameters ---
    # General settings
    start_date = config.get('General', 'StartDate')
    end_date = config.get('General', 'EndDate')
    starting_cash = config.getfloat('General', 'StartingCash')
    
    # Data and results directories
    data_dir = os.path.join(project_root, config.get('Paths', 'DataDir'))
    results_dir_base = os.path.join(project_root, config.get('Paths', 'ResultsDir'))
    
    # Create a timestamp for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Strategy-specific settings
    symbols = config.get('CryptoMomentum', 'Symbols').split(',')
    strategy_params = {
        'mom_lookback': config.getint('CryptoMomentum', 'MomentumLookback'),
        'mom_top_n': config.getint('CryptoMomentum', 'MomentumTopN'),
    }
    
    # Determine which strategies to run
    strategies_to_run = []
    if args.compare:
        strategies_to_run = ["CryptoMomentum", "CryptoMomentumEqual"]
        print("Running both strategies for comparison...")
    else:
        strategies_to_run = [args.strategy]
        
    # Run each strategy
    for strategy_name in strategies_to_run:
        strategy_class = STRATEGY_MAP[strategy_name]
        
        # Create a unique subdirectory for this strategy's results
        results_dir = os.path.join(results_dir_base, f"{strategy_name}_{timestamp}")
        os.makedirs(results_dir, exist_ok=True)
        
        print(f"\n--- Backtest Configuration for {strategy_name} ---")
        print(f"Symbols: {symbols}")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"Starting Cash: ${starting_cash:,.2f}")
        print(f"Data Directory: {data_dir}")
        print(f"Results Directory: {results_dir}")
        print(f"Strategy Parameters: {strategy_params}")
        print("----------------------------")
        
        # Run the backtest
        run_backtest(
            strategy_class=strategy_class,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            starting_cash=starting_cash,
            data_dir=data_dir,
            results_dir=results_dir,
            benchmark=config.get('General', 'Benchmark'),
            strategy_params=strategy_params
        )
        
        print(f"Completed backtest for {strategy_name}")
    
    if args.compare:
        print("\n--- Comparison Complete ---")
        print(f"Results for both strategies are saved in separate folders with timestamp {timestamp}")
        print(f"You can find the results in: {results_dir_base}")
        print("To compare the strategies, examine the performance metrics in each folder's results")

if __name__ == "__main__":
    main()