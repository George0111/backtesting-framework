import backtrader as bt
import datetime
import pandas as pd
import numpy as np
import yfinance as yf
import quantstats as qs
import os
import matplotlib.pyplot as plt
from matplotlib import rcParams
import requests
import ccxt
import concurrent.futures

rcParams['figure.figsize'] = 12, 8

# Import the strategy
from src.backtester.strategies.pairs_trading.medallion_pairs_strategy import MedallionPairsStrategy

class PandasData(bt.feeds.PandasData):
    """Custom PandasData class to handle yfinance data format"""
    params = (
        ('datetime', None),
        ('open', 'Open'),
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('openinterest', None),
        ('adj_close', 'Adj Close'),
    )

class BacktestRunner:
    """Class to handle the entire backtesting process"""
    
    def __init__(self, 
                 symbols, 
                 start_date='2010-01-01',
                 end_date=None,
                 initial_cash=100000,
                 commission=0.0005,
                 output_dir='backtest_results'):
        """
        Initialize the backtest runner
        
        Parameters:
        -----------
        symbols : list
            List of ticker symbols to backtest
        start_date : str
            Start date for the backtest in YYYY-MM-DD format
        end_date : str
            End date for the backtest in YYYY-MM-DD format
        initial_cash : float
            Initial capital for the backtest
        commission : float
            Commission rate per trade
        output_dir : str
            Directory to save backtest results
        """
        self.symbols = symbols
        self.start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        if end_date is None:
            self.end_date = datetime.datetime.now()
        else:
            self.end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        self.initial_cash = initial_cash
        self.commission = commission
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        self.data = {}
        self.cerebro = None
        self.results = None
        
        
    def get_cache_path(self, symbol):
        cache_dir = os.path.join(self.output_dir, "data_cache")
        os.makedirs(cache_dir, exist_ok=True)
        # Remove slashes for file name safety
        safe_symbol = symbol.replace("/", "")
        return os.path.join(cache_dir, f"{safe_symbol}.parquet")

    def fetch_data(self, timeframe='15m', lookback_days=365):
        """Fetch OHLCV data for all symbols using ccxt (Binance), with caching."""
        print(f"Fetching data for {len(self.symbols)} symbols from Binance via ccxt...")
        exchange = ccxt.binance()
        since = exchange.parse8601((self.start_date).strftime('%Y-%m-%dT00:00:00Z'))
        end_ts = exchange.parse8601((self.end_date).strftime('%Y-%m-%dT00:00:00Z'))
        limit_per_call = 1000  # Binance max per call for 15m timeframe

        for symbol in self.symbols:
            cache_path = self.get_cache_path(symbol)
            if os.path.exists(cache_path):
                try:
                    df = pd.read_parquet(cache_path)
                    self.data[symbol] = df
                    print(f"Loaded cached data for {symbol}: {len(df)} bars")
                    continue
                except Exception as e:
                    print(f"Error loading cache for {symbol}: {e}, refetching...")

            try:
                all_ohlcv = []
                since_local = since
                while since_local < end_ts:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_local, limit=limit_per_call)
                    if not ohlcv:
                        break
                    all_ohlcv += ohlcv
                    since_local = ohlcv[-1][0] + 15*60*1000  # next 15m in ms
                    if len(ohlcv) < limit_per_call:
                        break
                if not all_ohlcv or len(all_ohlcv) < 252:  # You may want to increase this for 15m data
                    print(f"Warning: Insufficient data for {symbol}, skipping.")
                    continue
                df = pd.DataFrame(all_ohlcv, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Datetime'] = pd.to_datetime(df['Datetime'], unit='ms')
                df.set_index('Datetime', inplace=True)
                self.data[symbol] = df
                df.to_parquet(cache_path)
                print(f"Fetched and cached data for {symbol}: {len(df)} bars")
            except Exception as e:
                print(f"Error fetching data for {symbol}: {str(e)}")
        return len(self.data) > 0
    
    def find_pairs(self, lookback=252, threshold=0.05, max_workers=6):
        """Find cointegrated pairs from the fetched data using threading for speed."""
        from statsmodels.tsa.stattools import coint

        print(f"Finding cointegrated pairs (threaded, max_workers={max_workers})...")
        pairs = []
        symbols = list(self.data.keys())

        # Prepare all possible pairs
        symbol_pairs = [
            (symbols[i], symbols[j])
            for i in range(len(symbols))
            for j in range(i + 1, len(symbols))
        ]

        def test_pair(pair):
            sym1, sym2 = pair
            df1 = self.data[sym1]
            df2 = self.data[sym2]
            # Pre-filter: require enough overlapping bars
            overlap = df1.index.intersection(df2.index)
            if len(overlap) < lookback:
                print(f"Skipping pair {sym1}-{sym2}: insufficient overlap ({len(overlap)} bars)")
                return None

            # Align both series to the overlap
            prices1 = df1.loc[overlap, 'Close'].values
            prices2 = df2.loc[overlap, 'Close'].values

            # Skip if any NaN values
            if np.isnan(prices1).any() or np.isnan(prices2).any():
                return None
            # Skip if series is constant
            if np.all(prices1 == prices1[0]) or np.all(prices2 == prices2[0]):
                return None

            score, pvalue, _ = coint(prices1[-lookback:], prices2[-lookback:])
            if pvalue < threshold:
                correlation = np.corrcoef(prices1[-lookback:], prices2[-lookback:])[0, 1]
                if abs(correlation) > 0.5:
                    print(f"Found cointegrated pair: {sym1} - {sym2} (p-value: {pvalue:.4f}, corr: {correlation:.2f}, overlap: {len(overlap)})")
                    return (sym1, sym2, pvalue, correlation)
            return None

        # Use ThreadPoolExecutor to parallelize the cointegration tests
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(test_pair, symbol_pairs))

        # Filter out None results
        pairs = [r for r in results if r is not None]

        # Sort pairs by p-value (strongest cointegration first)
        pairs.sort(key=lambda x: x[2])
        return pairs
    
    def setup_backtest(self, pair=None, strategy_params=None):
        """Set up the backtest with the specified pair or all available pairs"""
        self.cerebro = bt.Cerebro()
        
        # Set initial cash
        self.cerebro.broker.setcash(self.initial_cash)
        
        # Set commission
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # Add data feeds
        if pair:
            # Add specific pair
            sym1, sym2 = pair[0], pair[1]
            data1 = PandasData(dataname=self.data[sym1], name=sym1)
            data2 = PandasData(dataname=self.data[sym2], name=sym2)
            self.cerebro.adddata(data1)
            self.cerebro.adddata(data2)
        else:
            # Add all available data
            for symbol, df in self.data.items():
                data = PandasData(dataname=df, name=symbol)
                self.cerebro.adddata(data)
        
        # Set up strategy
        if strategy_params is None:
            strategy_params = {}
            
        self.cerebro.addstrategy(MedallionPairsStrategy, **strategy_params)
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, 
                                _name='sharpe',
                                riskfreerate=0.01,
                                annualize=True)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, 
                                _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, 
                                _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, 
                                _name='returns')
        
        # Add observers
        self.cerebro.addobserver(bt.observers.Value)
        self.cerebro.addobserver(bt.observers.DrawDown)
        
        print("Backtest setup complete")
        return self.cerebro
        
    def run_backtest(self):
        """Run the backtest"""
        print("Running backtest...")
        self.results = self.cerebro.run()
        print("Backtest complete")
        return self.results
    
    def analyze_results(self, pair_name=None):
        """Analyze the results of the backtest"""
        if self.results is None:
            print("No backtest results to analyze")
            return

        strategy = self.results[0]
        final_value = strategy.broker.getvalue()
        initial_value = self.initial_cash

        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
        trades_analysis = strategy.analyzers.trades.get_analysis()
        returns_analysis = strategy.analyzers.returns.get_analysis()

        sharpe_ratio = sharpe_analysis.get('sharperatio', 0)
        max_dd = drawdown_analysis.get('max', 0)
        net_profit = final_value - initial_value
        return_pct = (final_value / initial_value - 1) * 100
        # Analyzer results
        total_trades = trades_analysis.get('total', {}).get('total', 0)
        
        if total_trades > 0:
            # Print summary
            print("\n===== BACKTEST RESULTS =====")
            if pair_name:
                print(f"Pair: {pair_name}")
            print(f"Initial Capital: ${initial_value:.2f}")
            print(f"Final Capital: ${final_value:.2f}")
            print(f"Net Profit: ${net_profit:.2f}")
            print(f"Return: {return_pct:.2f}%")

            print("\n--- Performance Metrics ---")
            print(f"Sharpe Ratio: {sharpe_ratio:.4f}")
            print(f"Max Drawdown: {max_dd * 100:.2f}%")

            print("\n--- Trade Statistics ---")
        # total_trades = trades_analysis.get('total', {}).get('total', 0)
        # if total_trades > 0:
            won = trades_analysis.get('won', {}).get('total', 0)
            lost = trades_analysis.get('lost', {}).get('total', 0)
            win_rate = won / total_trades if total_trades > 0 else 0

            print(f"Total Trades: {total_trades}")
            print(f"Winning Trades: {won} ({win_rate * 100:.2f}%)")
            print(f"Losing Trades: {lost} ({(1 - win_rate) * 100:.2f}%)")

            if won > 0:
                avg_win = trades_analysis.get('won', {}).get('pnl', {}).get('average', 0)
                print(f"Average Profit per Winning Trade: ${avg_win:.2f}")

            if lost > 0:
                avg_loss = trades_analysis.get('lost', {}).get('pnl', {}).get('average', 0)
                print(f"Average Loss per Losing Trade: ${avg_loss:.2f}")
        else:
            print("No trades executed during the backtest for ".format(pair_name if pair_name else "this strategy"))
        # Create performance report using quantstats
        self.create_quantstats_report(pair_name)
        
        # Plot results
        self.plot_results(pair_name)
        
    def create_quantstats_report(self, pair_name=None):
        """Create a performance report using quantstats"""
        if self.results is None:
            return

        # Extract daily returns
        returns = pd.Series([r for r in self.results[0].analyzers.returns.get_analysis().values()])
        if returns.nunique() <= 1:
            print("Not enough return data to generate QuantStats report.")
            return

        # Convert to pandas Series with dates
        returns.index = pd.date_range(
            start=self.start_date,
            periods=len(returns),
            freq='B')

        # Generate report
        report_name = pair_name if pair_name else "portfolio"
        report_path = os.path.join(self.output_dir, f"{report_name}_report.html")

        # Get benchmark returns (S&P 500)
        benchmark_df = yf.download('^GSPC',
                                   start=self.start_date.strftime('%Y-%m-%d'),
                                   end=self.end_date.strftime('%Y-%m-%d'),
                                   progress=False)
        if 'Adj Close' in benchmark_df.columns:
            benchmark = benchmark_df['Adj Close'].pct_change().dropna()
        else:
            benchmark = benchmark_df['Close'].pct_change().dropna()

        # Align benchmark with strategy returns
        benchmark = benchmark[benchmark.index.isin(returns.index)]
        returns = returns[returns.index.isin(benchmark.index)]

        if returns.nunique() <= 1 or benchmark.nunique() <= 1:
            print("Not enough variability in returns or benchmark to generate QuantStats report.")
            return

        # Generate the report
        qs.reports.html(returns,
                       benchmark=benchmark,
                       output=report_path,
                       title=f"Medallion Pairs Strategy - {report_name}")

        print(f"QuantStats report saved to {report_path}")
        
    def plot_results(self, pair_name=None):
        """Plot the backtest results"""
        if self.results is None:
            return

        # Sanitize pair_name for file system
        safe_pair_name = pair_name.replace('/', '_') if pair_name else 'portfolio'
        plot_filename = os.path.join(
            self.output_dir, 
            f"{safe_pair_name}_plot.png")

        self.cerebro.plot(style='candlestick', barup='green', bardown='red',
                         plotdist=1, fmt_x_ticks='%Y-%m-%d', fmt_x_data='%Y-%m-%d',
                         volume=False)
        plt.savefig(plot_filename)
        print(f"Plot saved to {plot_filename}")
        
    def run_all_pairs(self, top_n=5, strategy_params=None):
        """Run backtest on the top N cointegrated pairs"""
        # Find cointegrated pairs
        pairs = self.find_pairs(max_workers=6)
        
        if not pairs:
            print("No cointegrated pairs found")
            return
            
        # Take top N pairs
        top_pairs = pairs[:min(top_n, len(pairs))]
        
        results = []
        
        # Run backtest for each pair
        for i, (sym1, sym2, pvalue, corr) in enumerate(top_pairs):
            print(f"\nTesting pair {i+1}/{len(top_pairs)}: {sym1} - {sym2}")
            
            # Setup and run backtest
            self.setup_backtest(pair=(sym1, sym2), strategy_params=strategy_params)
            self.run_backtest()
            
            # Calculate performance metrics
            final_value = self.cerebro.broker.getvalue()
            return_pct = (final_value / self.initial_cash - 1) * 100
            sharpe = self.results[0].analyzers.sharpe.get_analysis().get('sharperatio', 0)
            drawdown_analysis = self.results[0].analyzers.drawdown.get_analysis()
            max_dd = drawdown_analysis.get('drawdown', drawdown_analysis.get('max', 0)) * 100

            # Store results
            pair_result = {
                'pair': f"{sym1}-{sym2}",
                'return_pct': return_pct,
                'sharpe': sharpe,
                'max_drawdown': max_dd,
                'final_value': final_value
            }
            results.append(pair_result)
            
            # Analyze and save results
            self.analyze_results(pair_name=f"{sym1}_{sym2}")
            
        # Sort results by Sharpe ratio
        results.sort(key=lambda x: x['sharpe'], reverse=True)
        
        # Print summary of all pairs
        print("\n===== PAIRS SUMMARY =====")
        for i, result in enumerate(results):
            print(f"{i+1}. {result['pair']}: Return={result['return_pct']:.2f}%, "
                 f"Sharpe={result['sharpe']:.2f}, MaxDD={result['max_drawdown']:.2f}%")
                 
        return results


