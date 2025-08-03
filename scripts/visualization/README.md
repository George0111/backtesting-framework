# Visualization Scripts

Scripts for creating charts, plots, and visual representations of data and results.

## Scripts Overview

### 📈 plot_log.py
Creates interactive portfolio visualization from backtest logs.
- Loads JSON log files from backtest runs
- Creates interactive Plotly charts
- Shows portfolio holdings over time
- Dropdown selection for different assets

**Features:**
- Interactive portfolio value charts
- Asset-specific views with dropdown
- Time series visualization
- Export to HTML for web viewing

**Usage:**
```bash
python plot_log.py
```

### 📈 plot_log copy.py
Backup/copy of the plot_log.py script.
- Identical functionality to plot_log.py
- Useful for testing modifications

### 📊 visualize_tsmom_simple.py
Creates visualizations for TSMOM strategy results.
- Generates comprehensive charts for TSMOM backtests
- Shows equity curves, drawdowns, and performance metrics
- Creates publication-ready visualizations

**Features:**
- Equity curve plots
- Drawdown analysis charts
- Performance metrics visualization
- Trade analysis plots
- Risk-return scatter plots

**Usage:**
```bash
python visualize_tsmom_simple.py --results_dir results/TSMOM_20250802_100839
```

## Visualization Types

### Portfolio Analysis
- **Equity Curves**: Portfolio value over time
- **Drawdowns**: Maximum drawdown periods
- **Asset Allocation**: Holdings breakdown

### Performance Metrics
- **Returns**: Cumulative and periodic returns
- **Risk Metrics**: Volatility, VaR, maximum drawdown
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio

### Trading Analysis
- **Trade Distribution**: Win/loss distribution
- **Trade Timing**: Entry/exit timing analysis
- **Position Sizing**: Position size over time

## Output Formats

All visualization scripts support:
- **Interactive HTML**: Plotly-based interactive charts
- **Static Images**: PNG/JPEG for reports
- **PDF**: High-quality vector graphics
- **Web Dashboards**: Multi-panel interactive dashboards

## Interactive Features

- **Zoom/Pan**: Interactive navigation
- **Hover Information**: Detailed tooltips
- **Dropdown Selection**: Asset/strategy selection
- **Time Range Selection**: Customizable time periods
- **Export Options**: Save charts in various formats 