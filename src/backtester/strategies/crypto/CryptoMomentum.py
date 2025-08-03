import backtrader as bt
from ...utils import IsLastBusinessDayOfMonth
import datetime
import numpy as np

# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class CryptoMomentum(bt.Strategy):
    """
    A Cryptocurrency Momentum strategy based on rate of change.

    This strategy can rebalance at various frequencies (daily, weekly, monthly),
    investing in the top N cryptocurrencies with the highest momentum (rate of change)
    over a specified lookback period. Works with intraday data (e.g., 15-minute bars).
    """
    params = dict(
        mom_lookback=90,  # Lookback period for momentum calculation (in days)
        mom_top_n=5,      # Number of top assets to invest in
        reserve=0.05,     # Percentage of capital to keep in reserve (increased from 0.01)
        min_liquidity=0,  # Minimum trading volume to include in the universe
        rebalance_period='daily',  # Rebalancing frequency: 'daily', 'weekly', 'monthly'
        rebalance_time=0,  # Hour of day for rebalancing (0-23, 0 = midnight UTC)
        bars_per_day=96,  # Number of 15-minute bars per day (24 hours * 4 bars per hour)
        commission=0.001,  # Binance trading fee (0.1% for regular users)
        vol_lookback=20,  # Lookback period for volatility calculation (in days)
        max_pos_size=0.33,  # Maximum position size for any single asset (33% of portfolio)
        risk_factor=0.15,  # Target portfolio volatility (15% annualized)
    )

    def __init__(self):
        self.universe = []
        self.is_last_business_day = IsLastBusinessDayOfMonth()
        self.weight = (1.0 / self.p.mom_top_n) * (1.0 - self.p.reserve)
        self.returns = {}
        self.last_rebalance_date = None
        self.order_dict = {}  # Track open orders
        
        # For intraday data, we need to track the current day
        self.current_day = None
        
        # Calculate lookback in terms of bars for intraday data
        # For 15-minute data, each day has 96 bars (24 hours * 4 bars per hour)
        self.lookback_bars = self.p.mom_lookback * self.p.bars_per_day
        self.vol_lookback_bars = self.p.vol_lookback * self.p.bars_per_day
        
        # Set the commission for each data feed (Binance trading fee)
        self.broker.setcommission(commission=self.p.commission)  # Apply to all assets

    def should_rebalance(self, current_datetime):
        """
        Determines if rebalancing should occur based on the specified period.
        Handles intraday data by checking for day changes.
        
        Args:
            current_datetime: Current datetime from the strategy
            
        Returns:
            bool: True if rebalancing should occur, False otherwise
        """
        current_date = current_datetime.date()
        current_hour = current_datetime.hour
        
        # First run - always rebalance
        if self.last_rebalance_date is None:
            return True
            
        if self.p.rebalance_period == 'daily':
            # For daily rebalancing with intraday data:
            # 1. Check if the date has changed
            # 2. Check if we're at the specified rebalance hour
            if current_date != self.current_day:
                # New day detected
                self.current_day = current_date
                # Rebalance at the specified hour (default is midnight UTC)
                return current_hour == self.p.rebalance_time
            return False
            
        elif self.p.rebalance_period == 'weekly':
            # Rebalance on specified weekday at the specified hour
            if current_date.weekday() == 0 and current_hour == self.p.rebalance_time:  # Monday
                # Only rebalance once per week by checking the last rebalance date
                if self.last_rebalance_date is None or current_date > self.last_rebalance_date:
                    return True
            return False
            
        elif self.p.rebalance_period == 'monthly':
            # Rebalance on the last business day of the month at the specified hour
            if self.is_last_business_day(current_date) and current_hour == self.p.rebalance_time:
                # Only rebalance once per month by checking the last rebalance date
                if self.last_rebalance_date is None or current_date > self.last_rebalance_date:
                    return True
            return False
            
        elif self.p.rebalance_period.isdigit():
            # Rebalance every N days at the specified hour
            if current_hour == self.p.rebalance_time:
                days_since_last = (current_date - self.last_rebalance_date).days
                return days_since_last >= int(self.p.rebalance_period)
        
        return False

    def calculate_volatility(self, data):
        """
        Calculate the volatility of a data series.
        
        Args:
            data: The data series to calculate volatility for
            
        Returns:
            float: The volatility (standard deviation of returns)
        """
        if len(data) < self.vol_lookback_bars:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, min(len(data), self.vol_lookback_bars + 1)):
            if data[-i] != 0:
                ret = (data[-i] - data[-i-1]) / data[-i-1]
                returns.append(ret)
        
        if len(returns) < 2:
            return 0.0
        
        return np.std(returns)

    def calculate_position_sizes(self, top_assets):
        """
        Calculate position sizes based on volatility targeting.
        
        Args:
            top_assets: List of top assets to invest in
            
        Returns:
            dict: Dictionary mapping assets to position sizes
        """
        position_sizes = {}
        total_weight = 0.0
        
        for asset in top_assets:
            # Calculate volatility for this asset
            volatility = self.calculate_volatility(asset.close)
            
            # Inverse volatility weighting (lower volatility = higher weight)
            if volatility > 0:
                weight = 1.0 / volatility
            else:
                weight = 1.0
            
            position_sizes[asset] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            for asset in position_sizes:
                position_sizes[asset] = (position_sizes[asset] / total_weight) * (1.0 - self.p.reserve)
        
        return position_sizes

    def rebalance_portfolio(self):
        """
        Rebalance the portfolio based on momentum signals.
        """
        # 1. Calculate momentum for all assets in the universe
        for d in self.universe:
            if len(d) >= self.lookback_bars:
                dperiod = d.close[-self.lookback_bars]
                roc = (d.close[0] - dperiod) / dperiod
                self.returns[d] = roc

        if not self.returns:
            return # Not enough data to rank anything

        # 2. Rank assets by momentum
        sorted_returns = {k: v for k, v in sorted(self.returns.items(), key=lambda item: item[1], reverse=True)}
        
        # 3. Identify the top N assets to hold
        top_n = list(sorted_returns.keys())[:self.p.mom_top_n]
        
        # 4. Calculate position sizes based on volatility
        position_sizes = self.calculate_position_sizes(top_n)
        
        # 5. Exit positions not in the top N
        positions_to_exit = [d for d, pos in self.getpositions().items() if pos and d not in top_n]
        for d in positions_to_exit:
            self.order_target_percent(d, target=0.0)

        # 6. Enter or rebalance positions for the top N assets
        for d in top_n:
            target_weight = position_sizes.get(d, 0.0)
            self.order_target_percent(d, target=target_weight)
            
        # Update last rebalance date
        self.last_rebalance_date = self.current_day
        
        # Clear returns for the next rebalance period
        self.returns.clear()

    def prenext(self):
        self.universe = [d for d in self.datas if len(d)]
        self.next()

    def nextstart(self):
        self.universe = self.datas
        self.next()

    def next(self):
        # This is the main trading logic, but in this strategy,
        # all rebalancing happens on a timer.
        pass

    def notify_timer(self, timer, when, *args, **kwargs):
        """
        This method is called when the monthly timer triggers the rebalance.
        """
        self.rebalance_portfolio()

    def notify_order(self, order):
        """
        Handle order notifications.
        """
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def log(self, txt, dt=None):
        """
        Logging function for the strategy.
        """
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

