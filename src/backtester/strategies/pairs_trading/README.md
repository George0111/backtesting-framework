# Pairs Trading Strategies

Statistical arbitrage and pairs trading strategies based on mean reversion and cointegration.

## Scripts Overview

### 📊 medallion_pairs_strategy.py
Advanced pairs trading strategy inspired by Renaissance Technologies' Medallion Fund.
- Cointegration-based pair selection
- Kalman filter for dynamic hedge ratios
- Z-score based entry/exit signals
- Risk management and position sizing

**Features:**
- **Cointegration Testing**: Statistical tests for pair relationships
- **Dynamic Hedge Ratios**: Kalman filter for adaptive ratios
- **Z-Score Signals**: Entry/exit based on statistical extremes
- **Risk Management**: Drawdown limits and position sizing
- **Half-Life Analysis**: Mean reversion timing analysis

**Parameters:**
- `lookback`: Lookback period for calculations
- `entry_z`: Z-score threshold for entry
- `exit_z`: Z-score threshold for exit
- `max_hold_days`: Maximum holding period
- `max_positions`: Maximum number of concurrent positions
- `position_size`: Position size as fraction of portfolio
- `max_drawdown`: Maximum drawdown limit
- `use_adaptive`: Enable adaptive parameters
- `use_kalman`: Use Kalman filter for hedge ratios
- `use_half_life`: Use half-life analysis

## Strategy Components

### Pair Selection
- **Cointegration Testing**: Engle-Granger test for cointegration
- **Correlation Analysis**: Pearson correlation for pair selection
- **Liquidity Screening**: Volume and spread requirements
- **Sector Analysis**: Industry and sector considerations

### Signal Generation
- **Z-Score Calculation**: Standardized spread measure
- **Entry Signals**: Z-score above/below thresholds
- **Exit Signals**: Z-score returning to mean
- **Stop Loss**: Maximum loss per position

### Risk Management
- **Position Sizing**: Volatility-adjusted position sizes
- **Drawdown Limits**: Portfolio-level risk controls
- **Correlation Limits**: Maximum correlation between positions
- **Sector Limits**: Maximum exposure per sector

## Implementation Details

### Cointegration Testing
```python
# Engle-Granger test for cointegration
def test_cointegration(price1, price2):
    model = sm.OLS(price1, sm.add_constant(price2))
    results = model.fit()
    residuals = results.resid
    adf_stat, p_value = adfuller(residuals)
    return p_value < 0.05
```

### Z-Score Calculation
```python
# Calculate z-score of spread
def calculate_z_score(spread, lookback):
    mean = np.mean(spread[-lookback:])
    std = np.std(spread[-lookback:])
    return (spread[-1] - mean) / std
```

### Kalman Filter
```python
# Dynamic hedge ratio estimation
def kalman_filter(price1, price2, state):
    x, P, Q, R = state['x'], state['P'], state['Q'], state['R']
    x_pred, P_pred = x, P + Q
    K = P_pred / (P_pred + R)
    x = x_pred + K * (price1 - x_pred * price2)
    P = (1 - K) * P_pred
    return x, P
```

## Usage Examples

```python
# Import pairs trading strategy
from .pairs_trading.medallion_pairs_strategy import MedallionPairsStrategy

# Strategy parameters
params = {
    'lookback': 60,
    'entry_z': 2.0,
    'exit_z': 0.5,
    'max_hold_days': 10,
    'max_positions': 3,
    'position_size': 0.15,
    'max_drawdown': 0.15,
    'use_adaptive': True,
    'use_kalman': True,
    'commission': 0.0005
}
```

## Performance Considerations

### Pair Selection
- **Liquidity**: Ensure sufficient trading volume
- **Correlation**: Avoid highly correlated pairs
- **Sector Diversification**: Spread across different sectors
- **Market Conditions**: Adapt to changing market regimes

### Risk Management
- **Position Limits**: Maximum exposure per pair
- **Drawdown Controls**: Portfolio-level risk limits
- **Correlation Monitoring**: Avoid concentration risk
- **Liquidity Monitoring**: Exit illiquid positions

### Signal Quality
- **Z-Score Thresholds**: Balance signal frequency vs quality
- **Holding Periods**: Optimize for mean reversion timing
- **Entry/Exit Timing**: Consider transaction costs
- **Market Regimes**: Adapt to different market conditions

## Best Practices

1. **Thorough Testing**: Test pairs for cointegration stability
2. **Risk Controls**: Implement comprehensive risk management
3. **Transaction Costs**: Consider bid-ask spreads and commissions
4. **Market Regimes**: Monitor for regime changes
5. **Liquidity Management**: Ensure ability to exit positions 