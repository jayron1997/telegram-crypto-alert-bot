import os
import time
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volume import MFIIndicator
import requests

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
INTERVAL = int(os.getenv('INTERVAL', '900'))

exchange = ccxt.kucoin()
timeframes = ['15m', '1h']
limit = 100

# Dicionário para lembrar sinais já enviados
sent_signals = {}

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': msg,
        'parse_mode': 'Markdown'
    }
    requests.post(url, data=payload)

def start_message():
    send_telegram("🤖 Bot iniciado e rodando! Monitorando criptomoedas USDT na KuCoin.")

def analisar():
    symbols = [s['symbol'] for s in exchange.fetch_markets() if s['active'] and s['symbol'].endswith('/USDT')]

    for tf in timeframes:
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
                mfi = MFIIndicator(df['high'], df['low'], df['close'], df['volume'], window=14).money_flow_index().iloc[-1]

                key = f"{symbol}_{tf}"

                if rsi >= 80 and mfi >= 90:
                    # Se o último sinal não foi SHORT, envie
                    if sent_signals.get(key) != 'SHORT':
                        send_telegram(f"🔴 *SHORT* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}")
                        sent_signals[key] = 'SHORT'

                elif rsi <= 20 and mfi <= 10:
                    # Se o último sinal não foi LONG, envie
                    if sent_signals.get(key) != 'LONG':
                        send_telegram(f"🟢 *LONG* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}")
                        sent_signals[key] = 'LONG'

                else:
                    # Se o indicador saiu da zona de LONG ou SHORT, limpa o estado para permitir futuros alertas
                    if sent_signals.get(key) in ['LONG', 'SHORT']:
                        sent_signals.pop(key)

            except Exception as e:
                print(f"Erro em {symbol} - {tf}: {e}")

if __name__ == '__main__':
    start_message()
    while True:
        print("Analisando mercado...")
        analisar()
        time.sleep(INTERVAL)
