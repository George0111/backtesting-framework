import backtrader as bt
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import math
import matplotlib.pyplot as plt

class MedallionPairsStrategy(bt.Strategy):
    params = dict(
        lookback=60,
        entry_z=2.0,
        exit_z=0.5,
        max_hold_days=10,
        max_positions=3,
        position_size=0.15,
        max_drawdown=0.15,
        use_adaptive=True,
        vol_window=21,
        regime_window=50,
        use_kalman=True,
        use_half_life=True,
        min_half_life=5,
        max_half_life=30,
        commission=0.0005,
        slippage=0.0002,
        log_level=2
    )

    def __init__(self):
        self.asset1 = self.datas[0].close
        self.asset2 = self.datas[1].close
        self.holding_days = {}
        self.entry_prices = {}
        self.active_pairs = 0
        self.hedge_ratio = None
        self.spread = None
        self.z_score = None
        self.half_life = None
        self.kalman_state = {'x': 0, 'P': 1, 'Q': 0.01, 'R': 0.1}
        self.initial_capital = self.broker.getvalue()
        self.peak_value = self.initial_capital
        self.drawdown_lock = False
        self.trades_total = 0
        self.trades_won = 0
        self.total_return = 0
        self.zscore_history = []
        self.entry_points = []
        self.exit_points = []
        self.spreads = []
        self.price_history1 = []
        self.price_history2 = []
        self.adjusted_entry_z = self.p.entry_z
        self.adjusted_exit_z = self.p.exit_z
        self.entry_spread = {}  # <-- Add this line

        # Use bt.indicators for rolling mean and std
        self.spread_series = self.datas[0] - self.datas[1]
        self.spread_mean = bt.indicators.SimpleMovingAverage(self.spread_series, period=self.p.lookback)
        self.spread_std = bt.indicators.StandardDeviation(self.spread_series, period=self.p.lookback)

    def log(self, txt, level=1):
        if self.p.log_level >= level:
            dt = self.datas[0].datetime.date()
            print(f'{dt.isoformat()}: {txt}')

    def calculate_hedge_ratio(self):
        if len(self.price_history1) < self.p.lookback:
            return None
        if self.p.use_kalman:
            x, P, Q, R = self.kalman_state['x'], self.kalman_state['P'], self.kalman_state['Q'], self.kalman_state['R']
            x_pred, P_pred = x, P + Q
            K = P_pred / (P_pred + R)
            x = x_pred + K * (self.asset1[0] - x_pred * self.asset2[0])
            P = (1 - K) * P_pred
            self.kalman_state['x'], self.kalman_state['P'] = x, P
            return x
        y = np.array(self.price_history1)
        x = sm.add_constant(np.array(self.price_history2))
        return sm.OLS(y, x).fit().params[1]

    def calculate_spread(self, hedge_ratio):
        return self.asset1[0] - hedge_ratio * self.asset2[0] if hedge_ratio is not None else None

    def calculate_z_score(self, spread):
        if spread is None:
            return None
        self.spreads.append(spread)
        if len(self.spreads) > self.p.lookback:
            self.spreads.pop(0)
        if len(self.spreads) < 20:
            return None
        mean, std = np.mean(self.spreads), np.std(self.spreads)
        return (spread - mean) / std if std != 0 else 0

    def calculate_half_life(self):
        if len(self.spreads) < 20:
            return None
        spreads = np.array(self.spreads)
        spreads_lag = np.roll(spreads, 1)
        spreads_lag[0] = spreads_lag[1]
        delta = spreads - spreads_lag
        spreads_lag = sm.add_constant(spreads_lag)
        model = sm.OLS(delta[1:], spreads_lag[1:]).fit()
        return -math.log(2) / model.params[1] if model.params[1] < 0 else 100

    def check_pair_eligibility(self):
        if self.half_life is None:
            return False
        if len(self.price_history1) >= self.p.lookback:
            _, pvalue, _ = coint(self.price_history1, self.price_history2)
            if pvalue > 0.05:
                return False
        if self.p.use_half_life and not (self.p.min_half_life <= self.half_life <= self.p.max_half_life):
            return False
        return True

    def check_drawdown(self):
        current_value = self.broker.getvalue()
        self.peak_value = max(self.peak_value, current_value)
        drawdown = 1 - current_value / self.peak_value
        if drawdown > self.p.max_drawdown:
            if not self.drawdown_lock:
                self.log(f"Maximum drawdown reached: {drawdown:.2%}", 1)
                self.drawdown_lock = True
            return True
        if drawdown < self.p.max_drawdown * 0.7:
            self.drawdown_lock = False
        return False

    def next(self):
        # Use built-in len(self.datas[0]) for bar count
        if len(self.datas[0]) < self.p.lookback or len(self.datas[1]) < self.p.lookback:
            self.log(f"[DEBUG] Not enough data to calculate statistics {self.datas[0]._name}_{self.datas[1]._name}", 2)
            return

        # Update price history
        self.price_history1.append(self.asset1[0])
        self.price_history2.append(self.asset2[0])
        if len(self.price_history1) > self.p.lookback:
            self.price_history1.pop(0)
            self.price_history2.pop(0)

        try:
            self.hedge_ratio = self.calculate_hedge_ratio()
            self.spread = self.calculate_spread(self.hedge_ratio)
            self.z_score = self.calculate_z_score(self.spread)
            self.half_life = self.calculate_half_life()
        except Exception as e:
            self.log(f"[DEBUG] Error in calculations: {str(e)}", 1)
            return

        self.zscore_history.append(self.z_score if self.z_score is not None else np.nan)
        if self.z_score is None or self.hedge_ratio is None:
            self.log(f"[DEBUG] Skipping bar: z_score or hedge_ratio is None", 2)
            return

        if self.check_drawdown():
            self.log("[DEBUG] Max drawdown reached, closing positions if any", 2)
            if self.getposition(self.datas[0]).size != 0 or self.getposition(self.datas[1]).size != 0:
                self.close(self.datas[0])
                self.close(self.datas[1])
                self.log("Closing all positions due to maximum drawdown", 1)
            return

        pair_id = f"{self.datas[0]._name}_{self.datas[1]._name}"
        if pair_id in self.holding_days:
            self.holding_days[pair_id] += 1
            if self.holding_days[pair_id] >= self.p.max_hold_days:
                self.log(f"Max holding period reached for pair {pair_id}", 1)
                self.close(self.datas[0])
                self.close(self.datas[1])
                del self.holding_days[pair_id]
                del self.entry_prices[pair_id]
                self.active_pairs -= 1

        pair_eligible = self.check_pair_eligibility()
        has_position = (self.getposition(self.datas[0]).size != 0 or self.getposition(self.datas[1]).size != 0)

        # Entry logic
        if not has_position:
            cash = self.broker.getcash()
            position_value = cash * self.p.position_size
            hedge_ratio = max(min(self.hedge_ratio, 5), -5) if self.hedge_ratio is not None else 1

            # Calculate rolling volatility (e.g., 20-bar std of spread)
            if len(self.spreads) >= 20:
                vol = np.std(self.spreads[-20:])
                base_position = self.broker.getvalue() * self.p.position_size
                target_vol = 0.01  # Set this to your desired risk per trade (e.g., 1% spread move)
                if vol > 0:
                    position_value = base_position * (target_vol / vol)
                    position_value = min(position_value, base_position)
                else:
                    position_value = base_position
            else:
                position_value = self.broker.getvalue() * self.p.position_size

            if self.asset1[0] <= 0 or self.asset2[0] <= 0:
                self.log("Asset price is zero or negative, skipping trade.", 1)
            else:
                if self.z_score > self.p.entry_z:
                    size1 = -position_value / self.asset1[0]
                    size2 = position_value * hedge_ratio / self.asset2[0]
                    self.sell(data=self.datas[0], size=abs(size1))
                    self.buy(data=self.datas[1], size=abs(size2))
                    self.log(f"SHORT {self.datas[0]._name}: qty={abs(size1):.4f}, price={self.asset1[0]:.4f}, notional=${abs(size1)*self.asset1[0]:.2f}", 1)
                    self.log(f"LONG {self.datas[1]._name}: qty={abs(size2):.4f}, price={self.asset2[0]:.4f}, notional=${abs(size2)*self.asset2[0]:.2f}", 1)
                elif self.z_score < -self.p.entry_z:
                    size1 = position_value / self.asset1[0]
                    size2 = -position_value * hedge_ratio / self.asset2[0]
                    self.buy(data=self.datas[0], size=abs(size1))
                    self.sell(data=self.datas[1], size=abs(size2))
                    self.log(f"LONG {self.datas[0]._name}: qty={abs(size1):.4f}, price={self.asset1[0]:.4f}, notional=${abs(size1)*self.asset1[0]:.2f}", 1)
                    self.log(f"SHORT {self.datas[1]._name}: qty={abs(size2):.4f}, price={self.asset2[0]:.4f}, notional=${abs(size2)*self.asset2[0]:.2f}", 1)
            self.holding_days[pair_id] = 0
            self.entry_prices[pair_id] = (self.asset1[0], self.asset2[0])
            # Store entry spread
            self.entry_spread[pair_id] = self.spread
            self.active_pairs += 1
            self.trades_total += 1
            self.entry_points.append(len(self.zscore_history) - 1)
        # Exit logic
        else:
            if abs(self.z_score) < self.p.exit_z:
                try:
                    entry_price1, entry_price2 = self.entry_prices.get(pair_id, (None, None))
                    if entry_price1 is not None:
                        pos1 = self.getposition(self.datas[0])
                        if pos1.size > 0:
                            pnl = ((self.asset1[0] / entry_price1 - 1) - (self.asset2[0] / entry_price2 - 1) * self.hedge_ratio)
                        else:
                            pnl = ((entry_price1 / self.asset1[0] - 1) - (entry_price2 / self.asset2[0] - 1) * self.hedge_ratio)
                        self.total_return += pnl
                        if pnl > 0:
                            self.trades_won += 1
                    self.close(self.datas[0])
                    self.close(self.datas[1])
                    if pair_id in self.holding_days:
                        del self.holding_days[pair_id]
                    if pair_id in self.entry_prices:
                        del self.entry_prices[pair_id]
                    self.active_pairs -= 1
                    self.exit_points.append(len(self.zscore_history) - 1)
                except Exception as e:
                    self.log(f"Error closing position: {str(e)}", 1)
            # Check stop-loss
            if has_position and pair_id in self.entry_spread:
                stop_loss_threshold = 3 * self.spread_std[0]  # 3 standard deviations as stop-loss
                if abs(self.spread - self.entry_spread[pair_id]) > stop_loss_threshold:
                    self.log(f"Trade stop-loss hit for {pair_id}, closing positions.", 1)
                    self.close(self.datas[0])
                    self.close(self.datas[1])

    def stop(self):
        win_rate = self.trades_won / self.trades_total if self.trades_total > 0 else 0
        final_value = self.broker.getvalue()
        total_return = (final_value / self.initial_capital - 1) * 100
        self.log(f"Strategy Performance Summary:", 1)
        self.log(f"Total Return: {total_return:.2f}%", 1)
        self.log(f"Win Rate: {win_rate:.2%}", 1)
        self.log(f"Total Trades: {self.trades_total}", 1)
        plt.figure(figsize=(14, 6))
        plt.plot(self.zscore_history, label='Z-Score')
        plt.axhline(self.p.entry_z, color='green', linestyle='--', label='Entry Threshold')
        plt.axhline(-self.p.entry_z, color='green', linestyle='--')
        plt.axhline(self.p.exit_z, color='red', linestyle='--', label='Exit Threshold')
        plt.axhline(-self.p.exit_z, color='red', linestyle='--')
        plt.scatter(self.entry_points, [self.zscore_history[i] for i in self.entry_points], marker='^', color='blue', label='Entry', zorder=5)
        plt.scatter(self.exit_points, [self.zscore_history[i] for i in self.exit_points], marker='v', color='orange', label='Exit', zorder=5)
        plt.title('Z-Score with Entry/Exit Points')
        plt.legend()
        plt.show()
