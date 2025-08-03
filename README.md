# BACKTEST - Advanced Backtesting Framework

A comprehensive backtesting framework for quantitative trading strategies with support for multiple asset classes, advanced risk management, and detailed performance analysis.

## 🚀 Features

- **Multi-Strategy Support**: Momentum, TSMOM, Pairs Trading, Asset Allocation
- **Multi-Asset Classes**: Cryptocurrencies, Stocks, ETFs
- **Advanced Risk Management**: Position sizing, drawdown controls, volatility targeting
- **Comprehensive Analysis**: Performance metrics, risk analysis, trade analysis
- **Flexible Data Sources**: Support for multiple data formats and sources
- **Modular Architecture**: Clean, organized codebase with strategy categorization

## 📁 Project Structure

```
BACKTEST/
├── src/backtester/           # Core backtesting engine
│   ├── strategies/           # Trading strategies
│   │   ├── base/            # Base strategy classes
│   │   ├── momentum/        # Momentum strategies
│   │   ├── pairs_trading/   # Statistical arbitrage
│   │   ├── asset_allocation/# Portfolio allocation
│   │   └── crypto/          # Cryptocurrency strategies
│   ├── engine.py            # Main backtesting engine
│   ├── utils.py             # Utility functions
│   └── visualization.py     # Charting and visualization
├── scripts/                 # Execution scripts
│   ├── data_management/     # Data download and preprocessing
│   ├── backtesting/        # Strategy execution scripts
│   ├── analysis/           # Results analysis
│   ├── visualization/      # Chart generation
│   └── utilities/          # Helper scripts
├── config/                 # Configuration files
├── data/                   # Data storage (not in repo)
├── results/                # Backtest results (not in repo)
└── requirements.txt        # Python dependencies
```

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/BACKTEST.git
   cd BACKTEST
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download data** (optional):
   ```bash
   python scripts/data_management/download_crypto_data.py
   ```

## 📊 Quick Start

### Run a Simple Backtest

```bash
# Run TSMOM strategy on Bitcoin
python scripts/backtesting/run_backtest_crypto_tsmom_btc.py \
    --start_date 2023-01-01 \
    --end_date 2023-12-31 \
    --initial_cash 10000
```

### Available Strategies

- **CryptoTSMomentum**: Time Series Momentum for cryptocurrencies
- **CryptoMomentum**: Rate-of-change momentum strategy
- **TAA_Momentum**: Tactical Asset Allocation
- **TSMOM_SIMPLE**: Simple moving average crossover
- **MedallionPairsStrategy**: Statistical arbitrage

### Strategy Categories

#### Momentum Strategies
- Rate-of-change momentum
- Time series momentum (TSMOM)
- Moving average crossovers
- Volatility-adjusted position sizing

#### Pairs Trading
- Cointegration-based pair selection
- Kalman filter for dynamic hedge ratios
- Z-score based entry/exit signals
- Risk management and position sizing

#### Asset Allocation
- Tactical Asset Allocation (TAA)
- Portfolio rebalancing
- Risk budgeting
- Multi-asset optimization

## 📈 Performance Analysis

The framework provides comprehensive performance analysis:

- **Returns**: Total return, CAGR, annualized returns
- **Risk Metrics**: Volatility, maximum drawdown, VaR
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Trading Analysis**: Number of trades, win rate, average trade
- **Visualizations**: Equity curves, drawdown charts, correlation heatmaps

## 🔧 Configuration

### Strategy Parameters

Each strategy supports customizable parameters:

```python
# Example: CryptoTSMomentum parameters
strategy_params = {
    'lookback_period': 96,      # 24 hours (96 * 15min bars)
    'momentum_threshold': 0.01, # 1% minimum momentum
    'vol_lookback': 24,         # 6 hours for volatility
    'max_position_size': 0.3,   # Max 30% per position
    'stop_loss': 0.05,          # 5% stop loss
    'take_profit': 0.15,        # 15% take profit
    'commission': 0.001,        # 0.1% commission
    'max_daily_trades': 5,      # Max 5 trades per day
}
```

### Data Configuration

Support for multiple data sources and formats:

- **CSV files**: Standard OHLCV format
- **Real-time data**: CCXT integration for crypto
- **Custom data**: Flexible data loading system

## 📊 Example Results

The framework generates detailed reports including:

- Performance metrics and statistics
- Trade analysis and breakdown
- Risk metrics and drawdown analysis
- Interactive visualizations
- HTML reports with comprehensive analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Adding New Strategies

1. Create strategy class in appropriate category
2. Inherit from `BaseStrategy`
3. Implement required methods (`next()`, `notify_order()`, etc.)
4. Add to strategy mapping in execution scripts
5. Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Past performance does not guarantee future results. Trading involves substantial risk of loss and is not suitable for all investors.

## 📚 Documentation

- [Strategy Development Guide](docs/strategy_development.md)
- [Data Management Guide](docs/data_management.md)
- [Performance Analysis Guide](docs/performance_analysis.md)
- [API Reference](docs/api_reference.md)

## 🐛 Issues

If you encounter any issues, please:

1. Check the [Issues](https://github.com/yourusername/BACKTEST/issues) page
2. Create a new issue with detailed description
3. Include error messages and reproduction steps

## 📞 Support

For questions and support:

- Create an issue on GitHub
- Check the documentation
- Review example scripts in the `scripts/` directory

---

**Happy Backtesting! 📈**
