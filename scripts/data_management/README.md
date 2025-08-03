# Data Management Scripts

Scripts for downloading, cleaning, and preprocessing data for the backtesting project.

## Scripts Overview

### 📥 download_crypto_data.py
Downloads historical cryptocurrency data from Binance exchange.
- Downloads OHLCV data for major cryptocurrencies (BTC, ETH, BNB, XRP, ADA, SOL, DOGE)
- Supports multiple timeframes (default: 15m)
- Saves data to `./data/crypto/` directory
- Uses CCXT library for exchange connectivity

**Usage:**
```bash
python download_crypto_data.py
```

### 📥 download_yfinance.py
Downloads stock data using Yahoo Finance API.
- Simple script for downloading stock data
- Uses yfinance library

### 🔄 resample_to_daily.py
Converts intraday data to daily frequency.
- Resamples OHLCV data to daily bars
- Handles missing data and timezone issues

### 🔄 resample_to_daily_fixed.py
Enhanced version of daily resampling with additional features.
- More robust handling of data alignment
- Better error handling and logging

### 🧹 clean_TAA.py
Cleans and aligns TAA (Tactical Asset Allocation) data.
- Aligns all TAA symbols to a common date index
- Fills missing values with zeros
- Ensures consistent data structure across all TAA assets

**Usage:**
```bash
python clean_TAA.py
```

## Data Flow

1. **Download**: Use `download_crypto_data.py` or `download_yfinance.py` to get raw data
2. **Clean**: Use `clean_TAA.py` for TAA data or similar cleaning scripts
3. **Resample**: Use resampling scripts to convert to desired timeframe
4. **Validate**: Check data quality before proceeding to backtesting

## Data Formats

All scripts maintain consistent data formats:
- CSV files with datetime index
- OHLCV columns (Open, High, Low, Close, Volume)
- UTC timestamps for crypto data
- Proper handling of missing values 