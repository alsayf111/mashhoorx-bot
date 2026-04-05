import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "5652642650")

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    result = response.json()
    print(result)
    return result

def run_agent(signal: dict):
    symbol = signal.get("symbol", "Unknown")
    action = signal.get("action", "Unknown")
    price = signal.get("price", 0)
    tp = signal.get("tp", 0)
    sl = signal.get("sl", 0)

    message = (
        f"🔔 <b>HAKEM Signal</b>\n"
        f"📌 Symbol: {symbol}\n"
        f"⚡ Action: {action}\n"
        f"💰 Price: {price}\n"
        f"✅ TP: {tp}\n"
        f"❌ SL: {sl}"
    )
    return send_message(message)

if __name__ == "__main__":
    test_signal = {
        "symbol": "XAUUSD",
        "action": "BUY",
        "price": 3050.00,
        "tp": 3065.00,
        "sl": 3040.00
    }
    run_agent(test_signal)
