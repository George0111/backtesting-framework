import backtrader as bt
import datetime, pytz
import pandas as pd
import json
import quantstats
from Utils import IsLastBusinessDay, AlwaysAllow, get_benchmark  # Import the callable class

from src.backtester.strategies.base.Strategy import BaseStrategy
# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

'''
This is a simple example of a Backtrader strategy that uses two assets (SPY and AGG) to create a 60/40 portfolio.
We will need to create a rebalance_portfolio function that will be called every month.

Note in quantats/_plotting/core/plot_timeseries we made amendment from returns.sum(axis=0) to returns.sum() after upgrading to numpy>=2.0.0
    if resample:
        returns = returns.resample(resample)
        returns = returns.last() if compound is True else returns.sum()
        if isinstance(benchmark, _pd.Series):
            benchmark = benchmark.resample(resample)
            benchmark = benchmark.last() if compound is True else benchmark.sum()
'''

class SixtyForty(BaseStrategy):
    params = dict(
              rebal_weekday=4, # Friday
              weightings=[0.6, 0.4],
              reserve=0.01,  # 5% reserve capital
            #   cheat_on_close=True  # Allow orders to be executed at the close of the bar
             )

    def __init__(self, run_timestamp):
        # Call the base class's __init__ method to initialize the logger
        super().__init__(run_timestamp)
        
        # self.run_timestamp = run_timestamp

        # self.initial_rebalance_done = False

        self.weightings = [w * (1-self.p.reserve) for w in self.p.weightings]  # Adjust weightings to account for reserve capital
        print(f"Weightings: {self.weightings}")
 
        self.add_timer(
            when=bt.Timer.SESSION_START,
            weekdays=[self.p.rebal_weekday],
            weekcarry=True,  # if a day isn't there, execute on the next
        )


    # Initialize the strategy
    def next(self):
        # if not self.initial_rebalance_done:
        #             self.rebalance_portfolio()
        #             self.initial_rebalance_done = True
        
        temp_pos = {}
        # Check current holdings
        for data in self.datas:
            position = self.getposition(data)

            # Access position details
            size = position.size
            price = position.price
            cost = size * price

            # Calculate the current market value of the position
            market_value = position.size * data.close[0]

            # Calculate the profit and loss
            pnl = market_value - cost

            # Log the current position details
            loop_info = {
                'run_timestamp': self.run_timestamp,
                'event': 'next',
                'event_timestamp': data.datetime.datetime(0).isoformat(),  # Current bar's datetime
                'asset': data._name,  # Name of the data feed
                'open': data.open[0],
                'high': data.high[0],
                'low': data.low[0],
                'close': data.close[0],
                'volume': data.volume[0],
                'size': size,
                'price': price,
                'cost': cost,
                'pnl': pnl,
                'market_value': market_value,
                }
            self.next_logger.info(json.dumps(loop_info))  # Log the loop information to the `next()` logger
            temp_pos[data._name] = market_value

        cash = self.broker.getcash()
        port_info = {'run_timestamp': self.run_timestamp,
                'event': 'portfolio',
                'event_timestamp': self.datas[0].datetime.datetime(0).isoformat(),  # Current bar's datetime
                'equity': self.broker.getvalue(),
                'cash': cash,
                'market_values': temp_pos
                }
        self.next_logger.info(json.dumps(port_info))  # Log the current cash value

    # rebalance methodology
    def rebalance_portfolio(self):
        # Equity and Bond positions rebalance
        for i, d in enumerate(self.datas):
            self.order_target_percent(d, target=self.weightings[i])
        

    # timer function
    def notify_timer(self, timer, when, *args, **kwargs):
        # self.log(f"Timer triggered {self.data.datetime.date(0)} ")
        timer_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'rebalance',
            }
        self.next_logger.info(json.dumps(timer_info))
        self.rebalance_portfolio()

    # create order to target a specific portfolio percentage
    # This function is called on each rebalance event
    def order_target_percent(self, data, target):
        # Create an order to target a specific portfolio percentage
        order = super().order_target_percent(data=data, target=target)
        if order:
            self.track_order(order, data, target)

    # Track order details
    def track_order(self, order, data, target):
        order_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'track_order',
            'order_status': order.getstatusname(),
            'asset': data._name,
            'order_type': order.ordtypename(),
            'target_percent': f'{target * 100:.2f}%',
            'size': order.size,
            'price': order.executed.price if order.status == order.Completed else "Pending",
        }
        # Log the order details into the next_logger
        self.next_logger.info(json.dumps(order_info))

