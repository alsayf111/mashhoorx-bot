import os
import requests
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz
import json
import csv

TELEGRAM_TOKEN = os.environ.get(“TELEGRAM_TOKEN”, “”)
CHAT_ID = os.environ.get(“CHAT_ID”, “5652642650”)

def telegram_send(text):
try:
url = f”https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage”
requests.post(url, json={“chat_id”: CHAT_ID, “text”: text})
except Exception as e:
print(f”Telegram error: {e}”)

WATCHLIST_SA = {
“الطاقة”: [“2222.SR”, “2030.SR”, “4030.SR”, “2381.SR”],
“البنوك”: [“1180.SR”, “1120.SR”, “1050.SR”, “1060.SR”, “1080.SR”, “1010.SR”, “1020.SR”, “1030.SR”, “1040.SR”, “1150.SR”, “1160.SR”, “2110.SR”],
“الاتصالات”: [“7010.SR”, “7020.SR”, “7030.SR”, “7040.SR”],
“البتروكيماويات”: [“2010.SR”, “2020.SR”, “2060.SR”, “2070.SR”, “2090.SR”, “2100.SR”, “2120.SR”, “2150.SR”, “2160.SR”, “2170.SR”, “2180.SR”, “2200.SR”, “2210.SR”, “2250.SR”, “2290.SR”, “2300.SR”, “2330.SR”, “2350.SR”],
“التجزئة”: [“4051.SR”, “4190.SR”, “4240.SR”, “4270.SR”, “4290.SR”, “4310.SR”, “4003.SR”, “4008.SR”, “4050.SR”, “4160.SR”, “4180.SR”, “4200.SR”],
“الرعاية الصحية”: [“4002.SR”, “4004.SR”, “4005.SR”, “4006.SR”, “4013.SR”, “4017.SR”, “4019.SR”, “4061.SR”, “4065.SR”],
“العقار”: [“4090.SR”, “4100.SR”, “4150.SR”, “4220.SR”, “4300.SR”, “4322.SR”, “4323.SR”, “4325.SR”, “4326.SR”],
“الصناعة”: [“2040.SR”, “2050.SR”, “2080.SR”, “4140.SR”, “4200.SR”],
“الغذاء والزراعة”: [“6010.SR”, “6020.SR”, “6040.SR”, “6060.SR”, “6070.SR”, “6090.SR”],
“النقل”: [“4031.SR”, “4040.SR”, “9526.SR”, “9527.SR”],
“التأمين”: [“8010.SR”, “8020.SR”, “8030.SR”, “8040.SR”, “8050.SR”, “8060.SR”, “8070.SR”, “8100.SR”, “8120.SR”, “8150.SR”, “8160.SR”, “8180.SR”, “8200.SR”, “8210.SR”, “8230.SR”, “8260.SR”],
“التقنية”: [“7200.SR”, “7201.SR”, “7202.SR”, “9544.SR”, “9545.SR”],
}

# ─────────────────────────────────────────

# MARKET CONDITIONS

# ─────────────────────────────────────────

def is_market_open():
sa = pytz.timezone(“Asia/Riyadh”)
now = datetime.now(sa)
if now.weekday() in [4, 5]:
return False
market_open  = now.replace(hour=10, minute=0, second=0)
market_close = now.replace(hour=16, minute=0, second=0)
return market_open <= now <= market_close

def get_market_state():
try:
df = yf.download(”^TASI.SR”, period=“60d”, interval=“1d”, progress=False)
if df is None or len(df) < 20:
return “CALM”, “BULL”
close = df[“Close”]
high  = df[“High”]
low   = df[“Low”]
tr    = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
atr   = float(tr.rolling(14).mean().iloc[-1])
atr_pct = atr / float(close.iloc[-1])
state   = “CALM” if atr_pct < 0.015 else “VOLATILE”
ma20    = float(close.rolling(20).mean().iloc[-1])
price   = float(close.iloc[-1])
regime  = “BULL” if price > ma20 else “BEAR”
return state, regime
except:
return “CALM”, “BULL”

