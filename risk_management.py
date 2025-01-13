from utils.technical_indicators import calculate_atr

class RiskManager:
    def __init__(self, stop_loss_percentage=0.01, max_drawdown_percentage=0.1,
                 position_size_percentage=0.01, max_daily_loss=0.05, atr_period=14):
        self.stop_loss_percentage = stop_loss_percentage
        self.max_drawdown_percentage = max_drawdown_percentage
        self.position_size_percentage = position_size_percentage
        self.max_daily_loss = max_daily_loss
        self.atr_period = atr_period
        self.initial_balance = None
        self.daily_loss = 0

    def set_initial_balance(self, balance):
       """设置初始余额"""
       self.initial_balance = balance

    def calculate_stop_loss(self, entry_price, klines, stop_loss_type="fixed", volitility=None):
      """计算止损价格"""
      if stop_loss_type == 'fixed':
         return entry_price * (1 - self.stop_loss_percentage)
      elif stop_loss_type == 'volatility':
        if not klines or len(klines) <= self.atr_period:
          return entry_price * (1- self.stop_loss_percentage)
        high_prices = [float(item[2]) for item in klines]
        low_prices = [float(item[3]) for item in klines]
        close_prices = [float(item[4]) for item in klines]
        atr = calculate_atr(high_prices, low_prices, close_prices, self.atr_period)[-1]
        return entry_price - atr * self.stop_loss_percentage

    def calculate_position_size(self, balance, atr=None):
        """计算仓位大小"""
        if atr:
          return  balance * self.position_size_percentage / atr
        else:
          return  balance * self.position_size_percentage

    def check_max_drawdown(self, current_balance):
        """检查最大回撤"""
        if self.initial_balance is None:
            return False
        max_drawdown = 1 - (current_balance / self.initial_balance)
        if max_drawdown >= self.max_drawdown_percentage:
            return True
        return False


    def check_daily_loss(self, current_balance):
        """检查每日最大亏损"""
        if self.initial_balance is None:
            return False
        daily_loss = 1 - (current_balance / self.initial_balance)
        if daily_loss >= self.max_daily_loss:
            return True
        return False
