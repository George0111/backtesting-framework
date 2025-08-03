import backtrader as bt
import logging, json
import os
# ...existing imports...
EVENT_NEXT = 'next'
EVENT_PORTFOLIO = 'portfolio'
EVENT_ORDER = 'order'
EVENT_TRADE = 'trade'
EVENT_REBALANCE = 'rebalance'

def setup_logger(name, log_file, level=logging.INFO):
    """Simple logger setup function"""
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create file handler
    handler = logging.FileHandler(log_file)
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

class BaseStrategy_OLD(bt.Strategy):
    params = (
        ('run_timestamp', None),
        ('verbose', True),
        ('logfile', 'default_log'),
    )
    def __init__(self):
        self.run_timestamp = self.p.run_timestamp
        self.verbose = self.p.verbose
        logfile = self.p.logfile
        self.main_logger = setup_logger(
                            name='MainLogger',
                            log_file=f'./logs/{logfile}/orders_and_trades_{logfile}.log',
                            level=logging.INFO
                            )
        self.next_logger = setup_logger(
                            name='NextLogger',
                            log_file=f'./logs/{logfile}/next_events_{logfile}.log',
                            level=logging.INFO
                            )
    
    def log(self, txt, dt=None):
        # Log function to add timestamps
        dt = dt or self.datas[0].datetime.date(0)
        if self.verbose:
            print(f"{dt.isoformat()} - {txt}")

    def logging_next(self):
        if self.verbose:
            temp_pos = {}
            temp_size = {}
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
                temp_size[data._name] = size
            # Log the current cash value
            cash = self.broker.getcash()
            port_info = {'run_timestamp': self.run_timestamp,
                    'event': 'portfolio',
                    'event_timestamp': self.datas[0].datetime.datetime(0).isoformat(),  # Current bar's datetime
                    'equity': self.broker.getvalue(),
                    'cash': cash,
                    'market_values': temp_pos,
                    'positions': temp_size
                    }
            self.next_logger.info(json.dumps(port_info))  # Log the current cash value
    
    def log_timer_info(self):
        if self.verbose:
            timer_info = {
                'run_timestamp': self.run_timestamp,
                'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
                'event': 'rebalance',
                }
            
            self.next_logger.info(json.dumps(timer_info))

    def notify_order(self, order):
        order_info = {
            'run_timestamp': self.run_timestamp,
            'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the order event
            'event': 'order',
            'order_id': order.ref,
            'status': order.getstatusname(),
            'asset': order.data._name,  # Name of the data feed
            'size': order.size,
            'price': order.price,
            'created': order.created.dt if order.created else None,
            'executed': {
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
                'datetime': order.executed.dt
            }
        }
        if self.verbose:
            self.main_logger.info(json.dumps(order_info))  # Log the order info as a JSON string
        
        
    # Track trade status
    def notify_trade(self, trade):
        if self.verbose:
            trade_info = {
                'run_timestamp': self.run_timestamp,
                'event_timestamp': self.datas[0].datetime.date(0).isoformat(),  # Timestamp for the trade event
                'event': 'trade',
                'ref': trade.ref,
                'status': 'closed' if trade.isclosed else 'open' if trade.isopen else 'created',
                'tradeid': trade.tradeid,
                'asset': trade.data._name,  # Name of the data feed
                'size': trade.size,
                'price': trade.price,
                'value': trade.value,
                'commission': trade.commission,
                'pnl': trade.pnl,
                'pnlcomm': trade.pnlcomm,
                'isclosed': trade.isclosed,
                'isopen': trade.isopen,
                'justopened': trade.justopened,
                'baropen': trade.baropen,
                'dtopen': trade.open_datetime().isoformat() if trade.isopen else None,
                'barclose': trade.barclose,
                'dtclose': trade.close_datetime().isoformat() if trade.isclosed else None,
                'barlen': trade.barlen,
                'historyon': trade.historyon,
                'history': trade.history
            }
            self.main_logger.info(json.dumps(trade_info))  # Log the trade info as a JSON string
    
    # Track order details
    def track_order(self, order, data, target):
        if self.verbose:
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


