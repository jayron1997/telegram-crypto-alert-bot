import os
import time
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volume import MFIIndicator
import requests

# Carregar variáveis de ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
INTERVAL = int(os.getenv('INTERVAL', '900'))  # Intervalo em segundos (900 = 15 min)

# Conectar na Binance via CCXT
exchange = ccxt.binance()

# Timeframes para análise
timeframes = ['15m', '1h']
limit = 100  # Número de candles para buscar

# Função para enviar mensagem no Telegram
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': msg,
        'parse_mode': 'Markdown'
    }
    requests.post(url, data=payload)

# Função para enviar mensagem inicial ao iniciar o bot
def start_message():
    send_telegram("🤖 Bot iniciado e rodando! Monitorando criptomoedas USDT na Binance.")

# Função que faz a análise técnica e envia alertas
def analisar():
    # Pega todos os símbolos ativos que terminam com /USDT
    symbols = [s['symbol'] for s in exchange.fetch_markets() if s['active'] and s['symbol'].endswith('/USDT')]

    for tf in timeframes:
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Calcula RSI e MFI
                rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
                mfi = MFIIndicator(df['high'], df['low'], df['close'], df['volume'], window=14).money_flow_index().iloc[-1]

                # Condições para enviar alertas
                if rsi >= 80 and mfi >= 90:
                    send_telegram(f"🔴 *SHORT* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}")
                elif rsi <= 20 and mfi <= 10:
                    send_telegram(f"🟢 *LONG* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}")

            except Exception as e:
                print(f"Erro em {symbol} - {tf}: {e}")

# Loop principal
if __name__ == '__main__':
    start_message()
    while True:
        print("Analisando mercado...")
        analisar()
        time.sleep(INTERVAL)
