class Strategy(StrategyBase):
    def __init__(self):
        self.period = 60
        self.subscribed_books = {}
        self.options = {}
        self.curTotalPositionSize = None
        self.ORDER_PORTION = 1

    def on_tradingview_signal(self, signal, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()

        """
        Calculate New Position
        """
        self.newPositionSize = None

        signal_action = signal.get('action')
        log = signal.get('log')

        CA.log('📩 TradingView log: ' + str(log))

        items = log.split("/") # comment/market_position/market_position_size

        if items and len(items) >= 3:
            self.prevPositionSide = items[2]
            self.newPositionSide = items[1] # market_position: long, short, flat

        # if self.newPositionSize is None:
        #     CA.log("failed to parse position size from log " + log)
        #     return

        if self.newPositionSide is None:
            CA.log("⛔ failed to parse position from log " + log)
            return

        # self.newPositionSize = float(self.newPositionSize.strip()) * self.ORDER_PORTION
        # self.prevPositionSize = float(self.prevPositionSize.strip()) * self.ORDER_PORTION

        if self.newPositionSide ==  "long":
            self.newPositionSize = 1
        elif self.newPositionSide == "short":
            self.newPositionSize =  -1
        elif self.newPositionSide == "flat":
            self.newPositionSize = 0 # not sure
        else:
            CA.log("⛔ failed to parse position from log: expect long, short, or flat " + log)
            return

        if self.prevPositionSide ==  "long":
            self.prevPositionSize = 1
        elif self.prevPositionSide == "short":
            self.prevPositionSize =  -1
        elif self.prevPositionSide == "flat":
            self.prevPositionSize = 0 # not sure
        else:
            CA.log("⛔ failed to parse position from log: expect long, short, or flat " + log)
            return

        """
        Set Current Position
        """

        # will be current position
        self.curTotalPositionSize, self.curActualPositionSize = self.get_total_position_size_and_side()

        if self.curTotalPositionSize is None:
            CA.log("⛔ cannot get current total position")
            return

        # will be current position
        CA.log("💬 current Total Position " + str(self.curActualPositionSize))

        # start bot only if we were at 0 signal
        if self.curTotalPositionSize == 0 and self.prevPositionSize != 0:
            CA.log("⚠️ Prev Position is not 0; will wait and start position once we are at 0")
            return


        # 100%
        if self.curTotalPositionSize == self.newPositionSize:
            CA.log("⚠️ Position already synced")
            return

        if self.curTotalPositionSize > self.newPositionSize:
            if self.newPositionSize >= 0:
                # 3 -> 2
                # amount = self.curTotalPositionSize - self.newPositionSize
                CA.log("💬 Amount to close long: " + str(self.curActualPositionSize))
                CA.place_order(action="close_long", exchange=exchange, pair=pair,  percent=100)
            else:
                # 2 -> -1
                if self.curTotalPositionSize > 0:
                    # "closeLong/openShort"
                    # close_long_amount = self.curTotalPositionSize
                    # open_short_amount = abs(self.newPositionSize)
                    CA.log("💬 Amount to close long: " + str(self.curActualPositionSize))
                    CA.log("💬 Amount to open short: 100%")
                    CA.place_order(exchange, pair, action='close_long', percent=100, conditional_order_type='OTO', child_conditional_orders=[{
                        'action': 'open_short', 'percent': 100
                    }])
                else:
                    # -3 -> -2 = 1
                    # amount = abs(self.newPositionSize - self.curTotalPositionSize)
                    CA.log("💬 Amount to open short: " + str(self.curActualPositionSize))
                    CA.place_order(action="open_short", exchange=exchange, pair=pair,  percent=100)
        else:
            if self.newPositionSize <= 0:
                #  -3 -> -1
                # amount = abs(self.curTotalPositionSize - self.newPositionSize)
                CA.log("💬 Amount to close short: " + str(self.curActualPositionSize))
                CA.place_order(action="close_short", exchange=exchange, pair=pair,  percent=100)
            else:
                if self.curTotalPositionSize >= 0:
                    # 1 -> 2
                    # amount = (self.newPositionSize - self.curTotalPositionSize )
                    CA.log("💬 Amount to open long: " + str(self.curActualPositionSize))
                    CA.place_order(action="open_long", exchange=exchange, pair=pair,  percent=100)
                else:
                    # close_short_amount = self.curTotalPositionSize
                    # open_long_amount = abs(self.newPositionSize) 
                    CA.log("💬 Amount to close short: " + str(self.curActualPositionSize))
                    CA.log("💬 Amount to open long:  100%" )
                    CA.place_order(exchange, pair, action='close_short',  percent= 100, conditional_order_type='OTO', child_conditional_orders=[{
                        'action': 'open_long',  'percent': 100
                    }])

    def on_order_state_change(self,  order):
        if order.status == CA.OrderStatus.FILLED:
            CA.log('🎉 LATEST POS: ' + str(self.get_total_position_size_and_side()[0]))

    def trade(self, candles):
        pass

    # return current total position: -n 0, +n  where n is number of contracts
    def get_total_position_size_and_side(self):
        exchange, pair, base, quote = CA.get_exchange_pair()

        curTotalPositionSize = None
        total_long_position_size = None
        total_short_position_size = None

        long_position = CA.get_position(exchange, pair, CA.PositionSide.LONG)
        if long_position:
            total_long_position_size = long_position.total_size

        short_position = CA.get_position(exchange, pair, CA.PositionSide.SHORT)
        if short_position:
            total_short_position_size = short_position.total_size

        if total_long_position_size is None and total_short_position_size is None:
            curTotalPositionSize = (0,0)

        if total_long_position_size is not None:
            curTotalPositionSize = (abs(total_long_position_size),1)

        if total_short_position_size is not None:
            curTotalPositionSize = (-1 * abs(total_short_position_size),-1)

        return curTotalPositionSize