class SixtyForty_monthly(BaseStrategy):
    params = dict(
              weightings=[0.6, 0.4],
              reserve=0.01,  # 1% reserve capital
            #   cheat_on_close=True  # Allow orders to be executed at the close of the bar
             )

    def __init__(self, run_timestamp):
        # Call the base class's __init__ method to initialize the logger
        super().__init__(run_timestamp)
        
        # self.initial_rebalance_done = False
        self.is_last_business_day = IsLastBusinessDay() # Create an instance of the callable class
        self.always_allow = AlwaysAllow()  # Create an instance of the callable class

        self.weightings = [w * (1-self.p.reserve) for w in self.p.weightings]  # Adjust weightings to account for reserve capital
        print(f"Weightings: {self.weightings}")
 
        print("Adding timer...")

        self.add_timer(
            when=bt.Timer.SESSION_START,
            weekdays=[],
            allow=self.is_last_business_day,  # Allow all days
            monthcarry=True,
        )
        print("Timer added successfully!")
    
    # Initialize the strategy
    def next(self):
        # if not self.initial_rebalance_done:
        #             self.rebalance_portfolio()
        #             self.initial_rebalance_done = True
        temp_pos = {}
        # Check current holdings
        for data in self.datas:
            position = self.getposition(data)

            # Access position details
            size = position.size
            price = position.price
            cost = size * price

            # Calculate the current market value of the position
            market_value = position.size * data.close[0]

            # Calculate the profit and loss
            pnl = market_value - cost

            # Log the current position details
            loop_info = {
                'run_timestamp': self.run_timestamp,
                'event': 'next',
                'event_timestamp': data.datetime.datetime(0).isoformat(),  # Current bar's datetime
                'asset': data._name,  # Name of the data feed
                'open': data.open[0],
                'high': data.high[0],
                'low': data.low[0],
                'close': data.close[0],
                'volume': data.volume[0],
                'size': size,
                'price': price,
                'cost': cost,
                'pnl': pnl,
                'market_value': market_value,
                }
            self.next_logger.info(json.dumps(loop_info))  # Log the loop information to the `next()` logger
            temp_pos[data._name] = market_value

        cash = self.broker.getcash()
        port_info = {'run_timestamp': self.run_timestamp,
                'event': 'portfolio',
                'event_timestamp': self.datas[0].datetime.datetime(0).isoformat(),  # Current bar's datetime
                'equity': self.broker.getvalue(),
                'cash': cash,
                'market_values': temp_pos
                }
        self.next_logger.info(json.dumps(port_info))  # Log the current cash value

    # timer function
    def notify_timer(self, timer, when, *args, **kwargs):
        timer_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'rebalance',
            }
        self.next_logger.info(json.dumps(timer_info))
        self.rebalance_portfolio()

    # rebalance methodology
    def rebalance_portfolio(self):
        # Equity and Bond positions rebalance
        for i, d in enumerate(self.datas):
            self.order_target_percent(d, target=self.weightings[i])
        
    
    # create order to target a specific portfolio percentage
    # This function is called on each rebalance event
    def order_target_percent(self, data, target):
        # Create an order to target a specific portfolio percentage
        order = super().order_target_percent(data=data, target=target)
        if order:
            self.track_order(order, data, target)

    # Track order details
    def track_order(self, order, data, target):
        order_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'track_order',
            'order_status': order.getstatusname(),
            'asset': data._name,
            'order_type': order.ordtypename(),
            'target_percent': f'{target * 100:.2f}%',
            'size': order.size,
            'price': order.executed.price if order.status == order.Completed else "Pending",
        }
        # Log the order details into the next_logger
        self.next_logger.info(json.dumps(order_info))


