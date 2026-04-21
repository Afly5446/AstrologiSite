import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import swisseph as swe
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
ZODIAC_SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
ELEMENT_BY_SIGN = {"Овен": "Огонь", "Телец": "Земля", "Близнецы": "Воздух", "Рак": "Вода", "Лев": "Огонь", "Дева": "Земля", "Весы": "Воздух", "Скорпион": "Вода", "Стрелец": "Огонь", "Козерог": "Земля", "Водолей": "Воздух", "Рыбы": "Вода"}
CHINESE_ANIMALS = ["Крыса", "Бык", "Тигр", "Кролик", "Дракон", "Змея", "Лошадь", "Обезьяна", "Петух", "Собака", "Свинья"]
CHINESE_ELEMENTS = ["Металл", "Вода", "Дерево", "Огонь", "Земля"]
RELATION_PROFILES = {"romance": {"label": "Романтика", "base": 7, "strengths": ["Эмоциональная связь", "Сильное притяжение", "Теплота и забота"], "growth": ["Ожидания и ревность", "Баланс границ", "Разный темп"]}, "friendship": {"label": "Дружба", "base": 4, "strengths": ["Взаимопонимание", "Легкость", "Общие интересы"], "growth": ["Диалог", "Равный вклад", "Обратная связь"]}, "business": {"label": "Бизнес", "base": 3, "strengths": ["Стратегичность", "Командность", "Фокус"], "growth": ["Роли", "Скорость", "Критика"]}}
ASPECT_TARGETS = {"conjunction": 0, "sextile": 60, "square": 90, "trine": 120, "opposition": 180}

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

def destiny(name):
    if not name: return None
    total = sum([1,2,3,4,5,6,7,8,9][ord(c.upper())-65] for c in name.upper() if c.isalpha() and 65 <= ord(c.upper()) <= 90)
    return reduce_digit(total) if total else None

def chinese(d):
    y = d.year
    return {"animal": CHINESE_ANIMALS[(y-1900)%12], "element": CHINESE_ELEMENTS[((y-1900)%10)//2]}

def planet(dt, pid):
    dh = dt.hour + dt.minute/60 + dt.second/3600
    jd = swe.julday(dt.year, dt.month, dt.day, dh)
    r, _ = swe.calc_ut(jd, pid)
    return r[0]

def aspect(a, b):
    diff = min(abs(a-b)%360, 360-abs(a-b)%360)
    best = "neutral"
    for n, t in ASPECT_TARGETS.items():
        if abs(diff-t) < abs(diff - ASPECT_TARGETS[best]):
            best = n
    return best

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

def aspect_score(va, ma, moa):
    w = {"trine":9,"sextile":8,"conjunction":7,"opposition":3,"square":2,"neutral":5}
    return 8 + max(0,w[va[0]]-va[1]//3) + max(0,w[ma[0]]-ma[1]//3) + max(0,w[moa[0]]-moa[1]//3)

def handler(req):
    try:
        payload = json.loads(req.body) if req.body else {}
    except:
        payload = {}
    
    d1 = birth_dt(payload.get("birth1"), payload.get("birthTime1"), payload.get("timezone1"))
    d2 = birth_dt(payload.get("birth2"), payload.get("birthTime2"), payload.get("timezone2"))
    rp = payload.get("relationshipType", "romance")
    p = RELATION_PROFILES.get(rp, RELATION_PROFILES["romance"])
    
    s1, e1 = zodiac(planet(d1, swe.SUN))
    s2, e2 = zodiac(planet(d2, swe.SUN))
    v1, v2 = planet(d1, swe.VENUS), planet(d2, swe.VENUS)
    m1, m2 = planet(d1, swe.MARS), planet(d2, swe.MARS)
    mn1, mn2 = planet(d1, swe.MOON), planet(d2, swe.MOON)
    
    l1, l2 = life_path(d1), life_path(d2)
    d1n, d2n = destiny(payload.get("name1","")), destiny(payload.get("name2",""))
    c1, c2 = chinese(d1), chinese(d2)
    
    va = aspect(v1, v2)
    ma = aspect(m1, m2)
    moa = aspect(mn1, mn2)
    
    total = p["base"] + score_elem(e1,e2) + score_num(l1,l2) + score_chinese(c1,c2) + aspect_score(va, ma, moa)
    total = max(30, min(100, total))
    
    result = {
        "total": total,
        "relationProfile": p,
        "western": {"sign1": s1, "sign2": s2, "element1": e1, "element2": e2},
        "chinese": {"first": c1, "second": c2},
        "numerology": {"lifePath1": l1, "lifePath2": l2, "destiny1": d1n, "destiny2": d2n},
        "bonus": {"moon1": zodiac(mn1)[0], "moon2": zodiac(mn2)[0]},
        "insights": {"strengths": p["strengths"][:2], "growth": p["growth"][:2]}
    }
    
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}