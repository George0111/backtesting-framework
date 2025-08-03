# Asset Allocation Strategies

Portfolio allocation and asset allocation strategies for multi-asset portfolios.

## Scripts Overview

### 📊 TAA.py
Tactical Asset Allocation (TAA) strategy based on momentum.
- Monthly rebalancing with momentum-based asset selection
- Top N assets by momentum ranking
- Equal weighting within selected assets
- Cash reserve management

**Features:**
- **Momentum Ranking**: Rate of change over lookback period
- **Monthly Rebalancing**: End-of-month portfolio adjustments
- **Equal Weighting**: Equal allocation to top assets
- **Cash Reserve**: Maintains cash buffer for opportunities
- **Business Day Logic**: Handles month-end rebalancing

**Parameters:**
- `mom_lookback`: Lookback period for momentum calculation (126 days)
- `mom_top_n`: Number of top assets to hold (3)
- `reserve`: Cash reserve percentage (0.01)

### 📊 2ETF.py
Two-ETF strategy for simple asset allocation.
- Basic two-asset portfolio management
- Rebalancing logic for dual-asset portfolios
- Suitable for core-satellite approaches

**Features:**
- **Dual Asset Management**: Two-asset portfolio optimization
- **Rebalancing Logic**: Periodic portfolio rebalancing
- **Risk Management**: Position sizing and risk controls
- **Performance Tracking**: Portfolio performance monitoring

## Strategy Types

### Tactical Asset Allocation (TAA)
- **Momentum-Based**: Selects assets based on momentum ranking
- **Periodic Rebalancing**: Monthly portfolio adjustments
- **Equal Weighting**: Equal allocation to selected assets
- **Cash Management**: Maintains strategic cash reserves

### Core-Satellite Allocation
- **Core Holdings**: Stable, long-term positions
- **Satellite Positions**: Tactical, momentum-driven positions
- **Risk Budgeting**: Allocates risk across core and satellite
- **Rebalancing**: Periodic adjustments to maintain targets

## Implementation Details

### Momentum Calculation
```python
# Calculate momentum for each asset
for asset in universe:
    if len(asset) >= lookback:
        lookback_price = asset.close[-lookback]
        current_price = asset.close[0]
        momentum = (current_price - lookback_price) / lookback_price
        returns[asset] = momentum
```

### Asset Selection
```python
# Rank assets by momentum and select top N
sorted_returns = sorted(returns.items(), key=lambda x: x[1], reverse=True)
top_assets = [asset for asset, _ in sorted_returns[:top_n]]
```

### Position Sizing
```python
# Equal weighting with cash reserve
weight = (1.0 - reserve) / len(top_assets)
for asset in top_assets:
    self.order_target_percent(asset, target=weight)
```

### Rebalancing Logic
```python
# Monthly rebalancing on last business day
def notify_timer(self, timer, when, *args, **kwargs):
    if self.is_last_business_day(self.datas[0].datetime.date(0)):
        self.rebalance_portfolio()
```

## Usage Examples

```python
# Import TAA strategy
from .asset_allocation.TAA import TAA_Momentum

# Import 2ETF strategy
from .asset_allocation.2ETF import TwoETFStrategy

# Strategy parameters
params = {
    'mom_lookback': 126,
    'mom_top_n': 3,
    'reserve': 0.01
}
```

## Performance Considerations

### Asset Selection
- **Universe Size**: Balance diversification vs concentration
- **Momentum Stability**: Consider momentum persistence
- **Correlation**: Monitor asset correlations
- **Liquidity**: Ensure sufficient trading volume

### Rebalancing Frequency
- **Monthly**: Balance costs vs responsiveness
- **Transaction Costs**: Consider rebalancing impact
- **Market Impact**: Minimize market impact
- **Timing**: Optimize rebalancing timing

### Risk Management
- **Position Limits**: Maximum exposure per asset
- **Sector Limits**: Maximum sector concentration
- **Volatility Targeting**: Adjust for market volatility
- **Drawdown Controls**: Portfolio-level risk limits

## Best Practices

1. **Universe Selection**: Choose appropriate asset universe
2. **Momentum Stability**: Test momentum persistence
3. **Rebalancing Costs**: Consider transaction costs
4. **Risk Controls**: Implement comprehensive risk management
5. **Performance Monitoring**: Track strategy performance

## Asset Allocation Approaches

### Strategic Asset Allocation
- **Long-term Targets**: Set strategic asset allocation targets
- **Risk Tolerance**: Align with investor risk tolerance
- **Time Horizon**: Consider investment time horizon
- **Rebalancing**: Periodic rebalancing to targets

### Tactical Asset Allocation
- **Short-term Adjustments**: Tactical deviations from strategic targets
- **Market Opportunities**: Exploit short-term market opportunities
- **Risk Management**: Dynamic risk management
- **Performance Enhancement**: Improve risk-adjusted returns 