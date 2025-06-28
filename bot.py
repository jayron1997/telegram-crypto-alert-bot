import os
import time
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator, MoneyFlowIndexIndicator
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
INTERVAL = int(os.getenv('INTERVAL', '900'))

exchange = ccxt.binance()
timeframes = ['15m', '1h']
limit = 100

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

def analisar():
    symbols = [s['symbol'] for s in exchange.fetch_markets() if s['active'] and s['symbol'].endswith('/USDT')]
    for tf in timeframes:
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
                mfi = MoneyFlowIndexIndicator(df['high'], df['low'], df['close'], df['volume'], window=14).money_flow_index().iloc[-1]
                if rsi >= 80 and mfi >= 90:
                    send_telegram(f"🔴 *SHORT* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}")
                elif rsi <= 20 and mfi <= 10:
                    send_telegram(f"🟢 *LONG* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}")
            except Exception as e:
                print(f"Erro em {symbol} - {tf}: {e}")

if __name__ == '__main__':
    while True:
        print("Analisando mercado...")
        analisar()
        time.sleep(INTERVAL)
