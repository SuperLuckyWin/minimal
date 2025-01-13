import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
import requests
import websockets
import base64
import uuid

from config import OKX_API_KEY, OKX_API_SECRET, OKX_API_PASSPHRASE, OKX_BASE_URL, OKX_WS_URL, OKX_PRIVATE_WS_URL, TOP_N_VOLUME, MAX_SYMBOLS


def generate_signature_okx(timestamp, method, request_path, body, secret):
   """生成 OKX 请求签名"""
   message = str(timestamp) + method.upper() + request_path + (str(body) if body else '')
   mac = hmac.new(bytes(secret, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
   d = mac.digest()
   return base64.b64encode(d)


def send_signed_request_okx(method, url, params=None, body=None):
    """发送带签名的请求"""
    timestamp = str(int(time.time()))
    headers = {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": generate_signature_okx(timestamp, method, url, body, OKX_API_SECRET),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
        "Content-Type": "application/json" if body else 'application/x-www-form-urlencoded'
    }
    if params is None:
      params = {}
    if body:
        response = requests.request(method, OKX_BASE_URL+url, headers=headers, params=params, data=json.dumps(body))
    else:
       response = requests.request(method, OKX_BASE_URL + url, headers=headers, params=params)

    response.raise_for_status()
    return response.json()

def get_ticker_okx(symbol):
    """获取 OKX ticker 信息"""
    return send_signed_request_okx('GET', '/api/v5/market/ticker', {'instId': symbol})

def get_orderbook_okx(symbol, limit=5):
    """获取 OKX 深度图"""
    return send_signed_request_okx('GET', '/api/v5/market/books', {'instId': symbol, 'sz': limit})


def get_klines_okx(symbol, interval, limit=100, startTime=None, endTime=None):
    """获取 OKX K线数据"""
    params = {'instId': symbol, 'bar': interval, 'limit': limit}
    if startTime:
      params['after'] = startTime
    if endTime:
      params['before'] = endTime
    return send_signed_request_okx('GET', '/api/v5/market/candles', params=params)

def get_trades_okx(symbol, limit=100):
    """获取 OKX 最近成交记录"""
    return send_signed_request_okx('GET', '/api/v5/market/trades', {'instId': symbol, 'limit': limit})

def get_account_balance_okx():
   """获取 OKX 账户余额"""
   return send_signed_request_okx('GET', '/api/v5/account/balance')

def get_positions_okx(symbol):
  """获取 OKX 持仓信息"""
  return send_signed_request_okx('GET','/api/v5/account/positions', {'instId': symbol})


def create_order_okx(symbol, side, type, quantity, price=None, stopPrice=None, clientOid=None):
    """下单 OKX"""
    if not clientOid:
        clientOid = str(uuid.uuid4())
    params = {
        'instId': symbol,
        'side': side.lower(),
        'ordType': type.lower(),
        'sz': str(quantity),
        'clOrdId': clientOid
    }
    if price:
        params['px'] = str(price)
    if stopPrice:
        params['triggerPx'] = str(stopPrice)
        params['orderType'] = 'trigger'
    return send_signed_request_okx('POST', '/api/v5/trade/order', body=params)


def cancel_order_okx(symbol, orderId):
   """取消订单 OKX"""
   return send_signed_request_okx('POST', '/api/v5/trade/cancel-order', body={'instId': symbol, 'ordId': orderId})

async def start_private_data_stream_okx(symbols):
    """启动 OKX 私有数据流"""
    params = {
      "op": "subscribe",
      "args": []
    }
    for symbol in symbols:
      params['args'].append(
          {
           "channel": "orders",
            "instId": symbol
            }
      )
      params['args'].append(
          {
           "channel": "balance",
            "ccy": "USDT"
            }
       )

    ws_url = f'{OKX_PRIVATE_WS_URL}'
    return ws_url, params


async def process_private_data_stream_okx(ws_url, params, data_queue):
    """处理 OKX 私有数据流"""
    async with websockets.connect(ws_url) as websocket:
        await websocket.send(json.dumps(params))
        async for message in websocket:
          try:
              data = json.loads(message)
              if data['event'] == 'subscribe':
                print('subscribe success!')
              if data['data'] and len(data['data']) > 0 :
                  data_queue.put(data)
          except json.JSONDecodeError:
            print(f'Error decoding json message: {message}')


def get_top_volume_coins(limit=100):
    """获取 CoinGecko 上交易量前 N 的币种"""
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page={limit}&page=1&sparkline=false&locale=en"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    #返回列表，元素为 'BTC-USDT-SWAP' 格式
    return [item['symbol'].upper() + "-USDT-SWAP" for item in data]
