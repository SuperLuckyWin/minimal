import talib
import numpy as np

def is_hammer(high_prices, low_prices, close_prices):
    """判断是否出现锤子线"""
    high_prices = np.array(high_prices)
    low_prices = np.array(low_prices)
    close_prices = np.array(close_prices)
    hammer = talib.CDLHAMMER(high_prices, low_prices, close_prices)
    return hammer[-1] > 0

def is_engulfing(open_prices, high_prices, low_prices, close_prices):
    """判断是否出现吞没形态"""
    open_prices = np.array(open_prices)
    high_prices = np.array(high_prices)
    low_prices = np.array(low_prices)
    close_prices = np.array(close_prices)
    bullish = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices)
    return bullish[-1] > 0
