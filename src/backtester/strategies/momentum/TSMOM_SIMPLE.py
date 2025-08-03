import backtrader as bt
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class TSMOM_SIMPLE(bt.Strategy):
    """
    Simple Time Series Momentum Strategy using SMA Crossover.
    
    This is a simplified version that only uses:
    - Fast SMA (20 days)
    - Slow SMA (50 days)
    - Simple crossover signals
    - Daily timeframe
    
    Based on the principle that momentum can be captured through trend following.
    """
    
    params = (
        ("fast_period", 20),      # Fast SMA period
        ("slow_period", 50),      # Slow SMA period
        ("commission", 0.001),    # 0.1% commission
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Simple SMA indicators
        self.sma_fast = bt.indicators.SMA(self.dataclose, period=self.p.fast_period)
        self.sma_slow = bt.indicators.SMA(self.dataclose, period=self.p.slow_period)
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def next(self):
        if self.order:
            return

        current_price = self.dataclose[0]
        fast_sma = self.sma_fast[0]
        slow_sma = self.sma_slow[0]
        crossover_signal = self.crossover[0]

        # Log current state
        self.log(f"Price: {current_price:.2f}, Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f}, Signal: {crossover_signal}")

        if not self.position:
            # Entry condition: Fast SMA crosses above Slow SMA (bullish crossover)
            if crossover_signal == 1:  # 1 means fast SMA crossed above slow SMA
                # Calculate position size (use 95% of available cash)
                cash_to_use = self.broker.getcash() * 0.95
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Cash: {cash_to_use:.2f}")
                    self.order = self.buy(size=size)

        else:
            # Exit condition: Fast SMA crosses below Slow SMA (bearish crossover)
            if crossover_signal == -1:  # -1 means fast SMA crossed below slow SMA
                self.log(f"SELL CREATE, Price: {current_price:.2f}")
                self.order = self.sell()
                
            # Re-enter if we have a new bullish crossover
            elif crossover_signal == 1:  # 1 means fast SMA crossed above slow SMA
                # Calculate position size (use 95% of available cash)
                cash_to_use = self.broker.getcash() * 0.95
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY MORE CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Cash: {cash_to_use:.2f}")
                    self.order = self.buy(size=size)

    def stop(self):
        """
        Called at the end of the backtest to print final statistics.
        """
        self.log(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        self.log(f"Total Return: {(self.broker.getvalue() / 10000 - 1) * 100:.2f}%")


class TSMOM_SIMPLE_15MIN(bt.Strategy):
    """
    Simple Time Series Momentum Strategy for 15-minute data.
    
    This version is designed for 15-minute bars:
    - Fast SMA (96 periods = 24 hours)
    - Slow SMA (384 periods = 96 hours = 4 days)
    - Simple crossover signals
    - 15-minute timeframe
    
    Based on the principle that momentum can be captured through trend following.
    """
    
    params = (
        ("fast_period", 96),      # Fast SMA period (24 hours of 15-min bars)
        ("slow_period", 384),     # Slow SMA period (4 days of 15-min bars)
        ("commission", 0.001),    # 0.1% commission
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Simple SMA indicators
        self.sma_fast = bt.indicators.SMA(self.dataclose, period=self.p.fast_period)
        self.sma_slow = bt.indicators.SMA(self.dataclose, period=self.p.slow_period)
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def next(self):
        if self.order:
            return

        current_price = self.dataclose[0]
        fast_sma = self.sma_fast[0]
        slow_sma = self.sma_slow[0]
        crossover_signal = self.crossover[0]

        # Log current state (less frequently to avoid spam)
        if len(self) % 96 == 0:  # Log every 24 hours (96 * 15min)
            self.log(f"Price: {current_price:.2f}, Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f}, Signal: {crossover_signal}")

        if not self.position:
            # Entry condition: Fast SMA crosses above Slow SMA (bullish crossover)
            if crossover_signal == 1:  # 1 means fast SMA crossed above slow SMA
                # Calculate position size (use 95% of available cash)
                cash_to_use = self.broker.getcash() * 0.95
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Cash: {cash_to_use:.2f}")
                    self.order = self.buy(size=size)

        else:
            # Exit condition: Fast SMA crosses below Slow SMA (bearish crossover)
            if crossover_signal == -1:  # -1 means fast SMA crossed below slow SMA
                self.log(f"SELL CREATE, Price: {current_price:.2f}")
                self.order = self.sell()
                
            # Re-enter if we have a new bullish crossover
            elif crossover_signal == 1:  # 1 means fast SMA crossed above slow SMA
                # Calculate position size (use 95% of available cash)
                cash_to_use = self.broker.getcash() * 0.95
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY MORE CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Cash: {cash_to_use:.2f}")
                    self.order = self.buy(size=size)

    def stop(self):
        """
        Called at the end of the backtest to print final statistics.
        """
        self.log(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        self.log(f"Total Return: {(self.broker.getvalue() / 10000 - 1) * 100:.2f}%")


class TSMOM_SIMPLE_DAILY(bt.Strategy):
    """
    Simple Time Series Momentum Strategy for Daily data.
    
    This version is designed for daily bars:
    - Fast SMA (20 days)
    - Slow SMA (50 days)
    - Simple crossover signals
    - Daily timeframe
    
    Based on the principle that momentum can be captured through trend following.
    """
    
    params = (
        ("fast_period", 20),      # Fast SMA period (20 days)
        ("slow_period", 50),      # Slow SMA period (50 days)
        ("commission", 0.001),    # 0.1% commission
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Simple SMA indicators
        self.sma_fast = bt.indicators.SMA(self.dataclose, period=self.p.fast_period)
        self.sma_slow = bt.indicators.SMA(self.dataclose, period=self.p.slow_period)
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def next(self):
        if self.order:
            return

        current_price = self.dataclose[0]
        fast_sma = self.sma_fast[0]
        slow_sma = self.sma_slow[0]
        crossover_signal = self.crossover[0]

        # Log current state (less frequently for daily data)
        if len(self) % 5 == 0:  # Log every 5 days
            self.log(f"Price: {current_price:.2f}, Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f}, Signal: {crossover_signal}")

        if not self.position:
            # Entry condition: Fast SMA crosses above Slow SMA (bullish crossover)
            if crossover_signal == 1:  # 1 means fast SMA crossed above slow SMA
                # Calculate position size (use 95% of available cash)
                cash_to_use = self.broker.getcash() * 0.95
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Cash: {cash_to_use:.2f}")
                    self.order = self.buy(size=size)

        else:
            # Exit condition: Fast SMA crosses below Slow SMA (bearish crossover)
            if crossover_signal == -1:  # -1 means fast SMA crossed below slow SMA
                self.log(f"SELL CREATE, Price: {current_price:.2f}")
                self.order = self.sell()
                
            # Re-enter if we have a new bullish crossover
            elif crossover_signal == 1:  # 1 means fast SMA crossed above slow SMA
                # Calculate position size (use 95% of available cash)
                cash_to_use = self.broker.getcash() * 0.95
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY MORE CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Cash: {cash_to_use:.2f}")
                    self.order = self.buy(size=size)

    def stop(self):
        """
        Called at the end of the backtest to print final statistics.
        """
        self.log(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        self.log(f"Total Return: {(self.broker.getvalue() / 10000 - 1) * 100:.2f}%")


class TSMOM_SIMPLE_IMPROVED(bt.Strategy):
    """
    Improved Simple TSMOM Strategy with additional filters.
    
    This version adds:
    - Volume confirmation
    - Price above/below SMA filter
    - Position sizing based on volatility
    """
    
    params = (
        ("fast_period", 20),      # Fast SMA period
        ("slow_period", 50),      # Slow SMA period
        ("commission", 0.001),    # 0.1% commission
        ("use_volume", True),     # Use volume confirmation
        ("use_price_filter", True), # Use price above/below SMA filter
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datavolume = self.datas[0].volume
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # SMA indicators
        self.sma_fast = bt.indicators.SMA(self.dataclose, period=self.p.fast_period)
        self.sma_slow = bt.indicators.SMA(self.dataclose, period=self.p.slow_period)
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # Volume indicator (if enabled)
        if self.p.use_volume:
            self.volume_sma = bt.indicators.SMA(self.datavolume, period=20)
        
        # Volatility for position sizing
        self.volatility = bt.indicators.StdDev(self.dataclose, period=20)
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")

    def next(self):
        if self.order:
            return

        # Check if we have enough data
        if len(self.dataclose) < self.p.slow_period:
            return

        current_price = self.dataclose[0]
        fast_sma = self.sma_fast[0]
        slow_sma = self.sma_slow[0]
        crossover_signal = self.crossover[0]

        # Additional filters
        volume_ok = True
        if self.p.use_volume and len(self.volume_sma) > 0:
            current_volume = self.datavolume[0]
            avg_volume = self.volume_sma[0]
            volume_ok = current_volume > avg_volume * 0.8  # Volume above 80% of average

        price_filter_ok = True
        if self.p.use_price_filter:
            if crossover_signal == 1:  # Bullish crossover
                price_filter_ok = current_price > slow_sma  # Price above slow SMA
            elif crossover_signal == -1:  # Bearish crossover
                price_filter_ok = current_price < slow_sma  # Price below slow SMA

        # Log current state
        self.log(f"Price: {current_price:.2f}, Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f}, Signal: {crossover_signal}, Volume OK: {volume_ok}, Price Filter OK: {price_filter_ok}")

        if not self.position:
            # Entry condition: Bullish crossover with filters
            if (crossover_signal == 1 and volume_ok and price_filter_ok):
                # Calculate position size based on volatility
                volatility = self.volatility[0] if len(self.volatility) > 0 else 0.01
                position_size = min(1.0, 0.02 / max(volatility, 0.01))  # Inverse volatility sizing
                
                cash_to_use = self.broker.getcash() * position_size
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Position Size: {position_size:.2%}")
                    self.order = self.buy(size=size)

        else:
            # Exit condition: Bearish crossover
            if crossover_signal == -1:
                self.log(f"SELL CREATE, Price: {current_price:.2f}")
                self.order = self.sell()

    def stop(self):
        """
        Called at the end of the backtest to print final statistics.
        """
        self.log(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        self.log(f"Total Return: {(self.broker.getvalue() / 10000 - 1) * 100:.2f}%") 