def get_data(ticker):
try:
df = yf.download(ticker, period=“90d”, interval=“1d”, progress=False)
return df if len(df) >= 50 else None
except:
return None

# ─────────────────────────────────────────

# CANDLESTICK PATTERNS

# ─────────────────────────────────────────

def detect_candle_patterns(df):
patterns = []
o = df[“Open”].values.astype(float)
c = df[“Close”].values.astype(float)
h = df[“High”].values.astype(float)
l = df[“Low”].values.astype(float)

```
def body(i):  return abs(c[i] - o[i])
def full(i):  return h[i] - l[i]
def upper(i): return h[i] - max(o[i], c[i])
def lower(i): return min(o[i], c[i]) - l[i]
def is_green(i): return c[i] > o[i]
def is_red(i):   return c[i] < o[i]

if (is_green(-3) and is_green(-2) and is_green(-1) and
    c[-2] > c[-3] and c[-1] > c[-2] and
    o[-2] > o[-3] and o[-2] < c[-3] and
    o[-1] > o[-2] and o[-1] < c[-2] and
    full(-1) > 0 and body(-1)/full(-1) > 0.6 and
    full(-2) > 0 and body(-2)/full(-2) > 0.6 and
    full(-3) > 0 and body(-3)/full(-3) > 0.6):
    patterns.append(("3 White Soldiers", 90))

if (is_green(-1) and full(-1) > 0 and
    body(-1)/full(-1) > 0.9 and
    upper(-1) < body(-1)*0.05 and
    lower(-1) < body(-1)*0.05):
    patterns.append(("Marubozu", 75))

if (is_red(-2) and is_green(-1) and
    o[-1] < c[-2] and c[-1] > o[-2]):
    patterns.append(("Bullish Engulfing", 70))

if (is_red(-3) and
    body(-2) < body(-3)*0.3 and
    is_green(-1) and
    c[-1] > (o[-3] + c[-3])/2):
    patterns.append(("Morning Star", 72))

if (full(-1) > 0 and
    body(-1)/full(-1) < 0.35 and
    lower(-1) > body(-1)*2 and
    upper(-1) < body(-1)*0.5 and
    c[-4] > c[-1]):
    patterns.append(("Hammer", 65))

if (full(-1) > 0 and
    body(-1) > 0 and
    upper(-1) >= body(-1)*2 and
    lower(-1) < body(-1)*0.3 and
    c[-4] > c[-1]):
    patterns.append(("Inverted Hammer", 62))

if (is_red(-2) and is_green(-1) and
    o[-1] < l[-2] and
    c[-1] > (o[-2] + c[-2])/2):
    patterns.append(("Piercing Line", 68))

if (is_red(-2) and is_green(-1) and
    o[-1] > c[-2] and c[-1] < o[-2]):
    patterns.append(("Bullish Harami", 60))

return patterns
```

# ─────────────────────────────────────────

# CHART PATTERNS

# ─────────────────────────────────────────

def detect_chart_patterns(df):
patterns = []
close = df[“Close”].values.astype(float)
high  = df[“High”].values.astype(float)
low   = df[“Low”].values.astype(float)
n = len(close)