class CryptoMomentumEqual(bt.Strategy):
    """
    A simplified Cryptocurrency Momentum strategy with equal weighting.
    
    This strategy selects the top N cryptocurrencies based on momentum,
    but allocates equal weight to each position instead of using volatility-based sizing.
    """
    params = dict(
        mom_lookback=90,  # Lookback period for momentum calculation (in days)
        mom_top_n=5,      # Number of top assets to invest in
        reserve=0.05,     # Percentage of capital to keep in reserve
        rebalance_period='daily',  # Rebalancing frequency
        rebalance_time=0,  # Hour of day for rebalancing
        bars_per_day=96,  # Number of 15-minute bars per day
        commission=0.001,  # Trading fee
    )

    def __init__(self):
        self.universe = []
        self.is_last_business_day = IsLastBusinessDayOfMonth()
        self.weight = (1.0 / self.p.mom_top_n) * (1.0 - self.p.reserve)
        self.returns = {}
        self.last_rebalance_date = None
        self.current_day = None
        
        # Calculate lookback in terms of bars
        self.lookback_bars = self.p.mom_lookback * self.p.bars_per_day
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def should_rebalance(self, current_datetime):
        """
        Determines if rebalancing should occur.
        """
        current_date = current_datetime.date()
        current_hour = current_datetime.hour
        
        if self.last_rebalance_date is None:
            return True
            
        if self.p.rebalance_period == 'daily':
            if current_date != self.current_day:
                self.current_day = current_date
                return current_hour == self.p.rebalance_time
            return False
        
        return False

    def rebalance_portfolio(self):
        """
        Rebalance the portfolio with equal weighting.
        """
        # Calculate momentum for all assets
        for d in self.universe:
            if len(d) >= self.lookback_bars:
                dperiod = d.close[-self.lookback_bars]
                roc = (d.close[0] - dperiod) / dperiod
                self.returns[d] = roc

        if not self.returns:
            return

        # Rank assets by momentum
        sorted_returns = {k: v for k, v in sorted(self.returns.items(), key=lambda item: item[1], reverse=True)}
        
        # Get top N assets
        top_n = list(sorted_returns.keys())[:self.p.mom_top_n]
        
        # Exit positions not in top N
        positions_to_exit = [d for d, pos in self.getpositions().items() if pos and d not in top_n]
        for d in positions_to_exit:
            self.order_target_percent(d, target=0.0)

        # Equal weight allocation
        for d in top_n:
            self.order_target_percent(d, target=self.weight)
            
        self.last_rebalance_date = self.current_day
        self.returns.clear()

    def prenext(self):
        self.universe = [d for d in self.datas if len(d)]
        self.next()

    def nextstart(self):
        self.universe = self.datas
        self.next()

    def next(self):
        # All trading happens on timer
        pass

    def notify_timer(self, timer, when, *args, **kwargs):
        self.rebalance_portfolio()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

