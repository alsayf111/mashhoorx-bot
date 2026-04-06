import os
import requests
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import pytz
from hakem_logger import log_us_signal

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8719936616:AAF63mIxzhoB2iFjVe9w8FhGSshlMsOsvR4")
CHAT_ID = os.environ.get("CHAT_ID", "5652642650")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "7A1Rlo0TESCjHDqDs5T2lrdStLgTgpRV")


# ─────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────

def telegram_send(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    except Exception as e:
        print(f"Telegram error: {e}")


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
# OPTIONS DATA
# ─────────────────────────────────────────

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
        }

    except Exception as e:
        print(f"Options error {ticker}: {e}")
        return None


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

    if oi < 100 or volume < 10 or premium <= 0 or iv > 1.0:
        return None

    if bid > 0 and ask > 0:
        spread_pct = (ask - bid) / ask
        if spread_pct > 0.15:
            return None
    else:
        spread_pct = 0

    score = 0
    score += (1 - abs(abs(delta) - 0.45)) * 30
    score += (1 - abs(dte - 25) / 25) * 20
    score += (1 - strike_diff) * 20
    score += min(oi / 1000, 1) * 15
    score += min(volume / 500, 1) * 10
    if bid > 0 and ask > 0:
        score += (1 - spread_pct) * 5

    return round(score, 2)


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
    except:
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
    market_close = now.replace(hour=17, minute=0, second=0)
    return market_open <= now <= market_close


def get_market_state():
    try:
        df = yf.download("SPY", period="60d", interval="1d", progress=False)
        if df is None or len(df) < 20:
            return "CALM", "BULL"
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
        atr = float(tr.rolling(14).mean().iloc[-1])
        atr_pct = atr / float(close.iloc[-1])
        state = "CALM" if atr_pct < 0.012 else "VOLATILE"
        ma20 = float(close.rolling(20).mean().iloc[-1])
        price = float(close.iloc[-1])
        regime = "BULL" if price > ma20 else "BEAR"
        return state, regime
    except:
        return "CALM", "BULL"


def get_data(ticker):
    try:
        df = yf.download(ticker, period="90d", interval="1d", progress=False)
        return df if len(df) >= 50 else None
    except:
        return None


# ─────────────────────────────────────────
# BULLISH PATTERNS
# ─────────────────────────────────────────

def detect_bullish_candles(df):
    patterns = []
    o = df["Open"].values.astype(float)
    c = df["Close"].values.astype(float)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)

    def body(i): return abs(c[i] - o[i])
    def full(i): return h[i] - l[i]
    def upper(i): return h[i] - max(o[i], c[i])
    def lower(i): return min(o[i], c[i]) - l[i]
    def is_green(i): return c[i] > o[i]
    def is_red(i): return c[i] < o[i]

    if (is_green(-3) and is_green(-2) and is_green(-1) and
        c[-2] > c[-3] and c[-1] > c[-2] and
        o[-2] > o[-3] and o[-2] < c[-3] and
        o[-1] > o[-2] and o[-1] < c[-2] and
        full(-1) > 0 and body(-1)/full(-1) > 0.6 and
        full(-2) > 0 and body(-2)/full(-2) > 0.6):
        patterns.append(("3 White Soldiers", 90))

    if (is_green(-1) and full(-1) > 0 and
        body(-1)/full(-1) > 0.9 and
        upper(-1) < body(-1)*0.05 and
        lower(-1) < body(-1)*0.05):
        patterns.append(("Marubozu", 75))

    if (is_red(-2) and is_green(-1) and
        o[-1] < c[-2] and c[-1] > o[-2]):
        patterns.append(("Bullish Engulfing", 70))

    if (is_red(-3) and body(-2) < body(-3)*0.3 and
        is_green(-1) and c[-1] > (o[-3] + c[-3])/2):
        patterns.append(("Morning Star", 72))

    if (full(-1) > 0 and body(-1)/full(-1) < 0.35 and
        lower(-1) > body(-1)*2 and upper(-1) < body(-1)*0.5 and
        c[-4] > c[-1]):
        patterns.append(("Hammer", 65))

    if (full(-1) > 0 and body(-1) > 0 and
        upper(-1) >= body(-1)*2 and lower(-1) < body(-1)*0.3 and
        c[-4] > c[-1]):
        patterns.append(("Inverted Hammer", 62))

    if (is_red(-2) and is_green(-1) and
        o[-1] < l[-2] and c[-1] > (o[-2] + c[-2])/2):
        patterns.append(("Piercing Line", 68))

    if (is_red(-2) and is_green(-1) and
        o[-1] > c[-2] and c[-1] < o[-2]):
        patterns.append(("Bullish Harami", 60))

    return patterns


