#!/usr/bin/env python3
"""
Resample 15-minute crypto data to daily data.

This script converts high-frequency crypto data to daily OHLCV data
for use with trend-following strategies.
"""

import pandas as pd
import os
import sys
from datetime import datetime

def resample_to_daily(input_file, output_file):
    """Resample 15-minute data to daily OHLCV data"""
    
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Convert datetime column
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    
    # Resample to daily OHLCV
    daily_data = df.resample('D').agg({
        'open': 'first',
        'high': 'max', 
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Save daily data
    daily_data.to_csv(output_file)
    
    print(f"Resampled data saved to {output_file}")
    print(f"Original data: {len(df)} rows")
    print(f"Daily data: {len(daily_data)} rows")
    
    return daily_data

def main():
    # Create daily data directory
    daily_dir = "data/crypto/daily"
    os.makedirs(daily_dir, exist_ok=True)
    
    # Process all crypto files
    crypto_dir = "data/crypto"
    for filename in os.listdir(crypto_dir):
        if filename.endswith('.csv') and 'USDT' in filename:
            input_file = os.path.join(crypto_dir, filename)
            output_file = os.path.join(daily_dir, filename)
            
            print(f"\nProcessing {filename}...")
            try:
                resample_to_daily(input_file, output_file)
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    main() 