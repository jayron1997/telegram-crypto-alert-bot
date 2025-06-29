import os
import time
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volume import MFIIndicator
import requests

# Variáveis de ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
INTERVAL = int(os.getenv('INTERVAL', '900'))  # 900 segundos = 15 minutos
MIN_VOLUME_USDT = float(os.getenv('MIN_VOLUME_USDT', 500000))  # Mínimo de volume em USDT para analisar

# Inicializar exchange
exchange = ccxt.binance()

# Timeframes
timeframes = ['15m', '1h']
limit = 100

# Histórico de sinais já enviados (para evitar spam)
sent_signals = set()

# Função para enviar mensagem no Telegram
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': msg,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

# Mensagem de inicialização
def start_message():
    send_telegram("🤖 Bot iniciado! Monitorando criptos com bom volume em USDT na Binance.")

# Função principal de análise
def analisar():
    try:
        symbols = [s['symbol'] for s in exchange.fetch_markets() if s['active'] and s['symbol'].endswith('/USDT')]
    except Exception as e:
        print(f"Erro ao buscar mercados: {e}")
        return

    for tf in timeframes:
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Verificar volume do último candle
                last_close = df['close'].iloc[-1]
                last_volume = df['volume'].iloc[-1]
                volume_usdt = last_close * last_volume
                if volume_usdt < MIN_VOLUME_USDT:
                    continue  # Ignora moedas com volume baixo

                # Indicadores técnicos
                rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
                mfi = MFIIndicator(df['high'], df['low'], df['close'], df['volume'], window=14).money_flow_index().iloc[-1]

                # Gera chave única por símbolo + timeframe para evitar spam
                signal_key = f"{symbol}-{tf}"

                # Lógica de alertas
                if rsi >= 80 and mfi >= 90:
                    if signal_key not in sent_signals:
                        send_telegram(f"🔴 *SHORT* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}, Vol: ${volume_usdt:,.0f}")
                        sent_signals.add(signal_key)

                elif rsi <= 20 and mfi <= 10:
                    if signal_key not in sent_signals:
                        send_telegram(f"🟢 *LONG* em {symbol} | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}, Vol: ${volume_usdt:,.0f}")
                        sent_signals.add(signal_key)

            except Exception as e:
                print(f"Erro em {symbol} [{tf}]: {e}")

# Loop principal
if __name__ == '__main__':
    start_message()
    while True:
        print("Analisando mercado...")
        analisar()
        time.sleep(INTERVAL)

