class Strategy(StrategyBase):
    def __init__(self):
        self.period = 60
        self.subscribed_books = {}
        self.options = {}

    def on_tradingview_signal(self, signal, candles):
        CA.log('on_tradingview_signal: ' + str(signal))
        exchange, pair, base, quote = CA.get_exchange_pair()
        action = signal.get('action')
        if action == 'cancelAll' or action == 'cancel_all':
            CA.cancel_all()
        elif action == 'cancel':
            CA.cancel_order_by_client_order_id(signal.get('clientOrderId'))
        else:
            total_position = self.get_total_position()
            # close long / open short
            if action == 'openShort' and total_position > 0:
                CA.log("Amount to close long: " + str(total_position) + " and open short 100%")
                CA.place_order(exchange, pair, action='close_long', percent=100, conditional_order_type='OTO', child_conditional_orders=[{
                    'action': 'open_short', 'percent': 100
                }])
            # close short / open long
            elif action == 'openLong' and total_position < 0:
                CA.log("Amount to close short: " + str(total_position) + " and open long 100%")
                CA.place_order(exchange, pair, action='close_short', percent=100, conditional_order_type='OTO', child_conditional_orders=[{
                    'action': 'open_long', 'percent': 100
                }])
            else: 
                # other case (add position or when starting)
                CA.place_order(exchange, pair, action, signal.get('limit'), signal.get('fixed'), signal.get('percent'), signal.get('clientOrderId'), signal.get('profit'), signal.get('loss'))

        CA.log(signal.get('log'))

    def on_order_state_change(self,  order):
        CA.log('on_order_state_change: ' + str(order))

    def trade(self, candles):
        pass

    # return current total position: -n 0, +n  where n is number of contracts
    def get_total_position(self):
        exchange, pair, base, quote = CA.get_exchange_pair()

        curTotalPosition = None
        total_long_position_size = None
        total_short_position_size = None
        long_position = CA.get_position(exchange, pair, CA.PositionSide.LONG)
        if long_position:
            total_long_position_size = long_position.total_size

        short_position = CA.get_position(exchange, pair, CA.PositionSide.SHORT)
        if short_position:
            total_short_position_size = short_position.total_size

        if total_long_position_size is None and total_short_position_size is None:
            curTotalPosition = 0

        if total_long_position_size is not None:
            curTotalPosition = abs(total_long_position_size)

        if total_short_position_size is not None:
            curTotalPosition = -1 * abs(total_short_position_size)

        return curTotalPosition