class SixtyForty_yearly(BaseStrategy):
    params = dict(
              weightings=[0.6, 0.4],
              reserve=0.01,  # 1% reserve capital
            #   cheat_on_close=True  # Allow orders to be executed at the close of the bar
             )

    def __init__(self, run_timestamp):
        # Call the base class's __init__ method to initialize the logger
        super().__init__(run_timestamp)
        
        # self.initial_rebalance_done = False
        self.is_last_business_day = IsLastBusinessDay() # Create an instance of the callable class
        self.always_allow = AlwaysAllow()  # Create an instance of the callable class

        self.weightings = [w * (1-self.p.reserve) for w in self.p.weightings]  # Adjust weightings to account for reserve capital
        print(f"Weightings: {self.weightings}")
 
        print("Adding timer...")

        self.add_timer(
            when=bt.Timer.SESSION_START,
            weekdays=[],
            allow=self.is_last_business_day,  # Allow all days
            monthcarry=True,
        )
        print("Timer added successfully!")
    
    # Initialize the strategy
    def next(self):
        # if not self.initial_rebalance_done:
        #             self.rebalance_portfolio()
        #             self.initial_rebalance_done = True
        temp_pos = {}
        # Check current holdings
        for data in self.datas:
            position = self.getposition(data)

            # Access position details
            size = position.size
            price = position.price
            cost = size * price

            # Calculate the current market value of the position
            market_value = position.size * data.close[0]

            # Calculate the profit and loss
            pnl = market_value - cost

            # Log the current position details
            loop_info = {
                'run_timestamp': self.run_timestamp,
                'event': 'next',
                'event_timestamp': data.datetime.datetime(0).isoformat(),  # Current bar's datetime
                'asset': data._name,  # Name of the data feed
                'open': data.open[0],
                'high': data.high[0],
                'low': data.low[0],
                'close': data.close[0],
                'volume': data.volume[0],
                'size': size,
                'price': price,
                'cost': cost,
                'pnl': pnl,
                'market_value': market_value,
                }
            self.next_logger.info(json.dumps(loop_info))  # Log the loop information to the `next()` logger
            temp_pos[data._name] = market_value

        cash = self.broker.getcash()
        port_info = {'run_timestamp': self.run_timestamp,
                'event': 'portfolio',
                'event_timestamp': self.datas[0].datetime.datetime(0).isoformat(),  # Current bar's datetime
                'equity': self.broker.getvalue(),
                'cash': cash,
                'market_values': temp_pos
                }
        self.next_logger.info(json.dumps(port_info))  # Log the current cash value

    # timer function
    def notify_timer(self, timer, when, *args, **kwargs):
        timer_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'rebalance',
            }
        self.next_logger.info(json.dumps(timer_info))
        self.rebalance_portfolio()

    # rebalance methodology
    def rebalance_portfolio(self):
        # Equity and Bond positions rebalance
        for i, d in enumerate(self.datas):
            self.order_target_percent(d, target=self.weightings[i])
        
    
    # create order to target a specific portfolio percentage
    # This function is called on each rebalance event
    def order_target_percent(self, data, target):
        # Create an order to target a specific portfolio percentage
        order = super().order_target_percent(data=data, target=target)
        if order:
            self.track_order(order, data, target)

    # Track order details
    def track_order(self, order, data, target):
        order_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'track_order',
            'order_status': order.getstatusname(),
            'asset': data._name,
            'order_type': order.ordtypename(),
            'target_percent': f'{target * 100:.2f}%',
            'size': order.size,
            'price': order.executed.price if order.status == order.Completed else "Pending",
        }
        # Log the order details into the next_logger
        self.next_logger.info(json.dumps(order_info))


def main():
    # Set the run timestamp
    run_timestamp = datetime.datetime.now().isoformat()
    print(f"Run Timestamp: {run_timestamp}")

    # Create Cerebro engine
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(SixtyForty_monthly, run_timestamp)
    
    # Define start and end times with timezone
    start_dt = pd.Timestamp('2003-09-29 00:00:00', tz=pytz.UTC)
    end_dt = pd.Timestamp('2019-12-31 23:59:00', tz=pytz.UTC)
    # end_dt = pd.Timestamp('2003-12-31 23:59:00', tz=pytz.UTC)

    # Fetch historical data from csv file
    for s in ['SPY', 'AGG']:
        ohlcv = pd.read_csv(f'./data/{s}.csv', index_col=0, parse_dates=True)
        ohlcv.reset_index(inplace=True)
        ohlcv['Date'] = pd.to_datetime(ohlcv['Date'])
        ohlcv = ohlcv.loc[(ohlcv['Date']>=start_dt.to_datetime64()) & (ohlcv['Date']<=end_dt.to_datetime64())]
        ohlcv.set_index('Date', inplace=True)
        ohlcv.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                    }, inplace=True)
        dataframe = bt.feeds.PandasData(dataname=ohlcv,name=s, plot=False)
        cerebro.adddata(dataframe, name=s)

    # # Set starting cash
    cerebro.broker.set_cash(10000)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    # Add observers for equity curve and drawdown
    cerebro.addobserver(bt.observers.Value)  # Equity curve
    cerebro.addobserver(bt.observers.DrawDown)  # Drawdown

    # cerebro.broker.setcommission(commission=0.001)  # Example: 0.1% fee

    # cerebro.broker.set_slippage_perc(0.001)  # 0.1% slippage

    # cerebro.addsizer(bt.sizers.PercentSizer, percents=10)  # Use 10% of capital per trade

    # # Run backtest
    print(f"Starting Portfolio Value: {cerebro.broker.getvalue()}")
    results = cerebro.run()
    print(f"Ending Portfolio Value: {cerebro.broker.getvalue()}")

    # cerebro.plot()

    strat = results[0]
    pyfoliozer = strat.analyzers.getbyname('pyfolio')
    rets, positions, transactions, glev = pyfoliozer.get_pf_items()
    
    df = get_benchmark('SPY', start_dt, end_dt)
    
    # Convert both indices to timezone-naive
    rets.index = rets.index.tz_localize(None)
    df.index = df.index.tz_localize(None)
    rets, df = rets.align(df, join='inner')  # Align both Series/DataFrame to the same dates


    quantstats.reports.html(rets, benchmark=df, output='stats.html', title='Sixty Forty', match_dates=False)

if __name__ == '__main__':
    main()