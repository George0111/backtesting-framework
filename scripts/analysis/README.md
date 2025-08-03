# Analysis Scripts

Scripts for analyzing and comparing strategy results.

## Scripts Overview

### 📊 compare_strategies.py
Comprehensive strategy comparison and analysis tool.
- Loads results from multiple strategy backtest runs
- Performs side-by-side comparison of key metrics
- Generates comparison tables and visualizations
- Supports benchmark comparison

**Features:**
- Performance metrics comparison (Sharpe ratio, returns, volatility)
- Drawdown analysis
- Equity curve visualization
- Risk-adjusted returns analysis
- Statistical significance testing

**Usage:**
```bash
# Compare latest results for default strategies
python compare_strategies.py

# Compare specific strategies
python compare_strategies.py --strategies CryptoMomentum CryptoTSMomentum

# Compare results from same timestamp
python compare_strategies.py --timestamp 20250721_220135
```

**Output:**
- Comparison tables in console
- Equity curve plots
- Drawdown comparison charts
- HTML reports with interactive visualizations
- CSV files with detailed metrics

## Analysis Metrics

The comparison includes:
- **Returns**: Total return, CAGR, annualized returns
- **Risk**: Volatility, maximum drawdown, VaR
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Trading**: Number of trades, win rate, average trade
- **Timing**: Best/worst periods, monthly returns

## Visualization Features

- Interactive equity curves with dropdown selection
- Drawdown comparison charts
- Correlation heatmaps
- Monthly returns heatmaps
- Risk-return scatter plots

## Benchmark Comparison

Automatically includes benchmark performance (typically SPY or similar) for context and relative performance analysis. 