#!/usr/bin/env python3
"""
Improved resampling script for 15-minute crypto data to daily data.

This script properly handles UTC day boundaries and provides better aggregation
for crypto trading data.
"""

import pandas as pd
import os
import sys
from datetime import datetime, timezone

def resample_to_daily_fixed(input_file, output_file):
    """Resample 15-minute data to daily OHLCV data with proper UTC boundaries"""
    
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Convert datetime column and ensure UTC timezone
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    
    # Ensure timezone is UTC
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    elif df.index.tz != timezone.utc:
        df.index = df.index.tz_convert('UTC')
    
    print(f"Data range: {df.index.min()} to {df.index.max()}")
    print(f"Timezone: {df.index.tz}")
    
    # Resample to daily OHLCV using UTC day boundaries
    # 'D' in pandas uses midnight UTC as the boundary
    daily_data = df.resample('D', closed='left', label='left').agg({
        'open': 'first',
        'high': 'max', 
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Add some validation
    print(f"Daily data range: {daily_data.index.min()} to {daily_data.index.max()}")
    print(f"Sample daily aggregation:")
    print(f"  Date: {daily_data.index[0]}")
    print(f"  Open: {daily_data.iloc[0]['open']}")
    print(f"  High: {daily_data.iloc[0]['high']}")
    print(f"  Low: {daily_data.iloc[0]['low']}")
    print(f"  Close: {daily_data.iloc[0]['close']}")
    print(f"  Volume: {daily_data.iloc[0]['volume']}")
    
    # Save daily data
    daily_data.to_csv(output_file)
    
    print(f"Resampled data saved to {output_file}")
    print(f"Original data: {len(df)} rows")
    print(f"Daily data: {len(daily_data)} rows")
    
    return daily_data

def verify_resampling(input_file, output_file):
    """Verify that the resampling is correct by checking a specific day"""
    
    print(f"\nVerifying resampling for {input_file}...")
    
    # Load original 15-minute data
    df_15min = pd.read_csv(input_file)
    df_15min['datetime'] = pd.to_datetime(df_15min['datetime'])
    df_15min.set_index('datetime', inplace=True)
    
    # Load daily data
    df_daily = pd.read_csv(output_file)
    df_daily['datetime'] = pd.to_datetime(df_daily['datetime'])
    df_daily.set_index('datetime', inplace=True)
    
    # Check a specific day (first day in daily data)
    check_date = df_daily.index[0]
    print(f"Checking aggregation for {check_date}")
    
    # Get all 15-minute bars for this day
    day_start = check_date
    day_end = check_date + pd.Timedelta(days=1)
    
    day_bars = df_15min[(df_15min.index >= day_start) & (df_15min.index < day_end)]
    
    print(f"15-minute bars for {check_date}: {len(day_bars)} bars")
    if len(day_bars) > 0:
        print(f"  First bar: {day_bars.index[0]} - Open: {day_bars.iloc[0]['open']}")
        print(f"  Last bar: {day_bars.index[-1]} - Close: {day_bars.iloc[-1]['close']}")
        print(f"  High: {day_bars['high'].max()}")
        print(f"  Low: {day_bars['low'].min()}")
        print(f"  Volume sum: {day_bars['volume'].sum()}")
        
        # Compare with daily aggregation
        daily_row = df_daily.loc[check_date]
        print(f"Daily aggregation:")
        print(f"  Open: {daily_row['open']}")
        print(f"  High: {daily_row['high']}")
        print(f"  Low: {daily_row['low']}")
        print(f"  Close: {daily_row['close']}")
        print(f"  Volume: {daily_row['volume']}")
        
        # Verify
        assert abs(daily_row['open'] - day_bars.iloc[0]['open']) < 0.01, "Open mismatch"
        assert abs(daily_row['close'] - day_bars.iloc[-1]['close']) < 0.01, "Close mismatch"
        assert abs(daily_row['high'] - day_bars['high'].max()) < 0.01, "High mismatch"
        assert abs(daily_row['low'] - day_bars['low'].min()) < 0.01, "Low mismatch"
        assert abs(daily_row['volume'] - day_bars['volume'].sum()) < 0.01, "Volume mismatch"
        
        print("✅ Resampling verification passed!")

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
                resample_to_daily_fixed(input_file, output_file)
                verify_resampling(input_file, output_file)
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    main() 