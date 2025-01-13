import asyncio
import queue
import time
from api import get_ticker_okx, get_orderbook_okx, get_trades_okx, get_account_balance_okx, create_order_okx, cancel_order_okx, get_klines_okx, get_top_volume_coins
from data_manager import DataManager
from strategies.advanced_strategy import AdvancedStrategy
from risk_management import RiskManager
from config import OKX_WS_URL, OKX_BASE_URL, INTERVAL, TRADE_QTY, TOP_N_VOLUME, MAX_SYMBOLS
import logging
import random
import uuid


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def main():
    data_queue = queue.Queue()
    data_manager = DataManager()
    risk_manager = RiskManager()
    all_symbols = get_top_volume_coins(limit=TOP_N_VOLUME)
    symbols = all_symbols[:MAX_SYMBOLS] # 限制币种数量
    logging.info(f'Trading Symbols: {symbols}')

    # 初始化策略
    strategy = AdvancedStrategy(data_manager, symbols)
    trade_history = {}
    positions = {}


    # 获取账户初始余额
    account_balance = get_account_balance_okx()
    if account_balance and 'data' in account_balance and len(account_balance['data'])> 0:
       initial_balance = float(account_balance['data'][0]['details'][0]['cashBal'])
       risk_manager.set_initial_balance(initial_balance)
       logging.info(f"Initial account balance: {initial_balance} USDT")
    else:
        logging.error("Could not retrieve initial account balance. Exiting.")
        return
    # 订阅用户数据流，用于更新订单信息
    from api import start_private_data_stream_okx, process_private_data_stream_okx
    ws_url, params = await start_private_data_stream_okx(symbols)

    async def stream_handler(ws_url, params, data_queue):
      """处理用户数据流，并将数据更新到队列"""
       try:
         await process_private_data_stream_okx(ws_url, params, data_queue)
       except Exception as e:
          logging.error(f'Error processing user data stream: {e}')

    # 启动数据流处理，并使用单独的协程运行
    asyncio.create_task(stream_handler(ws_url, params, data_queue))
    #主循环
    while True:
        try:
          for symbol in symbols:
            # 获取市场数据
            ticker = get_ticker_okx(symbol)
            orderbook = get_orderbook_okx(symbol, limit=20)
            trades = get_trades_okx(symbol)
            klines = get_klines_okx(symbol, INTERVAL, limit=100)
            current_balance = get_account_balance_okx()
            if not ticker or not orderbook or not trades or not klines or not current_balance or 'data' not in current_balance or len(current_balance['data']) == 0:
                logging.warning(f'Could not fetch market data for {symbol}.')
                continue

            current_price = float(ticker['data'][0]['last'])
            data_manager.update_data(symbol, 'ticker', ticker)
            data_manager.update_data(symbol, 'orderbook', orderbook)
            data_manager.update_data(symbol, 'trades', trades)
            data_manager.update_data(symbol, 'klines', klines)

            if 'data' in current_balance and len(current_balance['data'])>0:
                current_balance = float(current_balance['data'][0]['details'][0]['cashBal'])
            else:
                logging.warning("Could not retrieve current balance.")
                continue

            # 生成交易信号
            signal = strategy.generate_signal(symbol)
            if signal and symbol not in positions:
                # 进入交易
                atr = calculate_atr([float(k[2]) for k in klines], [float(k[3]) for k in klines], [float(k[4]) for k in klines])[-1]
                stop_loss_price = risk_manager.calculate_stop_loss(current_price, klines, stop_loss_type='volatility', volitility=atr)
                position_size = risk_manager.calculate_position_size(current_balance, atr=atr)
                if signal == 'BUY':
                     order = create_order_okx(symbol, 'BUY', 'MARKET', quantity=TRADE_QTY)
                     if order and 'data' in order and len(order['data']) > 0:
                       positions[symbol] = {}
                       positions[symbol]['orderId'] = order['data'][0]['ordId']
                       positions[symbol]['entry_price'] = current_price
                       positions[symbol]['side'] = 'BUY'
                       positions[symbol]['stop_loss'] = stop_loss_price
                       trade_history[symbol]=order
                       logging.info(f'BUY order placed at {current_price} for {symbol}. orderId: {order["data"][0]["ordId"]}. stop_loss: {stop_loss_price}')

                elif signal == 'SELL':
                    order = create_order_okx(symbol, 'SELL', 'MARKET', quantity=TRADE_QTY)
                    if order and 'data' in order and len(order['data'])>0:
                      positions[symbol] = {}
                      positions[symbol]['orderId'] = order['data'][0]['ordId']
                      positions[symbol]['entry_price'] = current_price
                      positions[symbol]['side'] = 'SELL'
                      positions[symbol]['stop_loss'] = stop_loss_price
                      trade_history[symbol]=order
                      logging.info(f'SELL order placed at {current_price} for {symbol}. orderId: {order["data"][0]["ordId"]}. stop_loss: {stop_loss_price}')

            elif symbol in positions:
               # 检测出场信号
              exit_signal = strategy.generate_exit_signal(klines, positions[symbol], positions[symbol]['entry_price'], symbol = symbol)
              if exit_signal:
                if exit_signal == 'SELL' and positions[symbol]['side'] == 'BUY':
                    order = create_order_okx(symbol, 'SELL', 'MARKET', quantity=TRADE_QTY)
                    if order and 'data' in order and len(order['data'])>0:
                        del positions[symbol]
                        trade_history[symbol] = order
                        logging.info(f'Close BUY position at {current_price} for {symbol}. orderId: {order["data"][0]["ordId"]}')

                elif exit_signal == 'BUY' and positions[symbol]['side'] == 'SELL':
                    order = create_order_okx(symbol, 'BUY', 'MARKET', quantity=TRADE_QTY)
                    if order and 'data' in order and len(order['data'])>0 :
                        del positions[symbol]
                        trade_history[symbol] = order
                        logging.info(f'Close SELL position at {current_price} for {symbol}. orderId: {order["data"][0]["ordId"]}')


            # 处理用户数据流
            while not data_queue.empty():
              data = data_queue.get()
              if data and 'data' in data and len(data['data']) > 0 :
                   for item in data['data']:
                      if 'ordId' in item and any(item['ordId'] == o['data'][0]['ordId'] for o in trade_history.values()):
                          logging.info(f'Order {item["ordId"]} for {symbol} filled at price {item["tradePx"]}. Side {item["side"]} quantity {item["sz"]}')
                          for symbol_key, order_data in trade_history.items():
                            if order_data['data'][0]['ordId'] == item['ordId']:
                                del trade_history[symbol_key]
                                break
                      if 'bal' in item :
                        logging.info(f'Account update. Balance:{item["bal"]}')

          # 检查风险管理规则
          if risk_manager.check_max_drawdown(current_balance):
            logging.warning('Max drawdown limit reached. stopping trade.')
            break

          if risk_manager.check_daily_loss(current_balance):
            logging.warning('Max daily loss limit reached. stopping trade.')
            break
          time.sleep(1)
        except Exception as e:
           logging.error(f'Error during main loop: {e}')
           time.sleep(1)

    logging.info('Trading system stopped.')


if __name__ == '__main__':
    asyncio.run(main())
