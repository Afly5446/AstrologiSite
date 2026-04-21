from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import os
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import swisseph as swe
from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

BASE_DIR = Path(__file__).resolve().parent
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(Path(__file__).resolve().parent.parent / 'backend' / 'leads.db').as_posix()}")

class Base(DeclarativeBase):
    pass

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=True, default="")
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

ZODIAC_SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
ELEMENT_BY_SIGN = {"Овен": "Огонь", "Телец": "Земля", "Близнецы": "Воздух", "Рак": "Вода", "Лев": "Огонь", "Дева": "Земля", "Весы": "Воздух", "Скорпион": "Вода", "Стрелец": "Огонь", "Козерог": "Земля", "Водолей": "Воздух", "Рыбы": "Вода"}
CHINESE_ANIMALS = ["Крыса", "Бык", "Тигр", "Кролик", "Дракон", "Змея", "Лошадь", "Обезьяна", "Петух", "Собака", "Свинья"]
CHINESE_ELEMENTS = ["Металл", "Вода", "Дерево", "Огонь", "Земля"]
RELATION_PROFILES = {"romance": {"label": "Романтика", "base": 7, "strengths": ["Эмоциональная связь", "Сильное притяжение", "Теплота и забота"], "growth": ["Ожидания и ревность", "Баланс личных границ", "Разный темп решений"]}, "friendship": {"label": "Дружба", "base": 4, "strengths": ["Взаимопонимание", "Легкость общения", "Общие интересы"], "growth": ["Открытый диалог", "Равный вклад", "Регулярная обратная связь"]}, "business": {"label": "Бизнес", "base": 3, "strengths": ["Стратегичность", "Сильная командность", "Фокус на результате"], "growth": ["Согласование ролей", "Скорость решений", "Конструктивная критика"]}}
ASPECT_TARGETS = {"conjunction": 0, "sextile": 60, "square": 90, "trine": 120, "opposition": 180}
PYTHAGOREAN_MAP = {**{chr(c): v for c, v in zip(ord("A"), [1, 2, 3, 4, 5, 6, 7, 8, 9] * 3)}, "А": 1, "Б": 2, "В": 3, "Г": 4, "Д": 5, "Е": 6, "Ё": 7, "Ж": 8, "З": 9, "И": 1, "Й": 2, "К": 3, "Л": 4, "М": 5, "Н": 6, "О": 7, "П": 8, "Р": 9, "С": 1, "Т": 2, "У": 3, "Ф": 4, "Х": 5, "Ц": 6, "Ч": 7, "Ш": 8, "Щ": 9, "Ъ": 1, "Ы": 2, "Ь": 3, "Э": 4, "Ю": 5, "Я": 6}

def parse_timezone(tz_name):
    name = (tz_name or "UTC").strip()
    if not name:
        return timezone.utc
    if name.upper() == "UTC":
        return timezone.utc
    if len(name) == 6 and name[0] in {"+", "-"} and name[3] == ":":
        sign = 1 if name[0] == "+" else -1
        hours = int(name[1:3])
        minutes = int(name[4:6])
        return timezone(sign * timedelta(hours=hours, minutes=minutes))
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc

def parse_birth_datetime(date_value, time_value, timezone_name):
    tzinfo = parse_timezone(timezone_name)
    hour, minute = 12, 0
    if time_value:
        parsed_time = datetime.strptime(time_value, "%H:%M")
        hour = parsed_time.hour
        minute = parsed_time.minute
    local_dt = datetime.strptime(date_value, "%Y-%m-%d").replace(hour=hour, minute=minute, tzinfo=tzinfo)
    return local_dt.astimezone(timezone.utc)

