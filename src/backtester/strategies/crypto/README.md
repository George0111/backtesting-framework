# Cryptocurrency Strategies

Cryptocurrency-specific trading strategies designed for digital asset markets.

## Scripts Overview

### 🪙 CryptoMomentum.py
Comprehensive cryptocurrency momentum strategy with multiple variants.
- Multiple rebalancing frequencies (daily, weekly, monthly)
- Volatility-based position sizing
- Risk management features
- Intraday data support

**Strategy Variants:**
- `CryptoMomentum`: Full-featured momentum strategy
- `CryptoMomentumEqual`: Simplified equal-weighting version
- `CryptoTSMomentum`: Time series momentum for crypto

**Features:**
- **Flexible Rebalancing**: Daily, weekly, monthly, or custom periods
- **Volatility Sizing**: Position sizing based on asset volatility
- **Risk Management**: Maximum position limits and drawdown controls
- **Intraday Support**: Works with 15-minute and other intraday data
- **Commission Handling**: Binance trading fee integration

**Parameters:**
- `mom_lookback`: Momentum lookback period (90 days)
- `mom_top_n`: Number of top assets to hold (5)
- `reserve`: Cash reserve percentage (0.05)
- `rebalance_period`: Rebalancing frequency ('daily', 'weekly', 'monthly')
- `rebalance_time`: Hour of day for rebalancing (0-23)
- `bars_per_day`: Number of bars per day for intraday data (96)
- `commission`: Trading commission (0.001)
- `vol_lookback`: Volatility calculation period (20 days)
- `max_pos_size`: Maximum position size (0.33)
- `risk_factor`: Target portfolio volatility (0.15)

### 🪙 CryptoMomentum.py.bak
Backup version of the cryptocurrency momentum strategy.
- Identical functionality to CryptoMomentum.py
- Useful for testing modifications and comparisons

## Strategy Types

### Cryptocurrency Momentum
- **Rate of Change**: Price momentum over lookback period
- **Asset Selection**: Top cryptocurrencies by momentum
- **Volatility Sizing**: Position sizing based on volatility
- **Flexible Rebalancing**: Multiple rebalancing frequencies

### Cryptocurrency TSMOM
- **Time Series Momentum**: Trend-following approach
- **Signal Generation**: Technical indicator signals
- **Risk Management**: Comprehensive risk controls
- **Intraday Trading**: Support for high-frequency data

## Implementation Details

### Momentum Calculation
```python
# Calculate momentum for crypto assets
def calculate_momentum(self, data, lookback_bars):
    if len(data) >= lookback_bars:
        lookback_price = data.close[-lookback_bars]
        current_price = data.close[0]
        return (current_price - lookback_price) / lookback_price
    return None
```

### Volatility-Based Sizing
```python
# Calculate position sizes based on volatility
def calculate_position_sizes(self, top_assets):
    total_risk = self.p.risk_factor
    weights = {}
    
    for asset in top_assets:
        vol = self.calculate_volatility(asset)
        if vol > 0:
            # Inverse volatility weighting
            weights[asset] = (1 / vol) / sum(1 / self.calculate_volatility(a) for a in top_assets)
    
    return weights
```

### Rebalancing Logic
```python
# Flexible rebalancing based on period
def should_rebalance(self, current_datetime):
    if self.p.rebalance_period == 'daily':
        return current_datetime.hour == self.p.rebalance_time
    elif self.p.rebalance_period == 'weekly':
        return current_datetime.weekday() == 0  # Monday
    elif self.p.rebalance_period == 'monthly':
        return self.is_last_business_day(current_datetime.date())
```

## Usage Examples

```python
# Import crypto strategies
from .crypto.CryptoMomentum import CryptoMomentum, CryptoMomentumEqual, CryptoTSMomentum

# Strategy parameters
params = {
    'mom_lookback': 90,
    'mom_top_n': 5,
    'reserve': 0.05,
    'rebalance_period': 'daily',
    'rebalance_time': 0,  # Midnight UTC
    'commission': 0.001,
    'max_pos_size': 0.33,
    'risk_factor': 0.15
}
```

## Cryptocurrency-Specific Considerations

### Market Characteristics
- **24/7 Trading**: Continuous market operation
- **High Volatility**: Significant price swings
- **Low Correlation**: Different from traditional assets
- **Liquidity Variations**: Varying liquidity across assets

### Risk Management
- **Position Limits**: Maximum exposure per asset
- **Volatility Targeting**: Adjust for crypto volatility
- **Liquidity Monitoring**: Ensure ability to exit positions
- **Correlation Limits**: Avoid concentration in similar assets

### Data Considerations
- **Intraday Data**: 15-minute and hourly bars
- **UTC Timestamps**: Consistent timezone handling
- **Missing Data**: Handle gaps in crypto data
- **Volume Data**: Consider trading volume for liquidity

## Performance Considerations

### Rebalancing Frequency
- **Daily**: More responsive to market changes
- **Weekly**: Balance responsiveness vs costs
- **Monthly**: Lower transaction costs
- **Custom Periods**: Optimize for specific strategies

### Position Sizing
- **Equal Weighting**: Simple and effective
- **Volatility Weighting**: Risk-adjusted sizing
- **Market Cap Weighting**: Size-based allocation
- **Custom Weighting**: Strategy-specific approaches

### Risk Management
- **Maximum Drawdown**: Portfolio-level risk limits
- **Position Limits**: Per-asset exposure limits
- **Volatility Targeting**: Dynamic risk adjustment
- **Liquidity Requirements**: Minimum volume thresholds

## Best Practices

1. **Data Quality**: Ensure reliable crypto data sources
2. **Liquidity Management**: Monitor trading volume
3. **Risk Controls**: Implement comprehensive risk management
4. **Transaction Costs**: Consider crypto exchange fees
5. **Market Regimes**: Adapt to changing crypto market conditions 