def get_top_binance_usd_symbols(limit=200):
    """Fetch top crypto symbols from Binance and convert to yfinance format."""
    url = "https://api.binance.com/api/v3/ticker/24hr"
    response = requests.get(url)
    data = response.json()
    # Filter for USDT pairs and sort by quoteVolume
    usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
    usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
    # Get top N symbols
    top_symbols = [d['symbol'].replace('USDT', '-USD') for d in usdt_pairs[:limit]]
    return top_symbols

def get_top_binance_usd_symbols_ccxt(limit=200):
    """Fetch top crypto symbols from Binance using ccxt and return as 'COIN/USDT'."""
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    # Filter for USDT pairs and sort by quote volume if available
    usdt_pairs = [s for s in markets if s.endswith('/USDT') and not s.endswith('UP/USDT') and not s.endswith('DOWN/USDT')]
    # Optionally, sort by volume (requires fetching tickers)
    tickers = exchange.fetch_tickers(usdt_pairs)
    sorted_pairs = sorted(
        usdt_pairs,
        key=lambda s: tickers[s]['quoteVolume'] if 'quoteVolume' in tickers[s] and tickers[s]['quoteVolume'] else 0,
        reverse=True
    )
    return sorted_pairs[:limit]

# Example usage
if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    # Get top 200 Binance crypto symbols as ccxt tickers
    symbols = get_top_binance_usd_symbols_ccxt(limit=10)
    
    runner = BacktestRunner(
        symbols=symbols,
        start_date='2024-01-01',
        end_date='2024-02-31',
        initial_cash=100000,
        output_dir='medallion_results'
    )
    
    if runner.fetch_data():
        strategy_params = {
            'lookback': 60,
            'entry_z': 2.0,
            'exit_z': 0.5,
            'max_hold_days': 50,
            'position_size': 0.15,
            'max_positions': 3,
            'use_adaptive': True,
            'use_kalman': True,
            'log_level': 1
        }
        results = runner.run_all_pairs(top_n=5, strategy_params=strategy_params)