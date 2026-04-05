import os
import requests
from datetime import datetime
import pytz

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8719936616:AAHIhk-64LtEcYcBWKBJ8RG6s6LPpPJpd68")
LOG_CHANNEL_ID = "-1003880386831"

# رأس المال
US_CAPITAL = 1000      # دولار
US_PER_TRADE = 100     # 10% لكل صفقة
SA_CAPITAL = 3750      # ريال
SA_PER_TRADE = 375     # 10% لكل صفقة

def send_log(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": LOG_CHANNEL_ID, "text": msg})


def log_us_signal(signal, regime, market_state, action):
    """تسجيل إشارة السوق الأمريكي"""
    now = datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")
    direction_icon = "📈" if signal["direction"] == "LONG" else "📉"
    contract = "CALL" if signal["direction"] == "LONG" else "PUT"
    regime_icon = "🟢" if regime == "BULL" else "🔴"
    state_icon = "😌" if market_state == "CALM" else "⚡"

    # نسبة المخاطرة
    risk_amount = round(US_PER_TRADE * signal["stop_pct"] / 100, 2)
    reward_amount = round(US_PER_TRADE * signal["t1_pct"] / 100, 2)

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
📋 US TRADE LOG
━━━━━━━━━━━━━━━━━━━━━━━
🕐 {now}
🇺🇸 السوق الأمريكي

📌 {signal['ticker']} — {signal['sector']}
{direction_icon} {signal['direction']}  |  {regime_icon}  |  {state_icon}
🕯️ النمط: {signal['pattern']}
🎯 المسار: Track {signal['track']}

━━━━━━━━━━━━━━━━━━━━━━━
💰 تفاصيل الصفقة
━━━━━━━━━━━━━━━━━━━━━━━
Entry  ▸  ${signal['price']}
Stop   ▸  ${signal['stop']}  (-{signal['stop_pct']}%)
T1     ▸  ${signal['t1']}  (+{signal['t1_pct']}%)
T2     ▸  ${signal['t2']}  (+{signal['t2_pct']}%)
R/R    ▸  1 : {signal['rr']}

━━━━━━━━━━━━━━━━━━━━━━━
📊 Options: {contract}
━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━
💵 إدارة رأس المال
━━━━━━━━━━━━━━━━━━━━━━━
المحفظة الكلية  ▸  ${US_CAPITAL}
حجم الصفقة     ▸  ${US_PER_TRADE} (10%)
المخاطرة        ▸  ${risk_amount}
الربح المتوقع   ▸  ${reward_amount}

━━━━━━━━━━━━━━━━━━━━━━━
⭐ Confidence: {signal['confidence']}/100
{action}
━━━━━━━━━━━━━━━━━━━━━━━
        📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━"""

    send_log(msg)
    print(f"US Log sent: {signal['ticker']}")


def log_sa_signal(signal, regime, market_state, action):
    """تسجيل إشارة السوق السعودي"""
    now = datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")
    direction_icon = "📈" if signal["direction"] == "شراء" else "📉"
    regime_icon = "🟢" if regime == "BULL" else "🔴"
    state_icon = "😌" if market_state == "CALM" else "⚡"

    risk_amount = round(SA_PER_TRADE * signal["stop_pct"] / 100, 2)
    reward_amount = round(SA_PER_TRADE * signal["t1_pct"] / 100, 2)

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
📋 SA TRADE LOG
━━━━━━━━━━━━━━━━━━━━━━━
🕐 {now}
🇸🇦 السوق السعودي

📌 {signal['ticker']} — {signal['sector']}
{direction_icon} {signal['direction']}  |  {regime_icon}  |  {state_icon}
🕯️ النمط: {signal['pattern']}
🎯 المسار: Track {signal['track']}

━━━━━━━━━━━━━━━━━━━━━━━
💰 تفاصيل الصفقة
━━━━━━━━━━━━━━━━━━━━━━━
الدخول  ▸  {signal['price']} ر.س
الوقف   ▸  {signal['stop']} ر.س  (-{signal['stop_pct']}%)
ه1      ▸  {signal['t1']} ر.س  (+{signal['t1_pct']}%)
ه2      ▸  {signal['t2']} ر.س  (+{signal['t2_pct']}%)
ع/م     ▸  1 : {signal['rr']}

━━━━━━━━━━━━━━━━━━━━━━━
💵 إدارة رأس المال
━━━━━━━━━━━━━━━━━━━━━━━
المحفظة الكلية  ▸  {SA_CAPITAL} ر.س
حجم الصفقة     ▸  {SA_PER_TRADE} ر.س (10%)
المخاطرة        ▸  {risk_amount} ر.س
الربح المتوقع   ▸  {reward_amount} ر.س

━━━━━━━━━━━━━━━━━━━━━━━
⭐ Confidence: {signal['confidence']}/100
{action}
━━━━━━━━━━━━━━━━━━━━━━━
        📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━"""

    send_log(msg)
    print(f"SA Log sent: {signal['ticker']}")


def log_summary(us_signals, sa_signals, date=None):
    """ملخص يومي"""
    now = datetime.now(pytz.timezone("Asia/Riyadh"))
    date_str = date or now.strftime("%Y-%m-%d")

    total = len(us_signals) + len(sa_signals)

    msg = f"""━━━━━━━━━━━━━━━━━━━━━━━
📊 HAKEM DAILY SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━
📅 {date_str}

🇺🇸 إشارات أمريكية: {len(us_signals)}
🇸🇦 إشارات سعودية: {len(sa_signals)}
📈 إجمالي: {total} إشارة

━━━━━━━━━━━━━━━━━━━━━━━
🔵 Track A: {sum(1 for s in us_signals+sa_signals if s.get('track')=='A')}
🟠 Track B: {sum(1 for s in us_signals+sa_signals if s.get('track')=='B')}
🟣 Track C: {sum(1 for s in us_signals+sa_signals if s.get('track')=='C')}
━━━━━━━━━━━━━━━━━━━━━━━
        📡 HAKEM CONSULTING
━━━━━━━━━━━━━━━━━━━━━━━"""

    send_log(msg)
    print("Daily summary sent")


if __name__ == "__main__":
    # اختبار
    send_log("✅ HAKEM Logger — جاهز ويعمل بشكل صحيح!")
