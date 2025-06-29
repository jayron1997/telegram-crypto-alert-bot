import os
import time
import threading
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volume import MFIIndicator
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ativo!"

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
INTERVAL = int(os.getenv('INTERVAL', '900'))  # padrão 15min

kucoin = ccxt.kucoin()
binance = ccxt.binance()
timeframes = ['15m', '1h']
limit = 100

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

def start_message():
    send_telegram("🤖 Bot iniciado com links e contratos!")

def get_contract_address(symbol: str):
    try:
        base = symbol.split('/')[0].lower()
        response = requests.get(f'https://api.coingecko.com/api/v3/coins/{base}')
        if response.status_code == 200:
            data = response.json()
            # procura contratos, começa pelo Ethereum
            if 'platforms' in data and data['platforms']:
                for chain, address in data['platforms'].items():
                    if address:
                        return f"{chain}: `{address}`"
        return None
    except:
        return None

def analisar():
    kucoin_symbols = [s['symbol'] for s in kucoin.fetch_markets() if s['active'] and s['symbol'].endswith('/USDT')]
    binance_symbols = {s['symbol'] for s in binance.fetch_markets()}

    for tf in timeframes:
        for symbol in kucoin_symbols:
            try:
                ohlcv = kucoin.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
                mfi = MFIIndicator(df['high'], df['low'], df['close'], df['volume'], window=14).money_flow_index().iloc[-1]

                avg_volume = df['volume'].mean()
                if avg_volume < 10000:
                    continue

                kucoin_symbol = symbol.replace('/', '-')
                kucoin_link = f"https://www.kucoin.com/trade/{kucoin_symbol}"

                binance_symbol = symbol.replace('/', '')
                binance_link = f"https://www.binance.com/en/trade/{binance_symbol}_USDT" if binance_symbol in binance_symbols else None

                contract = get_contract_address(symbol)

                msg = f"💰 *{symbol}* | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}\n[🔗 KuCoin]({kucoin_link})"
                if binance_link:
                    msg += f"\n[🔗 Binance]({binance_link})"
                if contract:
                    msg += f"\n🏷 *Contrato*: {contract}"

                if rsi >= 80 and mfi >= 90:
                    send_telegram(f"🔴 *SHORT* em\n{msg}")
                elif rsi <= 20 and mfi <= 10:
                    send_telegram(f"🟢 *LONG* em\n{msg}")

            except Exception as e:
                print(f"Erro em {symbol} - {tf}: {e}")

def run_bot():
    start_message()
    while True:
        print("Analisando mercado...")
        analisar()
        time.sleep(INTERVAL)

threading.Thread(target=run_bot).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
