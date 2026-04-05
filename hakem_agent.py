import os
import requests
import yfinance as yf
from datetime import datetime
import pytz

TELEGRAM_TOKEN = "8719936616:AAHIhk-64LtEcYcBWKBJ8RG6s6LPpPJpd68"
CHAT_ID = os.environ.get("CHAT_ID", "5652642650")

WATCHLIST = {
    "Energy": ["XOM","CVX","OXY","SLB","HAL","MPC"],
    "Materials": ["LIN","APD","CAT","DE","HON"],
    "Communication": ["NFLX","META","GOOGL"],
    "Staples": ["PEP","KO","WMT","COST"],
    "Technology": ["NVDA","AAPL","MSFT","AMD"],
    "Biotech": ["MRNA","NVAX","SAVA","ACAD","IONS","BEAM","RXRX","NTLA","CRSP","EDIT"]
}

def is_market_open():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    return market_open <= now <= market_close

def get_spy_regime():
    try:
        df = yf.download("SPY", period="30d", interval="1d", progress=False)
        close = df["Close"]
        ma20 = float(close.rolling(20).mean().iloc[-1])
        price = float(close.iloc[-1])
        return "BULL" if price > ma20 else "BEAR"
    except:
        return "BULL"

def get_data(ticker):
    try:
        df = yf.download(ticker, period="60d", interval="1d", progress=False)
        return df if len(df) >= 30 else None
    except:
        return None

def analyze_biotech(ticker):
    df = get_data(ticker)
    if df is None:
        return None
    volume = df["Volume"]
    close = df["Close"]
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_now = float(volume.iloc[-1])
    price = float(close.iloc[-1])
    if vol_now > vol_avg * 3:
        stop = round(price * 0.92, 2)
        t1 = round(price * 1.15, 2)
        t2 = round(price * 1.30, 2)
        rr = round((t1 - price) / (price - stop), 2)
        if rr >= 1.5:
            return {
                "ticker": ticker,
                "sector": "Biotech 🧬",
                "direction": "LONG",
                "price": round(price, 2),
                "stop": stop,
                "t1": t1,
                "t2": t2,
                "rr": rr,
                "reason": [f"Volume Spike {int(vol_now/vol_avg*100)}% من المتوسط", "احتمال خبر FDA قادم"],
                "confidence": 70
            }
    return None

def analyze(ticker, sector, regime):
    df = get_data(ticker)
    if df is None:
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
    rsi = 100 - (100 / (1 + gain / loss))

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

    if sector == "Technology" and regime == "BEAR":
        return None

    if sector == "Staples" and regime == "BULL":
        if price < support * 0.998 and vol_now > vol_avg * 1.3:
            direction = "SHORT"
            reason.append(f"Breakdown في Staples — سوق صاعد")
            reason.append(f"Volume مرتفع {int(vol_now/vol_avg*100)}%")
            confidence += 15

    if direction is None:
        if price > resistance * 1.002 and vol_now > vol_avg * 1.3 and rsi_val > 50:
            direction = "LONG"
            reason.append(f"Breakout فوق {resistance:.2f}")
            reason.append(f"Volume {int(vol_now/vol_avg*100)}% من المتوسط")
            confidence += 20
        elif price > ma50_val and abs(price - ma20_val)/price < 0.01 and rsi_val < 45:
            direction = "LONG"
            reason.append("Pullback على MA20")
            reason.append(f"RSI {rsi_val:.0f} منطقة شراء")
            confidence += 15
        elif price < support * 0.998 and vol_now > vol_avg * 1.3 and rsi_val < 50:
            direction = "SHORT"
            reason.append(f"Breakdown تحت {support:.2f}")
            reason.append(f"Volume {int(vol_now/vol_avg*100)}% من المتوسط")
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

    if confidence < 65:
        return None

    return {
        "ticker": ticker,
        "sector": sector,
        "direction": direction,
        "price": round(price, 2),
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "rr": rr,
        "reason": reason,
        "confidence": confidence
    }

def send_signal(s, regime):
    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
🚨 HAKEM TRADE ALERT
━━━━━━━━━━━━━━━━━━━━━━━

السهم: {s['ticker']} ({s['sector']})
الاتجاه: {"📈 LONG" if s['direction']=='LONG' else "📉 SHORT"}
السوق: {"🟢 Bull" if regime=='BULL' else "🔴 Bear"}

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
    result = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}).json()
    print(result)

def run():
    if not is_market_open():
        print("السوق مغلق")
        return

    regime = get_spy_regime()
    print(f"Market Regime: {regime}")

    best = None

    for sector, tickers in WATCHLIST.items():
        for ticker in tickers:
            try:
                if sector == "Biotech":
                    signal = analyze_biotech(ticker)
                else:
                    signal = analyze(ticker, sector, regime)
                if signal:
                    if best is None or signal['confidence'] > best['confidence']:
                        best = signal
            except Exception as e:
                print(f"Error {ticker}: {e}")

    if best:
        send_signal(best, regime)
    else:
        print("No signals found")

if __name__ == "__main__":
    run()