```
try:
    highs_20 = high[-20:]
    lows_20  = low[-20:]
    resistance = np.max(highs_20)
    resistance_touches = np.sum(highs_20 > resistance * 0.995)
    lows_trend = np.polyfit(range(20), lows_20, 1)[0]
    if resistance_touches >= 2 and lows_trend > 0 and close[-1] > resistance * 0.998:
        patterns.append(("Ascending Triangle", 78))
except: pass

try:
    highs_30 = high[-30:]
    lows_30  = low[-30:]
    h_slope  = np.polyfit(range(30), highs_30, 1)[0]
    l_slope  = np.polyfit(range(30), lows_30,  1)[0]
    if h_slope < -0.01 and l_slope > 0.01:
        if close[-1] > close[-2] and close[-1] > np.mean(highs_30[-5:]):
            patterns.append(("Symmetrical Triangle", 72))
except: pass

try:
    highs_25 = high[-25:]
    lows_25  = low[-25:]
    h_slope  = np.polyfit(range(25), highs_25, 1)[0]
    l_slope  = np.polyfit(range(25), lows_25,  1)[0]
    if h_slope < 0 and l_slope < 0 and l_slope < h_slope:
        if close[-1] > close[-3]:
            patterns.append(("Falling Wedge", 75))
except: pass

try:
    lows_40  = low[-40:]
    min1_idx = np.argmin(lows_40[:20])
    min2_idx = np.argmin(lows_40[20:]) + 20
    min1 = lows_40[min1_idx]
    min2 = lows_40[min2_idx]
    if abs(min1 - min2)/min1 < 0.03 and close[-1] > np.max(lows_40[min1_idx:min2_idx]):
        patterns.append(("Double Bottom W", 80))
except: pass

try:
    lows_50 = low[-50:]
    left  = np.min(lows_50[:15])
    head  = np.min(lows_50[15:35])
    right = np.min(lows_50[35:])
    if head < left and head < right and abs(left-right)/left < 0.05:
        neckline = np.max(high[-50:][15:35])
        if close[-1] > neckline * 0.998:
            patterns.append(("Inverse H&S", 85))
except: pass

try:
    if n >= 50:
        cup_low   = np.min(close[-50:-10])
        cup_start = close[-50]
        cup_end   = close[-10]
        handle_low = np.min(close[-10:])
        if (abs(cup_start - cup_end)/cup_start < 0.05 and
            cup_low < cup_start * 0.9 and
            handle_low > cup_low and
            close[-1] > cup_end * 0.995):
            patterns.append(("Cup & Handle", 82))
except: pass

try:
    pole_gain  = (close[-15] - close[-25]) / close[-25]
    flag_slope = np.polyfit(range(10), close[-10:], 1)[0]
    if pole_gain > 0.05 and -0.002 < flag_slope < 0.001:
        if close[-1] > close[-2]:
            patterns.append(("Bull Flag", 76))
except: pass

return patterns
```

# ─────────────────────────────────────────

# SUPPORT & RESISTANCE

# ─────────────────────────────────────────

def get_key_levels(df):
high  = df[“High”].values.astype(float)
low   = df[“Low”].values.astype(float)
close = df[“Close”].values.astype(float)
resistance = float(np.max(high[-20:]))
support    = float(np.min(low[-20:]))
price      = float(close[-1])
near_resistance = abs(price - resistance) / price < 0.015
above_support   = price > support * 1.005
return support, resistance, near_resistance, above_support

# ─────────────────────────────────────────

# ✅ تعديل ١ — RSI الفعلي كفلتر

# ─────────────────────────────────────────

def calc_rsi(close_series, period=14):
delta = close_series.diff()
gain  = delta.where(delta > 0, 0).rolling(period).mean()
loss  = -delta.where(delta < 0, 0).rolling(period).mean()
rs    = gain / loss
rsi   = 100 - (100 / (1 + rs))
return float(rsi.iloc[-1])

def rsi_is_valid(rsi):
“”“RSI بين 40-65 = منطقة شراء صحية، مو overbought ومو في downtrend”””
return 40 <= rsi <= 65

# ─────────────────────────────────────────

# ✅ تعديل ٣ — إيقاف الإشارات في السوق الهابط

# ─────────────────────────────────────────

def market_allows_entry(regime, market_state):
“””
BEAR + VOLATILE = لا إشارات إطلاقاً
BEAR + CALM     = فقط إشارات B وC بثقة عالية جداً
BULL            = كل الإشارات مسموحة
“””
if regime == “BEAR” and market_state == “VOLATILE”:
return False
return True

# ─────────────────────────────────────────