def detect_bullish_chart(df):
    patterns = []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)
    n = len(close)

    try:
        highs_20 = high[-20:]
        lows_20 = low[-20:]
        resistance = np.max(highs_20)
        resistance_touches = np.sum(highs_20 > resistance * 0.995)
        lows_trend = np.polyfit(range(20), lows_20, 1)[0]
        if resistance_touches >= 2 and lows_trend > 0 and close[-1] > resistance * 0.998:
            patterns.append(("Ascending Triangle", 78))
    except: pass

    try:
        highs_25 = high[-25:]
        lows_25 = low[-25:]
        h_slope = np.polyfit(range(25), highs_25, 1)[0]
        l_slope = np.polyfit(range(25), lows_25, 1)[0]
        if h_slope < 0 and l_slope < 0 and l_slope < h_slope and close[-1] > close[-3]:
            patterns.append(("Falling Wedge", 75))
    except: pass

    try:
        lows_40 = low[-40:]
        min1_idx = np.argmin(lows_40[:20])
        min2_idx = np.argmin(lows_40[20:]) + 20
        min1 = lows_40[min1_idx]
        min2 = lows_40[min2_idx]
        if abs(min1 - min2)/min1 < 0.03 and close[-1] > np.max(lows_40[min1_idx:min2_idx]):
            patterns.append(("Double Bottom", 80))
    except: pass

    try:
        lows_50 = low[-50:]
        left = np.min(lows_50[:15])
        head = np.min(lows_50[15:35])
        right = np.min(lows_50[35:])
        if head < left and head < right and abs(left-right)/left < 0.05:
            neckline = np.max(high[-50:][15:35])
            if close[-1] > neckline * 0.998:
                patterns.append(("Inverse H&S", 85))
    except: pass

    try:
        if n >= 50:
            cup_low = np.min(close[-50:-10])
            cup_start = close[-50]
            cup_end = close[-10]
            if (abs(cup_start - cup_end)/cup_start < 0.05 and
                cup_low < cup_start * 0.9 and
                np.min(close[-10:]) > cup_low and
                close[-1] > cup_end * 0.995):
                patterns.append(("Cup & Handle", 82))
    except: pass

    try:
        pole_gain = (close[-15] - close[-25]) / close[-25]
        flag_slope = np.polyfit(range(10), close[-10:], 1)[0]
        if pole_gain > 0.05 and -0.002 < flag_slope < 0.001 and close[-1] > close[-2]:
            patterns.append(("Bull Flag", 76))
    except: pass

    return patterns


# ─────────────────────────────────────────
# BEARISH PATTERNS
# ─────────────────────────────────────────

