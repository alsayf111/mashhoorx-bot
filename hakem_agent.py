import os
import requests
import yfinance as yf
import pandas as pd

TELEGRAM_TOKEN = "8719936616:AAHIhk-64LtEcYcBWKBJ8RG6s6LPpPJpd68"
CHAT_ID = os.environ.get("CHAT_ID", "5652642650")

WATCHLIST = {
    "Energy": ["XOM","CVX","OXY","SLB","HAL","MPC"],
    "Materials": ["LIN","APD","CAT","DE","HON"],
    "Communication": ["NFLX","META","GOOGL"],
    "Staples": ["PEP","KO","WMT","COST"],
    "Technology": ["NVDA","AAPL","MSFT","AMD"]
}

def get_data(ticker):
    df = yf.download(ticker, period="60d", interval="1d", progress=False)
    return df

def analyze(ticker, sector):
    df = get_data(ticker)
    if df is None or len(df) < 30:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    price = float(close.iloc[-1])
    rsi_val = float(rsi.iloc[-1])
    ma20_val = float(ma20.iloc[-1])
    ma50_val = float(ma50.iloc[-1])
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_now = float(volume.iloc[-1])

    resistance = float(high.rolling(20).max().iloc[-2])
    support = float(low.rolling(20).min().iloc[-2])

    direction = None
    reason = []
    confidence = 50

    # Breakout LONG
    if price > resistance * 1.002 and vol_now > vol_avg * 1.3 and rsi_val > 50:
        direction = "LONG"
        reason.append(f"Breakout فوق {resistance:.2f}")
        reason.append(f"Volume مرتفع {int(vol_now/vol_avg*100)}%")
        confidence += 20

    # Pullback LONG
    elif price > ma50_val and abs(price - ma20_val) / price < 0.01 and rsi_val < 45:
        direction = "LONG"
        reason.append(f"Pullback على MA20")
        reason.append(f"RSI {rsi_val:.0f} منطقة شراء")
        confidence += 15

    # SHORT Breakdown
    elif price < support * 0.998 and vol_now > vol_avg * 1.3 and rsi_val < 50:
        direction = "SHORT"
        reason.append(f"Breakdown تحت {support:.2f}")
        reason.append(f"Volume مرتفع {int(vol_now/vol_avg*100)}%")
        confidence += 20

    if direction is None:
        return None

    if direction == "LONG":
        stop = round(price * 0.985, 2)
        t1 = round(price * 1.02, 2)
        t2 = round(price * 1.035, 2)
    else:
        stop = round(price * 1.015, 2)
        t1 = round(price * 0.98, 2)
        t2 = round(price * 0.965, 2)

    risk = abs(price - stop)
    reward = abs(t1 - price)
    rr = round(reward / risk, 2) if risk > 0 else 0

    if rr < 1.5:
        return None

    if ma20_val > ma50_val:
        confidence += 10
    if rsi_val > 55 and direction == "LONG":
        confidence += 5
    if rsi_val < 45 and direction == "SHORT":
        confidence += 5

    confidence = min(confidence, 95)

    return {
        "ticker": ticker,
        "sector": sector,
        "direction": direction,
        "price": round(price, 2),
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "rr": rr,
        "rsi": round(rsi_val, 1),
        "reason": reason,
        "confidence": confidence
    }

def send_signal(s):
    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
🚨 HAKEM TRADE ALERT
━━━━━━━━━━━━━━━━━━━━━━━

السهم: {s['ticker']} ({s['sector']})
الاتجاه: {"📈 LONG" if s['direction']=='LONG' else "📉 SHORT"}

سبب الدخول:
"""
    for r in s['reason']:
        msg += f"• {r}\n"

    msg += f"""
Entry: {s['price']}
Stop: {s['stop']}
T1: {s['t1']}
T2: {s['t2']}
R/R: 1:{s['rr']}

━━━━━━━━━━━━━━━━━━━━━━━
⭐ Confidence: {s['confidence']}/100
━━━━━━━━━━━━━━━━━━━━━━━"""

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    result = requests.post(url, json=payload).json()
    print(result)

def run():
    best = None
    for sector, tickers in WATCHLIST.items():
        for ticker in tickers:
            try:
                signal = analyze(ticker, sector)
                if signal:
                    if best is None or signal['confidence'] > best['confidence']:
                        best = signal
            except Exception as e:
                print(f"Error {ticker}: {e}")

    if best:
        send_signal(best)
    else:
        print("No signals found")

if __name__ == "__main__":
    run()
