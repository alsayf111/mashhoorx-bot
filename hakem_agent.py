import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
import pytz

TELEGRAM_TOKEN = "8719936616:AAHIhk-64LtEcYcBWKBJ8RG6s6LPpPJpd68"
CHAT_ID = os.environ.get("CHAT_ID", "5652642650")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "7A1Rlo0TESCjHDqDs5T2lrdStLgTgpRV")

WATCHLIST = {
    "Energy": ["XOM", "CVX", "OXY", "SLB", "HAL", "MPC"],
    "Materials": ["LIN", "APD", "CAT", "DE", "HON"],
    "Communication": ["NFLX", "META", "GOOGL"],
    "Staples": ["PEP", "KO", "WMT", "COST"],
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD"],
    "Biotech": ["MRNA", "NVAX", "SAVA", "ACAD", "IONS", "BEAM", "RXRX", "NTLA", "CRSP", "EDIT"],
    "Financials": ["JPM", "GS", "BAC", "MS"],
    "Healthcare": ["JNJ", "UNH", "ABT", "PFE"],
    "ETFs": ["SPY", "QQQ", "IWM", "XLE"],
    "Consumer Discretionary": ["F", "GM", "TSLA", "AMZN", "HD", "MCD"],
    "Industrials": ["BA", "GE", "RTX", "UPS", "FDX"],
    "Utilities": ["NEE", "DUK", "SO", "AEP"],
    "Real Estate": ["AMT", "PLD", "SPG", "EQIX"]
}

# ─────────────────────────────────────────
# ACTION DECISION
# ─────────────────────────────────────────

def get_action(signal, opt):
    score = 0
    reasons = []

    # 1) Confidence
    if signal["confidence"] >= 85:
        score += 1
    else:
        reasons.append("Confidence دون 85")

    # 2) R/R
    if signal["rr"] >= 2.0:
        score += 1
    else:
        reasons.append("R/R دون 1:2")

    # 3) Options
    if opt and opt.get("premium", 0) > 0:
        delta = abs(opt.get("delta", 0))
        iv = opt.get("iv", 0)
        oi = opt.get("oi", 0)
        spread = opt.get("ask", 0) - opt.get("bid", 0)
        premium = opt.get("premium", 0)

        opt_ok = (
            0.40 <= delta <= 0.55
            and iv < 0.60
            and oi >= 500
            and spread <= premium * 0.10
        )
        if opt_ok:
            score += 1
        else:
            reasons.append("Options لا تطابق المعايير المثالية")
    else:
        reasons.append("لا توجد بيانات Options")

    if score == 3:
        return "🚀 ACTION: ENTER NOW", None
    elif score == 2:
        return "⚡ ACTION: CONSIDER", reasons
    else:
        return "⚠️ ACTION: WAIT", reasons


# ─────────────────────────────────────────
# OPTIONS SELECTION — HAKEM Rules
# ─────────────────────────────────────────

def score_contract(contract, snapshot, current_price, direction):
    delta = snapshot.get("delta", 0)
    premium = snapshot.get("premium", 0)
    volume = snapshot.get("volume", 0)
    oi = snapshot.get("oi", 0)
    bid = snapshot.get("bid", 0)
    ask = snapshot.get("ask", 0)
    iv = snapshot.get("iv", 0)
    strike = contract.get("strike_price", 0)
    expiry_str = contract.get("expiration_date", "")

    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
        dte = (expiry_date - datetime.now()).days
    except:
        return None

    if direction == "LONG":
        if not (0.35 <= delta <= 0.60):
            return None
    else:
        if not (-0.60 <= delta <= -0.35):
            return None

    if not (15 <= dte <= 35):
        return None

    if current_price > 0:
        strike_diff = abs(strike - current_price) / current_price
        if strike_diff > 0.05:
            return None
    else:
        strike_diff = 0

    if oi < 100:
        return None
    if volume < 10:
        return None

    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / ask
        if spread_pct > 0.15:
            return None
    else:
        spread_pct = 0

    if premium <= 0:
        return None
    if iv > 1.0:
        return None

    score = 0
    score += (1 - abs(abs(delta) - 0.45)) * 30
    score += (1 - abs(dte - 25) / 25) * 20
    score += (1 - strike_diff) * 20
    score += min(oi / 1000, 1) * 15
    score += min(volume / 500, 1) * 10
    if bid > 0 and ask > 0:
        score += (1 - spread_pct) * 5

    return round(score, 2)


