import argparse
import configparser
import os
import sys
from datetime import datetime

# Add the project root to the Python path to allow for absolute imports
# Get the absolute path to the project root (two levels up from this script)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from src.backtester.engine import run_backtest
from src.backtester.strategies.crypto.CryptoMomentum import CryptoTSMomentum

# A mapping from strategy names to their classes
STRATEGY_MAP = {
    'CryptoTSMomentum': CryptoTSMomentum
}

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run a backtest for crypto strategies.')
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
    parser.add_argument('--lookback', type=int, default=96,
                        help='Lookback period for momentum calculation (in bars).')
    parser.add_argument('--momentum_threshold', type=float, default=0.02,
                        help='Minimum momentum threshold for entry (e.g., 0.02 for 2%).')
    parser.add_argument('--vol_lookback', type=int, default=48,
                        help='Lookback period for volatility calculation (in bars).')
    parser.add_argument('--max_position_size', type=float, default=0.3,
                        help='Maximum position size as fraction of portfolio (e.g., 0.3 for 30%).')
    parser.add_argument('--stop_loss', type=float, default=0.05,
                        help='Stop loss percentage.')
    parser.add_argument('--take_profit', type=float, default=0.15,
                        help='Take profit percentage.')
    parser.add_argument('--max_daily_trades', type=int, default=5,
                        help='Maximum number of trades per day.')
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

def get_strategy_params(args, config):
    if config and args.strategy in config:
        section = config[args.strategy]
        return {
            'lookback_period': int(section.get('lookback_period', args.lookback)),
            'momentum_threshold': float(section.get('momentum_threshold', 0.02)),
            'vol_lookback': int(section.get('vol_lookback', 48)),
            'max_position_size': float(section.get('max_position_size', 0.3)),
            'stop_loss': float(section.get('stop_loss', args.stop_loss)),
            'take_profit': float(section.get('take_profit', args.take_profit)),
            'commission': float(section.get('commission', args.commission)),
            'max_daily_trades': int(section.get('max_daily_trades', 5)),
        }
    return {
        'lookback_period': args.lookback,
        'momentum_threshold': 0.01,  # 1% instead of 0.5%
        'vol_lookback': 24,  # 6 hours instead of 12 hours
        'max_position_size': 0.3,

        'stop_loss': args.stop_loss,
        'take_profit': args.take_profit,
        'commission': args.commission,
        'max_daily_trades': 5,
    }

def main():
    args = parse_arguments()
    config = load_config(args.config)
    strategy_params = get_strategy_params(args, config)

    # Define BTC as the only asset for this backtest
    assets = ['BTC']
    from datetime import datetime as dt
    start_date = dt.strptime(args.start_date, '%Y-%m-%d')
    end_date = dt.strptime(args.end_date, '%Y-%m-%d')

    data_dir = os.path.join(project_root, 'data', 'crypto')
    btc_data_file = os.path.join(data_dir, 'BTC_USDT.csv')
    if not os.path.exists(btc_data_file):
        print(f"Error: BTC data file {btc_data_file} does not exist.")
        print("Please ensure BTC historical data is available at 'data/crypto/BTC_USDT.csv' with appropriate CSV format.")
        print("Data should include columns: timestamp, open, high, low, close, volume.")
        sys.exit(1)

    print(f"Running backtest for {args.strategy} on BTC from {start_date} to {end_date} with timeframe {args.timeframe}")
    print(f"Strategy parameters: {strategy_params}")

    # Create a unique subfolder for results with strategy name and timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    strategy_name = args.strategy
    results_subfolder = f"{strategy_name}_{timestamp}"
    unique_results_dir = os.path.join(project_root, 'results', results_subfolder)
    os.makedirs(unique_results_dir, exist_ok=True)
    print(f"Saving results to: {unique_results_dir}")

    try:
        run_backtest(
            strategy_class=STRATEGY_MAP[args.strategy],
            symbols=['BTC_USDT'],
            start_date=start_date,
            end_date=end_date,
            starting_cash=args.initial_cash,
            data_dir=os.path.join(project_root, 'data', 'crypto'),
            results_dir=unique_results_dir,
            benchmark='BTC_USDT',
            strategy_params=strategy_params
        )
    except Exception as e:
        print(f"Error during backtest: {e}")
        print("Falling back to default timeframe '1H' to test compatibility...")
        args.timeframe = '1H'
        run_backtest(
            strategy_class=STRATEGY_MAP[args.strategy],
            symbols=['BTC_USDT'],
            start_date=start_date,
            end_date=end_date,
            starting_cash=args.initial_cash,
            data_dir=os.path.join(project_root, 'data', 'crypto'),
            results_dir=os.path.join(project_root, 'results'),
            benchmark='BTC_USDT',
            strategy_params=strategy_params
        )

if __name__ == '__main__':
    main()