def zodiac_from_longitude(lon):
    idx = int((lon % 360) // 30)
    sign = ZODIAC_SIGNS[idx]
    return sign, ELEMENT_BY_SIGN[sign]

def reduce_to_single_digit(value):
    current = value
    while current > 9 and current not in (11, 22, 33):
        current = sum(int(c) for c in str(current))
    return current

def life_path_number(date):
    digits = date.strftime("%Y%m%d")
    return reduce_to_single_digit(sum(int(c) for c in digits))

def destiny_number(name):
    cleaned = [c for c in name.upper() if c.isalpha()]
    if not cleaned:
        return None
    total = sum(PYTHAGOREAN_MAP.get(c, 0) for c in cleaned)
    if total == 0:
        return None
    return reduce_to_single_digit(total)

def personal_year(date, target_year):
    value = f"{target_year}{date.month:02d}{date.day:02d}"
    return reduce_to_single_digit(sum(int(c) for c in value))

def chinese_data(date):
    year = date.year
    return {"year": year, "animal": CHINESE_ANIMALS[(year - 1900) % 12], "element": CHINESE_ELEMENTS[((year - 1900) % 10) // 2]}

def planet_longitude(utc_dt, planet_id):
    decimal_hour = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour)
    result, _ = swe.calc_ut(jd, planet_id)
    return result[0]

def angle_diff(a, b):
    diff = abs((a - b) % 360)
    return min(diff, 360 - diff)

def nearest_aspect(a, b):
    diff = angle_diff(a, b)
    best_name, best_delta = "neutral", 999.0
    for name, target in ASPECT_TARGETS.items():
        delta = abs(diff - target)
        if delta < best_delta:
            best_delta = delta
            best_name = name
    return best_name, best_delta

def score_by_elements(e1, e2):
    if e1 == e2:
        return 27
    supportive = {("Огонь", "Воздух"), ("Воздух", "Огонь"), ("Земля", "Вода"), ("Вода", "Земля")}
    return 22 if (e1, e2) in supportive else 14

def score_by_numerology(n1, n2):
    diff = abs(n1 - n2)
    if diff == 0:
        return 23
    if diff <= 2:
        return 20
    if diff <= 4:
        return 16
    return 12

def score_by_chinese(c1, c2):
    score = 20 if c1["element"] == c2["element"] else 14
    if c1["animal"] == c2["animal"]:
        score += 2
    return score

def aspect_score(venus_aspect, mars_aspect, moon_aspect):
    base = 8
    weights = {"trine": 9, "sextile": 8, "conjunction": 7, "opposition": 3, "square": 2, "neutral": 5}
    v = max(0, weights[venus_aspect[0]] - int(venus_aspect[1] // 3))
    m = max(0, weights[mars_aspect[0]] - int(mars_aspect[1] // 3))
    moon = max(0, weights[moon_aspect[0]] - int(moon_aspect[1] // 3))
    return base + v + m + moon

def aspect_text(name):
    return {"conjunction": "соединение", "sextile": "секстиль", "square": "квадрат", "trine": "трин", "opposition": "оппозиция", "neutral": "нейтральный аспект"}.get(name, "нейтральный аспект")

def element_relation_text(e1, e2):
    if e1 == e2:
        return "Одинаковые стихии: легко понимать мотивацию друг друга."
    supportive = {("Огонь", "Воздух"), ("Воздух", "Огонь"), ("Земля", "Вода"), ("Вода", "Земля")}
    if (e1, e2) in supportive:
        return "Стихии усиливают друг друга: хороший потенциал синергии."
    return "Стихии контрастные: важны договоренности о темпе и ожиданиях."

def chinese_relation_text(c1, c2):
    if c1["animal"] == c2["animal"]:
        return "Одинаковый знак года: схожие привычки и интуитивное понимание."
    if c1["element"] == c2["element"]:
        return "Одинаковая стихия года: легко синхронизироваться в целях."
    return "Разные энергии года: союз продуктивен при разделении ролей."

def lunar_phase_name(angle):
    if angle < 22.5 or angle >= 337.5: return "Новолуние"
    if angle < 67.5: return "Растущий серп"
    if angle < 112.5: return "Первая четверть"
    if angle < 157.5: return "Растущая луна"
    if angle < 202.5: return "Полнолуние"
    if angle < 247.5: return "Убывающая луна"
    if angle < 292.5: return "Последняя четверть"
    return "Убывающий серп"

def build_compatibility(payload):
    date1 = parse_birth_datetime(payload["birth1"], payload.get("birthTime1"), payload.get("timezone1"))
    date2 = parse_birth_datetime(payload["birth2"], payload.get("birthTime2"), payload.get("timezone2"))
    relation_type = payload.get("relationshipType", "romance")
    profile = RELATION_PROFILES.get(relation_type, RELATION_PROFILES["romance"])
    city1, city2 = (payload.get("city1") or "").strip(), (payload.get("city2") or "").strip()
    name1, name2 = (payload.get("name1") or "").strip(), (payload.get("name2") or "").strip()
    timezone1, timezone2 = (payload.get("timezone1") or "UTC").strip(), (payload.get("timezone2") or "UTC").strip()

    sun1, sun2 = planet_longitude(date1, swe.SUN), planet_longitude(date2, swe.SUN)
    moon1, moon2 = planet_longitude(date1, swe.MOON), planet_longitude(date2, swe.MOON)
    venus1, venus2 = planet_longitude(date1, swe.VENUS), planet_longitude(date2, swe.VENUS)
    mars1, mars2 = planet_longitude(date1, swe.MARS), planet_longitude(date2, swe.MARS)

    sun_sign1, sun_elem1 = zodiac_from_longitude(sun1)
    sun_sign2, sun_elem2 = zodiac_from_longitude(sun2)
    moon_sign1, _ = zodiac_from_longitude(moon1)
    moon_sign2, _ = zodiac_from_longitude(moon2)

    life1, life2 = life_path_number(date1), life_path_number(date2)
    destiny1, destiny2 = destiny_number(name1), destiny_number(name2)
    chinese1, chinese2 = chinese_data(date1), chinese_data(date2)

    venus_aspect = nearest_aspect(venus1, venus2)
    mars_aspect = nearest_aspect(mars1, mars2)
    moon_aspect = nearest_aspect(moon1, moon2)

    total_score = profile["base"] + score_by_elements(sun_elem1, sun_elem2) + score_by_numerology(life1, life2) + score_by_chinese(chinese1, chinese2) + aspect_score(venus_aspect, mars_aspect, moon_aspect)
    total_score = max(30, min(100, total_score))
    current_year = datetime.now(timezone.utc).year
    pyear1, pyear2 = personal_year(date1, current_year), personal_year(date2, current_year)

    compatibility_vector = {"emotional": max(35, min(100, 55 + (12 - int(moon_aspect[1])) * 3)), "communication": max(35, min(100, 50 + score_by_elements(sun_elem1, sun_elem2) * 2)), "passion": max(35, min(100, 52 + (12 - int(mars_aspect[1])) * 3)), "stability": max(35, min(100, 48 + score_by_numerology(life1, life2) * 2))}

    return {"total": total_score, "relationProfile": profile, "western": {"sign1": sun_sign1, "sign2": sun_sign2, "element1": sun_elem1, "element2": sun_elem2, "venusAspect": aspect_text(venus_aspect[0]), "marsAspect": aspect_text(mars_aspect[0]), "elementDynamics": element_relation_text(sun_elem1, sun_elem2)}, "chinese": {"first": chinese1, "second": chinese2}, "numerology": {"lifePath1": life1, "lifePath2": life2, "destiny1": destiny1, "destiny2": destiny2, "personalYear1": pyear1, "personalYear2": pyear2}, "bonus": {"moon1": moon_sign1, "moon2": moon_sign2, "moonAspect": aspect_text(moon_aspect[0])}, "birthMeta": {"city1": city1, "city2": city2, "timezone1": timezone1, "timezone2": timezone2}, "insights": {"strengths": profile["strengths"][:2], "growth": profile["growth"][:2], "weeklyAdvice": "Запланируйте один честный разговор и одно приятное совместное действие на этой неделе.", "conflictTip": f"Зона напряжения чаще всего проявляется через аспект Венеры ({aspect_text(venus_aspect[0])}) и Марса ({aspect_text(mars_aspect[0])}). Используйте формат: факт -> чувство -> просьба.", "forecastTip": "Прогноз: стабильная динамика при регулярном диалоге.", "funTip": "Создайте PNG-карту пары и делитесь результатом в соцсетях."}}

def handler(request):
    if request.method == "POST":
        payload = json.loads(request.body) if request.body else {}
    else:
        payload = {}
    try:
        result = build_compatibility(payload)
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}
    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}