def detect_bearish_candles(df):
    patterns = []
    o = df["Open"].values.astype(float)
    c = df["Close"].values.astype(float)
    h = df["High"].values.astype(float)
    l = df["Low"].values.astype(float)

    def body(i): return abs(c[i] - o[i])
    def full(i): return h[i] - l[i]
    def upper(i): return h[i] - max(o[i], c[i])
    def lower(i): return min(o[i], c[i]) - l[i]
    def is_green(i): return c[i] > o[i]
    def is_red(i): return c[i] < o[i]

    if (is_red(-3) and is_red(-2) and is_red(-1) and
        c[-2] < c[-3] and c[-1] < c[-2] and
        o[-2] < o[-3] and o[-2] > c[-3] and
        o[-1] < o[-2] and o[-1] > c[-2] and
        full(-1) > 0 and body(-1)/full(-1) > 0.6 and
        full(-2) > 0 and body(-2)/full(-2) > 0.6):
        patterns.append(("3 Black Crows", 90))

    if (is_red(-1) and full(-1) > 0 and
        body(-1)/full(-1) > 0.9 and
        upper(-1) < body(-1)*0.05 and
        lower(-1) < body(-1)*0.05):
        patterns.append(("Bearish Marubozu", 75))

    if (is_green(-2) and is_red(-1) and
        o[-1] > c[-2] and c[-1] < o[-2]):
        patterns.append(("Bearish Engulfing", 70))

    if (is_green(-3) and body(-2) < body(-3)*0.3 and
        is_red(-1) and c[-1] < (o[-3] + c[-3])/2):
        patterns.append(("Evening Star", 72))

    if (full(-1) > 0 and body(-1) > 0 and
        upper(-1) >= body(-1)*2 and lower(-1) < body(-1)*0.3 and
        c[-4] < c[-1]):
        patterns.append(("Shooting Star", 68))

    if (full(-1) > 0 and body(-1)/full(-1) < 0.35 and
        lower(-1) > body(-1)*2 and upper(-1) < body(-1)*0.5 and
        c[-4] < c[-1]):
        patterns.append(("Hanging Man", 65))

    if (is_green(-2) and is_red(-1) and
        o[-1] < c[-2] and c[-1] > o[-2]):
        patterns.append(("Bearish Harami", 60))

    if (is_green(-2) and is_red(-1) and
        o[-1] > h[-2] and c[-1] < (o[-2] + c[-2])/2):
        patterns.append(("Dark Cloud Cover", 68))

    return patterns


def detect_bearish_chart(df):
    patterns = []
    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float)
    low = df["Low"].values.astype(float)

    try:
        highs_50 = high[-50:]
        left = np.max(highs_50[:15])
        head = np.max(highs_50[15:35])
        right = np.max(highs_50[35:])
        if head > left and head > right and abs(left-right)/left < 0.05:
            neckline = np.min(low[-50:][15:35])
            if close[-1] < neckline * 1.002:
                patterns.append(("Head & Shoulders", 85))
    except: pass

    try:
        highs_40 = high[-40:]
        max1_idx = np.argmax(highs_40[:20])
        max2_idx = np.argmax(highs_40[20:]) + 20
        max1 = highs_40[max1_idx]
        max2 = highs_40[max2_idx]
        if abs(max1 - max2)/max1 < 0.03 and close[-1] < np.min(highs_40[max1_idx:max2_idx]):
            patterns.append(("Double Top", 80))
    except: pass

    try:
        highs_25 = high[-25:]
        lows_25 = low[-25:]
        h_slope = np.polyfit(range(25), highs_25, 1)[0]
        l_slope = np.polyfit(range(25), lows_25, 1)[0]
        if h_slope > 0 and l_slope > 0 and l_slope > h_slope and close[-1] < close[-3]:
            patterns.append(("Rising Wedge", 75))
    except: pass

    try:
        highs_20 = high[-20:]
        lows_20 = low[-20:]
        support = np.min(lows_20)
        support_touches = np.sum(lows_20 < support * 1.005)
        highs_trend = np.polyfit(range(20), highs_20, 1)[0]
        if support_touches >= 2 and highs_trend < 0 and close[-1] < support * 1.002:
            patterns.append(("Descending Triangle", 78))
    except: pass

    try:
        pole_drop = (close[-25] - close[-15]) / close[-25]
        flag_slope = np.polyfit(range(10), close[-10:], 1)[0]
        if pole_drop > 0.05 and 0.001 > flag_slope > -0.001 and close[-1] < close[-2]:
            patterns.append(("Bear Flag", 76))
    except: pass

    return patterns


