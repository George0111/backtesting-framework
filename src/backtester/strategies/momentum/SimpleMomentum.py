import backtrader as bt
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class SimpleMomentum(bt.Strategy):
    """
    Simple Momentum Strategy based on academic research findings.
    
    Key Research Insights Incorporated:
    1. Jegadeesh & Titman (1993): 3-12 month momentum effects
    2. Moskowitz et al. (2012): Time series momentum across asset classes
    3. Asness et al. (2013): Cross-sectional momentum
    4. Novy-Marx (2012): Focus on 6-12 month returns, avoid recent 1 month
    5. Goyal & Welch (2008): Momentum as reliable predictor
    
    Strategy Features:
    - 12-month lookback period (optimal from research)
    - Avoid 1-month reversal (Novy-Marx finding)
    - Volatility-adjusted position sizing
    - Simple trend filter
    - Risk management with stop losses
    """
    
    params = (
        ("lookback_period", 252),     # 12 months (252 trading days)
        ("skip_recent", 21),          # Skip recent 1 month (21 trading days)
        ("momentum_threshold", 0.05), # 5% minimum momentum
        ("max_position_size", 0.25),  # Max 25% per position
        ("stop_loss", 0.10),          # 10% stop loss
        ("take_profit", 0.30),        # 30% take profit
        ("commission", 0.001),        # 0.1% commission
        ("vol_lookback", 60),         # 60 days for volatility calculation
        ("trend_period", 50),         # 50-day SMA for trend filter
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

        # Momentum calculation based on research
        # Use 12-month return minus 1-month return (Novy-Marx finding)
        self.momentum_12m = self.dataclose / self.dataclose(-self.p.lookback_period) - 1
        self.momentum_1m = self.dataclose / self.dataclose(-self.p.skip_recent) - 1
        self.momentum = self.momentum_12m - self.momentum_1m  # Intermediate-term momentum
        
        # Volatility calculation for position sizing
        self.volatility = bt.indicators.StdDev(self.dataclose, period=self.p.vol_lookback)
        
        # Trend filter (50-day SMA)
        self.sma_trend = bt.indicators.SMA(self.dataclose, period=self.p.trend_period)
        
        # Risk management
        self.peak_value = self.broker.getvalue()
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def calculate_position_size(self, momentum, volatility):
        """
        Calculate position size based on momentum strength and volatility.
        Based on research showing momentum works better with volatility adjustment.
        """
        # Base position size from momentum strength
        momentum_score = abs(momentum) / max(volatility, 0.01)
        
        # Scale by momentum threshold
        if abs(momentum) < self.p.momentum_threshold:
            return 0.0
        
        # Cap at max position size
        position_size = min(
            self.p.max_position_size,
            momentum_score * 0.1  # Scale factor
        )
        
        return position_size

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed = len(self)
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}")
                if self.position.size <= 0:
                    self.bar_executed = 0

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
        if len(self.dataclose) < self.p.lookback_period:
            return

        available_cash = self.broker.getcash()
        current_price = self.dataclose[0]

        # Get indicators
        momentum_12m = self.momentum_12m[0] if len(self.momentum_12m) > 0 else 0.0
        momentum_1m = self.momentum_1m[0] if len(self.momentum_1m) > 0 else 0.0
        momentum = momentum_12m - momentum_1m  # Intermediate-term momentum
        volatility = self.volatility[0] if len(self.volatility) > 0 else 0.01
        trend_up = current_price > self.sma_trend[0] if len(self.sma_trend) > 0 else False

        # Log indicators
        self.log(f"12M: {momentum_12m:.4f}, 1M: {momentum_1m:.4f}, Momentum: {momentum:.4f}, Vol: {volatility:.4f}, Trend: {'UP' if trend_up else 'DOWN'}")

        if not self.position:
            # Entry conditions based on research
            if (momentum > self.p.momentum_threshold and  # Positive momentum
                trend_up and                              # Price above trend
                momentum_12m > 0):                        # Overall positive 12-month return
                
                # Calculate position size
                position_size = self.calculate_position_size(momentum, volatility)
                
                if position_size > 0:
                    cash_to_use = available_cash * position_size
                    size = cash_to_use / current_price
                    
                    if size > 0:
                        self.log(f"BUY CREATE, Price: {current_price:.2f}, Size: {size:.4f}, Position Size: {position_size:.2%}")
                        self.order = self.buy(size=size)

        else:
            # Exit conditions
            current_position = self.position.size if self.position else 0.0
            
            # Stop loss
            if current_price <= self.buyprice * (1 - self.p.stop_loss):
                self.log(f"STOP LOSS TRIGGERED, {current_price:.2f}")
                self.order = self.sell(size=current_position)
            
            # Take profit
            elif current_price >= self.buyprice * (1 + self.p.take_profit):
                self.log(f"TAKE PROFIT TRIGGERED, {current_price:.2f}")
                self.order = self.sell(size=current_position)
            
            # Momentum reversal (Novy-Marx finding)
            elif momentum < -self.p.momentum_threshold:
                self.log(f"MOMENTUM REVERSAL, {current_price:.2f}")
                self.order = self.sell(size=current_position)
            
            # Trend reversal
            elif not trend_up:
                self.log(f"TREND REVERSAL, {current_price:.2f}")
                self.order = self.sell(size=current_position)
            
            # Holding period (12 months)
            elif len(self) >= (self.bar_executed + self.p.lookback_period):
                self.log(f"HOLDING PERIOD OVER, {current_price:.2f}")
                self.order = self.sell(size=current_position)

    def stop(self):
        """
        Called at the end of the backtest to print final statistics.
        """
        self.log(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        self.log(f"Total Return: {(self.broker.getvalue() / 10000 - 1) * 100:.2f}%")
        
        # Calculate drawdown
        portfolio_value = self.broker.getvalue()
        drawdown = (self.peak_value - portfolio_value) / self.peak_value if self.peak_value > portfolio_value else 0
        self.log(f"Max Drawdown: {drawdown:.2%}")


class CrossSectionalMomentum(bt.Strategy):
    """
    Cross-Sectional Momentum Strategy based on Asness et al. (2013).
    
    This strategy ranks multiple assets by their momentum and invests in the top performers.
    Key features:
    - Ranks assets by 12-month momentum
    - Invests in top N assets
    - Equal-weighted or momentum-weighted positions
    - Rebalances monthly
    """
    
    params = (
        ("lookback_period", 252),     # 12 months
        ("top_n", 3),                 # Number of top assets to hold
        ("rebalance_freq", 21),       # Rebalance every 21 days (monthly)
        ("equal_weight", True),       # Equal weight vs momentum weight
        ("commission", 0.001),        # 0.1% commission
        ("log_to_terminal", True),    # Whether to print logs
    )

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if getattr(self.p, 'log_to_terminal', True):
            print(f"{dt.isoformat()} {txt}")

    def __init__(self):
        self.order = None
        self.rebalance_counter = 0
        self.momentum_scores = {}
        
        # Calculate momentum for each asset
        for data in self.datas:
            self.momentum_scores[data] = data.close / data.close(-self.p.lookback_period) - 1
        
        # Set commission
        self.broker.setcommission(commission=self.p.commission)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}")
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"Order Canceled/Margin/Rejected")

        self.order = None

    def next(self):
        if self.order:
            return

        # Check if we have enough data
        if len(self.datas[0]) < self.p.lookback_period:
            return

        # Rebalance counter
        self.rebalance_counter += 1
        
        if self.rebalance_counter >= self.p.rebalance_freq:
            self.rebalance_portfolio()
            self.rebalance_counter = 0

    def rebalance_portfolio(self):
        """
        Rebalance portfolio based on momentum rankings.
        """
        # Calculate current momentum scores
        current_momentum = {}
        for data in self.datas:
            if len(data) >= self.p.lookback_period:
                momentum = data.close[0] / data.close[-self.p.lookback_period] - 1
                current_momentum[data] = momentum

        if not current_momentum:
            return

        # Rank assets by momentum
        ranked_assets = sorted(current_momentum.items(), key=lambda x: x[1], reverse=True)
        
        # Get top N assets
        top_assets = ranked_assets[:self.p.top_n]
        
        self.log(f"Top {self.p.top_n} assets by momentum:")
        for asset, momentum in top_assets:
            self.log(f"  {asset._name}: {momentum:.4f}")

        # Calculate position sizes
        if self.p.equal_weight:
            position_size = 1.0 / self.p.top_n
        else:
            # Momentum-weighted (proportional to momentum strength)
            total_momentum = sum(max(0, momentum) for _, momentum in top_assets)
            if total_momentum > 0:
                position_sizes = {asset: max(0, momentum) / total_momentum for asset, momentum in top_assets}
            else:
                position_sizes = {asset: 1.0 / self.p.top_n for asset, _ in top_assets}

        # Close positions not in top N
        for data in self.datas:
            if data not in [asset for asset, _ in top_assets]:
                if self.getposition(data).size > 0:
                    self.order_target_percent(data, 0.0)

        # Set target positions for top N assets
        for asset, momentum in top_assets:
            if self.p.equal_weight:
                target_size = 1.0 / self.p.top_n
            else:
                target_size = position_sizes.get(asset, 0.0)
            
            self.order_target_percent(asset, target_size * 100)  # Convert to percentage

    def stop(self):
        """
        Called at the end of the backtest to print final statistics.
        """
        self.log(f"Final Portfolio Value: {self.broker.getvalue():.2f}")
        self.log(f"Total Return: {(self.broker.getvalue() / 10000 - 1) * 100:.2f}%") 