#!/usr/bin/env python3
"""
Visualization Script for TSMOM_SIMPLE Strategy

This script creates a chart showing:
- Price data
- Fast SMA (20-day)
- Slow SMA (50-day)
- Buy/Sell signals
- Crossover points
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import argparse

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backtester.strategies.momentum.TSMOM_SIMPLE import TSMOM_SIMPLE
import backtrader as bt

def load_data(symbol, start_date, end_date, data_dir):
    """Load and prepare data for visualization"""
    file_path = os.path.join(data_dir, f"{symbol}.csv")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    # Load data
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    
    # Convert timezone-aware dates to timezone-naive for comparison
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Filter by date range
    df = df[(df.index >= start_date) & (df.index <= end_date)]
    
    return df

def calculate_indicators(df, fast_period=20, slow_period=50):
    """Calculate SMA indicators"""
    df['sma_fast'] = df['close'].rolling(window=fast_period).mean()
    df['sma_slow'] = df['close'].rolling(window=slow_period).mean()
    
    # Calculate crossover signals
    df['crossover'] = 0
    df.loc[df['sma_fast'] > df['sma_slow'], 'crossover'] = 1
    df.loc[df['sma_fast'] < df['sma_slow'], 'crossover'] = -1
    
    # Find actual crossover points (when signal changes)
    df['signal_change'] = df['crossover'].diff()
    
    return df

def create_visualization(df, symbol, start_date, end_date):
    """Create the visualization chart"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[3, 1])
    
    # Plot 1: Price and SMAs
    ax1.plot(df.index, df['close'], label='Price', alpha=0.7, linewidth=1)
    ax1.plot(df.index, df['sma_fast'], label=f'Fast SMA ({20})', linewidth=2, color='orange')
    ax1.plot(df.index, df['sma_slow'], label=f'Slow SMA ({50})', linewidth=2, color='red')
    
    # Highlight buy signals (crossover from -1 to 1)
    buy_signals = df[df['signal_change'] == 2].index
    sell_signals = df[df['signal_change'] == -2].index
    
    # Plot buy signals
    if len(buy_signals) > 0:
        ax1.scatter(buy_signals, df.loc[buy_signals, 'close'], 
                   color='green', marker='^', s=100, label='Buy Signal', zorder=5)
    
    # Plot sell signals
    if len(sell_signals) > 0:
        ax1.scatter(sell_signals, df.loc[sell_signals, 'close'], 
                   color='red', marker='v', s=100, label='Sell Signal', zorder=5)
    
    ax1.set_title(f'TSMOM_SIMPLE Strategy - {symbol} ({start_date} to {end_date})')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Crossover signals
    ax2.plot(df.index, df['crossover'], label='Crossover Signal', linewidth=2)
    ax2.set_ylabel('Signal')
    ax2.set_xlabel('Date')
    ax2.set_ylim(-1.5, 1.5)
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Add horizontal lines for signal levels
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax2.axhline(y=1, color='green', linestyle='--', alpha=0.5, label='Buy Level')
    ax2.axhline(y=-1, color='red', linestyle='--', alpha=0.5, label='Sell Level')
    
    plt.tight_layout()
    
    # Save the plot
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'TSMOM_SIMPLE_visualization_{symbol}_{timestamp}.png'
    filepath = os.path.join(output_dir, filename)
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to: {filepath}")
    
    # Show summary statistics
    print(f"\n=== Strategy Summary ===")
    print(f"Total buy signals: {len(buy_signals)}")
    print(f"Total sell signals: {len(sell_signals)}")
    print(f"Data points: {len(df)}")
    print(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")
    
    # Show some example signals
    if len(buy_signals) > 0:
        print(f"\nFirst 5 buy signals:")
        for i, signal_date in enumerate(buy_signals[:5]):
            price = df.loc[signal_date, 'close']
            fast_sma = df.loc[signal_date, 'sma_fast']
            slow_sma = df.loc[signal_date, 'sma_slow']
            print(f"  {signal_date.date()}: Price=${price:.2f}, Fast SMA=${fast_sma:.2f}, Slow SMA=${slow_sma:.2f}")
    
    if len(sell_signals) > 0:
        print(f"\nFirst 5 sell signals:")
        for i, signal_date in enumerate(sell_signals[:5]):
            price = df.loc[signal_date, 'close']
            fast_sma = df.loc[signal_date, 'sma_fast']
            slow_sma = df.loc[signal_date, 'sma_slow']
            print(f"  {signal_date.date()}: Price=${price:.2f}, Fast SMA=${fast_sma:.2f}, Slow SMA=${slow_sma:.2f}")
    
    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Visualize TSMOM_SIMPLE Strategy')
    parser.add_argument('--symbol', type=str, default='BTC_USDT', help='Symbol to analyze')
    parser.add_argument('--start_date', type=str, default='2023-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2023-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--data_dir', type=str, default='data/crypto', help='Data directory')
    
    args = parser.parse_args()
    
    # Convert dates
    start_date = pd.to_datetime(args.start_date)
    end_date = pd.to_datetime(args.end_date)
    
    try:
        # Load data
        print(f"Loading data for {args.symbol}...")
        df = load_data(args.symbol, start_date, end_date, args.data_dir)
        
        if len(df) == 0:
            print("No data found for the specified date range")
            return
        
        print(f"Loaded {len(df)} data points")
        
        # Calculate indicators
        print("Calculating indicators...")
        df = calculate_indicators(df)
        
        # Create visualization
        print("Creating visualization...")
        create_visualization(df, args.symbol, start_date, end_date)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 