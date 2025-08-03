# Momentum Strategies

Momentum-based trading strategies that capitalize on price trends and rate of change.

## Scripts Overview

### 📈 SimpleMomentum.py
Basic momentum strategy implementation.
- Simple rate-of-change momentum calculation
- Configurable lookback periods
- Equal weighting across assets
- Monthly rebalancing

**Features:**
- **Momentum Calculation**: Rate of change over specified period
- **Asset Selection**: Top N assets by momentum
- **Equal Weighting**: Equal allocation to selected assets
- **Monthly Rebalancing**: End-of-month portfolio rebalancing

**Parameters:**
- `mom_lookback`: Lookback period for momentum calculation
- `mom_top_n`: Number of top assets to hold
- `reserve`: Cash reserve percentage

### 📈 TSMOM_SIMPLE.py
Time Series Momentum strategies with multiple variants.
- SMA crossover-based signals
- Multiple timeframe support (daily, 15min)
- Volume and price filters
- Risk management features

**Strategy Variants:**
- `TSMOM_SIMPLE`: Basic SMA crossover strategy
- `TSMOM_SIMPLE_15MIN`: 15-minute timeframe version
- `TSMOM_SIMPLE_DAILY`: Daily timeframe version
- `TSMOM_SIMPLE_IMPROVED`: Enhanced version with filters

**Features:**
- **SMA Crossover**: Fast and slow moving average signals
- **Multiple Timeframes**: Support for different data frequencies
- **Volume Confirmation**: Volume-based signal filtering
- **Price Filters**: Additional price-based filters
- **Risk Management**: Position sizing and stop losses

**Parameters:**
- `fast_period`: Fast SMA period
- `slow_period`: Slow SMA period
- `commission`: Trading commission
- `use_volume`: Enable volume confirmation
- `use_price_filter`: Enable price filters

## Strategy Types

### Simple Momentum
- **Rate of Change**: Price change over lookback period
- **Asset Ranking**: Rank assets by momentum
- **Equal Weighting**: Equal allocation to top assets
- **Periodic Rebalancing**: Monthly or weekly rebalancing

### Time Series Momentum (TSMOM)
- **Trend Following**: Follow price trends using moving averages
- **Signal Generation**: SMA crossover signals
- **Multiple Timeframes**: Support for different data frequencies
- **Risk Management**: Position sizing and filters

## Implementation Details

### Momentum Calculation
```python
# Rate of change momentum
momentum = (current_price - lookback_price) / lookback_price

# SMA crossover
fast_sma = SMA(close, period=fast_period)
slow_sma = SMA(close, period=slow_period)
signal = fast_sma > slow_sma
```

### Asset Selection
```python
# Rank assets by momentum
ranked_assets = sorted(assets, key=lambda x: momentum[x], reverse=True)
top_assets = ranked_assets[:top_n]
```

### Position Sizing
```python
# Equal weighting
weight = (1.0 - reserve) / len(top_assets)
for asset in top_assets:
    self.order_target_percent(asset, target=weight)
```

## Usage Examples

```python
# Simple momentum strategy
from .momentum.SimpleMomentum import SimpleMomentum

# TSMOM strategy
from .momentum.TSMOM_SIMPLE import TSMOM_SIMPLE_DAILY

# Strategy parameters
params = {
    'mom_lookback': 90,
    'mom_top_n': 5,
    'fast_period': 20,
    'slow_period': 50,
    'commission': 0.001
}
```

## Performance Considerations

- **Lookback Period**: Longer periods for more stable signals
- **Rebalancing Frequency**: Balance between costs and responsiveness
- **Position Sizing**: Consider volatility and correlation
- **Risk Management**: Implement stop losses and position limits 