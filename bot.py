import os
import time
import threading
import ccxt
import pandas as pd
import requests
from ta.momentum import RSIIndicator
from ta.volume import MFIIndicator
from flask import Flask

# Flask para manter o Render ativo
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot está rodando!"

# Variáveis de ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
INTERVAL = int(os.getenv('INTERVAL', '900'))  # Padrão: 15 minutos

# Exchange KuCoin
exchange = ccxt.kucoin()
timeframes = ['15m', '1h']
limit = 100

# Enviar mensagens pro Telegram
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

# Mensagem inicial
def start_message():
    send_telegram("🤖 Bot iniciado com sucesso!")

# Buscar endereço do contrato via CoinGecko
def get_contract_address(symbol: str) -> str:
    try:
        base = symbol.split('/')[0].lower()
        url = f"https://api.coingecko.com/api/v3/coins/{base}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            contract = data.get('platforms', {}).get('ethereum')  # pode trocar para 'binance-smart-chain'
            return contract if contract else ''
    except Exception as e:
        print(f"Erro ao buscar contrato para {symbol}: {e}")
    return ''

# Lógica principal
def analisar():
    symbols = [s['symbol'] for s in exchange.fetch_markets() if s['active'] and s['symbol'].endswith('USDT')]
    for tf in timeframes:
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
                mfi = MFIIndicator(df['high'], df['low'], df['close'], df['volume'], window=14).money_flow_index().iloc[-1]

                avg_volume = df['volume'].mean()
                if avg_volume < 10000:  # filtro de moedas com volume baixo
                    continue

                kucoin_symbol = symbol.replace('/', '-')
                kucoin_link = f"https://www.kucoin.com/trade/{kucoin_symbol}"

                msg = f"💰 *{symbol}* | TF: {tf}\nRSI: {rsi:.2f}, MFI: {mfi:.2f}\n[🔗 KuCoin]({kucoin_link})"

                contract = get_contract_address(symbol)
                if contract:
                    msg += f"\n🏷 *Contrato:* `{contract}`"

                if rsi >= 80 and mfi >= 90:
                    send_telegram(f"🔴 *SHORT* sinal:\n{msg}")
                elif rsi <= 20 and mfi <= 10:
                    send_telegram(f"🟢 *LONG* sinal:\n{msg}")

            except Exception as e:
                print(f"Erro em {symbol} - {tf}: {e}")

# Executar o bot
def run_bot():
    start_message()
    while True:
        print("Analisando mercado...")
        analisar()
        time.sleep(INTERVAL)

# Iniciar em thread separada
threading.Thread(target=run_bot).start()

# Iniciar servidor Flask no Render
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
