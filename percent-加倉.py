class Strategy(StrategyBase):
    # 初始設置
    def __init__(self):
        self.period = 60
        self.subscribed_books = {}
        self.options = {}
        # 機器人啟動時設置開倉金額 
        exchange, pair, base, quote = CA.get_exchange_pair()
        quote_balance = CA.get_balance(exchange, quote)
        self.ca_initial_capital = quote_balance.available
        CA.log('Total inital ' + str(quote) + ' quote amount: ' + str(self.ca_initial_capital))

    # 處理TradingView 訊號進來
    def on_tradingview_signal(self, signal, candles):
        CA.log('on_tradingview_signal: ' + str(signal))
        exchange, pair, base, quote = CA.get_exchange_pair()
        # 抓動作 i.e open/close long/short
        action = signal.get('action')
        # 取消全部訂單
        if action == 'cancelAll' or action == 'cancel_all':
            CA.cancel_all()
        # 取消訂單
        elif action == 'cancel':
            CA.cancel_order_by_client_order_id(signal.get('clientOrderId'))
        # 關單
        elif action == 'closeLong' or action == 'closeShort':
            CA.place_order(exchange, pair, action, signal.get('limit'), None, signal.get('percent'), signal.get('clientOrderId'), signal.get('profit'), signal.get('loss'))
        # 開單
        elif action == 'openLong' or action == 'openShort':
            percent = float(signal.get('percent'))
            notional = signal.get('notional')
            if percent is not None:
                # 下以之前的平倉金額percent對應的金額
                notional = self.ca_initial_capital * (percent * 0.01)
            CA.place_order(exchange, pair, action, limit=signal.get('limit'), amount=signal.get('fixed'), percent=percent, client_order_id=signal.get('clientOrderId'), profit=signal.get('profit'), loss=signal.get('loss'), notional=notional)
        else:
            CA.log("🛑 Invalid action")
            
        CA.log(signal.get('log'))

    # 處理單更新
    def on_order_state_change(self,  order):
        exchange, pair, base, quote = CA.get_exchange_pair()
        quote_balance = CA.get_balance(exchange, quote)
        ca_available_capital = quote_balance.available
        ca_position = self.get_ca_position()

        if order.status == CA.OrderStatus.FILLED:
            # 看CA的倉位已經用了多少%的本金去開了
            ca_position_percent_of_capital = (self.ca_initial_capital - ca_available_capital) / self.ca_initial_capital
            CA.log("🎉 現在CA倉位數量: " + str(ca_position) + " =  CA倉位本金%: " + str(ca_position_percent_of_capital * 100) + "  ℹ️ CA入場本金$: " + str(self.ca_initial_capital)  + "  CA可用資金$: " + str(ca_available_capital))
            
      # 平倉時 設置新的開倉金
        if ca_position == 0:
            self.ca_initial_capital = ca_available_capital
            CA.log('⚡新的CA開倉本金: ' + str(self.ca_initial_capital))

    def trade(self, candles):
        pass

    # return current total position: -n 0, +n  where n is number of contracts
    def get_ca_position(self):
        exchange, pair, base, quote = CA.get_exchange_pair()
        long_position = CA.get_position(exchange, pair, CA.PositionSide.LONG)
        if long_position:
            return abs(long_position.total_size)
        short_position = CA.get_position(exchange, pair, CA.PositionSide.SHORT)
        if short_position:
            return -1 * abs(short_position.total_size)
        return  0
