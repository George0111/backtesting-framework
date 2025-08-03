#!/usr/bin/env python3
"""
Simple TSMOM Strategy Test Script

This script tests the TSMOM_SIMPLE strategy using basic SMA crossover.
"""

import sys
import os
import argparse
from datetime import datetime
import pandas as pd

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backtester.engine import run_backtest
from backtester.strategies.momentum.TSMOM_SIMPLE import TSMOM_SIMPLE, TSMOM_SIMPLE_15MIN, TSMOM_SIMPLE_DAILY, TSMOM_SIMPLE_IMPROVED

def main():
    parser = argparse.ArgumentParser(description='Run Simple TSMOM Strategy Backtest')
    parser.add_argument('--strategy', type=str, default='TSMOM_SIMPLE_DAILY',
                        choices=['TSMOM_SIMPLE', 'TSMOM_SIMPLE_15MIN', 'TSMOM_SIMPLE_DAILY', 'TSMOM_SIMPLE_IMPROVED'],
                        help='Strategy to use')
    parser.add_argument('--symbol', type=str, default='BTC_USDT',
                        help='Symbol to trade')
    parser.add_argument('--start_date', type=str, default='2023-01-01',
                        help='Start date for backtest')
    parser.add_argument('--end_date', type=str, default='2023-12-31',
                        help='End date for backtest')
    parser.add_argument('--fast_period', type=int, default=20,
                        help='Fast SMA period')
    parser.add_argument('--slow_period', type=int, default=50,
                        help='Slow SMA period')
    parser.add_argument('--commission', type=float, default=0.001,
                        help='Commission rate per trade')
    parser.add_argument('--use_volume', action='store_true',
                        help='Use volume confirmation (for improved version)')
    parser.add_argument('--use_price_filter', action='store_true',
                        help='Use price filter (for improved version)')
    
    args = parser.parse_args()

    # Strategy parameters
    if args.strategy == 'TSMOM_SIMPLE':
        strategy_params = {
            'fast_period': args.fast_period,
            'slow_period': args.slow_period,
            'commission': args.commission,
        }
        strategy_class = TSMOM_SIMPLE
    elif args.strategy == 'TSMOM_SIMPLE_15MIN':
        strategy_params = {
            'fast_period': 96,  # 24 hours of 15-min bars
            'slow_period': 384,  # 4 days of 15-min bars
            'commission': args.commission,
        }
        strategy_class = TSMOM_SIMPLE_15MIN
    elif args.strategy == 'TSMOM_SIMPLE_DAILY':
        strategy_params = {
            'fast_period': args.fast_period,  # 20 days
            'slow_period': args.slow_period,  # 50 days
            'commission': args.commission,
        }
        strategy_class = TSMOM_SIMPLE_DAILY
    elif args.strategy == 'TSMOM_SIMPLE_IMPROVED':
        strategy_params = {
            'fast_period': args.fast_period,
            'slow_period': args.slow_period,
            'commission': args.commission,
            'use_volume': args.use_volume,
            'use_price_filter': args.use_price_filter,
        }
        strategy_class = TSMOM_SIMPLE_IMPROVED
    else:
        strategy_params = {
            'fast_period': 96,
            'slow_period': 384,
            'commission': args.commission,
        }
        strategy_class = TSMOM_SIMPLE_15MIN

    print(f"Running {args.strategy} backtest for {args.symbol}")
    print(f"Period: {args.start_date} to {args.end_date}")
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
        # Use daily data for daily strategy, regular data for others
        if args.strategy == 'TSMOM_SIMPLE_DAILY':
            data_dir = os.path.join('data', 'crypto', 'daily')
        else:
            data_dir = os.path.join('data', 'crypto')
            
        run_backtest(
            strategy_class=strategy_class,
            symbols=[args.symbol],
            start_date=start_date,
            end_date=end_date,
            starting_cash=10000.0,
            data_dir=data_dir,
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