# ─────────────────────────────────────────
# ANALYSIS — 3 TRACKS
# ─────────────────────────────────────────

def analyze(ticker, sector, market_state, regime):
    df = get_data(ticker)
    if df is None:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    price = float(close.iloc[-1])
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_now = float(volume.iloc[-1])

    tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    atr = float(tr.rolling(14).mean().iloc[-1])
    atr_pct = atr / price

    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])

    delta_s = close.diff()
    gain = delta_s.where(delta_s > 0, 0).rolling(14).mean()
    loss = -delta_s.where(delta_s < 0, 0).rolling(14).mean()
    rsi = float((100 - (100 / (1 + gain / loss))).iloc[-1])

    support = float(low.rolling(20).min().iloc[-2])
    resistance = float(high.rolling(20).max().iloc[-2])

    bull_candles = detect_bullish_candles(df)
    bull_charts = detect_bullish_chart(df)
    bear_candles = detect_bearish_candles(df)
    bear_charts = detect_bearish_chart(df)

    all_bull = bull_candles + bull_charts
    all_bear = bear_candles + bear_charts

    results = []

    def make_signal(track, label, direction, pattern, conf, reason):
        if direction == "LONG":
            stop = round(price - atr * 1.5, 2)
            t1 = round(price + atr * 2, 2)
            t2 = round(price + atr * 3.5, 2)
        else:
            stop = round(price + atr * 1.5, 2)
            t1 = round(price - atr * 2, 2)
            t2 = round(price - atr * 3.5, 2)

        rr = round(abs(t1-price)/abs(price-stop), 2) if price != stop else 0
        if rr < 1.5:
            return None

        return {
            "track": track,
            "track_label": label,
            "ticker": ticker,
            "sector": sector,
            "pattern": pattern,
            "direction": direction,
            "price": round(price, 2),
            "stop": stop,
            "stop_pct": round(abs(price-stop)/price*100, 1),
            "t1": t1,
            "t1_pct": round(abs(t1-price)/price*100, 1),
            "t2": t2,
            "t2_pct": round(abs(t2-price)/price*100, 1),
            "rr": rr,
            "reason": reason,
            "confidence": min(conf, 95),
            "market_state": market_state
        }

    if all_bull and vol_now > vol_avg * 1.1:
        top = max(all_bull, key=lambda x: x[1])
        conf = 50 + int(top[1] * 0.3)
        if regime == "BULL": conf += 5
        reason = [f"Pattern: {top[0]}", f"Volume {int(vol_now/vol_avg*100)}%"]
        if conf >= 60:
            s = make_signal("A", "🔵 Signal A — Price Action", "LONG", top[0], conf, reason)
            if s: results.append(s)

    if all_bear and vol_now > vol_avg * 1.1:
        top = max(all_bear, key=lambda x: x[1])
        conf = 50 + int(top[1] * 0.3)
        if regime == "BEAR": conf += 5
        reason = [f"Pattern: {top[0]}", f"Volume {int(vol_now/vol_avg*100)}%"]
        if conf >= 60:
            s = make_signal("A", "🔵 Signal A — Price Action", "SHORT", top[0], conf, reason)
            if s: results.append(s)

    b_long = None
    for p in bull_candles:
        if p[0] == "3 White Soldiers": b_long = p; break
        if p[0] == "Inverted Hammer" and market_state == "CALM": b_long = p; break
    if not b_long:
        for p in bull_charts:
            if p[0] in ["Inverse H&S", "Double Bottom", "Cup & Handle"]: b_long = p; break

    if b_long and price > ema20 and vol_now > vol_avg * 1.2 and atr_pct < 0.03:
        conf = 55 + int(b_long[1] * 0.35)
        if regime == "BULL": conf += 10
        if market_state == "CALM": conf += 5
        reason = [f"Pattern: {b_long[0]}", f"Price > EMA20", f"Volume {int(vol_now/vol_avg*100)}%"]
        if conf >= 65:
            s = make_signal("B", "🟠 Signal B — HAKEM Method", "LONG", b_long[0], conf, reason)
            if s: results.append(s)

    b_short = None
    for p in bear_candles:
        if p[0] == "3 Black Crows": b_short = p; break
        if p[0] == "Shooting Star" and market_state == "CALM": b_short = p; break
    if not b_short:
        for p in bear_charts:
            if p[0] in ["Head & Shoulders", "Double Top", "Rising Wedge"]: b_short = p; break

    if b_short and price < ema20 and vol_now > vol_avg * 1.2 and atr_pct < 0.03:
        conf = 55 + int(b_short[1] * 0.35)
        if regime == "BEAR": conf += 10
        if market_state == "CALM": conf += 5
        reason = [f"Pattern: {b_short[0]}", f"Price < EMA20", f"Volume {int(vol_now/vol_avg*100)}%"]
        if conf >= 65:
            s = make_signal("B", "🟠 Signal B — HAKEM Method", "SHORT", b_short[0], conf, reason)
            if s: results.append(s)

    if all_bull and price > ema20 and vol_now > vol_avg * 1.2:
        top = max(all_bull, key=lambda x: x[1])
        conf = 55 + int(top[1] * 0.35)
        if regime == "BULL": conf += 8
        if market_state == "CALM": conf += 5
        if rsi < 60: conf += 5
        if price > support * 1.005: conf += 5
        reason = [f"Pattern: {top[0]}", f"Price > EMA20", f"Volume {int(vol_now/vol_avg*100)}%"]
        if conf >= 65:
            s = make_signal("C", "🟣 Signal C — Combined", "LONG", top[0], conf, reason)
            if s: results.append(s)

    if all_bear and price < ema20 and vol_now > vol_avg * 1.2:
        top = max(all_bear, key=lambda x: x[1])
        conf = 55 + int(top[1] * 0.35)
        if regime == "BEAR": conf += 8
        if market_state == "CALM": conf += 5
        if rsi > 40: conf += 5
        if price < resistance * 0.995: conf += 5
        reason = [f"Pattern: {top[0]}", f"Price < EMA20", f"Volume {int(vol_now/vol_avg*100)}%"]
        if conf >= 65:
            s = make_signal("C", "🟣 Signal C — Combined", "SHORT", top[0], conf, reason)
            if s: results.append(s)

    return results if results else None


