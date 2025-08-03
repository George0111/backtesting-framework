import backtrader as bt
import datetime, pytz
import pandas as pd
import json, os
import quantstats
from Analyzes.data_utils import IsFirstBusinessDayOfYear, get_benchmark, fetch_data  # Import the callable class
from ..base.Strategy import BaseStrategy
from Analyzes.metrics_analyze import PerAssetPnL, DataFrameLogger

# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class twoETF(BaseStrategy):
    params = dict(
              weightings=[0.67, 0.33],
              reserve=0.05,  # 1% reserve capital
            #   cheat_on_close=True  # Allow orders to be executed at the close of the bar
             )

    def __init__(self):
        # Call the base class's __init__ method to initialize the logger
        super().__init__()
        
        # self.initial_rebalance_done = False
        self.is_first_business_day = IsFirstBusinessDayOfYear() # Create an instance of the callable class

        self.weightings = [w * (1-self.p.reserve) for w in self.p.weightings]  # Adjust weightings to account for reserve capital
        print(f"Weightings: {self.weightings}")
 
        print("Adding timer...")

        self.add_timer(
            when=bt.Timer.SESSION_START,
            # weekdays=[],
            allow=self.is_first_business_day,  # Allow all days
            monthcarry=True,
        )
        print("Timer added successfully!")
    
    # Initialize the strategy
    def next(self):
        super().next()

    # timer function
    def notify_timer(self, timer, when, *args, **kwargs):
        self.log_timer_info()
        # self.log(f"Timer event triggered: {when}")
        self.rebalance_portfolio()

    # rebalance methodology
    def rebalance_portfolio(self):
        # Equity and Bond positions rebalance
        for i, d in enumerate(self.datas):
            self.order_target_percent(d, target=self.weightings[i])
        

def main():
    # Set the run timestamp
    run_timestamp = datetime.datetime.now().isoformat()
    print(f"Run Timestamp: {run_timestamp}")

    # Create Cerebro engine
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(twoETF, run_timestamp=run_timestamp, verbose=True, logfile=f'twoETF_{run_timestamp}.json')
    
    # Define start and end times with timezone
    start_dt = pd.Timestamp('2012-01-01 00:00:00', tz=pytz.UTC)
    end_dt = pd.Timestamp('2025-05-01 23:59:00', tz=pytz.UTC)

    # Fetch historical data from csv file
    universe = ['BTAL','TQQQ']
    benchmark = 'QQQ'

    for s in universe:
        ohlcv = fetch_data('./2ETF/',  s, start_dt, end_dt)
        dataframe = bt.feeds.PandasData(dataname=ohlcv,name=s, plot=False)
        cerebro.adddata(dataframe, name=s)

    # # Set starting cash
    cerebro.broker.set_cash(10000)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    # cerebro.broker.setcommission(commission=0.001)  # Example: 0.1% fee

    # cerebro.broker.set_slippage_perc(0.001)  # 0.1% slippage

    # cerebro.addsizer(bt.sizers.PercentSizer, percents=10)  # Use 10% of capital per trade

    # # Run backtest
    print(f"Starting Portfolio Value: {cerebro.broker.getvalue()}")
    results = cerebro.run(runonce=True, stdstats=False)
    print(f"Ending Portfolio Value: {cerebro.broker.getvalue()}")


    strat = results[0]
    pyfoliozer = strat.analyzers.getbyname('pyfolio')
    rets, positions, transactions, glev = pyfoliozer.get_pf_items()
    df = get_benchmark(benchmark, start_dt, end_dt)
    
    # Convert both indices to timezone-naive
    rets.index = rets.index.tz_localize(None)
    df.index = df.index.tz_localize(None)
    rets, df = rets.align(df, join='inner')  # Align both Series/DataFrame to the same dates

    
    quantstats.reports.html(rets, benchmark=df, output=f'./2ETF/stats_twoETF.html', title='twoETF', match_dates=False)

if __name__ == '__main__':
    main()