class BaseStrategy(bt.Strategy):
    params = (
        ('run_timestamp', None),
        ('verbose', True),
        ('logfile', 'default_log.json'),
    )

    def __init__(self):
        self.run_timestamp = self.p.run_timestamp
        self.verbose = self.p.verbose
        self.logfile = self.p.logfile
        self.log_events = []  # All events will be appended here

        # Ensure log directory exists
        logdir = os.path.dirname(f'./logs/{self.logfile}')
        if logdir and not os.path.exists(logdir):
            os.makedirs(logdir)

    def log_event(self, event_dict):
        """Append event to log_events list."""
        self.log_events.append(event_dict)
        if self.verbose:
            print(json.dumps(event_dict, indent=2))

    # def next(self):
    #     dt = self.datas[0].datetime.datetime(0).isoformat()
    #     positions = {}
    #     market_values = {}
    #     for data in self.datas:
    #         pos = self.getposition(data)
    #         asset = getattr(data, '_name', getattr(data, '_dataname', str(data)))
    #         size = pos.size
    #         price = data.close[0]
    #         market_value = size * price
    #         pnl = market_value - (pos.size * pos.price)
    #         event = {
    #             'run_timestamp': self.run_timestamp,
    #             'event': 'next',
    #             'datetime': dt,
    #             'asset': asset,
    #             'open': data.open[0],
    #             'high': data.high[0],
    #             'low': data.low[0],
    #             'close': data.close[0],
    #             'volume': data.volume[0],
    #             'position_size': size,
    #             'position_price': pos.price,
    #             'market_value': market_value,
    #             'pnl': pnl,
    #             'cash': self.broker.getcash(),
    #             'total_value': self.broker.getvalue(),
    #         }
    #         self.log_event(event)
    #         positions[asset] = size
    #         market_values[asset] = market_value

    #     # Portfolio snapshot (aggregate)
    #     port_event = {
    #         'run_timestamp': self.run_timestamp,
    #         'event': 'portfolio',
    #         'datetime': dt,
    #         'cash': self.broker.getcash(),
    #         'total_value': self.broker.getvalue(),
    #         'positions': positions,
    #         'market_values': market_values
    #     }
    #     self.log_event(port_event)

    def next(self):
        dt = self.datas[0].datetime.datetime(0).isoformat()
        positions, market_values = self._log_positions(dt)
        self._log_portfolio_snapshot(dt, positions, market_values)

    def _log_positions(self, dt):
        """Log individual asset positions."""
        positions = {}
        market_values = {}
        for data in self.datas:
            pos = self.getposition(data)
            asset = getattr(data, '_name', getattr(data, '_dataname', str(data)))
            size = pos.size
            price = data.close[0]
            market_value = size * price
            pnl = market_value - (pos.size * pos.price)
            event = {
                'run_timestamp': self.run_timestamp,
                'event': EVENT_NEXT,
                'datetime': dt,
                'asset': asset,
                'open': data.open[0],
                'high': data.high[0],
                'low': data.low[0],
                'close': data.close[0],
                'volume': data.volume[0],
                'position_size': size,
                'position_price': pos.price,
                'market_value': market_value,
                'pnl': pnl,
                'cash': self.broker.getcash(),
                'total_value': self.broker.getvalue(),
            }
            self.log_event(event)
            positions[asset] = size
            market_values[asset] = market_value
        return positions, market_values

    def _log_portfolio_snapshot(self, dt, positions, market_values):
        """Log portfolio snapshot."""
        port_event = {
            'run_timestamp': self.run_timestamp,
            'event': EVENT_PORTFOLIO,
            'datetime': dt,
            'cash': self.broker.getcash(),
            'total_value': self.broker.getvalue(),
            'positions': positions,
            'market_values': market_values,
        }
        self.log_event(port_event)
        
    def log_timer_info(self):
        timer_event = {
            'run_timestamp': self.run_timestamp,
            'event': 'rebalance',
            'datetime': self.datas[0].datetime.datetime(0).isoformat(),
        }
        self.log_event(timer_event)


    def notify_order(self, order):
        asset = getattr(order.data, '_name', getattr(order.data, '_dataname', str(order.data)))
        order_event = {
            'order_id': order.ref,
            'status': order.getstatusname(),
            'asset': asset,
            'size': order.size,
            'price': order.price,
            'created_dt': order.created.dt if order.created else None,
            'executed': {
                'price': order.executed.price,
                'size': order.executed.size,
                'value': order.executed.value,
                'commission': order.executed.comm,
                'datetime': order.executed.dt,
            },
        }
        self._log_event_with_type(EVENT_ORDER, order_event)

    def notify_trade(self, trade):
        asset = getattr(trade.data, '_name', getattr(trade.data, '_dataname', str(trade.data)))
        trade_event = {
            'trade_ref': trade.ref,
            'status': 'closed' if trade.isclosed else 'open' if trade.isopen else 'created',
            'tradeid': trade.tradeid,
            'asset': asset,
            'size': trade.size,
            'price': trade.price,
            'value': trade.value,
            'commission': trade.commission,
            'pnl': trade.pnl,
            'pnlcomm': trade.pnlcomm,
            'isclosed': trade.isclosed,
            'isopen': trade.isopen,
            'justopened': trade.justopened,
            'baropen': trade.baropen,
            'dtopen': trade.open_datetime().isoformat() if trade.isopen else None,
            'barclose': trade.barclose,
            'dtclose': trade.close_datetime().isoformat() if trade.isclosed else None,
            'barlen': trade.barlen,
        }
        self._log_event_with_type(EVENT_TRADE, trade_event)

    def _log_event_with_type(self, event_type, details):
        """Helper to log events with a specific type."""
        event = {
            'run_timestamp': self.run_timestamp,
            'event': event_type,
            'datetime': self.datas[0].datetime.datetime(0).isoformat(),
            'details': details,
        }
        self.log_event(event)

    def stop(self):
        """Write all events to a JSON file."""
        try:
            with open(f'./logs/{self.logfile}', 'w') as f:
                json.dump(self.log_events, f, indent=2, default=str)
            if self.verbose:
                print(f"All log events written to ./logs/{self.logfile}")
        except Exception as e:
            print(f"Error writing log file: {e}")