def get_options_data(ticker, direction):
    try:
        contract_type = "call" if direction == "LONG" else "put"
        today = datetime.now()
        min_expiry = today + timedelta(days=15)
        max_expiry = today + timedelta(days=35)

        url = "https://api.polygon.io/v3/reference/options/contracts"
        params = {
            "underlying_ticker": ticker,
            "contract_type": contract_type,
            "expiration_date.gte": min_expiry.strftime("%Y-%m-%d"),
            "expiration_date.lte": max_expiry.strftime("%Y-%m-%d"),
            "limit": 100,
            "sort": "expiration_date",
            "apiKey": POLYGON_API_KEY
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "results" not in data or not data["results"]:
            return None

        stock = yf.Ticker(ticker)
        current_price = stock.fast_info.get("lastPrice") or stock.info.get("regularMarketPrice", 0)
        if not current_price:
            return None

        best_contract = None
        best_snapshot = None
        best_score = -1

        for contract in data["results"]:
            ticker_symbol = contract.get("ticker", "")
            if not ticker_symbol:
                continue
            snapshot = get_option_snapshot(ticker_symbol)
            if not snapshot:
                continue
            score = score_contract(contract, snapshot, current_price, direction)
            if score is not None and score > best_score:
                best_score = score
                best_contract = contract
                best_snapshot = snapshot

        if not best_contract:
            return None

        expiry_str = best_contract.get("expiration_date", "")
        try:
            dte = (datetime.strptime(expiry_str, "%Y-%m-%d") - datetime.now()).days
        except:
            dte = 0

        return {
            "type": contract_type.upper(),
            "strike": best_contract.get("strike_price", 0),
            "expiry": expiry_str,
            "dte": dte,
            "premium": best_snapshot.get("premium", 0),
            "delta": best_snapshot.get("delta", 0),
            "volume": best_snapshot.get("volume", 0),
            "oi": best_snapshot.get("oi", 0),
            "iv": best_snapshot.get("iv", 0),
            "bid": best_snapshot.get("bid", 0),
            "ask": best_snapshot.get("ask", 0),
            "symbol": best_contract.get("ticker", "")
        }

    except Exception as e:
        print(f"Options error {ticker}: {e}")
        return None


def get_option_snapshot(option_ticker):
    try:
        url = f"https://api.polygon.io/v3/snapshot/options/{option_ticker}"
        params = {"apiKey": POLYGON_API_KEY}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        result = data.get("results", {})
        if not result:
            return {}

        day = result.get("day", {})
        greeks = result.get("greeks", {})

        return {
            "premium": round(day.get("close", 0) or day.get("last", 0), 2),
            "delta": round(greeks.get("delta", 0), 3),
            "volume": int(day.get("volume", 0)),
            "oi": int(result.get("open_interest", 0)),
            "iv": round(result.get("implied_volatility", 0), 3),
            "bid": round(day.get("open", 0), 2),
            "ask": round(day.get("close", 0), 2),
        }
    except Exception as e:
        print(f"Snapshot error {option_ticker}: {e}")
        return {}


# ─────────────────────────────────────────
# MARKET CONDITIONS
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# DATA & ANALYSIS
# ─────────────────────────────────────────

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
                "stop_pct": round((price - stop) / price * 100, 1),
                "t1": t1,
                "t1_pct": round((t1 - price) / price * 100, 1),
                "t2": t2,
                "t2_pct": round((t2 - price) / price * 100, 1),
                "rr": rr,
                "reason": [
                    f"Volume Spike {int(vol_now/vol_avg*100)}% من المتوسط",
                    "احتمال خبر FDA قادم"
                ],
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
            reason.append(f"Breakout فوق ${resistance:.2f}")
            reason.append(f"Volume {int(vol_now/vol_avg*100)}% من المتوسط")
            confidence += 20
        elif price > ma50_val and abs(price - ma20_val) / price < 0.01 and rsi_val < 45:
            direction = "LONG"
            reason.append("Pullback على MA20")
            reason.append(f"RSI {rsi_val:.0f} منطقة شراء")
            confidence += 15
        elif price < support * 0.998 and vol_now > vol_avg * 1.3 and rsi_val < 50:
            direction = "SHORT"
            reason.append(f"Breakdown تحت ${support:.2f}")
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
        "stop_pct": round(abs(price - stop) / price * 100, 1),
        "t1": t1,
        "t1_pct": round(abs(t1 - price) / price * 100, 1),
        "t2": t2,
        "t2_pct": round(abs(t2 - price) / price * 100, 1),
        "rr": rr,
        "reason": reason,
        "confidence": confidence
    }


