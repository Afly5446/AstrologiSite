from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import swisseph as swe
from dotenv import load_dotenv
import os
import json
import time
import requests

load_dotenv()

ZODIAC_SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
ELEMENT_BY_SIGN = {"Овен": "Огонь", "Телец": "Земля", "Близнецы": "Воздух", "Рак": "Вода", "Лев": "Огонь", "Дева": "Земля", "Весы": "Воздух", "Скорпион": "Вода", "Стрелец": "Огонь", "Козерог": "Земля", "Водолей": "Воздух", "Рыбы": "Вода"}
CHINESE_ANIMALS = ["Крыса", "Бык", "Тигр", "Кролик", "Дракон", "Змея", "Лошадь", "Коза", "Обезьяна", "Петух", "Собака", "Свинья"]
CHINESE_ELEMENTS = ["Металл", "Вода", "Дерево", "Огонь", "Земля"]
RELATION_PROFILES = {"romance": {"label": "Романтика", "base": 7, "strengths": ["Эмоциональная связь", "Сильное притяжение", "Теплота"], "growth": ["Ожидания", "Баланс границ", "Разный темп"]}, "friendship": {"label": "Дружба", "base": 4, "strengths": ["Взаимопонимание", "Легкость", "Общие интересы"], "growth": ["Диалог", "Равный вклад", "Обратная связь"]}, "business": {"label": "Бизнес", "base": 3, "strengths": ["Стратегичность", "Командность", "Фокус"], "growth": ["Роли", "Скорость", "Критика"]}}

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

SYSTEM_PROMPT = """Ты — опытный эксперт-коуч по отношениям. Даёшь тёплые, конкретные советы. Отвечай на русском как друг.

Формат: кратко, до 3–5 абзацев, без длинных вступлений."""


def _tg_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_lead_telegram_html(name, contact, message_body, context, *, at_dt=None):
    ctx = context or {}
    lines = []
    header = "📋 <b>Новая заявка</b> <i>(сайт / Vercel)</i>"
    lines.append(header)
    if at_dt is not None:
        utc = at_dt.astimezone(timezone.utc) if at_dt.tzinfo else at_dt.replace(tzinfo=timezone.utc)
        lines.append(f"🕐 {utc.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")
    lines.append(f"<b>Имя:</b> {_tg_escape(name)}")
    lines.append(f"<b>Контакт:</b> {_tg_escape(contact)}")
    msg = message_body or "—"
    if len(msg) > 2800:
        msg = msg[:2797] + "…"
    lines.append(f"<b>Сообщение:</b> {_tg_escape(msg)}")
    score = ctx.get("score")
    rel = (ctx.get("relationType") or "").strip()
    c1 = (ctx.get("city1") or "").strip()
    c2 = (ctx.get("city2") or "").strip()
    tz1 = (ctx.get("timezone1") or "").strip()
    tz2 = (ctx.get("timezone2") or "").strip()
    if score is not None or rel or c1 or c2 or tz1 or tz2:
        lines.append("")
        lines.append("<b>Контекст калькулятора:</b>")
        if score is not None:
            lines.append(f"• Балл совместимости: {_tg_escape(str(score))}")
        if rel:
            lines.append(f"• Тип связи: {_tg_escape(rel)}")
        if c1 or c2:
            lines.append(f"• Города: {_tg_escape(c1 or '—')} / {_tg_escape(c2 or '—')}")
        if tz1 or tz2:
            lines.append(f"• Часовые пояса: {_tg_escape(tz1 or '—')} / {_tg_escape(tz2 or '—')}")
    text = "\n".join(lines)
    return text[:4090] + "…" if len(text) > 4090 else text


def _telegram_proxy_dict():
    raw = (
        os.getenv("TELEGRAM_HTTPS_PROXY", "").strip()
        or os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
    )
    if not raw:
        return None
    return {"http": raw, "https": raw}


def telegram_api_send(payload):
    if not TELEGRAM_BOT_TOKEN:
        return False, "no token"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    proxies = _telegram_proxy_dict()
    last_err = ""
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, timeout=18, proxies=proxies)
            try:
                data = resp.json()
            except ValueError:
                data = {}
            if resp.status_code == 200 and isinstance(data, dict) and data.get("ok"):
                return True, ""
            last_err = resp.text[:400] if resp.text else str(resp.status_code)
        except Exception as exc:
            last_err = str(exc)
        if attempt < 2:
            time.sleep(0.6 * (2**attempt))
    return False, last_err


def send_lead_telegram(name, contact, message_body, context):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    text = format_lead_telegram_html(
        name, contact, message_body, context, at_dt=datetime.now(timezone.utc)
    )
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    ok, err = telegram_api_send(payload)
    if not ok:
        print(f"Telegram (Vercel): не отправлено — {err[:400]}")

