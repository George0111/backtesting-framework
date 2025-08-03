import backtrader as bt
from ...utils import IsLastBusinessDayOfMonth

# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class TAA_Momentum(bt.Strategy):
    """
    A Tactical Asset Allocation (TAA) strategy based on momentum.

    This strategy rebalances at the end of each month, investing in the
    top N assets with the highest momentum (rate of change) over a
    specified lookback period.
    """
    params = dict(
        mom_lookback=126,
        mom_top_n=3,
        reserve=0.01,  # Percentage of capital to keep in reserve
    )

    def __init__(self):
        self.universe = []
        self.is_last_business_day = IsLastBusinessDayOfMonth()
        self.weight = (1.0 / self.p.mom_top_n) * (1.0 - self.p.reserve)
        self.returns = {}
        self.ranks = {}

        self.add_timer(
            when=bt.Timer.SESSION_START,
            weekdays=[],
            allow=self.is_last_business_day,
            monthcarry=True,
        )

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

    def rebalance_portfolio(self):
        # 1. Calculate momentum for all assets in the universe
        for d in self.universe:
            if len(d) >= self.p.mom_lookback:
                dperiod = d.close[-self.p.mom_lookback]
                roc = (d.close[0] - dperiod) / dperiod
                self.returns[d] = roc

        if not self.returns:
            return # Not enough data to rank anything

        # 2. Rank assets by momentum
        sorted_returns = {k: v for k, v in sorted(self.returns.items(), key=lambda item: item[1], reverse=True)}
        
        # 3. Identify the top N assets to hold
        top_n = list(sorted_returns.keys())[:self.p.mom_top_n]
        
        # 4. Exit positions not in the top N
        positions_to_exit = [d for d, pos in self.getpositions().items() if pos and d not in top_n]
        for d in positions_to_exit:
            self.order_target_percent(d, target=0.0)

        # 5. Enter or rebalance positions for the top N assets
        for d in top_n:
            self.order_target_percent(d, target=self.weight)
            
        # Clear returns for the next rebalance period
        self.returns.clear()
