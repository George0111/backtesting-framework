# Backtesting Scripts

Scripts for running various backtesting strategies and simulations.

## Scripts Overview

### 🏃‍♂️ run_backtest.py
Main backtesting engine runner.
- Generic backtesting script that can run any strategy
- Supports TAA (Tactical Asset Allocation) strategy
- Configurable via INI files
- Generates comprehensive results and reports

**Usage:**
```bash
python run_backtest.py --strategy TAA --config config/default.ini
```

### 🏃‍♂️ run_backtest_crypto_mom.py
Runs cryptocurrency momentum strategy backtests.
- Implements momentum-based trading for crypto assets
- Supports multiple cryptocurrencies
- Configurable momentum lookback periods

### 🏃‍♂️ run_backtest_crypto_tsmom_btc.py
Runs time-series momentum strategy specifically for Bitcoin.
- TSMOM (Time Series Momentum) implementation
- Focused on BTC/USDT trading
- Includes advanced momentum calculations

### 🔍 run_backtest_grid_search.py
Performs grid search optimization for strategy parameters.
- Tests multiple parameter combinations
- Automates hyperparameter optimization
- Generates comparison reports for best parameters

### 🏃‍♂️ run_simple_momentum.py
Runs a simple momentum strategy backtest.
- Basic momentum implementation
- Good starting point for strategy development
- Easy to understand and modify

### 🏃‍♂️ run_tsmom_simple.py
Runs simple TSMOM (Time Series Momentum) strategy.
- Multiple TSMOM variants (daily, 15min, improved)
- SMA crossover-based signals
- Volume and price filter options

**Usage:**
```bash
python run_tsmom_simple.py --strategy TSMOM_SIMPLE_DAILY --symbol BTC_USDT
```

### 📊 sixty_forty.py
Implements 60/40 portfolio strategy.
- Classic 60% stocks, 40% bonds allocation
- Rebalancing logic
- Benchmark comparison

### 📈 mean_reversion.py
Implements mean reversion trading strategy.
- Statistical arbitrage approach
- Mean reversion signals
- Risk management features

### 🔬 Strategy_Explore.py
Interactive strategy exploration and testing.
- Quick strategy testing
- Parameter exploration
- Real-time analysis

## Strategy Types

### Momentum Strategies
- `run_simple_momentum.py` - Basic momentum
- `run_backtest_crypto_mom.py` - Crypto momentum
- `run_tsmom_simple.py` - Time series momentum

### Asset Allocation
- `run_backtest.py` - TAA strategy
- `sixty_forty.py` - 60/40 portfolio

### Statistical Arbitrage
- `mean_reversion.py` - Mean reversion

### Optimization
- `run_backtest_grid_search.py` - Parameter optimization

## Output

All backtesting scripts generate:
- Performance metrics (Sharpe ratio, returns, drawdowns)
- Trade logs
- Equity curves
- Risk analysis
- HTML reports with visualizations

## Configuration

Most scripts support:
- Command line arguments for parameters
- Configuration files for complex setups
- Customizable date ranges
- Multiple asset support 