# ✅ تعديل ٥ — سجل الإشارات CSV

# ─────────────────────────────────────────

SIGNALS_LOG = “signals_log.csv”

def log_signal(signal, regime, market_state, action):
sa   = pytz.timezone(“Asia/Riyadh”)
now  = datetime.now(sa).strftime(”%Y-%m-%d %H:%M”)
file_exists = os.path.isfile(SIGNALS_LOG)
with open(SIGNALS_LOG, “a”, newline=””, encoding=“utf-8”) as f:
writer = csv.DictWriter(f, fieldnames=[
“datetime”, “ticker”, “sector”, “track”, “pattern”,
“price”, “stop”, “t1”, “t2”, “rr”,
“confidence”, “rsi”, “regime”, “market_state”, “action”
])
if not file_exists:
writer.writeheader()
writer.writerow({
“datetime”:     now,
“ticker”:       signal[“ticker”],
“sector”:       signal[“sector”],
“track”:        signal[“track”],
“pattern”:      signal[“pattern”],
“price”:        signal[“price”],
“stop”:         signal[“stop”],
“t1”:           signal[“t1”],
“t2”:           signal[“t2”],
“rr”:           signal[“rr”],
“confidence”:   signal[“confidence”],
“rsi”:          signal.get(“rsi”, “-”),
“regime”:       regime,
“market_state”: market_state,
“action”:       action,
})
print(f”📝 Logged: {signal[‘ticker’]} Track {signal[‘track’]}”)

# ─────────────────────────────────────────

# MAIN ANALYSIS — 3 TRACKS (مُحسَّن)

# ─────────────────────────────────────────

def analyze(ticker, sector, market_state, regime):
# ✅ تعديل ٣ — وقف التحليل في السوق الهابط المتوتر
if not market_allows_entry(regime, market_state):
return None

