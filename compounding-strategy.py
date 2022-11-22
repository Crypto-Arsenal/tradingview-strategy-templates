class Strategy(StrategyBase):
    def __init__(self):
        self.period = 60
        self.subscribed_books = {}
        self.options = {}
        self.percentage_of_order_amount = 0.96 # broker already defaults to 99%
        exchange, pair, base, quote = CA.get_exchange_pair()
        quote_balance = CA.get_balance(exchange, quote)
        self.init_available_quote_amount = quote_balance.available
        CA.log('total inital ' + str(quote) + ' quote amount: ' + str(self.init_available_quote_amount))

    def on_tradingview_signal(self, signal, candles):
        CA.log('on_tradingview_signal: ' + str(signal))
        exchange, pair, base, quote = CA.get_exchange_pair()

        action = signal.get('action')
        CA.log(signal.get('log'))
        
        if action == 'cancelAll' or action == 'cancel_all':
            CA.cancel_all()
        elif action == 'cancel':
            CA.cancel_order_by_client_order_id(signal.get('clientOrderId'))
        elif action == 'openLong' or action == 'openShort':
            # 
            # get available quote amount
            quote_balance = CA.get_balance(exchange, quote)
            available_quote_amount = quote_balance.available
            # if profit then stick with init amount / if lose money then use available_quote_amount
            order_quote_amount = min(self.init_available_quote_amount, available_quote_amount)  * self.percentage_of_order_amount
            order_price =   float(signal.get('limit')) if signal.get('limit') is not None else candles[exchange][pair][0]['close']
           
            CA.log("USDT To Place Order: " + str(order_quote_amount))
            CA.log("Order Price: " + str(order_price))

            # check if 0 or None
            if not order_price or not order_quote_amount:
                return

            fixed_amount = order_quote_amount / order_price
            
            CA.log("Order Amount: " + str(fixed_amount))
            CA.place_order(exchange, pair, action, signal.get('limit'), fixed_amount, signal.get('percent'), signal.get('clientOrderId'), signal.get('profit'), signal.get('loss'))
        elif action == 'closeLong' or action == 'closeShort':
            # close 100% 
            CA.place_order(exchange, pair, action, signal.get('limit'), None, signal.get('percent'), signal.get('clientOrderId'), signal.get('profit'), signal.get('loss'))

    def on_order_state_change(self,  order):
        CA.log('on_order_state_change: ' + str(order))

    def trade(self, candles):
        pass
