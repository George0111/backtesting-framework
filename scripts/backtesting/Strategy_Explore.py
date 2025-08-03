import backtrader as bt
import backtrader.indicators as btind
import os
import configparser



class BaseStrategy(bt.Strategy):
    params = (
        ('verbose', False),  # Add a parameter to control logging
    )
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.OUTPUT_DIR = config['General']['OUTPUT_DIR']
        self.pnl_history = []  # To store PnL for each bar
        # Log file initialization
        self.log_file = os.path.join(self.OUTPUT_DIR, 'backtest_logs.log')

    def log(self, txt, dt=None):
            """ Logging function """
            dt = dt or self.datas[0].datetime.datetime(0)
            log_entry = f'{dt.isoformat()} {txt}'
            with open(self.log_file, 'a') as f:
                f.write(log_entry + '\n')
            if self.params.verbose:
                print(log_entry)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}")
            elif order.issell():
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, , PnL={self.broker.getvalue() - 10000}")
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            
    def next(self):
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        pnl = value - 10000  # Assuming starting cash is 10,000
        self.pnl_history.append(pnl)  # Append to PnL history for plotting
        

class RSIMomentumStrategy(BaseStrategy):
    params = (
        ('rsi_period', 14),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
        ('cooldown_period', 10),  # Minimum bars between trades
        ('risk_per_trade', 0.02),  # 2% risk per trade
        ('stop_loss_pct', 0.03),  # 3% stop-loss
        ('profit_target_pct', 0.05),  # 5% profit target
    )

    def __init__(self):
        super().__init__()
        self.rsi = btind.RSI_SMA(period=self.p.rsi_period)
        self.last_trade_time = None  # Keep track of the last trade's time index

    def next(self):
        super().next()
        portfolio_value = self.broker.getvalue()
        risk_amount = portfolio_value * self.p.risk_per_trade
        current_price = self.data.close[0]
        size = risk_amount / current_price  # Position size based on risk amount and current price

        if not self.position:
            # Entry Logic with Cooldown
            if self.last_trade_time is None or len(self) - self.last_trade_time > self.p.cooldown_period:
                if self.rsi[0] < self.p.rsi_oversold:
                    self.buy(size=size)
                    self.stop_price = current_price * (1 - self.p.stop_loss_pct)
                    self.take_profit_price = current_price * (1 + self.p.profit_target_pct)
                    self.last_trade_time = len(self)
                elif self.rsi[0] > self.p.rsi_overbought:
                    self.sell(size=size)
                    self.stop_price = current_price * (1 + self.p.stop_loss_pct)
                    self.take_profit_price = current_price * (1 - self.p.profit_target_pct)
                    self.last_trade_time = len(self)
        else:
            # Exit Logic: Stop Loss or Profit Target
            if self.position.size > 0:  # Long position
                if self.data.low[0] < self.stop_price or self.data.high[0] > self.take_profit_price:
                    self.sell(size=self.position.size)
            elif self.position.size < 0:  # Short position
                if self.data.high[0] > self.stop_price or self.data.low[0] < self.take_profit_price:
                    self.buy(size=-self.position.size)