class CryptoTSMomentum(bt.Strategy):
    """
    Improved Time Series Momentum strategy for cryptocurrency trading.
    
    This strategy addresses the issues found in the original implementation:
    - Excessive trading frequency
    - Poor risk management
    - Lack of proper signal filtering
    - No volatility-based position sizing
    """
    params = (
        ("lookback_period", 96),      # 24 hours (96 * 15min bars)
        ("momentum_threshold", 0.01), # 1% minimum momentum for entry (more realistic)
        ("vol_lookback", 24),         # 6 hours for volatility calculation (shorter period)
        ("max_position_size", 0.3),   # Max 30% per position
        ("stop_loss", 0.05),          # 5% stop loss
        ("take_profit", 0.15),        # 15% take profit
        ("commission", 0.001),        # 0.1% commission
        ("max_daily_trades", 5),      # Max 5 trades per day
        ("log_to_terminal", True),    # Whether to print logs
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if getattr(self.p, 'log_to_terminal', True):
            print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.bar_executed = 0

        # Improved momentum calculation
        self.momentum = self.dataclose / self.dataclose(-self.p.lookback_period) - 1
        
        # Volatility calculation for position sizing (but not for entry filter)
        self.volatility = bt.indicators.StdDev(self.dataclose, period=self.p.vol_lookback)
        
        # Trend filters - using longer periods for more stable signals
        self.sma_fast = bt.indicators.SMA(self.dataclose, period=48)  # 12 hours
        self.sma_slow = bt.indicators.SMA(self.dataclose, period=192)  # 48 hours
        
        # Risk management
        self.daily_trades = 0
        self.last_trade_date = None
        self.peak_value = self.broker.getvalue()
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def check_risk_limits(self):
        """
        Check various risk management limits.
        """
        current_date = self.datas[0].datetime.date(0)
        
        # Reset daily trade counter
        if self.last_trade_date != current_date:
            self.daily_trades = 0
            self.last_trade_date = current_date
        
        # Check daily trade limit
        if self.daily_trades >= self.p.max_daily_trades:
            return False
        
        # Check drawdown
        portfolio_value = self.broker.getvalue()
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        
        drawdown = (self.peak_value - portfolio_value) / self.peak_value
        if drawdown > 0.15:  # 15% max drawdown
            return False
        
        return True

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        current_position = self.position.size if self.position else 0.0
        available_cash = self.broker.getcash()

        if order.status in [order.Completed]:
            self.daily_trades += 1
            
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size:.4f}, Position After: {current_position:.4f}, Cash: {available_cash:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed = len(self)
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, Size: {order.executed.size:.4f}, Position After: {current_position:.4f}, Cash: {available_cash:.2f}")
                if current_position <= 0:
                    self.bar_executed = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            order_type = 'BUY' if order.isbuy() else 'SELL'
            self.log(f"Order Canceled/Margin/Rejected - Type: {order_type}, Position: {current_position:.4f}, Cash: {available_cash:.2f}")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        current_position = self.position.size if self.position else 0.0
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}, Position After Trade: {current_position:.4f}")

    def next(self):
        if self.order:
            return

        # Check risk limits
        if not self.check_risk_limits():
            return

        available_cash = self.broker.getcash()
        current_price = self.dataclose[0]

        # Get indicators
        momentum = self.momentum[0] if len(self.momentum) > 0 else 0.0
        volatility = self.volatility[0] if len(self.volatility) > 0 else 0.01
        trend_up = (self.sma_fast[0] > self.sma_slow[0] if len(self.sma_fast) > 0 and len(self.sma_slow) > 0 else False)

        # Log indicators for debugging
        self.log(f"Momentum: {momentum:.4f}, Volatility: {volatility:.4f}, Trend: {'UP' if trend_up else 'DOWN'}, Price: {current_price:.2f}")

        if not self.position:
            # Entry conditions: positive momentum and trend up (removed volatility filter)
            if (momentum > self.p.momentum_threshold and trend_up):
                
                # Position sizing based on volatility and risk limits
                position_size = min(
                    self.p.max_position_size,
                    0.02 / max(volatility, 0.01)  # Inverse volatility sizing
                )
                
                cash_to_use = available_cash * position_size
                size = cash_to_use / current_price
                
                if size > 0:
                    self.log(f"BUY CREATE, Price: {current_price:.2f}, Available Cash: {available_cash:.2f}, Size: {size:.4f}")
                    self.order = self.buy(size=size)
                else:
                    self.log(f"BUY CREATE FAILED, Price: {current_price:.2f}, Insufficient Cash: {available_cash:.2f}")

        else:
            # Exit conditions
            current_position = self.position.size if self.position else 0.0
            if current_position <= 0:
                self.log(f"WARNING: Sell attempted with no position! Position: {current_position:.4f}")
            else:
                # Stop loss
                if current_price <= self.buyprice * (1 - self.p.stop_loss):
                    self.log(f"STOP LOSS TRIGGERED, {current_price:.2f}, Position: {current_position:.4f}")
                    self.order = self.sell(size=current_position)
                # Take profit
                elif current_price >= self.buyprice * (1 + self.p.take_profit):
                    self.log(f"TAKE PROFIT TRIGGERED, {current_price:.2f}, Position: {current_position:.4f}")
                    self.order = self.sell(size=current_position)
                # Momentum reversal
                elif momentum < -self.p.momentum_threshold:
                    self.log(f"MOMENTUM REVERSAL, {current_price:.2f}, Position: {current_position:.4f}")
                    self.order = self.sell(size=current_position)
                # Trend reversal
                elif not trend_up:
                    self.log(f"TREND REVERSAL, {current_price:.2f}, Position: {current_position:.4f}")
                    self.order = self.sell(size=current_position)
                # Holding period
                elif len(self) >= (self.bar_executed + self.p.lookback_period):
                    self.log(f"HOLDING PERIOD OVER, {current_price:.2f}, Position: {current_position:.4f}")
                    self.order = self.sell(size=current_position)
