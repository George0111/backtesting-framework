import os
import pandas as pd
import numpy as np
import yfinance as yf
import quantstats
import backtrader as bt
import matplotlib.pyplot as plt
import pandas_market_calendars as mcal

# --- Data Loading ---

def fetch_data(path, symbol, start_dt, end_dt):
    """
    Loads a CSV data file from the given path and filters it by date.
    Automatically identifies and handles different time resolutions (minute/hour/day).
    """
    file_path = os.path.join(path, f"{symbol}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    # Convert start_dt and end_dt to pandas datetime if they aren't already
    start_dt = pd.to_datetime(start_dt, utc=True)
    end_dt = pd.to_datetime(end_dt, utc=True)
    
    if "USDT" in symbol:
        # For USDT pairs, load with datetime index in UTC
        ohlcv = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        # Ensure the index is in UTC timezone
        if ohlcv.index.tzinfo is None:
            ohlcv.index = pd.to_datetime(ohlcv.index, utc=True)
        
        # Filter by date range
        ohlcv = ohlcv.loc[(ohlcv.index >= start_dt) & (ohlcv.index <= end_dt)]
        
        # Rename columns to standard format if needed
        if 'open' in ohlcv.columns:
            ohlcv.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
    else:
        ohlcv = pd.read_csv(file_path, index_col=0, parse_dates=True)
        ohlcv.reset_index(inplace=True)
        ohlcv['Date'] = pd.to_datetime(ohlcv['Date'])
        
        # Identify time resolution by examining the first few timestamps
        if len(ohlcv) > 1:
            # Get the first few time differences
            time_diffs = []
            for i in range(1, min(10, len(ohlcv))):
                diff = ohlcv['Date'].iloc[i] - ohlcv['Date'].iloc[i-1]
                time_diffs.append(diff.total_seconds())
            
            # Calculate the median time difference
            median_diff = pd.Series(time_diffs).median()
            
            # Determine resolution based on median time difference
            if median_diff <= 60:  # Less than or equal to 1 minute
                resolution = 'minute'
            elif median_diff <= 3600:  # Less than or equal to 1 hour
                resolution = 'hour'
            else:  # Greater than 1 hour (likely daily)
                resolution = 'day'
            
            print(f"Detected time resolution for {symbol}: {resolution}")
        else:
            # Default to daily if we can't determine
            resolution = 'day'
        
        # Filter by date based on resolution
        if resolution == 'day':
            # For daily data, compare only the dates
            ohlcv['Date_Only'] = ohlcv['Date'].dt.date
            start_date = start_dt.date()
            end_date = end_dt.date()
            ohlcv = ohlcv.loc[(ohlcv['Date_Only'] >= start_date) & (ohlcv['Date_Only'] <= end_date)]
            ohlcv.drop('Date_Only', axis=1, inplace=True)
        else:
            # For minute/hour data, use the full timestamp
            ohlcv = ohlcv.loc[(ohlcv['Date'] >= start_dt) & 
                              (ohlcv['Date'] <= end_dt)]
        
        ohlcv.set_index('Date', inplace=True)
    
    return ohlcv

def get_benchmark(symbol, start_dt, end_dt, data_dir="./data"):
    """
    Downloads or loads benchmark data from the data directory.
    Properly calculates benchmark returns for accurate performance comparison.
    
    Args:
        symbol: The benchmark symbol
        start_dt: Start datetime
        end_dt: End datetime
        data_dir: Data directory path
        
    Returns:
        DataFrame with benchmark returns at the appropriate time resolution
    """
    # Determine the correct path for crypto data
    # if "USDT" in symbol:
    #     file_path = os.path.join(data_dir, "crypto", f"{symbol}.csv")
    # else:
    #     file_path = os.path.join(data_dir, f"{symbol}.csv")
    file_path = os.path.join(data_dir, f"{symbol}.csv")
    try:
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        print(f"Loaded benchmark data from {file_path}")
    except FileNotFoundError:
        print(f"Benchmark file not found at {file_path}, downloading from yfinance...")
        df = yf.download(symbol, period='max', auto_adjust=False, multi_level_index=False)
        df.to_csv(file_path)
    
    # Ensure start_dt and end_dt are timezone-aware
    start_dt = pd.to_datetime(start_dt, utc=True)
    end_dt = pd.to_datetime(end_dt, utc=True)
    
    if "USDT" in symbol:
        # For crypto data
        if 'close' in df.columns:
            price_col = 'close'
        else:
            price_col = 'Close'
            
        # Make sure index is datetime with timezone
        df.index = pd.to_datetime(df.index, utc=True)
        
        # Filter by date range
        df = df.loc[(df.index >= start_dt) & (df.index <= end_dt)]
        
        # Log the first and last prices to verify total return calculation
        first_price = df[price_col].iloc[0]
        last_price = df[price_col].iloc[-1]
        total_return_pct = ((last_price / first_price) - 1) * 100
        
        print(f"Benchmark {symbol} - First price: {first_price:.2f}, Last price: {last_price:.2f}")
        print(f"Total return: {total_return_pct:.2f}% over {(df.index[-1] - df.index[0]).days} days")
        
        # For daily returns calculation, resample to daily if needed
        if len(df) > 365 * 2:  # If we have high-frequency data
            # Resample to daily for performance metrics
            daily_df = df.resample('D').last().dropna()
            
            # Calculate daily returns
            daily_returns = daily_df[[price_col]].pct_change().dropna()
            daily_returns.columns = [f'{symbol}']
            
            # Also calculate the cumulative return series for proper benchmarking
            cumulative_factor = (1 + daily_returns).cumprod()
            
            print(f"Resampled to {len(daily_returns)} daily returns for performance metrics")
            
            return daily_returns
        else:
            # Calculate returns at the original time resolution
            returns = df[[price_col]].pct_change().dropna()
            returns.columns = [f'{symbol}']
            return returns
        
    else:
        # For stock/ETF data
        price_col = 'Close'
        
        # Make sure index is datetime
        df.index = pd.to_datetime(df.index)
        
        # Add timezone info if not present
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize('UTC')
        
        # Filter by date range
        df = df.loc[(df.index >= start_dt) & (df.index <= end_dt)]
        
        # Log the first and last prices
        first_price = df[price_col].iloc[0]
        last_price = df[price_col].iloc[-1]
        total_return_pct = ((last_price / first_price) - 1) * 100
        
        print(f"Benchmark {symbol} - First price: {first_price:.2f}, Last price: {last_price:.2f}")
        print(f"Total return: {total_return_pct:.2f}% over {(df.index[-1] - df.index[0]).days} days")
        
        # Calculate returns at the original time resolution
        returns = df[[price_col]].pct_change().dropna()
        returns.columns = [f'{symbol}']
    
    # Ensure the index is timezone-aware
    if returns.index.tzinfo is None:
        returns.index = returns.index.tz_localize('UTC')
    
    return returns

# --- Analysis & Reporting ---

def save_backtrader_plot(cerebro, output_dir, filename="backtrader_plot.png", plot_option=False):
    """
    Saves the Backtrader plot to a file.
    Skips plotting if there are too many data points to prevent hanging.
    """
    output_path = os.path.join(output_dir, filename)
    
    # Check if we have too much data to plot
    total_bars = 0
    for data in cerebro.datas:
        total_bars += len(data)
    print('total_bars:', total_bars)
    
    # Skip plotting if we have more than 10,000 bars (arbitrary threshold)
    if total_bars > 10000:
        print(f"Skipping Backtrader plot generation - too many data points ({total_bars} bars)")
        
        # Create a simple text file explaining why the plot was skipped
        with open(output_path.replace('.png', '.txt'), 'w') as f:
            f.write(f"Backtrader plot was skipped because the dataset contains {total_bars} bars,\n")
            f.write("which is too large to visualize effectively. Please use the interactive\n")
            f.write("visualization (trade_visualization.html) instead for detailed analysis.")
        return
    
    try:
        fig = cerebro.plot(plot=plot_option, style='candlestick', barup='green', bardown='red')[0][0]
        fig.savefig(output_path, dpi=300)
        plt.close(fig)
        print(f"Backtrader plot saved to {output_path}")
    except Exception as e:
        print(f"Error saving Backtrader plot: {e}")
        
        # Create a simple text file explaining the error
        with open(output_path.replace('.png', '_error.txt'), 'w') as f:
            f.write(f"Error generating Backtrader plot: {str(e)}\n")
            f.write("Please use the interactive visualization (trade_visualization.html) instead.")

# --- Calendar & Timers ---

class IsLastBusinessDayOfMonth(object):
    """
    Callable class for Backtrader timers. Returns True if the date is the last business day of the month.
    """
    def __call__(self, d):
        month_start = d.replace(day=1)
        month_end = (month_start + pd.offsets.MonthEnd(0)).date()
        business_days = pd.date_range(start=month_start, end=month_end, freq='B')
        return d == business_days[-1].date()

class IsFirstBusinessDayOfYear(object):
    """
    Callable class for Backtrader timers. Returns True if the date is the first business day of the year.
    """
    def __init__(self):
        self.nyse = mcal.get_calendar('NYSE')

    def __call__(self, d):
        year_start = d.replace(month=1, day=1)
        year_end = d.replace(month=12, day=31)
        business_days = self.nyse.valid_days(start_date=year_start, end_date=year_end)
        return d == business_days[0].date()
    
# Test if fetch data function is working
if __name__ == "__main__":
    # Example usage
    path = "./data/crypto"
    symbol = "BTC_USDT"
    start_dt = "2023-01-01"
    end_dt = "2023-12-31"
    
    try:
        data = fetch_data(path, symbol, start_dt, end_dt)
        print(data.head())
    except FileNotFoundError as e:
        print(e)