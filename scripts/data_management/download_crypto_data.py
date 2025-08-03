import ccxt
import pandas as pd
import os
from datetime import datetime, timedelta

"""
Data is downloaded with UTC time as the reference
Every candle timestamp represents the start of the period in UTC
Structure of the OHLCV data:
[
    [
        1504541580000, // UTC timestamp in milliseconds, integer
        4235.4,        // (O)pen price, float
        4240.6,        // (H)ighest price, float
        4230.0,        // (L)owest price, float
        4230.7,        // (C)losing price, float
        37.72941911    // (V)olume float
    ],
    ...
]
"""
# Define the universe of cryptocurrencies
crypto_universe = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'SOL/USDT', 'DOGE/USDT']

# Define the path to save the data
data_path = './data/crypto/'

# Create the directory if it doesn't exist
os.makedirs(data_path, exist_ok=True)

# Initialize Binance exchange
exchange = ccxt.binance({
    'rateLimit': 1200,
    'enableRateLimit': True,
})

# Function to fetch historical data
def fetch_binance_data(symbol, timeframe='15m', since=None):
    """
    Fetch historical OHLCV data from Binance.
    :param symbol: The trading pair (e.g., 'BTC/USDT').
    :param timeframe: The timeframe for the candles (e.g., '15m').
    :param since: Timestamp in milliseconds to start fetching data.
    :return: DataFrame containing OHLCV data with UTC datetime index.
    """
    all_data = []
    limit = 1000  # Binance allows up to 1000 candles per request
    while True:
        print(f"Fetching data for {symbol} since {since}...")
        data = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        if not data:
            break
        all_data.extend(data)
        since = data[-1][0] + 1  # Move to the next batch
        if len(data) < limit:
            break

    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Convert timestamp to UTC datetime and set as index
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df.set_index('datetime')
    
    # Keep the original timestamp column for reference
    # Sort by index to ensure chronological order
    df = df.sort_index()
    
    return df

# Download historical data for each cryptocurrency
for crypto in crypto_universe:
    print(f"Downloading data for {crypto}...")
    since = int((datetime.now() - timedelta(days=365 * 5)).timestamp() * 1000)  # Start from 5 years ago
    df = fetch_binance_data(crypto, since=since)
    # Save the data to a CSV file
    file_path = os.path.join(data_path, f'{crypto.replace("/", "_")}.csv')
    df.to_csv(file_path)
    print(f"Saved data for {crypto} to {file_path}")

print("Download complete!")