# ─────────────────────────────────────────
# ACTION DECISION
# ─────────────────────────────────────────

def get_action(signal):
    score = 0
    reasons = []
    if signal["confidence"] >= 80:
        score += 1
    else:
        reasons.append("Confidence below 80")
    if signal["rr"] >= 2.0:
        score += 1
    else:
        reasons.append("R/R below 1:2")
    if signal["track"] in ["B", "C"]:
        score += 1
    if score == 3:
        return "🚀 ACTION: ENTER NOW", None
    elif score == 2:
        return "⚡ ACTION: CONSIDER", reasons
    else:
        return "⚠️ ACTION: WAIT", reasons


# ─────────────────────────────────────────
# SEND SIGNAL
# ─────────────────────────────────────────

def send_signal(s, regime):
    opt = get_options_data(s["ticker"], s["direction"])
    action, action_reasons = get_action(s)
    regime_icon = "🟢 Bull" if regime == "BULL" else "🔴 Bear"
    state_icon = "😌 Calm" if s["market_state"] == "CALM" else "⚡ Volatile"
    direction_icon = "📈 LONG" if s["direction"] == "LONG" else "📉 SHORT"

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
{s['track_label']}
━━━━━━━━━━━━━━━━━━━━━━━
📌 {s['ticker']} — {s['sector']}
━━━━━━━━━━━━━━━━━━━━━━━