```
df = get_data(ticker)
if df is None:
    return None

close  = df["Close"]
high   = df["High"]
low    = df["Low"]
volume = df["Volume"]

price   = float(close.iloc[-1])
vol_avg = float(volume.rolling(20).mean().iloc[-1])
vol_now = float(volume.iloc[-1])

if price * vol_now < 500_000:
    return None

tr      = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
atr     = float(tr.rolling(14).mean().iloc[-1])
atr_pct = atr / price

ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])

# ✅ تعديل ١ — RSI محسوب ومستخدم فعلياً
rsi = calc_rsi(close)

support, resistance, near_resistance, above_support = get_key_levels(df)

candle_patterns = detect_candle_patterns(df)
chart_patterns  = detect_chart_patterns(df)

if not candle_patterns and not chart_patterns:
    return None

results = []

# ════════════════════════════════
# TRACK A — ✅ تعديل ٢: أضفنا شرط فوق EMA20
# ════════════════════════════════
a_patterns = candle_patterns + chart_patterns
if (a_patterns and
    vol_now > vol_avg * 1.1 and
    price > ema20 and           # ✅ تعديل ٢
    rsi_is_valid(rsi)):         # ✅ تعديل ١
    top  = max(a_patterns, key=lambda x: x[1])
    conf = 50 + int(top[1] * 0.3)
    reason = [
        f"نمط: {top[0]}",
        f"Volume {int(vol_now/vol_avg*100)}% من المتوسط",
        f"RSI: {round(rsi,1)} ✅"
    ]
    if regime == "BULL": conf += 5
    conf = min(conf, 95)
    if conf >= 60:
        stop = round(price - atr * 1.5, 2)
        t1   = round(price + atr * 2,   2)
        t2   = round(price + atr * 3.5, 2)
        rr   = round(abs(t1-price)/abs(price-stop), 2) if price != stop else 0
        if rr >= 1.5:
            results.append({
                "track": "A",
                "track_label": "🔵 إشارة A — Price Action الكامل",
                "ticker": ticker.replace(".SR",""),
                "sector": sector,
                "pattern": top[0],
                "direction": "شراء",
                "price": round(price,2), "stop": stop,
                "stop_pct": round(abs(price-stop)/price*100,1),
                "t1": t1, "t1_pct": round(abs(t1-price)/price*100,1),
                "t2": t2, "t2_pct": round(abs(t2-price)/price*100,1),
                "rr": rr, "reason": reason,
                "confidence": conf, "rsi": round(rsi,1),
                "market_state": market_state
            })

# ════════════════════════════════
# TRACK B — منهجية HAKEM
# ════════════════════════════════
b_candle = None
for p in candle_patterns:
    if p[0] == "3 White Soldiers":
        b_candle = p; break
    if p[0] == "Inverted Hammer" and market_state == "CALM":
        b_candle = p; break

b_chart = None
for p in chart_patterns:
    if p[0] in ["Inverse H&S", "Double Bottom W", "Cup & Handle"]:
        b_chart = p; break

b_top = b_candle or b_chart
# ✅ تعديل ١: أضفنا شرط RSI صحيح
# ✅ تعديل ٣: في BEAR نرفع حد الثقة
if (b_top and
    price > ema20 and
    vol_now > vol_avg * 1.2 and
    atr_pct < 0.03 and
    rsi_is_valid(rsi)):         # ✅ تعديل ١
    conf = 55 + int(b_top[1] * 0.35)
    reason = [
        f"نمط: {b_top[0]}",
        f"السعر فوق EMA20",
        f"Volume {int(vol_now/vol_avg*100)}% من المتوسط",
        f"RSI: {round(rsi,1)} ✅"
    ]
    if regime == "BULL":        conf += 10
    if regime == "BEAR":        conf -= 15  # ✅ تعديل ٣ عقوبة في BEAR
    if market_state == "CALM":  conf += 5
    conf = min(conf, 95)
    min_conf = 75 if regime == "BEAR" else 65  # ✅ تعديل ٣
    if conf >= min_conf:
        stop = round(price - atr * 1.5, 2)
        t1   = round(price + atr * 2,   2)
        t2   = round(price + atr * 3.5, 2)
        rr   = round(abs(t1-price)/abs(price-stop), 2) if price != stop else 0
        if rr >= 1.5:
            results.append({
                "track": "B",
                "track_label": "🟠 إشارة B — منهجية HAKEM",
                "ticker": ticker.replace(".SR",""),
                "sector": sector,
                "pattern": b_top[0],
                "direction": "شراء",
                "price": round(price,2), "stop": stop,
                "stop_pct": round(abs(price-stop)/price*100,1),
                "t1": t1, "t1_pct": round(abs(t1-price)/price*100,1),
                "t2": t2, "t2_pct": round(abs(t2-price)/price*100,1),
                "rr": rr, "reason": reason,
                "confidence": conf, "rsi": round(rsi,1),
                "market_state": market_state
            })

# ════════════════════════════════
# TRACK C — المنهجية المشتركة
# ════════════════════════════════
c_patterns = candle_patterns + chart_patterns
# ✅ تعديل ١: أضفنا شرط RSI صحيح
if (c_patterns and
    price > ema20 and
    vol_now > vol_avg * 1.2 and
    rsi_is_valid(rsi)):         # ✅ تعديل ١
    top  = max(c_patterns, key=lambda x: x[1])
    conf = 55 + int(top[1] * 0.35)
    reason = [
        f"نمط: {top[0]}",
        f"السعر فوق EMA20",
        f"Volume {int(vol_now/vol_avg*100)}% من المتوسط",
        f"RSI: {round(rsi,1)} ✅"
    ]
    if regime == "BULL":        conf += 8
    if regime == "BEAR":        conf -= 15  # ✅ تعديل ٣
    if market_state == "CALM":  conf += 5
    if rsi < 60:                conf += 5   # ✅ تعديل ١ مكافأة إضافية
    if above_support:           conf += 5
    conf = min(conf, 95)
    min_conf = 75 if regime == "BEAR" else 65  # ✅ تعديل ٣
    if conf >= min_conf:
        stop = round(price - atr * 1.5, 2)
        t1   = round(price + atr * 2,   2)
        t2   = round(price + atr * 3.5, 2)
        rr   = round(abs(t1-price)/abs(price-stop), 2) if price != stop else 0
        if rr >= 1.5:
            results.append({
                "track": "C",
                "track_label": "🟣 إشارة C — المنهجية المشتركة",
                "ticker": ticker.replace(".SR",""),
                "sector": sector,
                "pattern": top[0],
                "direction": "شراء",
                "price": round(price,2), "stop": stop,
                "stop_pct": round(abs(price-stop)/price*100,1),
                "t1": t1, "t1_pct": round(abs(t1-price)/price*100,1),
                "t2": t2, "t2_pct": round(abs(t2-price)/price*100,1),
                "rr": rr, "reason": reason,
                "confidence": conf, "rsi": round(rsi,1),
                "market_state": market_state
            })

return results if results else None
```

