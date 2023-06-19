class Strategy(StrategyBase):
    def __init__(self):
        self.period = 60
        self.subscribed_books = {}
        self.options = {}
        exchange, pair, base, quote = CA.get_exchange_pair()
        CA_QUOTE_BALANCE = CA.get_balance(exchange, quote)
        self.CA_INITIAL_QUOTE = CA_QUOTE_BALANCE.available
        self.CA_TOTAL_CAPITAL_AT_NO_POSITION = CA_QUOTE_BALANCE.available
        CA.log('Total inital ' + str(quote) + ' quote amount: ' + str(self.CA_TOTAL_CAPITAL_AT_NO_POSITION))

    def on_tradingview_signal(self, signal, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()
        log = signal.get('log')
        CA.log('TradingView log: ' + str(log))

        position = signal.get('position')
        entryOrder = signal.get('entryOrder')
        if not position or not entryOrder:
            return CA.log('⛔ Invalid signal,  missing position or entryOrder')

        TV_ORDER_MODE = entryOrder.get("mode") # availableBalancePercent, totalBalancePercent, fixedTotalBalance
        TV_ORDER_VALUE = entryOrder.get("value")
        TV_ORDER_SIZE = entryOrder.get("size")
        TV_ORDER_PRICE = entryOrder.get("price")
        
        TV_POSITION = self.get_position_from_size_and_side(position.get("size"), position.get("side"))
        TV_PREV_POSITION = self.get_position_from_size_and_side(position.get("prev_size"), position.get("prev_side"))

        # 檢查訊號正確性
        if TV_ORDER_MODE is None or TV_POSITION is None:
            return CA.log('⛔ Invalid signal, missing TV_ORDER_MODE or TV_POSITION')

        CA_POSITION = self.get_ca_position()
        CA_QUOTE_BALANCE = CA.get_balance(exchange, quote)
        CA_AVILABLE_QUOTE = CA_QUOTE_BALANCE.available

        # 如果不能給之前的倉位那就 預設至 CA_POSITION
        if TV_PREV_POSITION is None:
            TV_PREV_POSITION = CA_POSITION

        """
        If reverse position or adding to position
        """
        if (abs(TV_POSITION) > abs(TV_PREV_POSITION) and TV_POSITION * TV_PREV_POSITION >= 0) or TV_POSITION * TV_PREV_POSITION < 0:
            ca_order_captial = CA_AVILABLE_QUOTE
            newOrderArgs = None
            
            # Percentage of balance with compounding: "Trade a percentage (entry value) of your balance, including profits. E.g., with 100U, a 10% trade uses 10U, and the next 10% trade uses 9U from the remaining 90U."
            if TV_ORDER_MODE == "Percentage of Balance with Compounding":
                percent = TV_ORDER_VALUE * CA.get_leverage()
                newOrderArgs = dict(percent=percent)   # default to 1
            
            # Percentage of initial balance only: "Trade a percentage  (entry value) of your initial balance, excluding profits. E.g., with 100U, even if it grows to 130U, a 10% trade uses 10U, based on the initial 100U."
            elif TV_ORDER_MODE == "Percentage of Initial Balance Only":
                profitQuote = CA_AVILABLE_QUOTE - self.CA_INITIAL_QUOTE
                if profitQuote > 0:
                    offset_percent = (diff / CA_AVILABLE_QUOTE) * 100
                    TV_ORDER_VALUE -= offset_percent
                percent = TV_ORDER_VALUE * CA.get_leverage()
                newOrderArgs = dict(percent=percent) 
            # Fixed amount from available balance: "Trade a fixed quote amount  (entry value). E.g., an entry vaule of 100U opens a position worth 100U."
            elif TV_ORDER_MODE == "Fixed Quote Amount":
                TV_ORDER_VALUE = min(TV_ORDER_VALUE, CA_AVILABLE_QUOTE)
                notional = TV_ORDER_VALUE * CA.get_leverage() # default to 1
                newOrderArgs = dict(notional = notional)   
            # Strategy Base Amount: "Trade base asset amount based on TradingView Strategy's amount E.g., Follows the exact contract amount from TradingView."
            elif TV_ORDER_MODE == "Strategy Order Size":
                # Will not use TV_ORDER_VALUE
                if TV_POSITION * TV_PREV_POSITION < 0:
                    TV_ORDER_SIZE -= abs(TV_PREV_POSITION)
                newOrderArgs = dict(amount = TV_ORDER_SIZE)
            # Fixed base asset amount: "Trade a fixed base asset amount  (entry value). E.g., an entry vaule of 1ETH opens a position worth 1ETH."
            elif TV_ORDER_MODE == "Fixed Base Amount":
                newOrderArgs = dict(amount = TV_ORDER_VALUE)   
            # Percentage of balance at no position: "When adding to a position, use a percentage (entry value) of your total balance when no position is open. E.g., with 100U (no position), entering 10% and another 20% uses 10U and 20U."
            elif TV_ORDER_MODE == "Percentage of Balance at No Position":
                TV_ORDER_VALUE /= 100
                notional = self.CA_TOTAL_CAPITAL_AT_NO_POSITION * TV_ORDER_VALUE * CA.get_leverage()
                newOrderArgs = dict(notional = notional)   
            # Fixed capital for investment percentage: "Use a fixed capital amount  (entry value) to calculate the investment percentage. This could be the equity of your TradingView strategy or a fixed investment amount."
            elif TV_ORDER_MODE == "Strategy Percentage with Fixed Capital":
                # close short -> open long (一個正 一個反) 有一些order數量是反轉時要關艙的 所以要拿掉
                if TV_POSITION * TV_PREV_POSITION < 0: # 代表倉位方向不一樣
                    TV_ORDER_SIZE -= abs(TV_PREV_POSITION) # 其實就是 TV_POSITION
                # 用下單金額和權益去反推TV下單% TV_ORDER_VALUE 是我們的固定本金
                TV_ORDER_VALUE = (TV_ORDER_SIZE * TV_ORDER_PRICE) / TV_ORDER_VALUE
                 # 用CA空倉時的金額去下開或加倉的金額
                notional = self.CA_TOTAL_CAPITAL_AT_NO_POSITION * TV_ORDER_VALUE * CA.get_leverage() # default to 1
                newOrderArgs = dict(notional = notional)   
            else:
                return CA.log("⛔ Invalid TV_ORDER_MODE: " + str(TV_ORDER_MODE))

            if not newOrderArgs:
                return CA.log("⛔ Failed to place order based on the TV signal")

            # close short -> open long 不用管 prev_tv_position 因為我們知道一定會開多 但是要先確保 CA 倉位是對的
            if TV_POSITION > 0 and CA_POSITION < 0:
                CA.log("Close all short position then open long")
                return CA.place_order(exchange, pair, action='close_short', conditional_order_type='OTO', percent=100,
                                   child_conditional_orders=[{'action': 'open_long',  **newOrderArgs}])

            # close long -> open short 不用管 prev_tv_position 因為我們知道一定會開空 但是要先確保 CA 倉位是對的
            elif TV_POSITION < 0 and CA_POSITION > 0:
                CA.log("Close all long position then open short")
                return CA.place_order(exchange, pair, action='close_long', conditional_order_type='OTO', percent=100,
                                   child_conditional_orders=[{'action': 'open_short', **newOrderArgs}])

            # CA 倉位是在對的方向
            action = "open_long" if TV_POSITION > 0 else "open_short"
            CA.log("New Order: " + str(newOrderArgs))
            return CA.place_order(exchange, pair, action=action, **newOrderArgs)
        # 照比例關艙區
        else: 
            # 沒有倉位不用關
            if CA_POSITION == 0:
                return CA.log("Skip closing since there is no open position")
            # flat 全關
            if TV_POSITION == 0:
                action = "close_long" if CA_POSITION > 0 else "close_short"
                return CA.place_order(exchange, pair, action=action, percent=100)
            elif TV_POSITION > 0 and CA_POSITION < 0:
                CA.log("TV and CA positions conflic - Close all short")
                return CA.place_order(exchange, pair, action="close_short", percent=100)
            elif TV_POSITION < 0 and CA_POSITION > 0:
                CA.log("TV and CA positions conflic - Close all long")
                return CA.place_order(exchange, pair, action="close_long" , percent=100)


            # 用TV前和後倉位去看關了多少 不行超過 1
            tv_order_percent_of_position = min((TV_PREV_POSITION - TV_POSITION) / TV_PREV_POSITION, 1) * 100
            
            CA.log("Close Position%: " + str(tv_order_percent_of_position))

            action = "close_long" if TV_PREV_POSITION > 0 else "close_short"
            return CA.place_order(exchange, pair, action=action, percent=tv_order_percent_of_position)

    def trade(self, candles):
        pass
    
    def on_order_state_change(self,  order):
        exchange, pair, base, quote = CA.get_exchange_pair()
        CA_QUOTE_BALANCE = CA.get_balance(exchange, quote)
        CA_AVILABLE_QUOTE = CA_QUOTE_BALANCE.available
        CA_POSITION = self.get_ca_position()

        if order.status == CA.OrderStatus.FILLED:
            # 看CA的倉位已經用了多少%的本金去開了
            ca_position_percent_of_capital = (self.CA_TOTAL_CAPITAL_AT_NO_POSITION - CA_AVILABLE_QUOTE) / self.CA_TOTAL_CAPITAL_AT_NO_POSITION
            CA.log("Position: " + str(CA_POSITION) + "\n Position %: " + str(ca_position_percent_of_capital * 100) + " \n Available Quote$: " + str(CA_AVILABLE_QUOTE) )
            
      # 平倉時 設置新的開倉金
        if CA_POSITION == 0:
            self.CA_TOTAL_CAPITAL_AT_NO_POSITION = CA_AVILABLE_QUOTE
            CA.log('Availabe Quote at No Position: ' + str(self.CA_TOTAL_CAPITAL_AT_NO_POSITION))
            
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
    
