import argparse
import configparser
import os
import sys
from datetime import datetime

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.backtester.engine import run_backtest
from src.backtester.strategies.asset_allocation.TAA import TAA_Momentum
# Import other strategies here as they are created
# from src.backtester.strategies.pairs_trading import PairsTradingStrategy

# A mapping from strategy names to their classes
STRATEGY_MAP = {
    "TAA": TAA_Momentum,
    # "PAIRS": PairsTradingStrategy,
}

def main():
    # --- Configuration & Argument Parsing ---
    parser = argparse.ArgumentParser(description="Event-Driven Backtesting Engine")
    parser.add_argument(
        "--strategy",
        required=True,
        default="TAA",
        choices=STRATEGY_MAP.keys(),
        help="The name of the strategy to run."
    )
    parser.add_argument(
        "--config",
        default=os.path.join(project_root, "config", "default.ini"),
        help="Path to the configuration file."
    )
    # args = parser.parse_args()
    args = argparse.Namespace(
    strategy="TAA",
    config=os.path.join(project_root, "config", "default.ini")
    )

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
    
    # Create a unique subdirectory for this run's results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = os.path.join(results_dir_base, f"{args.strategy}_{timestamp}")
    os.makedirs(results_dir, exist_ok=True)

    # Strategy-specific settings
    strategy_class = STRATEGY_MAP[args.strategy]
    symbols = config.get('StrategyTAA', 'Symbols').split(',')
    strategy_params = {
        'mom_lookback': config.getint('StrategyTAA', 'MomentumLookback'),
        'mom_top_n': config.getint('StrategyTAA', 'MomentumTopN'),
    }

    print("--- Backtest Configuration ---")
    print(f"Strategy: {args.strategy}")
    print(f"Symbols: {symbols}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Starting Cash: ${starting_cash:,.2f}")
    print(f"Data Directory: {data_dir}")
    print(f"Results Directory: {results_dir}")
    print(f"Strategy Parameters: {strategy_params}")
    print("----------------------------")

    # --- Run the Backtest ---
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

if __name__ == "__main__":
    main()