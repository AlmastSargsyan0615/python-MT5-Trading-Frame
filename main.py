import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import datetime
import time
import logging
import json
import talib

# Set up logging
logging.basicConfig(filename='history.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from JSON file
def load_config(filename='config.json'):
    with open(filename, 'r') as file:
        config = json.load(file)
    return config

# Define global variables
config = load_config()
login = config['login']
password = config['password']
server = config['server']
symbol = config['symbol']
sl_distance = config['sl_distance']
tp_distance = config['tp_distance']
deviation = config['deviation']
magic = config['magic']
buy_threshold = config['buy_threshold']
sell_threshold = config['sell_threshold']
start_time = datetime.datetime.strptime(config['start_time'], "%H:%M:%S").time()
end_time = datetime.datetime.strptime(config['end_time'], "%H:%M:%S").time()

# Initialize MetaTrader 5
def initialize_mt5():
    if not mt5.initialize(login=login, password=password, server=server):
        logging.error(f"MT5 Initialization failed, error code: {mt5.last_error()}")
        quit()
    logging.info("MT5 Initialized successfully")

def get_candlestick_data(symbol, timeframe, num_bars=5000):
    """Retrieve candlestick data from MT5."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    if rates is None:
        logging.error(f"Failed to get candlestick data for {symbol}")
        return None
    data = pd.DataFrame(rates)
    data['time'] = pd.to_datetime(data['time'], unit='s')
    return data

def calculate_macd(data):
    """Calculate MACD and RSI indicators."""
    data['macd'], data['macdsignal'], data['macdhist'] = talib.MACD(data['close'])
    data['rsi'] = talib.RSI(data['close'])
    return data

def execute_trade(action, volume=0.01):
    """
    Execute a trade with specified parameters.
    
    :param action: 'buy' or 'sell'
    :param volume: Volume of the trade
    """
    current_tick = mt5.symbol_info_tick(symbol)
    if current_tick is None:
        logging.error("Failed to get current tick")
        return

    if action == 'buy':
        price = current_tick.ask
        sl_price = price - sl_distance
        tp_price = price + tp_distance
        order_type = mt5.ORDER_TYPE_BUY  # 1 for Buy
    elif action == 'sell':
        price = current_tick.bid
        sl_price = price + sl_distance
        tp_price = price - tp_distance
        order_type = mt5.ORDER_TYPE_SELL  # 2 for Sell
    else:
        logging.error("Invalid action type")
        return

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': volume,
        'type': order_type,
        'price': price,
        'sl': sl_price,
        'tp': tp_price,
        'deviation': deviation,
        'magic': magic,
        'comment': 'Algo Trade',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC
    }
    # Print all information inline
    print(f"Trade Request Information:")
    print(f"Action: {'Buy' if action == 'buy' else 'Sell'}")
    print(f"Symbol: {symbol}")
    print(f"Volume: {volume}")
    print(f"Price: {price}")
    print(f"Stop Loss: {sl_price}")
    print(f"Take Profit: {tp_price}")
    print(f"Deviation: {deviation}")
    print(f"Magic Number: {magic}")
    print(f"Order Type: {'Buy' if action == 'buy' else 'Sell'}")
    print(f"Order Time: Good Till Cancel")
    print(f"Order Filling: Immediate or Cancel")

    # Send the trade request
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Trade failed: {result.retcode}")
    else:
        log_trade(action, price, volume)
        logging.info("Trade successful")
        print(f"Trade successful. Order ID: {result.order}")

def log_trade(action, price, volume):
    """Log trade details."""
    logging.info(f"Trade executed - Action: {action}, Price: {price}, Volume: {volume}")

def close_all_positions():
    """Close all open positions."""
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        for pos in positions:
            # print(pos)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": pos.identifier,
                "price": mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask,
                "deviation": deviation,
                "magic": magic,
                "comment": "python script close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN
            }
            #          request = {
            #     'action': mt5.TRADE_ACTION_DEAL,
            #     'symbol': symbol,
            #     'volume': pos.volume,
            #     'type': mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            #     'price': mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask,
            #     "position": pos.identifier,
            #     'deviation': deviation,
            #     'magic': magic,
            #     'comment': 'Closing position before end of trading session',
            #     'type_time': mt5.ORDER_TIME_GTC,
            #     'type_filling': mt5.ORDER_FILLING_IOC
            # }
            result = mt5.order_send(request)
            print(result)
            if result is None:
                logging.error("Failed to send trade request.")
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                logging.error(f"Trade failed: {result.retcode}")
            else:
                logging.info("Position closed successfully")


def real_time_trading_logic():
    """Perform real-time trading logic."""
    current_time = datetime.datetime.now().time()
    if current_time < start_time or current_time > end_time:
        logging.info("Outside trading hours")
        return

    latest_data = get_candlestick_data(symbol, mt5.TIMEFRAME_M1, num_bars=1)
    if latest_data is not None:
        latest_data_with_macd = calculate_macd(latest_data)
        latest_macd_data = latest_data_with_macd.iloc[-1]

        current_tick = mt5.symbol_info_tick(symbol)
        if current_tick is not None:
            print(f"Real-time Price - Bid: {current_tick.bid}, Ask: {current_tick.ask}")
        if latest_macd_data['macd'] > latest_macd_data['macdsignal'] and latest_macd_data['rsi'] < 30:
            execute_trade('buy', volume=0.01)
        elif latest_macd_data['macd'] < latest_macd_data['macdsignal'] and latest_macd_data['rsi'] > 70:
            execute_trade('sell', volume=0.01)

        # Example conditions for trading using values from config
        if current_tick.bid > buy_threshold:
            execute_trade('buy', volume=0.01)
        elif current_tick.bid < sell_threshold:
            execute_trade('sell', volume=0.01)

def main():
    initialize_mt5()
    
    # Main trading loop
    try:
        while True:
            if datetime.datetime.now().time() >= end_time:
                close_all_positions()
            real_time_trading_logic()
            # Check time and close positions if past end time

            time.sleep(1)  # Check every second
    except KeyboardInterrupt:
        logging.info("Trading stopped by user")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