{direction_icon}  |  {regime_icon}  |  {state_icon}
🕯️ Pattern: {s['pattern']}

"""
    for r in s["reason"]:
        msg += f"• {r}\n"

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
💰 TRADE SETUP
━━━━━━━━━━━━━━━━━━━━━━━
Entry  ▸  ${s['price']}
Stop   ▸  ${s['stop']}  ({'-' if s['direction']=='LONG' else '+'}{s['stop_pct']}%)
T1     ▸  ${s['t1']}  ({'+' if s['direction']=='LONG' else '-'}{s['t1_pct']}%)
T2     ▸  ${s['t2']}  ({'+' if s['direction']=='LONG' else '-'}{s['t2_pct']}%)
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
{'CALL' if s['direction']=='LONG' else 'PUT'}  ${opt['strike']}  |  {opt['dte']} DTE
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
⚠️ No contract matches HAKEM criteria
"""

    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━
⭐ Confidence  {s['confidence']} / 100
━━━━━━━━━━━━━━━━━━━━━━━
{action}"""

    if action_reasons:
        for r in action_reasons:
            msg += f"\n  · {r}"

    msg += """
━━━━━━━━━━━━━━━━━━━━━━━
        📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━"""

    telegram_send(msg)
    log_us_signal(s, regime, s["market_state"], action)
    print(f"Sent: {s['ticker']} {s['direction']} Track {s['track']} — {action}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def run():
    try:
        if not is_market_open():
            print("السوق مغلق")
            return

        market_state, regime = get_market_state()
        print(f"Market: {market_state} | Regime: {regime}")

        best_a_long = None
        best_a_short = None
        best_b_long = None
        best_b_short = None
        best_c_long = None
        best_c_short = None

        for sector, tickers in WATCHLIST.items():
            for ticker in tickers:
                try:
                    results = analyze(ticker, sector, market_state, regime)
                    if not results:
                        continue
                    for signal in results:
                        t = signal["track"]
                        d = signal["direction"]
                        if t == "A" and d == "LONG":
                            if best_a_long is None or signal["confidence"] > best_a_long["confidence"]:
                                best_a_long = signal
                        elif t == "A" and d == "SHORT":
                            if best_a_short is None or signal["confidence"] > best_a_short["confidence"]:
                                best_a_short = signal
                        elif t == "B" and d == "LONG":
                            if best_b_long is None or signal["confidence"] > best_b_long["confidence"]:
                                best_b_long = signal
                        elif t == "B" and d == "SHORT":
                            if best_b_short is None or signal["confidence"] > best_b_short["confidence"]:
                                best_b_short = signal
                        elif t == "C" and d == "LONG":
                            if best_c_long is None or signal["confidence"] > best_c_long["confidence"]:
                                best_c_long = signal
                        elif t == "C" and d == "SHORT":
                            if best_c_short is None or signal["confidence"] > best_c_short["confidence"]:
                                best_c_short = signal
                except Exception as e:
                    print(f"Error {ticker}: {e}")

        sent = False
        for signal in [best_a_long, best_a_short, best_b_long, best_b_short, best_c_long, best_c_short]:
            if signal:
                send_signal(signal, regime)
                sent = True

        if sent:
            telegram_send("✅ System OK — Signals Sent 🇺🇸")
        else:
            telegram_send("📭 🇺🇸 اليوم: لا توجد إشارات أمريكية\nالنظام عمل بشكل طبيعي ✅")

    except Exception as e:
        telegram_send(f"""━━━━━━━━━━━━━━━━━━━━━━━
❌ HAKEM US ERROR
━━━━━━━━━━━━━━━━━━━━━━━

{str(e)}

━━━━━━━━━━━━━━━━━━━━━━━""")
        print(f"FATAL ERROR: {e}")


if __name__ == "__main__":
    run()