# ─────────────────────────────────────────

# TELEGRAM MESSAGE

# ─────────────────────────────────────────

def get_action(signal, regime):
score   = 0
reasons = []
if signal[“confidence”] >= 80:
score += 1
else:
reasons.append(“الثقة دون 80”)
if signal[“rr”] >= 2.0:
score += 1
else:
reasons.append(“العائد/المخاطرة دون 1:2”)
if signal[“track”] in [“B”, “C”]:
score += 1
# ✅ تعديل ٣ — في BEAR نرفع المعيار
if regime == “BEAR”:
score -= 1
if score >= 3:
return “🚀 القرار: ادخل الآن”, None
elif score == 2:
return “⚡ القرار: فكّر فيه”, reasons
else:
return “⚠️ القرار: انتظر”, reasons

def send_signal(s, regime):
action, action_reasons = get_action(s, regime)
regime_icon = “🟢 صاعد” if regime == “BULL” else “🔴 هابط”
state_icon  = “😌 هادئ” if s[“market_state”] == “CALM” else “⚡ متوتر”

```
msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
```

{s[‘track_label’]}
━━━━━━━━━━━━━━━━━━━━━━━
📌 {s[‘ticker’]} — {s[‘sector’]}
━━━━━━━━━━━━━━━━━━━━━━━

📈 شراء  |  {regime_icon}  |  {state_icon}
🕯️ النمط: {s[‘pattern’]}
📊 RSI: {s.get(‘rsi’, ‘-’)}

“””
for r in s[“reason”]:
msg += f”• {r}\n”

```
msg += f"""
```

━━━━━━━━━━━━━━━━━━━━━━━
💰 تفاصيل الصفقة
━━━━━━━━━━━━━━━━━━━━━━━
الدخول  ▸  {s[‘price’]} ر.س
الوقف   ▸  {s[‘stop’]} ر.س  (-{s[‘stop_pct’]}%)
ه1      ▸  {s[‘t1’]} ر.س  (+{s[‘t1_pct’]}%)
ه2      ▸  {s[‘t2’]} ر.س  (+{s[‘t2_pct’]}%)
ع/م     ▸  1 : {s[‘rr’]}

━━━━━━━━━━━━━━━━━━━━━━━
⭐ الثقة  {s[‘confidence’]} / 100
━━━━━━━━━━━━━━━━━━━━━━━
{action}”””

```
if action_reasons:
    for r in action_reasons:
        msg += f"\n  · {r}"

msg += """
```

━━━━━━━━━━━━━━━━━━━━━━━
📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━”””

```
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
log_signal(s, regime, s["market_state"], action)  # ✅ تعديل ٥
print(f"Sent SA: {s['ticker']} Track {s['track']} — {action}")
```

# ─────────────────────────────────────────

# ✅ تعديل ٦ — تقرير نهاية اليوم

# ─────────────────────────────────────────

