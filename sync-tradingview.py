class Strategy(StrategyBase):
    def __init__(self):
        self.period = 60
        self.subscribed_books = {}
        self.options = {}
        exchange, pair, base, quote = CA.get_exchange_pair()
        quote_balance = CA.get_balance(exchange, quote)
        self.ca_initial_capital = quote_balance.available
        self.ca_total_capital = quote_balance.available
        CA.log('Total inital ' + str(quote) + ' quote amount: ' + str(self.ca_total_capital))

    def on_tradingview_signal(self, signal, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()
        leverage = int(CA.get_leverage())
        log = signal.get('log')
        CA.log('? TradingView log: ' + str(log))

        """
        "entryOrder mode": 每次開單的設定
        1. "compoundAvailableBalancePercent" 用復利可用資金去下%
        2. "noCompoundAvailableBalancePercent" 用單利去下%
        3. "totalBalancePercent" 用空倉時的資金固定去下%
        4. "fixedTotalBalance" 用固定初始本金去下 需要 size and price
        ex. "entryOrder": {
                "value": 100,
                "mode": "fixedTotalBalance",
                "size": {{strategy.order.contracts}},
                "price": {{strategy.order.price}},
            }
        ===   
{
   "connectorName":"REPLACE_NAME",
   "connectorToken":"REPLACE_TOKEN",
   "log":"short",
   "entryOrder":{
      "value":100,
      "mode":"compoundAvailableBalancePercent"
   },
   "position":{
      "side":"{{strategy.market_position}}",
      "size":{{strategy.market_position_size}},
      "prev_side":"{{strategy.prev_market_position}}",
      "prev_size":{{strategy.prev_market_position_size}}
   }
}
        """

        position = signal.get('position')
        entryOrder = signal.get('entryOrder')
        if not position or not entryOrder:
            return CA.log('⛔ Invalid signal,  missing position or entryOrder')

        tv_order_mode = entryOrder.get("mode") # availableBalancePercent, totalBalancePercent, fixedTotalBalance
        tv_order_value = entryOrder.get("value")
        tv_order_size = entryOrder.get("size")
        tv_order_price = entryOrder.get("price")
        
        tv_position = self.get_position_from_size_and_side(position.get("size"), position.get("side"))
        tv_prev_position = self.get_position_from_size_and_side(position.get("prev_size"), position.get("prev_side"))


        # 檢查訊號正確性
        if tv_order_mode is None or tv_position is None:
            return CA.log('⛔ Invalid signal, missing tv_order_mode or tv_position')

        ca_position = self.get_ca_position()
        quote_balance = CA.get_balance(exchange, quote)
        ca_available_capital = quote_balance.available

        # 如果不能給之前的倉位那就 預設至 ca_position
        if tv_prev_position is None:
            tv_prev_position = ca_position


        """
        如果反向開單或是加倉
        """
        if (abs(tv_position) > abs(tv_prev_position) and tv_position * tv_prev_position >= 0) or tv_position * tv_prev_position < 0:
            ca_order_captial = ca_available_capital
            # PPC  複利
            if tv_order_mode == "compoundAvailableBalancePercent":
                ca_order_captial = None
                tv_order_percent_of_capitial = tv_order_value
                
                newOrderAmount = dict(percent=tv_order_percent_of_capitial * int(CA.get_leverage()))   # default to 1
                CA.log("CA開倉比例% " + str(tv_order_percent_of_capitial * int(CA.get_leverage())) + " \n CA下單金額%" + str(tv_order_percent_of_capitial * int(CA.get_leverage())) +  " \n CA入場本金$: " + str(self.ca_total_capital)  + " \n CA可用資金$: " + str(ca_available_capital))
            # 單利
            elif tv_order_mode == "noCompoundAvailableBalancePercent":
                ca_order_captial = None
                diff = ca_available_capital - self.ca_initial_capital
                tv_order_percent_of_capitial = tv_order_value
                # 賺錢
                if diff > 0:
                    # 算多賺的是幾％
                    offset_percent = (diff / ca_available_capital) * 100
                    tv_order_percent_of_capitial = tv_order_value - offset_percent
                newOrderAmount = dict(percent=tv_order_percent_of_capitial * int(CA.get_leverage()))   # default to 1
                CA.log("CA開倉比例% " + str(tv_order_percent_of_capitial * int(CA.get_leverage())) + " \n CA下單金額%" + str(tv_order_percent_of_capitial * int(CA.get_leverage())) +  " \n CA入場本金$: " + str(newOrderAmount)  + " \n CA可用資金$: " + str(ca_available_capital))
            # 下固定金額
            elif tv_order_mode == "noCompoundAvailableBalanceNotional":
                ca_order_captial = tv_order_value
                # 不夠開
                if ca_available_capital < tv_order_value: 
                    ca_order_captial = ca_available_capital
                notional = ca_order_captial * int(CA.get_leverage()) # default to 1
                newOrderAmount = dict(notional = notional)   
                CA.log( " \n CA下單金額$ " + str(notional) + " \n CA可用資金$: " + str(ca_available_capital))
            # 下固定 contract
            elif tv_order_mode == "FixedAssetTrade":
                newOrderAmount = dict(amount = tv_order_value )   
                # CA.log( " \n CA下單金額$ " + str(notional) + " \n CA可用資金$: " + str(ca_available_capital))
            # PPC  複利 加倉
            elif tv_order_mode == "totalBalancePercent":
                ca_order_captial = self.ca_total_capital
                tv_order_percent_of_capitial = tv_order_value / 100
                 # 用CA空倉時的金額去下開或加倉的金額
                notional = ca_order_captial * tv_order_percent_of_capitial * int(CA.get_leverage()) # default to 1
                newOrderAmount = dict(notional = notional)   
                CA.log("CA開倉比例% " + str(tv_order_percent_of_capitial * 100 * int(CA.get_leverage())) + " \n CA下單金額$ " + str(notional) +  " \n CA入場本金$: " + str(self.ca_total_capital)  + " \n CA可用資金$: " + str(ca_available_capital))
            elif tv_order_mode == "fixedTotalBalance":
                ca_order_captial = self.ca_total_capital
                # close short -> open long (一個正 一個反) 有一些order數量是反轉時要關艙的 所以要拿掉
                if tv_position * tv_prev_position < 0: # 代表倉位方向不一樣
                    tv_order_size = tv_order_size - abs(tv_prev_position) # 其實就是 tv_position
                # 用下單金額和權益去反推TV下單% tv_order_value 是我們的固定本金
                tv_order_percent_of_capitial = (tv_order_size * tv_order_price) / tv_order_value
                 # 用CA空倉時的金額去下開或加倉的金額
                notional = ca_order_captial * tv_order_percent_of_capitial * int(CA.get_leverage()) # default to 1
                newOrderAmount = dict(notional = notional)   
                CA.log("CA開倉比例% " + str(tv_order_percent_of_capitial * 100 * int(CA.get_leverage())) + " \n CA下單金額$ " + str(notional) +  " \n CA入場本金$: " + str(self.ca_total_capital)  + " \n CA可用資金$: " + str(ca_available_capital))
            else:
                return CA.log("⛔ Invalid tv_order_mode" + str(tv_order_mode))
            
            # close short -> open long 不用管 prev_tv_position 因為我們知道一定會開多 但是要先確保 CA 倉位是對的
            if tv_position > 0 and ca_position < 0:
                CA.log("先全關空倉在開多")
                return CA.place_order(exchange, pair, action='close_short', conditional_order_type='OTO', percent=100,
                                   child_conditional_orders=[{'action': 'open_long',  **newOrderAmount}])

            # close long -> open short 不用管 prev_tv_position 因為我們知道一定會開空 但是要先確保 CA 倉位是對的
            elif tv_position < 0 and ca_position > 0:
                CA.log("先全關多倉在開空")
                return CA.place_order(exchange, pair, action='close_long', conditional_order_type='OTO', percent=100,
                                   child_conditional_orders=[{'action': 'open_short', **newOrderAmount}])

            # CA 倉位是在對的方向
            action = "open_long" if tv_position > 0 else "open_short"
            CA.log("newOrderAmount" + str(newOrderAmount))
            return CA.place_order(exchange, pair, action=action, **newOrderAmount)
        # 照比例關艙區
        else: 
            # 沒有倉位不用關
            if ca_position == 0:
                return CA.log("沒有倉位不用關")

            # flat 全關
            if tv_position == 0:
                action = "close_long" if ca_position > 0 else "close_short"
                return CA.place_order(exchange, pair, action=action, percent=100)
            elif tv_position > 0 and ca_position < 0:
                CA.log("倉位錯亂 全關空倉")
                return CA.place_order(exchange, pair, action="close_short", percent=100)
            elif tv_position < 0 and ca_position > 0:
                CA.log("倉位錯亂 全關多倉")
                return CA.place_order(exchange, pair, action="close_long" , percent=100)


            # 用TV前和後倉位去看關了多少 不行超過 1
            tv_order_percent_of_position = min((tv_prev_position - tv_position) / tv_prev_position, 1) * 100
            
            CA.log("關倉比例% " + str(tv_order_percent_of_position))

            action = "close_long" if tv_prev_position > 0 else "close_short"
            return CA.place_order(exchange, pair, action=action, percent=tv_order_percent_of_position)

    def trade(self, candles):
        pass
    
    def on_order_state_change(self,  order):
        exchange, pair, base, quote = CA.get_exchange_pair()
        quote_balance = CA.get_balance(exchange, quote)
        ca_available_capital = quote_balance.available
        ca_position = self.get_ca_position()

        if order.status == CA.OrderStatus.FILLED:
            # 看CA的倉位已經用了多少%的本金去開了
            ca_position_percent_of_capital = (self.ca_total_capital - ca_available_capital) / self.ca_total_capital
            CA.log("? 現在CA倉位數量: " + str(ca_position) + " 本金%: " + str(ca_position_percent_of_capital * 100 *  int(CA.get_leverage()))+ " \n CA入場本金$: " + str(self.ca_total_capital)  + " \n CA可用資金$: " + str(ca_available_capital))
            
      # 平倉時 設置新的開倉金
        if ca_position == 0:
            self.ca_total_capital = ca_available_capital
            CA.log('新的CA開倉本金: ' + str(self.ca_total_capital))
            
    def get_position_from_size_and_side(self, positionSize, positionSide):
        if positionSide is None or positionSize is None:
            return None
        if positionSide ==  "long":
            return abs(positionSize)
        elif positionSide == "short":
            return abs(positionSize) * -1
        elif positionSide == "flat":
            return 0 # not sure
        return None

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
    
