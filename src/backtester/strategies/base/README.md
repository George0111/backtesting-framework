# Base Strategy Classes

Base classes and common functionality for all trading strategies.

## Scripts Overview

### 📋 Strategy.py
Base strategy class with common functionality for all strategies.
- Provides logging infrastructure
- Handles order and trade notifications
- Manages portfolio tracking
- Includes event logging for analysis

**Key Features:**
- **Event Logging**: Comprehensive logging of all trading events
- **Portfolio Tracking**: Real-time portfolio value and position tracking
- **Order Management**: Order status tracking and notification
- **Trade Analysis**: Trade execution and P&L tracking
- **Timer Support**: Built-in timer functionality for rebalancing

**Classes:**
- `BaseStrategy_OLD`: Legacy base strategy class
- `BaseStrategy`: Current base strategy class with improved functionality

**Usage:**
```python
from .base.Strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        # Your strategy initialization
        
    def next(self):
        # Your trading logic
        pass
```

## Common Functionality

### Logging System
- **Event Logging**: Logs all trading events with timestamps
- **Portfolio Snapshots**: Tracks portfolio value and positions
- **Order Tracking**: Monitors order status and execution
- **Trade Analysis**: Records trade details and P&L

### Portfolio Management
- **Position Tracking**: Real-time position monitoring
- **Cash Management**: Available cash tracking
- **Market Value Calculation**: Current portfolio value
- **Risk Management**: Position sizing and risk controls

### Timer Support
- **Rebalancing Timers**: Automatic rebalancing triggers
- **Custom Timers**: Flexible timer implementation
- **Business Day Logic**: End-of-month and business day handling

### Event Types
- `EVENT_NEXT`: Bar-by-bar processing events
- `EVENT_PORTFOLIO`: Portfolio snapshot events
- `EVENT_ORDER`: Order status events
- `EVENT_TRADE`: Trade execution events
- `EVENT_REBALANCE`: Rebalancing events

## Best Practices

1. **Inherit from BaseStrategy**: Always inherit from the base class for new strategies
2. **Use Logging**: Leverage the built-in logging system for analysis
3. **Implement Required Methods**: Override `next()`, `notify_order()`, `notify_trade()`
4. **Handle Timers**: Use timer functionality for rebalancing strategies
5. **Document Parameters**: Clearly document all strategy parameters

## Example Implementation

```python
from .base.Strategy import BaseStrategy

class SimpleStrategy(BaseStrategy):
    params = (
        ('lookback', 20),
        ('commission', 0.001),
    )
    
    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.lookback)
        
    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()
        else:
            if self.data.close[0] < self.sma[0]:
                self.sell()
``` 