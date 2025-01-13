from utils.technical_indicators import calculate_ma, calculate_rsi, calculate_macd, calculate_atr
from utils.pattern_recognition import is_hammer, is_engulfing
from data_manager import DataManager
from utils.news_analysis import NewsAnalyzer
from utils.ml_model import SimpleLinearRegression
from config import NEWS_SOURCE, KEYWORDS


class AdvancedStrategy:
    def __init__(self, data_manager, symbols, ma_periods=(20, 50, 100), rsi_period=14,
                 macd_fast=12, macd_slow=26, macd_signal=9, atr_period=14, news_interval=60, ml_lookback=20):
        self.data_manager = data_manager
        self.symbols = symbols
        self.ma_periods = ma_periods
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.news_analyzer = NewsAnalyzer(news_source=NEWS_SOURCE, keywords=KEYWORDS, interval=news_interval)
        self.ml_lookback = ml_lookback
        self.ml_model = SimpleLinearRegression()
        self.last_trend = {} # 使用字典存储每个币种的趋势

    def calculate_trend(self, klines, symbol):
        """计算趋势"""
        if not klines or len(klines) < max(self.ma_periods) + 1:
            return None
        close_prices = [float(item[4]) for item in klines]
        ma_short = calculate_ma(close_prices, self.ma_periods[0])[-1]
        ma_medium = calculate_ma(close_prices, self.ma_periods[1])[-1]
        ma_long = calculate_ma(close_prices, self.ma_periods[2])[-1]
        if ma_short > ma_medium > ma_long:
            self.last_trend[symbol] = 'UP'
            return 'UP'
        elif ma_short < ma_medium < ma_long:
            self.last_trend[symbol] = 'DOWN'
            return 'DOWN'
        else:
            self.last_trend[symbol] = 'CONSOLIDATION'
            return 'CONSOLIDATION'

    def generate_entry_signal(self, klines, trades, orderbook, symbol):
        """生成入场信号"""
        if not klines or len(klines) < max(self.ma_periods) + 1:
            return None
        close_prices = [float(item[4]) for item in klines]
        high_prices = [float(item[2]) for item in klines]
        low_prices = [float(item[3]) for item in klines]
        open_prices = [float(item[1]) for item in klines]
        current_price = close_prices[-1]
        trend = self.calculate_trend(klines, symbol)
        if not trend:
            return None
        rsi = calculate_rsi(close_prices, self.rsi_period)[-1]
        macd, signal, hist = calculate_macd(close_prices, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
        news_signal = self.news_analyzer.generate_signal()
        if trend == 'UP':
            if is_hammer(high_prices[-3:], low_prices[-3:], close_prices[-3:]) or \
               is_engulfing(open_prices[-2:], high_prices[-2:], low_prices[-2:], close_prices[-2:]) and \
               rsi > 30 and macd > signal and news_signal != 'SELL':
                # 判断订单薄买方是否足够
                if orderbook and len(orderbook['bids']) > 0:
                    total_bid_qty = sum(float(bid[1]) for bid in orderbook['bids'][:5])
                    total_ask_qty = sum(float(ask[1]) for ask in orderbook['asks'][:5])
                    if total_bid_qty > total_ask_qty:
                       return 'BUY'
        elif trend == 'DOWN':
             if is_hammer(high_prices[-3:], low_prices[-3:], close_prices[-3:]) or \
                is_engulfing(open_prices[-2:], high_prices[-2:], low_prices[-2:], close_prices[-2:]) and \
               rsi < 70 and macd < signal and news_signal != 'BUY':
                 if orderbook and len(orderbook['asks']) > 0:
                    total_bid_qty = sum(float(bid[1]) for bid in orderbook['bids'][:5])
                    total_ask_qty = sum(float(ask[1]) for ask in orderbook['asks'][:5])
                    if total_bid_qty < total_ask_qty:
                       return 'SELL'

        return None


    def generate_exit_signal(self, klines, positions, entry_price, atr=None, symbol = None):
       """生成出场信号"""
       if not klines or len(klines) < self.ma_periods[0]:
         return None
       close_prices = [float(item[4]) for item in klines]
       current_price = close_prices[-1]
       if symbol and symbol in self.last_trend:
           trend = self.last_trend[symbol]
       else:
           trend = self.calculate_trend(klines, symbol)

       if not positions:
         return None
       if positions['side'] == 'BUY':
         if current_price < entry_price: # 追踪止损
           return 'SELL'
         if trend == 'DOWN':
             return 'SELL'
       elif positions['side'] == 'SELL':
         if current_price > entry_price:
           return 'BUY'
         if trend == 'UP':
            return 'BUY'
       return None

    def predict_price_trend(self, klines):
      """使用线性回归模型预测价格趋势"""
      if not klines or len(klines) < self.ml_lookback * 2:
         return 0

      close_prices = [float(item[4]) for item in klines]
      x = list(range(len(close_prices) - self.ml_lookback, len(close_prices)))
      y = close_prices[-self.ml_lookback:]

      self.ml_model.train(x, y)
      last_price = x[-1] + 1
      predicted_price = self.ml_model.predict(last_price)
      return predicted_price - close_prices[-1]

    def generate_signal(self, symbol):
      """生成交易信号"""
      klines = self.data_manager.get_data(symbol, 'klines', limit=max(self.ma_periods) + 10)
      trades = self.data_manager.get_data(symbol, 'trades', limit=20)
      orderbook = self.data_manager.get_data(symbol, 'orderbook', limit=5)
      if not klines or not trades:
         return None
      entry_signal = self.generate_entry_signal(klines, trades, orderbook, symbol)
      if entry_signal:
          return entry_signal
      return None
