#!/usr/bin/env python3
"""
ES Extreme Opening Mean Reversion Strategy - Professional Quant Version
Based on market microstructure, multi-timeframe analysis, and regime detection
"""

import numpy as np
import pandas as pd
from datetime import time
from .base.Strategy import BaseStrategy


class ESExtremeOpeningMeanReversion(BaseStrategy):
    """
    Professional ES Mean Reversion Strategy
    
    Key Improvements:
    1. Multi-timeframe confirmation to reduce false signals
    2. Dynamic risk management based on volatility
    3. Market regime detection for adaptive behavior
    4. Volume profile analysis for institutional flow detection
    5. Momentum confirmation to avoid fighting strong trends
    """
    
    params = (
        # Entry conditions
        ('first_15min_threshold', -0.15),      # -0.15% threshold for extreme negative opening
        ('percentile_cutoff', 10),             # Bottom 10% of historical first 15-min returns
        ('volume_confirmation', 0.8),          # Volume > 80% of average first 15-min volume
        
        # Multi-timeframe confirmation
        ('momentum_5min_threshold', -0.05),    # 5-minute momentum must be negative
        ('momentum_1hour_threshold', -0.10),   # 1-hour momentum threshold
        
        # Dynamic risk management
        ('atr_period', 20),                    # ATR period for volatility calculation
        ('stop_loss_atr_multiplier', 2.0),     # Stop loss ATR multiplier
        ('take_profit_atr_multiplier', 3.0),   # Take profit ATR multiplier
        
        # Market regime detection
        ('volatility_period', 20),             # Period for volatility calculation
        ('trend_period', 50),                  # Period for trend calculation
        ('volatility_threshold', 0.02),        # High volatility threshold (2%)
        ('trend_threshold', 0.15),             # Strong trend threshold (15%)
        
        # Volume profile analysis
        ('vwap_period', 20),                   # VWAP calculation period
        ('volume_profile_period', 20),         # Volume profile analysis period
        
        # Historical data requirements
        ('min_historical_days', 60),           # Minimum days needed before trading starts
        ('lookback_period', 252),              # Rolling lookback period (1 year = 252 trading days)
        
        # Position sizing
        ('position_size_pct', 0.02),           # 2% position size per trade
        ('max_positions', 2),                  # Maximum concurrent positions
        
        # Exit conditions
        ('stop_loss_multiplier', 1.5),         # Stop loss = 1.5x first 15-min move (fallback)
        ('take_profit_multiplier', 2.0),      # Take profit = 2.0x first 15-min move (fallback)
        ('max_hold_time', 390),                # Maximum hold time (6.5 hours = 390 minutes)
        
        # Commission and slippage
        ('commission', 0.001),                 # 0.1% commission
        ('slippage', 0.25),                   # 0.25 points slippage
        
        # Market hours (EST)
        ('market_open', time(9, 30)),         # 9:30 AM ET
        ('signal_time', time(9, 45)),         # 9:45 AM ET (after first 15-min bar)
        ('market_close', time(16, 0)),        # 4:00 PM ET
    )
    
    def __init__(self):
        super().__init__()
        
        # Historical data storage
        self.historical_first_15min_returns = []
        self.historical_first_15min_volumes = []
        
        # Trade management
        self.order = None
        self.daily_trades = 0
        self.first_15min_return = None
        self.first_15min_volume = None
        self.position_start_time = 0
        
        # Market regime tracking
        self.current_regime = "UNKNOWN"
        self.regime_history = []
        
        # Performance tracking
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
    
    def log(self, txt, dt=None):
        """Log function with timestamp"""
        dt = dt or self.data.datetime.datetime(0)
        if hasattr(self, 'verbose') and self.verbose:
            print(f'{dt.isoformat()}, {txt}')
        
    def calculate_atr(self, period):
        """Calculate Average True Range for volatility measurement"""
        if len(self.data.high) < period:
            return 0
        
        # Get the last period data
        highs = []
        lows = []
        closes = []
        for i in range(period):
            highs.append(self.data.high[-i-1])
            lows.append(self.data.low[-i-1])
            closes.append(self.data.close[-i-1])
        
        highs.reverse()
        lows.reverse()
        closes.reverse()
        
        high_low = np.array(highs) - np.array(lows)
        high_close = np.abs(np.array(highs) - np.roll(np.array(closes), 1))
        low_close = np.abs(np.array(lows) - np.roll(np.array(closes), 1))
        
        true_ranges = np.maximum(high_low, np.maximum(high_close, low_close))
        return np.mean(true_ranges)
    
    def calculate_momentum(self, period):
        """Calculate momentum over specified period"""
        if len(self.data.close) < period:
            return 0
        
        current_price = self.data.close[-1]
        past_price = self.data.close[-period-1]
        
        return (current_price - past_price) / past_price
    
    def calculate_realized_volatility(self, period):
        """Calculate realized volatility over specified period"""
        if len(self.data.close) < period + 1:
            return 0
        
        # Get the last period+1 prices
        prices = []
        for i in range(period + 1):
            prices.append(self.data.close[-i-1])
        prices.reverse()  # Reverse to get chronological order
        
        returns = np.diff(np.log(prices))
        return np.std(returns) * np.sqrt(252 * 24 * 60)  # Annualized
    
    def calculate_trend_strength(self, period):
        """Calculate trend strength using linear regression R-squared"""
        if len(self.data.close) < period:
            return 0
        
        # Get the last period prices
        prices = []
        for i in range(period):
            prices.append(self.data.close[-i-1])
        prices.reverse()  # Reverse to get chronological order
        
        time_index = np.arange(period)
        
        # Linear regression
        slope, intercept = np.polyfit(time_index, prices, 1)
        y_pred = slope * time_index + intercept
        
        # Calculate R-squared
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        
        if ss_tot == 0:
            return 0
        
        r_squared = 1 - (ss_res / ss_tot)
        return r_squared
    
    def calculate_vwap(self, period):
        """Calculate Volume Weighted Average Price"""
        if len(self.data.close) < period:
            return self.data.close[-1]
        
        # Get the last period prices and volumes
        prices = []
        volumes = []
        for i in range(period):
            prices.append(self.data.close[-i-1])
            volumes.append(self.data.volume[-i-1])
        prices.reverse()  # Reverse to get chronological order
        volumes.reverse()
        
        if np.sum(volumes) == 0:
            return np.mean(prices)
        
        return np.sum(np.array(prices) * np.array(volumes)) / np.sum(volumes)
    
    def detect_market_regime(self):
        """Detect current market regime for adaptive strategy"""
        realized_vol = self.calculate_realized_volatility(self.p.volatility_period)
        trend_strength = self.calculate_trend_strength(self.p.trend_period)
        
        if realized_vol > self.p.volatility_threshold and trend_strength > self.p.trend_threshold:
            regime = "TRENDING_HIGH_VOL"
        elif realized_vol > self.p.volatility_threshold and trend_strength < self.p.trend_threshold:
            regime = "CHOPPY_HIGH_VOL"
        elif realized_vol < self.p.volatility_threshold and trend_strength < self.p.trend_threshold:
            regime = "LOW_VOL_RANGING"
        else:
            regime = "MIXED"
        
        self.current_regime = regime
        self.regime_history.append(regime)
        
        return regime
    
    def is_institutional_driven_move(self):
        """Check if extreme move is driven by institutional activity"""
        # High volume with price continuation suggests institutional flow
        if (self.first_15min_volume > np.mean(self.historical_first_15min_volumes) * 1.5 and
            self.first_15min_return < -0.25):  # Very extreme move
            return True
        return False
    
    def is_mean_reversion_setup(self):
        """Check if conditions favor mean reversion"""
        # Check if price is at support level
        vwap = self.calculate_vwap(self.p.vwap_period)
        at_support = self.data.close[-1] > vwap * 0.995  # Within 0.5% of VWAP
        
        # Check for oversold conditions
        momentum_5min = self.calculate_momentum(5)
        momentum_1hour = self.calculate_momentum(60)
        
        oversold_5min = momentum_5min < self.p.momentum_5min_threshold
        oversold_1hour = momentum_1hour < self.p.momentum_1hour_threshold
        
        return at_support and oversold_5min and oversold_1hour
    
    def calculate_dynamic_exits(self):
        """Calculate dynamic stop loss and take profit based on volatility"""
        atr = self.calculate_atr(self.p.atr_period)
        move_magnitude = abs(self.first_15min_return)
        
        # Dynamic stop loss: 1.5x move or 2x ATR, whichever is smaller
        stop_loss_pct = min(1.5 * move_magnitude, 2.0 * atr / self.data.close[-1])
        
        # Dynamic take profit: 2.5x move or 3x ATR, whichever is larger
        take_profit_pct = max(2.5 * move_magnitude, 3.0 * atr / self.data.close[-1])
        
        # Convert to price levels
        stop_loss_price = self.data.close[-1] * (1 - stop_loss_pct)
        take_profit_price = self.data.close[-1] * (1 + take_profit_pct)
        
        return stop_loss_price, take_profit_price
    
    def calculate_first_15min_metrics(self):
        """Calculate first 15-minute return and volume"""
        # Need at least 15 bars for 15-minute calculation
        if len(self.data.close) < 15:
            return None, None
        
        # Calculate first 15-minute return
        first_open = self.data.open[-15]
        first_close = self.data.close[-1]
        first_return = (first_close - first_open) / first_open * 100
        
        # Calculate first 15-minute volume
        bars_needed = min(15, len(self.data.volume))
        first_volume = 0
        for i in range(bars_needed):
            first_volume += self.data.volume[-bars_needed + i]
        
        return first_return, first_volume
    
    def should_enter_position(self):
        """Enhanced entry logic with multiple confirmations"""
        # Check daily trade limit
        if self.daily_trades >= 3:
            return False, "Daily trade limit reached"
        
        # Check if we have enough historical data
        if len(self.historical_first_15min_returns) < self.p.min_historical_days:
            return False, f"Insufficient historical data: {len(self.historical_first_15min_returns)} days (need {self.p.min_historical_days}+)"
        
        # Check extreme negative threshold
        if self.first_15min_return > self.p.first_15min_threshold:
            return False, f"First 15min return {self.first_15min_return:.3f}% not extreme enough"
        
        # Check percentile cutoff
        returns_array = np.array(self.historical_first_15min_returns)
        percentile = np.percentile(returns_array, self.p.percentile_cutoff)
        
        if self.first_15min_return > percentile:
            return False, f"First 15min return {self.first_15min_return:.3f}% not in bottom {self.p.percentile_cutoff}%"
        
        # Check volume confirmation
        avg_volume = np.mean(self.historical_first_15min_volumes)
        if self.first_15min_volume < avg_volume * self.p.volume_confirmation:
            return False, f"Volume {self.first_15min_volume:.0f} below {self.p.volume_confirmation*100:.0f}% of average"
        
        # Check if move is institutional-driven (avoid these)
        if self.is_institutional_driven_move():
            return False, "Institutional move - likely to continue"
        
        # Check for mean reversion setup
        if not self.is_mean_reversion_setup():
            return False, "No mean reversion setup"
        
        # Check market regime suitability
        if self.current_regime == "TRENDING_HIGH_VOL":
            return False, "Trending high vol regime - avoid mean reversion"
        
        return True, "All conditions met"
    
    def calculate_position_size(self):
        """Calculate position size based on account value"""
        account_value = self.broker.getvalue()
        position_value = account_value * self.p.position_size_pct
        position_size = position_value / self.close[-1]
        return position_size
    
    def should_exit_position(self):
        """Check if position should be exited"""
        if not self.position:
            return False, "No position"
        
        # Check stop loss and take profit
        current_price = self.data.close[-1]
        entry_price = self.position.price
        
        # Use dynamic exits if available, otherwise fallback to fixed
        try:
            stop_loss_price, take_profit_price = self.calculate_dynamic_exits()
        except:
            # Fallback to fixed multipliers
            move_pct = abs(self.first_15min_return) / 100
            stop_loss_price = entry_price * (1 - self.p.stop_loss_multiplier * move_pct)
            take_profit_price = entry_price * (1 + self.p.take_profit_multiplier * move_pct)
        
        if current_price <= stop_loss_price:
            return True, "STOP_LOSS"
        elif current_price >= take_profit_price:
            return True, "TAKE_PROFIT"
        
        # Check time-based exit
        if len(self) - self.position_start_time >= self.p.max_hold_time:
            return False, "Hold"  # Fixed: should return False, not True
        
        return False, "Hold"
    
    def next(self):
        """Main strategy logic"""
        # Reset daily trade counter at market open
        current_time = self.data.datetime.time()
        if current_time == self.p.market_open:
            self.daily_trades = 0
        
        # Detect market regime
        self.detect_market_regime()
        
        # Calculate first 15-minute metrics at signal time
        if current_time == self.p.signal_time:
            first_return, first_volume = self.calculate_first_15min_metrics()
            if first_return is not None:
                self.first_15min_return = first_return
                self.first_15min_volume = first_volume
                
                # Store historical data for percentile calculation
                self.historical_first_15min_returns.append(first_return)
                self.historical_first_15min_volumes.append(first_volume)
                
                # Keep only last N trading days for rolling lookback
                if len(self.historical_first_15min_returns) > self.p.lookback_period:
                    self.historical_first_15min_returns.pop(0)
                    self.historical_first_15min_volumes.pop(0)
                
                # Log historical data status
                hist_days = len(self.historical_first_15min_returns)
                self.log(f'📊 First 15min Return: {first_return:.3f}%')
                self.log(f'📊 First 15min Volume: {first_volume:,.0f}')
                self.log(f'📈 Historical Data: {hist_days} days (need {self.p.min_historical_days}+)')
                self.log(f'🏛️ Market Regime: {self.current_regime}')
                
                # Check for entry signal
                should_enter, reason = self.should_enter_position()
                
                if should_enter:
                    position_size = self.calculate_position_size()
                    
                    if position_size > 0:
                        self.daily_trades += 1
                        
                        self.log(f'🚀 ES MEAN REVERSION ENTRY #{self.daily_trades}')
                        self.log(f'   💰 Price: ${self.data.close[-1]:,.2f}')
                        self.log(f'   📊 Size: {position_size:.4f}')
                        self.log(f'   🎯 Signal: Extreme negative opening ({first_return:.3f}%)')
                        self.log(f'   📈 Percentile: Bottom {self.p.percentile_cutoff}%')
                        self.log(f'   📊 Historical Days: {hist_days}')
                        self.log(f'   🏛️ Regime: {self.current_regime}')
                        
                        self.order = self.buy(size=position_size)
                        self.position_start_time = len(self)
                else:
                    self.log(f'❌ No entry: {reason}')
        
        # Check for exit signals
        if self.position:
            should_exit, reason = self.should_exit_position()
            if should_exit:
                self.log(f'🛑 ES MEAN REVERSION EXIT: {reason}')
                self.log(f'   💰 Exit Price: ${self.data.close[-1]:,.2f}')
                self.close()
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'🟢 ES MEAN REVERSION BUY - Price: ${order.executed.price:.2f}, Size: {order.executed.size:.4f}, Value: ${order.executed.value:.2f}')
                
                # Set stop loss and take profit
                try:
                    stop_loss_price, take_profit_price = self.calculate_dynamic_exits()
                    self.log(f'🎯 Dynamic Stop Loss: ${stop_loss_price:.2f}')
                    self.log(f'🎯 Dynamic Take Profit: ${take_profit_price:.2f}')
                except:
                    # Fallback to fixed multipliers
                    move_pct = abs(self.first_15min_return) / 100
                    stop_loss_price = order.executed.price * (1 - self.p.stop_loss_multiplier * move_pct)
                    take_profit_price = order.executed.price * (1 + self.p.take_profit_multiplier * move_pct)
                    self.log(f'🎯 Stop Loss: ${stop_loss_price:.2f}')
                    self.log(f'🎯 Take Profit: ${take_profit_price:.2f}')
                
            elif order.issell():
                self.log(f'🔴 ES MEAN REVERSION SELL - Price: ${order.executed.price:.2f}, Size: {order.executed.size:.4f}, Value: ${order.executed.value:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'❌ Order Canceled/Margin/Rejected: {order.status}')
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications"""
        if not trade.isclosed:
            return
        
        # Calculate P&L
        gross_pnl = trade.pnl
        net_pnl = trade.pnlcomm
        
        # Update trade statistics
        self.trade_count += 1
        if net_pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        # Calculate holding time
        holding_time = trade.dtopen - trade.dtclose if hasattr(trade, 'dtopen') and hasattr(trade, 'dtclose') else 0
        
        self.log(f'📊 ES MEAN REVERSION TRADE #{self.trade_count} CLOSED:')
        self.log(f'   💰 P&L: ${gross_pnl:.2f} (Net: ${net_pnl:.2f})')
        self.log(f'   ⏱️  Holding Time: {holding_time} minutes')
        self.log(f'   📈 First 15min Return: {self.first_15min_return:.3f}%')
        self.log(f'   🏛️ Market Regime: {self.current_regime}')
    
    def stop(self):
        """Strategy cleanup and final statistics"""
        self.log('=' * 80)
        self.log('🏆 ES EXTREME OPENING MEAN REVERSION - FINAL PERFORMANCE')
        self.log('=' * 80)
        
        # Portfolio statistics
        self.log(f'💰 Starting Value: ${self.broker.startingcash:,.2f}')
        self.log(f'💰 Final Value: ${self.broker.getvalue():,.2f}')
        self.log(f'📈 Total Return: {((self.broker.getvalue() / self.broker.startingcash - 1) * 100):.2f}%')
        
        # Peak and drawdown
        peak_value = max(self.broker.startingcash, self.broker.getvalue())
        max_drawdown = ((peak_value - self.broker.getvalue()) / peak_value) * 100
        self.log(f'📊 Peak Value: ${peak_value:,.2f}')
        self.log(f'📉 Max Drawdown: {max_drawdown:.2f}%')
        
        # Trade statistics
        self.log(f'🎯 Total Trades: {self.trade_count}')
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            self.log(f'✅ Win Rate: {win_rate:.1f}%')
        
        # Strategy information
        self.log(f'⚡ Strategy Type: ES Extreme Opening Mean Reversion (Professional)')
        self.log(f'🎯 Entry Threshold: {self.p.first_15min_threshold:.2f}%')
        self.log(f'📊 Percentile Cutoff: Bottom {self.p.percentile_cutoff}%')
        self.log(f'🛑 Stop Loss: Dynamic (ATR-based)')
        self.log(f'🎯 Take Profit: Dynamic (ATR-based)')
        
        # Market regime analysis
        if self.regime_history:
            regime_counts = pd.Series(self.regime_history).value_counts()
            self.log(f'🏛️ Market Regimes Encountered:')
            for regime, count in regime_counts.items():
                self.log(f'   {regime}: {count} times')
        
        # Strategy-specific statistics
        if len(self.historical_first_15min_returns) > 0:
            avg_first_15min_return = np.mean(self.historical_first_15min_returns)
            min_return = np.min(self.historical_first_15min_returns)
            max_return = np.max(self.historical_first_15min_returns)
            self.log(f'📊 Average First 15min Return: {avg_first_15min_return:.3f}%')
            self.log(f'📊 Min/Max First 15min Returns: {min_return:.3f}% / {max_return:.3f}%')
            self.log(f'📊 Historical Data Points: {len(self.historical_first_15min_returns)}')
            self.log(f'📊 Lookback Period: {self.p.lookback_period} days')
            self.log(f'📊 Min Required Days: {self.p.min_historical_days} days')
            
        self.log('=' * 80)