def send_daily_report(signals_sent, regime, market_state):
sa  = pytz.timezone(“Asia/Riyadh”)
now = datetime.now(sa).strftime(”%Y-%m-%d”)
regime_icon = “🟢 صاعد” if regime == “BULL” else “🔴 هابط”
state_icon  = “😌 هادئ” if market_state == “CALM” else “⚡ متوتر”

```
if signals_sent:
    tracks = [s["track"] for s in signals_sent]
    tickers = [s["ticker"] for s in signals_sent]
    confs   = [s["confidence"] for s in signals_sent]
    avg_conf = round(sum(confs) / len(confs), 1)

    lines = "\n".join([
        f"  • {s['ticker']} [{s['track']}] — ثقة {s['confidence']} — {s['pattern']}"
        for s in signals_sent
    ])

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
```

📋 تقرير نهاية اليوم
━━━━━━━━━━━━━━━━━━━━━━━
📅 {now}
السوق: {regime_icon} | {state_icon}

✅ إشارات اليوم: {len(signals_sent)}
📊 متوسط الثقة: {avg_conf}

{lines}

━━━━━━━━━━━━━━━━━━━━━━━
📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━”””
else:
msg = f””“━━━━━━━━━━━━━━━━━━━━━━━
📋 تقرير نهاية اليوم
━━━━━━━━━━━━━━━━━━━━━━━
📅 {now}
السوق: {regime_icon} | {state_icon}

📭 لا توجد إشارات اليوم
النظام عمل بشكل طبيعي ✅

━━━━━━━━━━━━━━━━━━━━━━━
📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━”””

```
telegram_send(msg)
print("Daily report sent.")
```

# ─────────────────────────────────────────

# MAIN

# ─────────────────────────────────────────

def run(is_final_run=False):
try:
if not is_market_open():
print(“السوق السعودي مغلق”)
return

```
    market_state, regime = get_market_state()
    print(f"Market: {market_state} | Regime: {regime}")

    # ✅ تعديل ٣ — إيقاف كامل في BEAR + VOLATILE
    if not market_allows_entry(regime, market_state):
        telegram_send(
            "⛔ السوق هابط ومتوتر — تم إيقاف الإشارات اليوم لحماية رأس المال\n📡 HAKEM CONSULTING"
        )
        print("BEAR+VOLATILE — signals blocked")
        return

    best_a = None
    best_b = None
    best_c = None

    for sector, tickers in WATCHLIST_SA.items():
        for ticker in tickers:
            try:
                results = analyze(ticker, sector, market_state, regime)
                if not results:
                    continue
                for signal in results:
                    if signal["track"] == "A":
                        if best_a is None or signal["confidence"] > best_a["confidence"]:
                            best_a = signal
                    elif signal["track"] == "B":
                        if best_b is None or signal["confidence"] > best_b["confidence"]:
                            best_b = signal
                    elif signal["track"] == "C":
                        if best_c is None or signal["confidence"] > best_c["confidence"]:
                            best_c = signal
            except Exception as e:
                print(f"Error {ticker}: {e}")

    signals_sent = []
    for signal in [best_a, best_b, best_c]:
        if signal:
            send_signal(signal, regime)
            signals_sent.append(signal)

    if signals_sent:
        telegram_send("✅ System OK — Signals Sent 🇸🇦")
        print("Signals sent successfully")
    else:
        print("No signals today")

    # ✅ تعديل ٦ — تقرير نهاية اليوم فقط في آخر تشغيل
    if is_final_run:
        send_daily_report(signals_sent, regime, market_state)

except Exception as e:
    telegram_send(f"""━━━━━━━━━━━━━━━━━━━━━━━
```

❌ HAKEM SA ERROR
━━━━━━━━━━━━━━━━━━━━━━━

{str(e)}

━━━━━━━━━━━━━━━━━━━━━━━”””)
print(f”FATAL ERROR: {e}”)

if **name** == “**main**”:
import sys
final = “–final” in sys.argv
run(is_final_run=final)