def parse_tz(tz):
    if not tz: return timezone.utc
    if tz.upper() == "UTC": return timezone.utc
    if len(tz) == 6 and tz[0] in "+-" and tz[3] == ":":
        s = 1 if tz[0] == "+" else -1
        return timezone(s * timedelta(hours=int(tz[1:3]), minutes=int(tz[4:6])))
    try: return ZoneInfo(tz)
    except: return timezone.utc

def birth_dt(date_val, time_val, tz):
    tzi = parse_tz(tz)
    h, m = 12, 0
    if time_val:
        pt = datetime.strptime(time_val, "%H:%M")
        h, m = pt.hour, pt.minute
    return datetime.strptime(date_val, "%Y-%m-%d").replace(hour=h, minute=m, tzinfo=tzi).astimezone(timezone.utc)

def zodiac(lon):
    return ZODIAC_SIGNS[int((lon % 360) // 30)], ELEMENT_BY_SIGN[ZODIAC_SIGNS[int((lon % 360) // 30)]]

def reduce_digit(v):
    while v > 9 and v not in (11, 22, 33):
        v = sum(int(c) for c in str(v))
    return v

def life_path(d):
    return reduce_digit(sum(int(c) for c in d.strftime("%Y%m%d")))

def chinese(d):
    y = d.year
    return {"animal": CHINESE_ANIMALS[(y-1900)%12], "element": CHINESE_ELEMENTS[((y-1900)%10)//2]}

def planet(dt, pid):
    dh = dt.hour + dt.minute/60 + dt.second/3600
    jd = swe.julday(dt.year, dt.month, dt.day, dh)
    r, _ = swe.calc_ut(jd, pid)
    return r[0]

def score_elem(e1, e2):
    if e1 == e2: return 27
    return 22 if (e1,e2) in {("Огонь","Воздух"),("Воздух","Огонь"),("Земля","Вода"),("Вода","Земля")} else 14

def score_num(n1, n2):
    d = abs(n1-n2)
    if d == 0: return 23
    if d <= 2: return 20
    if d <= 4: return 16
    return 12

def score_chinese(c1, c2):
    return 20 if c1["element"]==c2["element"] else 14

def handler(req):
    path = req.uri.split('?')[0] if req.uri else "/"
    method = req.method
    
    # Parse body
    body = req.body or b"{}"
    try:
        payload = json.loads(body) if body else {}
    except:
        payload = {}
    
    if path == "/api/compatibility" and method == "POST":
        
        d1 = birth_dt(payload.get("birth1"), payload.get("birthTime1"), payload.get("timezone1"))
        d2 = birth_dt(payload.get("birth2"), payload.get("birthTime2"), payload.get("timezone2"))
        rp = payload.get("relationshipType", "romance")
        p = RELATION_PROFILES.get(rp, RELATION_PROFILES["romance"])
        
        try:
            s1, e1 = zodiac(planet(d1, swe.SUN))
            s2, e2 = zodiac(planet(d2, swe.SUN))
            c1, c2 = chinese(d1), chinese(d2)
            l1, l2 = life_path(d1), life_path(d2)
            
            total = p["base"] + score_elem(e1,e2) + score_num(l1,l2) + score_chinese(c1,c2)
            total = max(30, min(100, total))
            
            result = {
                "total": total,
                "relationProfile": p,
                "western": {"sign1": s1, "sign2": s2, "element1": e1, "element2": e2},
                "chinese": {"first": c1, "second": c2},
                "numerology": {"lifePath1": l1, "lifePath2": l2},
                "insights": {"strengths": p["strengths"][:2], "growth": p["growth"][:2]}
            }
            return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}
        except Exception as e:
            return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}
    
    if path == "/api/chat" and method == "POST":
        message = (payload.get("message") or "").strip()
        if not message:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Введите сообщение"})}
        
        if not DEEPSEEK_API_KEY:
            return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"reply": "Чат недоступен. Оставьте заявку."})}
        
        try:
            resp = requests.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}],
                    "temperature": 0.65,
                    "max_tokens": 380,
                    "top_p": 0.9,
                },
                timeout=40
            )
            reply = resp.json()["choices"][0]["message"]["content"]
        except:
            reply = "Не удалось получить ответ. Попробуйте ещё раз."
        
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"reply": reply})}
    
    if path == "/api/leads" and method == "POST":
        
        name = (payload.get("name") or "").strip()
        contact = (payload.get("contact") or "").strip()
        message = (payload.get("message") or "").strip()
        
        if not name or not contact:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Введите имя и контакт"})}
        
        send_lead_telegram(name, contact, message, payload.get("context") or {})

        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"ok": True, "message": "Заявка отправлена"})}
    
    if path == "/leads":
        return {"statusCode": 200, "headers": {"Content-Type": "text/html"}, "body": "<html><body><h1>Заявки</h1><p>Заявок пока нет</p></body></html>"}
    
    return {"statusCode": 404, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Not found"})}