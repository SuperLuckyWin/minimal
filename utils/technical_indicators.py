import talib
import numpy as np


def calculate_ma(close_prices, period):
    """计算移动平均线"""
    return talib.MA(np.array(close_prices), timeperiod=period)


def calculate_rsi(close_prices, period):
    """计算相对强弱指标"""
    return talib.RSI(np.array(close_prices), timeperiod=period)


def calculate_macd(close_prices, fastperiod=12, slowperiod=26, signalperiod=9):
    """计算移动平均线收敛发散指标"""
    return talib.MACD(np.array(close_prices), fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)

def calculate_atr(high_prices, low_prices, close_prices, period=14):
    """计算平均真实波动幅度"""
    high_prices = np.array(high_prices)
    low_prices = np.array(low_prices)
    close_prices = np.array(close_prices)
    return talib.ATR(high_prices, low_prices, close_prices, timeperiod=period)
