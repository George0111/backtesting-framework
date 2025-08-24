#!/usr/bin/env python3
"""
ES Extreme Opening Mean Reversion Strategy Runner

This script runs the ES Extreme Opening Mean Reversion strategy using data from the SQLite database.
"""

import sys
import os
import pandas as pd
import backtrader as bt
import pytz
from datetime import datetime, timedelta

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from backtester.strategies.ESExtremeOpeningMeanReversion import ESExtremeOpeningMeanReversion
from backtester.utils import load_es_futures_from_db


def main():
    """Main function to run the ES Mean Reversion strategy"""
    
    # Set the run timestamp
    run_timestamp = datetime.now().isoformat()
    print(f"Run Timestamp: {run_timestamp}")
    
    # Create Cerebro engine
    cerebro = bt.Cerebro(stdstats=False, maxcpus=1)
    
    # Add strategy with parameters
    strategy_params = {
        'run_timestamp': run_timestamp,
        'verbose': True,
        'logfile': f'es_mean_reversion_{run_timestamp}.json',
        
        # Core entry conditions
        'first_15min_threshold': -0.15,      # -0.15% threshold
        'percentile_cutoff': 10,             # Bottom 10%
        'volume_confirmation': 0.8,          # 80% volume confirmation
        
        # Multi-timeframe confirmation
        'momentum_5min_threshold': -0.05,    # 5-minute momentum must be negative
        'momentum_1hour_threshold': -0.10,   # 1-hour momentum threshold
        
        # Dynamic risk management
        'atr_period': 20,                    # ATR period for volatility calculation
        'stop_loss_atr_multiplier': 2.0,     # Stop loss ATR multiplier
        'take_profit_atr_multiplier': 3.0,   # Take profit ATR multiplier
        
        # Market regime detection
        'volatility_period': 20,             # Period for volatility calculation
        'trend_period': 50,                  # Period for trend calculation
        'volatility_threshold': 0.02,        # High volatility threshold (2%)
        'trend_threshold': 0.15,             # Strong trend threshold (15%)
        
        # Volume profile analysis
        'vwap_period': 20,                   # VWAP calculation period
        'volume_profile_period': 20,         # Volume profile analysis period
        
        # Historical data requirements
        'min_historical_days': 60,            # Need 60+ days before trading starts
        'lookback_period': 252,               # 1-year rolling lookback for percentiles
        
        # Position sizing
        'position_size_pct': 0.02,           # 2% position size
        'max_positions': 2,                  # Max 2 concurrent positions
        
        # Risk management (fallback)
        'stop_loss_multiplier': 1.5,         # 1.5x stop loss (fallback)
        'take_profit_multiplier': 2.0,       # 2.0x take profit (fallback)
    }
    
    cerebro.addstrategy(ESExtremeOpeningMeanReversion, **strategy_params)
    
    # Define start and end times (EST timezone)
    # Use 2023 data for comprehensive backtesting
    start_dt = datetime(2023, 1, 1, 9, 30, 0)  # January 1, 2023, 9:30 AM ET
    end_dt = datetime(2023, 12, 31, 16, 0, 0)  # December 31, 2023, 4:00 PM ET
    
    # Convert to EST timezone
    est_tz = pytz.timezone('US/Eastern')
    start_dt = est_tz.localize(start_dt)
    end_dt = est_tz.localize(end_dt)
    
    print(f"Backtest Period: {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Load ES futures data from SQLite database
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'datbases', 'es_futures.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print("Please ensure the ES futures database exists in data/datbases/")
        return
    
    print(f"📊 Loading ES futures data from: {db_path}")
    
    # Load data
    df = load_es_futures_from_db(db_path, start_dt, end_dt)
    
    if df is None or len(df) == 0:
        print("❌ No data loaded from database")
        return
    
    print(f"✅ Loaded {len(df)} bars of ES futures data")
    print(f"📅 Data range: {df.index.min()} to {df.index.max()}")
    print(f"📊 Data columns: {list(df.columns)}")
    
    # Create data feed for backtrader
    data_feed = bt.feeds.PandasData(
        dataname=df,
        name='ES',
        plot=False
    )
    
    cerebro.adddata(data_feed, name='ES')
    
    # Set starting cash
    starting_cash = 100000  # $100,000 starting capital
    cerebro.broker.setcash(starting_cash)
    
    # Configure broker with realistic transaction costs
    cerebro.broker.setcommission(commission=0.001)  # 0.1% commission
    cerebro.broker.set_slippage_perc(0.0)          # 0% slippage for testing
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    
    # Add observers
    cerebro.addobserver(bt.observers.Value)      # Equity curve
    cerebro.addobserver(bt.observers.DrawDown)   # Drawdown
    
    # Run backtest
    print(f"\n🚀 Starting ES Mean Reversion Backtest")
    print(f"💰 Starting Portfolio Value: ${cerebro.broker.getvalue():,.2f}")
    print("=" * 80)
    
    strat = None  # Initialize strat variable
    try:
        results = cerebro.run(runonce=False, stdstats=False)
        print("✅ Backtest completed successfully!")
        
        # Get strategy results
        strat = results[0]
        
        # Final portfolio value
        final_value = cerebro.broker.getvalue()
        total_return = (final_value / starting_cash - 1) * 100
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"💰 Final Portfolio Value: ${final_value:,.2f}")
        print(f"📈 Total Return: {total_return:.2f}%")
        
        # Get analyzer results
        if hasattr(strat, 'analyzers'):
            # Sharpe Ratio
            sharpe = strat.analyzers.sharpe.get_analysis()
            if 'sharperatio' in sharpe and sharpe['sharperatio'] is not None:
                print(f"📊 Sharpe Ratio: {sharpe['sharperatio']:.3f}")
            
            # Maximum Drawdown
            drawdown = strat.analyzers.drawdown.get_analysis()
            if 'max' in drawdown and 'drawdown' in drawdown['max']:
                print(f"📉 Max Drawdown: {drawdown['max']['drawdown']:.2f}%")
            
            # Trade Analysis
            trade_analyzer = strat.analyzers.tradeanalyzer.get_analysis()
            if 'total' in trade_analyzer and 'total' in trade_analyzer['total']:
                total_trades = trade_analyzer['total']['total']
                print(f"🎯 Total Trades: {total_trades}")
                
                if 'won' in trade_analyzer['total'] and 'lost' in trade_analyzer['total']:
                    won = trade_analyzer['total']['won']
                    lost = trade_analyzer['total']['lost']
                    win_rate = (won / total_trades * 100) if total_trades > 0 else 0
                    print(f"✅ Win Rate: {win_rate:.1f}% ({won}/{total_trades})")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Backtest failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Save results
    results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'es_mean_reversion')
    os.makedirs(results_dir, exist_ok=True)
    
    # Save backtest summary
    try:
        summary_file = os.path.join(results_dir, f'backtest_summary_{run_timestamp}.txt')
        with open(summary_file, 'w') as f:
            f.write("ES EXTREME OPENING MEAN REVERSION STRATEGY - BACKTEST SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Run Timestamp: {run_timestamp}\n")
            f.write(f"Backtest Period: {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
            f.write(f"Starting Cash: ${starting_cash:,.2f}\n")
            f.write(f"Final Portfolio Value: ${cerebro.broker.getvalue():,.2f}\n")
            f.write(f"Total Return: {((cerebro.broker.getvalue() / starting_cash - 1) * 100):.2f}%\n")
            f.write(f"Data Bars Processed: {len(df)}\n")
            f.write(f"Data Range: {df.index.min()} to {df.index.max()}\n")
            f.write(f"\nSTRATEGY PARAMETERS:\n")
            f.write(f"Entry Threshold: {strategy_params['first_15min_threshold']:.2f}%\n")
            f.write(f"Percentile Cutoff: Bottom {strategy_params['percentile_cutoff']}%\n")
            f.write(f"Min Historical Days: {strategy_params['min_historical_days']}\n")
            f.write(f"Lookback Period: {strategy_params['lookback_period']} days\n")
            f.write(f"Position Size: {strategy_params['position_size_pct']*100:.1f}%\n")
            f.write(f"\nMULTI-TIMEFRAME CONFIRMATION:\n")
            f.write(f"5-Min Momentum Threshold: {strategy_params['momentum_5min_threshold']:.2f}%\n")
            f.write(f"1-Hour Momentum Threshold: {strategy_params['momentum_1hour_threshold']:.2f}%\n")
            f.write(f"\nDYNAMIC RISK MANAGEMENT:\n")
            f.write(f"ATR Period: {strategy_params['atr_period']} bars\n")
            f.write(f"Stop Loss: Dynamic (ATR-based)\n")
            f.write(f"Take Profit: Dynamic (ATR-based)\n")
            f.write(f"\nMARKET REGIME DETECTION:\n")
            f.write(f"Volatility Period: {strategy_params['volatility_period']} bars\n")
            f.write(f"Trend Period: {strategy_params['trend_period']} bars\n")
            f.write(f"High Vol Threshold: {strategy_params['volatility_threshold']*100:.1f}%\n")
            f.write(f"Strong Trend Threshold: {strategy_params['trend_threshold']*100:.1f}%\n")
        print(f"📊 Backtest summary saved to: {summary_file}")
    except Exception as e:
        print(f"⚠️  Could not save summary: {e}")
    
    # Try to save strategy log if available
    if strat and hasattr(strat, 'log_events'):
        try:
            log_file = os.path.join(results_dir, f'es_mean_reversion_{run_timestamp}.json')
            import json
            with open(log_file, 'w') as f:
                json.dump(strat.log_events, f, indent=2, default=str)
            print(f"📝 Strategy log saved to: {log_file}")
        except Exception as e:
            print(f"⚠️  Could not save strategy log: {e}")
    
    print(f"\n🏁 ES Mean Reversion backtest completed!")
    print(f"📁 Results saved to: {results_dir}")
    
    # Show results directory location
    abs_results_dir = os.path.abspath(results_dir)
    print(f"📍 Absolute path: {abs_results_dir}")


if __name__ == '__main__':
    main()
