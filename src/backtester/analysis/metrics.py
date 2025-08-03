import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Function to calculate metrics
def calculate_metrics(strategy, initial_cash, final_value, pnl_history, benchmarks):
    pnl_series = pd.Series(pnl_history)

    # Total Return (USD)
    total_return_usd = final_value - initial_cash

    # Total Return (%)
    total_return_pct = (final_value - initial_cash) / initial_cash * 100

    # Hourly Returns (Percentage Change)
    hourly_returns = pnl_series.pct_change().dropna()[1:] # Drop first row as it is inf

    # Handle cases where hourly_returns becomes empty
    if hourly_returns.empty or hourly_returns.std() == 0:
        print("Warning: Hourly returns are empty or have zero variance.")
        sharpe_ratio = float('nan')
        sortino_ratio = float('nan')
        annualized_volatility_pct = float('nan')
    else:
        # Sharpe Ratio
        annualized_returns_mean = hourly_returns.mean() * 8760  # Scale hourly mean returns to annualized
        annualized_returns_std = hourly_returns.std() * (8760 ** 0.5)  # Annualized standard deviation
        sharpe_ratio = annualized_returns_mean / annualized_returns_std

        # Sortino Ratio
        downside_returns = hourly_returns[hourly_returns < 0]
        annualized_downside_std = downside_returns.std() * (8760 ** 0.5) if not downside_returns.empty else 0
        sortino_ratio = (
            annualized_returns_mean / annualized_downside_std
            if annualized_downside_std != 0 else float('nan')
        )

        # Annualized Volatility (%)
        annualized_volatility_pct = annualized_returns_std * 100
        
    # Sharpe Ratio
    annualized_returns_mean = hourly_returns.mean() * 8760  # Scale hourly mean returns to annualized
    annualized_returns_std = hourly_returns.std() * (8760 ** 0.5)  # Annualized standard deviation
    sharpe_ratio = annualized_returns_mean / annualized_returns_std if annualized_returns_std != 0 else 0

    # Sortino Ratio
    downside_returns = hourly_returns[hourly_returns < 0]
    annualized_downside_std = downside_returns.std() * (8760 ** 0.5)
    sortino_ratio = (
        annualized_returns_mean / annualized_downside_std
        if annualized_downside_std != 0 else 0
    )

    # Annualized Volatility (%)
    annualized_returns_std = hourly_returns.std() * np.sqrt(8760)  # Annualized standard deviation
    annualized_volatility_pct = annualized_returns_std * 100  # Convert to percentage

    # Maximum Drawdown
    high_watermark = pnl_series.cummax()
    # drawdown = pnl_series - high_watermark
    # max_drawdown = drawdown.min()
    # max_drawdown_pct = (max_drawdown / high_watermark.max()) * 100 if high_watermark.max() != 0 else 0

    running_max = pnl_series.cummax()
    print(running_max)
    # Compute drawdowns
    drawdown = pnl_series - running_max
    drawdown_pct = drawdown / running_max * 100

    # Get the maximum drawdown
    max_drawdown = drawdown.min()
    max_drawdown_pct = drawdown_pct.min()

    # CAGR
    num_days = len(pnl_history) / 24  # Assuming hourly data
    cagr = ((final_value / initial_cash) ** (1 / (num_days / 365)) - 1) * 100 if num_days > 0 else 0

    # Calmar Ratio
    calmar_ratio = cagr / abs(max_drawdown_pct) if max_drawdown_pct != 0 else 0

    # Benchmark comparison
    benchmark_results = {}
    for symbol, data in benchmarks.items():
        # Ensure benchmark returns are percentage-based
            # Calculate hourly returns from benchmark OHLCV data
        benchmark_hourly_returns = data['ohlcv']["close"].pct_change().dropna()

        # Annualized Volatility for Benchmark
        benchmark_annualized_volatility_pct = (
            benchmark_hourly_returns.std() * np.sqrt(8760) * 100 if benchmark_hourly_returns.std() != 0 else 0
        )
        benchmark_results[f"Benchmark ({symbol.upper()}) Return (%)"] = data['return_pct']
        benchmark_results[f"Outperformance vs {symbol.upper()} (%)"] = total_return_pct - data['return_pct']
        benchmark_results[f"Benchmark ({symbol.upper()}) Annualized Volatility (%)"] = benchmark_annualized_volatility_pct

    metrics = {
        'Total Return (USD)': total_return_usd,
        'Total Return (%)': total_return_pct,
        'Sharpe Ratio': sharpe_ratio,
        'Sortino Ratio': sortino_ratio,
        'Annualized Volatility (%)': annualized_volatility_pct,
        'Max Drawdown (USD)': max_drawdown,
        'Max Drawdown (%)': max_drawdown_pct,
        'CAGR (%)': cagr,
        'Calmar Ratio': calmar_ratio
    }

    # Add benchmarks to metrics
    metrics.update(benchmark_results)
    return metrics

import backtrader as bt
import pandas as pd

class PerAssetPnL(bt.Analyzer):
    def __init__(self):
        self.pnl_dict = {d._name: [] for d in self.datas}
        self.datetime = []

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        self.datetime.append(dt)
        for d in self.datas:
            pos = self.strategy.getposition(d)
            # PnL = (current price - price at entry) * position size
            if pos.size != 0:
                pnl = (d.close[0] - pos.price) * pos.size
            else:
                pnl = 0.0
            self.pnl_dict[d._name].append(pnl)

    def get_analysis(self):
        df = pd.DataFrame(self.pnl_dict)
        df['datetime'] = self.datetime
        return df.set_index('datetime')


class DataFrameLogger(bt.Analyzer):
    """
    Analyzer to log data to a DataFrame.
    This analyzer captures the data feed's OHLCV values, position size, cash, and value at each step.
    It also captures the values of all indicators defined in the strategy.
    """
    def __init__(self):
        self.rows = []

    def next(self):
        # 假設只處理第一個 data feed，可擴展多個
        data = self.datas[0]
        row = {
            'datetime': data.datetime.datetime(0),
            'open': data.open[0],
            'high': data.high[0],
            'low': data.low[0],
            'close': data.close[0],
            'volume': data.volume[0],
            'position': self.strategy.getposition(data).size,
            'cash': self.strategy.broker.getcash(),
            'value': self.strategy.broker.getvalue(),
        }
        # 動態記錄所有指標（以策略內定義的為例）
        for attr in dir(self.strategy):
            indicator = getattr(self.strategy, attr)
            # 判斷是否為指標物件
            if isinstance(indicator, bt.Indicator):
                try:
                    row[attr] = indicator[0]
                except Exception:
                    pass  # 有些指標可能還沒計算出來
        self.rows.append(row)

    def stop(self):
        self.df = pd.DataFrame(self.rows)

    def get_analysis(self):
        return self.df

    def save_csv(self, filepath):
        if hasattr(self, 'df'):
            self.df.to_csv(filepath, index=False)