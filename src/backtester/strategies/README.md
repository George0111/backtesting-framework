# Strategies Directory

This directory contains all the trading strategies for the backtesting project, organized by strategy type for better maintainability.

## Directory Structure

### 📁 base/
Base strategy classes and common functionality.

### 📁 momentum/
Momentum-based trading strategies.

### 📁 pairs_trading/
Statistical arbitrage and pairs trading strategies.

### 📁 asset_allocation/
Portfolio allocation and asset allocation strategies.

### 📁 crypto/
Cryptocurrency-specific trading strategies.

## Strategy Categories

### Base Strategies
- **Base Classes**: Common functionality and logging for all strategies
- **Abstract Classes**: Template classes for strategy development

### Momentum Strategies
- **Simple Momentum**: Basic momentum implementation
- **TSMOM**: Time Series Momentum strategies
- **SMA Crossover**: Moving average crossover strategies

### Pairs Trading
- **Medallion Pairs**: Statistical arbitrage implementation
- **Cointegration**: Mean reversion strategies
- **Spread Trading**: Spread-based strategies

### Asset Allocation
- **TAA**: Tactical Asset Allocation
- **ETF Strategies**: Exchange-traded fund strategies
- **Portfolio Management**: Multi-asset portfolio strategies

### Crypto Strategies
- **Crypto Momentum**: Cryptocurrency momentum strategies
- **Crypto TSMOM**: Time series momentum for crypto
- **Crypto Pairs**: Cryptocurrency pairs trading

## Usage

```python
# Import base strategy
from .base.Strategy import BaseStrategy

# Import specific strategies
from .momentum.TSMOM_SIMPLE import TSMOM_SIMPLE
from .crypto.CryptoMomentum import CryptoMomentum
from .asset_allocation.TAA import TAA_Momentum
from .pairs_trading.medallion_pairs_strategy import MedallionPairsStrategy
```

## Strategy Development

When creating new strategies:

1. **Inherit from BaseStrategy**: Use the base class for common functionality
2. **Choose the Right Category**: Place strategies in appropriate directories
3. **Follow Naming Conventions**: Use descriptive class names
4. **Document Parameters**: Clearly document all strategy parameters
5. **Include Examples**: Add usage examples in docstrings

Each subdirectory contains its own README with detailed information about the strategies in that category. 