# ─────────────────────────────────────────
# TELEGRAM MESSAGE
# ─────────────────────────────────────────

def send_signal(s, regime, rank):
    opt = get_options_data(s["ticker"], s["direction"])
    action, action_reasons = get_action(s, opt)

    medal = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}
    direction_icon = "📈 LONG" if s["direction"] == "LONG" else "📉 SHORT"
    regime_icon = "🟢 Bull Market" if regime == "BULL" else "🔴 Bear Market"

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
{medal[rank]} HAKEM SIGNAL #{rank}
━━━━━━━━━━━━━━━━━━━━━━━
📌 {s['ticker']} — {s['sector']}
━━━━━━━━━━━━━━━━━━━━━━━

{direction_icon}  |  {regime_icon}

"""
    for r in s["reason"]:
        msg += f"• {r}\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
💰 TRADE SETUP
━━━━━━━━━━━━━━━━━━━━━━━
Entry  ▸  ${s['price']}
Stop   ▸  ${s['stop']}  (-{s['stop_pct']}%)
T1     ▸  ${s['t1']}  (+{s['t1_pct']}%)
T2     ▸  ${s['t2']}  (+{s['t2_pct']}%)
R/R    ▸  1 : {s['rr']}
"""

    if opt and opt.get("premium", 0) > 0:
        delta_val = opt["delta"]
        delta_icon = "🟢" if abs(delta_val) >= 0.45 else "🟡" if abs(delta_val) >= 0.35 else "🔴"
        iv_pct = round(opt["iv"] * 100, 1) if opt.get("iv") else 0
        iv_icon = "✅" if iv_pct < 60 else "⚠️"
        spread = round(opt.get("ask", 0) - opt.get("bid", 0), 2)

        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
🎯 OPTIONS PLAY
━━━━━━━━━━━━━━━━━━━━━━━
{opt['type']}  ${opt['strike']}  |  {opt['dte']} DTE
─────────────────────────
Premium  ▸  ${opt['premium']}
Delta    ▸  {delta_val}  {delta_icon}
IV       ▸  {iv_pct}%  {iv_icon}
Spread   ▸  ${spread}
─────────────────────────
Volume   ▸  {opt['volume']:,}
OI       ▸  {opt['oi']:,}
"""
    else:
        msg += """
━━━━━━━━━━━━━━━━━━━━━━━
🎯 OPTIONS
⚠️ لا يوجد عقد يطابق معايير HAKEM
"""

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
⭐ Confidence  {s['confidence']} / 100
━━━━━━━━━━━━━━━━━━━━━━━
{action}"""

    if action_reasons:
        for r in action_reasons:
            msg += f"\n  · {r}"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
        📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━"""

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    print(f"Sent: {s['ticker']} #{rank} — {action}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def run():
    if not is_market_open():
        print("السوق مغلق")
        return

    regime = get_spy_regime()
    print(f"Market Regime: {regime}")

    signals = []

    for sector, tickers in WATCHLIST.items():
        for ticker in tickers:
            try:
                if sector == "Biotech":
                    signal = analyze_biotech(ticker)
                else:
                    signal = analyze(ticker, sector, regime)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"Error {ticker}: {e}")

    signals = sorted(signals, key=lambda x: x["confidence"], reverse=True)[:5]

    if signals:
        for i, signal in enumerate(signals, 1):
            send_signal(signal, regime, i)
    else:
        print("No signals found")


if __name__ == "__main__":
    run()
