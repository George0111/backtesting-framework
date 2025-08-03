#!/usr/bin/env python3
"""
Simple Momentum Strategy Test Script

This script tests the SimpleMomentum strategy based on academic research findings.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import pandas as pd

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backtester.engine import run_backtest
from backtester.strategies.momentum.SimpleMomentum import SimpleMomentum, CrossSectionalMomentum

def main():
    parser = argparse.ArgumentParser(description='Run Simple Momentum Strategy Backtest')
    parser.add_argument('--strategy', type=str, default='SimpleMomentum',
                        choices=['SimpleMomentum', 'CrossSectionalMomentum'],
                        help='Strategy to use')
    parser.add_argument('--symbol', type=str, default='BTC_USDT',
                        help='Symbol to trade')
    parser.add_argument('--start_date', type=str, default='2023-01-01',
                        help='Start date for backtest')
    parser.add_argument('--end_date', type=str, default='2023-12-31',
                        help='End date for backtest')
    parser.add_argument('--timeframe', type=str, default='1D',
                        help='Timeframe for data')
    parser.add_argument('--initial_cash', type=float, default=10000.0,
                        help='Initial cash for the backtest')
    parser.add_argument('--commission', type=float, default=0.001,
                        help='Commission rate per trade')
    parser.add_argument('--lookback_period', type=int, default=252,
                        help='Lookback period for momentum calculation (days)')
    parser.add_argument('--momentum_threshold', type=float, default=0.05,
                        help='Minimum momentum threshold')
    parser.add_argument('--max_position_size', type=float, default=0.25,
                        help='Maximum position size')
    parser.add_argument('--stop_loss', type=float, default=0.10,
                        help='Stop loss percentage')
    parser.add_argument('--take_profit', type=float, default=0.30,
                        help='Take profit percentage')
    parser.add_argument('--top_n', type=int, default=3,
                        help='Number of top assets to hold (for CrossSectionalMomentum)')
    parser.add_argument('--rebalance_freq', type=int, default=21,
                        help='Rebalance frequency in days (for CrossSectionalMomentum)')
    
    args = parser.parse_args()

    # Strategy parameters
    if args.strategy == 'SimpleMomentum':
        strategy_params = {
            'lookback_period': args.lookback_period,
            'momentum_threshold': args.momentum_threshold,
            'max_position_size': args.max_position_size,
            'stop_loss': args.stop_loss,
            'take_profit': args.take_profit,
            'commission': args.commission,
        }
        strategy_class = SimpleMomentum
    else:  # CrossSectionalMomentum
        strategy_params = {
            'lookback_period': args.lookback_period,
            'top_n': args.top_n,
            'rebalance_freq': args.rebalance_freq,
            'commission': args.commission,
        }
        strategy_class = CrossSectionalMomentum

    print(f"Running {args.strategy} backtest for {args.symbol}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Strategy parameters: {strategy_params}")

    # Convert dates to datetime objects
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

    # Create results directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = os.path.join('results', f"{args.strategy}_{timestamp}")
    os.makedirs(results_dir, exist_ok=True)

    # Run the backtest
    try:
        run_backtest(
            strategy_class=strategy_class,
            symbols=[args.symbol],
            start_date=start_date,
            end_date=end_date,
            starting_cash=args.initial_cash,
            data_dir=os.path.join('data', 'crypto'),
            results_dir=results_dir,
            benchmark=args.symbol,
            strategy_params=strategy_params
        )
        
        print(f"\nBacktest completed successfully!")
        print(f"Results saved to: {results_dir}")
        
    except Exception as e:
        print(f"Error during backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 