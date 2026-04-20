from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
import requests
from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
import swisseph as swe

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()

SYSTEM_PROMPT = """Ты — опытный эксперт-коуч по отношениям с 15-летним стажем. Ты помогаешь людям разобраться в их отношениях, даёшь мудрые и тёплые советы. Твой стиль общения — как опытный друг, который искренне заботится. Ты используешь нумерологию и астрологию как инструменты самопознания, но фокусируешься на психологии отношений и практических советах. Отвечай на русском языке, будто ты живой человек — не как робот. Будь конкретным, задавай уточняющие вопросы. Избегай общих фраз типа "всё будет хорошо"."""

chat_history: dict[str, list[dict[str, str]]] = {}


BASE_DIR = Path(__file__).resolve().parent.parent
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(Path(__file__).resolve().parent / 'leads.db').as_posix()}")
CRM_WEBHOOK_URL = os.getenv("CRM_WEBHOOK_URL", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


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


engine = create_engine(DB_URL, future=True)
Base.metadata.create_all(engine)


ZODIAC_SIGNS = [
    "Овен",
    "Телец",
    "Близнецы",
    "Рак",
    "Лев",
    "Дева",
    "Весы",
    "Скорпион",
    "Стрелец",
    "Козерог",
    "Водолей",
    "Рыбы",
]

ELEMENT_BY_SIGN = {
    "Овен": "Огонь",
    "Телец": "Земля",
    "Близнецы": "Воздух",
    "Рак": "Вода",
    "Лев": "Огонь",
    "Дева": "Земля",
    "Весы": "Воздух",
    "Скорпион": "Вода",
    "Стрелец": "Огонь",
    "Козерог": "Земля",
    "Водолей": "Воздух",
    "Рыбы": "Вода",
}

CHINESE_ANIMALS = [
    "Крыса",
    "Бык",
    "Тигр",
    "Кролик",
    "Дракон",
    "Змея",
    "Лошадь",
    "Коза",
    "Обезьяна",
    "Петух",
    "Собака",
    "Свинья",
]
CHINESE_ELEMENTS = ["Металл", "Вода", "Дерево", "Огонь", "Земля"]

RELATION_PROFILES = {
    "romance": {
        "label": "Романтика",
        "base": 7,
        "strengths": ["Эмоциональная связь", "Сильное притяжение", "Теплота и забота"],
        "growth": ["Ожидания и ревность", "Баланс личных границ", "Разный темп решений"],
    },
    "friendship": {
        "label": "Дружба",
        "base": 4,
        "strengths": ["Взаимопонимание", "Легкость общения", "Общие интересы"],
        "growth": ["Открытый диалог", "Равный вклад", "Регулярная обратная связь"],
    },
    "business": {
        "label": "Бизнес",
        "base": 3,
        "strengths": ["Стратегичность", "Сильная командность", "Фокус на результате"],
        "growth": ["Согласование ролей", "Скорость решений", "Конструктивная критика"],
    },
}

ASPECT_TARGETS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

PYTHAGOREAN_MAP = {
    **{ch: val for ch, val in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [1, 2, 3, 4, 5, 6, 7, 8, 9] * 3)},
    "А": 1,
    "Б": 2,
    "В": 3,
    "Г": 4,
    "Д": 5,
    "Е": 6,
    "Ё": 7,
    "Ж": 8,
    "З": 9,
    "И": 1,
    "Й": 2,
    "К": 3,
    "Л": 4,
    "М": 5,
    "Н": 6,
    "О": 7,
    "П": 8,
    "Р": 9,
    "С": 1,
    "Т": 2,
    "У": 3,
    "Ф": 4,
    "Х": 5,
    "Ц": 6,
    "Ч": 7,
    "Ш": 8,
    "Щ": 9,
    "Ъ": 1,
    "Ы": 2,
    "Ь": 3,
    "Э": 4,
    "Ю": 5,
    "Я": 6,
}


def parse_timezone(tz_name: str | None) -> timezone:
    name = (tz_name or "UTC").strip()
    if not name:
        return timezone.utc
    if name.upper() == "UTC":
        return timezone.utc
    # Support fixed offsets like +03:00 / -05:30.
    if len(name) == 6 and name[0] in {"+", "-"} and name[3] == ":":
        sign = 1 if name[0] == "+" else -1
        try:
            hours = int(name[1:3])
            minutes = int(name[4:6])
            return timezone(sign * timedelta(hours=hours, minutes=minutes))
        except ValueError:
            return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def parse_birth_datetime(date_value: str, time_value: str | None, timezone_name: str | None) -> datetime:
    tzinfo = parse_timezone(timezone_name)

    hour = 12
    minute = 0
    if time_value:
        parsed_time = datetime.strptime(time_value, "%H:%M")
        hour = parsed_time.hour
        minute = parsed_time.minute
    local_dt = datetime.strptime(date_value, "%Y-%m-%d").replace(hour=hour, minute=minute, tzinfo=tzinfo)
    return local_dt.astimezone(timezone.utc)


def zodiac_from_longitude(lon: float) -> tuple[str, str]:
    idx = int((lon % 360) // 30)
    sign = ZODIAC_SIGNS[idx]
    return sign, ELEMENT_BY_SIGN[sign]


def reduce_to_single_digit(value: int) -> int:
    current = value
    while current > 9 and current not in (11, 22, 33):
        current = sum(int(c) for c in str(current))
    return current


def life_path_number(date: datetime) -> int:
    digits = date.strftime("%Y%m%d")
    return reduce_to_single_digit(sum(int(c) for c in digits))


def destiny_number(name: str) -> int | None:
    cleaned = [c for c in name.upper() if c.isalpha()]
    if not cleaned:
        return None
    total = sum(PYTHAGOREAN_MAP.get(c, 0) for c in cleaned)
    if total == 0:
        return None
    return reduce_to_single_digit(total)


def personal_year(date: datetime, target_year: int) -> int:
    value = f"{target_year}{date.month:02d}{date.day:02d}"
    return reduce_to_single_digit(sum(int(c) for c in value))


def chinese_data(date: datetime) -> dict[str, Any]:
    year = date.year
    return {
        "year": year,
        "animal": CHINESE_ANIMALS[(year - 1900) % 12],
        "element": CHINESE_ELEMENTS[((year - 1900) % 10) // 2],
    }


def planet_longitude(utc_dt: datetime, planet_id: int) -> float:
    decimal_hour = utc_dt.hour + (utc_dt.minute / 60.0) + (utc_dt.second / 3600.0)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour)
    result, _ = swe.calc_ut(jd, planet_id)
    return result[0]


def angle_diff(a: float, b: float) -> float:
    diff = abs((a - b) % 360)
    return min(diff, 360 - diff)


def nearest_aspect(a: float, b: float) -> tuple[str, float]:
    diff = angle_diff(a, b)
    best_name = "neutral"
    best_delta = 999.0
    for name, target in ASPECT_TARGETS.items():
        delta = abs(diff - target)
        if delta < best_delta:
            best_delta = delta
            best_name = name
    return best_name, best_delta


def score_by_elements(e1: str, e2: str) -> int:
    if e1 == e2:
        return 27
    supportive = {("Огонь", "Воздух"), ("Воздух", "Огонь"), ("Земля", "Вода"), ("Вода", "Земля")}
    return 22 if (e1, e2) in supportive else 14


def score_by_numerology(n1: int, n2: int) -> int:
    diff = abs(n1 - n2)
    if diff == 0:
        return 23
    if diff <= 2:
        return 20
    if diff <= 4:
        return 16
    return 12


def score_by_chinese(c1: dict[str, Any], c2: dict[str, Any]) -> int:
    score = 20 if c1["element"] == c2["element"] else 14
    if c1["animal"] == c2["animal"]:
        score += 2
    return score


def aspect_score(venus_aspect: tuple[str, float], mars_aspect: tuple[str, float], moon_aspect: tuple[str, float]) -> int:
    base = 8
    weights = {
        "trine": 9,
        "sextile": 8,
        "conjunction": 7,
        "opposition": 3,
        "square": 2,
        "neutral": 5,
    }
    v = max(0, weights[venus_aspect[0]] - int(venus_aspect[1] // 3))
    m = max(0, weights[mars_aspect[0]] - int(mars_aspect[1] // 3))
    moon = max(0, weights[moon_aspect[0]] - int(moon_aspect[1] // 3))
    return base + v + m + moon


def aspect_text(name: str) -> str:
    labels = {
        "conjunction": "соединение",
        "sextile": "секстиль",
        "square": "квадрат",
        "trine": "трин",
        "opposition": "оппозиция",
        "neutral": "нейтральный аспект",
    }
    return labels.get(name, "нейтральный аспект")


def element_relation_text(e1: str, e2: str) -> str:
    if e1 == e2:
        return "Одинаковые стихии: легко понимать мотивацию друг друга."
    supportive = {("Огонь", "Воздух"), ("Воздух", "Огонь"), ("Земля", "Вода"), ("Вода", "Земля")}
    if (e1, e2) in supportive:
        return "Стихии усиливают друг друга: хороший потенциал синергии."
    return "Стихии контрастные: важны договоренности о темпе и ожиданиях."


def chinese_relation_text(c1: dict[str, Any], c2: dict[str, Any]) -> str:
    if c1["animal"] == c2["animal"]:
        return "Одинаковый знак года: схожие привычки и интуитивное понимание."
    if c1["element"] == c2["element"]:
        return "Одинаковая стихия года: легко синхронизироваться в целях."
    return "Разные энергии года: союз продуктивен при разделении ролей."


def lunar_phase_name(angle: float) -> str:
    if angle < 22.5 or angle >= 337.5:
        return "Новолуние"
    if angle < 67.5:
        return "Растущий серп"
    if angle < 112.5:
        return "Первая четверть"
    if angle < 157.5:
        return "Растущая луна"
    if angle < 202.5:
        return "Полнолуние"
    if angle < 247.5:
        return "Убывающая луна"
    if angle < 292.5:
        return "Последняя четверть"
    return "Убывающий серп"


def best_days_for_pair(venus1: float, venus2: float, moon_aspect_delta: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now_utc = datetime.now(timezone.utc)
    candidates: list[dict[str, Any]] = []
    phase_bonus = {
        "Новолуние": 4,
        "Растущий серп": 8,
        "Первая четверть": 7,
        "Растущая луна": 10,
        "Полнолуние": 9,
        "Убывающая луна": 6,
        "Последняя четверть": 5,
        "Убывающий серп": 4,
    }
    for i in range(30):
        day_dt = (now_utc + timedelta(days=i)).replace(hour=12, minute=0, second=0, microsecond=0)
        moon_t = planet_longitude(day_dt, swe.MOON)
        sun_t = planet_longitude(day_dt, swe.SUN)
        phase_angle = (moon_t - sun_t) % 360
        phase = lunar_phase_name(phase_angle)
        venus_sync = max(0.0, 12.0 - min(angle_diff(moon_t, venus1), 12.0))
        venus_sync += max(0.0, 12.0 - min(angle_diff(moon_t, venus2), 12.0))
        mood_bonus = max(0.0, 8.0 - moon_aspect_delta)
        score = phase_bonus[phase] + venus_sync * 1.4 + mood_bonus
        candidates.append(
            {
                "date": day_dt.date().isoformat(),
                "phase": phase,
                "score": round(score, 2),
            }
        )
    phase_reasons = {
        "Новолуние": "Время для спокойного диалога и планирования совместного будущего.",
        "Растущий серп": "Благоприятный момент для начала важного разговора.",
        "Первая четверть": "Энергия для активного обсуждения и принятия решений.",
        "Растущая луна": "Открытость и готовность к новым идеям в отношениях.",
        "Полнолуние": "Эмоциональный подъём — время для искреннего и глубокого общения.",
        "Убывающая луна": "Период завершения споров и поиска компромиссов.",
        "Последняя четверть": "Время мудрых размышлений и подготовки к новому циклу.",
    }
    trend = [{"date": item["date"], "score": item["score"], "phase": item["phase"]} for item in candidates]
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:5]
    for item in top:
        item["reason"] = phase_reasons.get(item["phase"], "Благоприятный день для отношений.")
    return top, trend


def relationship_flags(
    sun_elem1: str,
    sun_elem2: str,
    venus_aspect: tuple[str, float],
    mars_aspect: tuple[str, float],
    moon_aspect: tuple[str, float],
    life1: int,
    life2: int,
) -> dict[str, list[str]]:
    green_flags = [
        f"Стихии {sun_elem1}/{sun_elem2}: {element_relation_text(sun_elem1, sun_elem2).lower()}",
        f"Лунный аспект ({aspect_text(moon_aspect[0])}, орб {round(moon_aspect[1], 1)}°) поддерживает эмоциональное понимание.",
        f"ЧЖП {life1} и {life2}: есть потенциал договоренностей через осознанный диалог.",
    ]
    red_flags = [
        f"Аспект Марса ({aspect_text(mars_aspect[0])}, орб {round(mars_aspect[1], 1)}°) может усиливать резкость в спорах.",
        f"Аспект Венеры ({aspect_text(venus_aspect[0])}, орб {round(venus_aspect[1], 1)}°) требует внимания к ожиданиям и проявлению чувств.",
        "При стрессе возможен разный темп решений, важно заранее согласовать правила обсуждения конфликтов.",
    ]
    return {"green": green_flags, "red": red_flags}


def area_scores(
    vector: dict[str, int],
    venus_aspect: tuple[str, float],
    mars_aspect: tuple[str, float],
    moon_aspect: tuple[str, float],
) -> dict[str, int]:
    sex_bonus = 5 if mars_aspect[0] in {"trine", "sextile", "conjunction"} else -3
    life_bonus = 4 if moon_aspect[0] in {"trine", "sextile", "conjunction"} else 0
    money_bonus = 4 if venus_aspect[0] in {"trine", "sextile"} else -2
    return {
        "быт": max(35, min(100, int((vector["stability"] + vector["communication"]) / 2 + life_bonus))),
        "секс": max(35, min(100, int((vector["passion"] + vector["emotional"]) / 2 + sex_bonus))),
        "деньги": max(35, min(100, int((vector["stability"] + vector["communication"]) / 2 + money_bonus))),
        "коммуникация": vector["communication"],
        "цели": max(35, min(100, int((vector["stability"] + vector["communication"]) / 2 + 2))),
    }


def build_forecast(score: int) -> str:
    if score >= 80:
        return "Прогноз 3/6/12 мес.: высокий потенциал роста и укрепления доверия при регулярном диалоге."
    if score >= 65:
        return "Прогноз 3/6/12 мес.: стабильная динамика, если заранее согласовать ожидания и правила."
    return "Прогноз 3/6/12 мес.: возможны качели, но союз можно усилить через честную коммуникацию."


def build_compatibility(payload: dict[str, Any]) -> dict[str, Any]:
    date1 = parse_birth_datetime(payload["birth1"], payload.get("birthTime1"), payload.get("timezone1"))
    date2 = parse_birth_datetime(payload["birth2"], payload.get("birthTime2"), payload.get("timezone2"))
    relation_type = payload.get("relationshipType", "romance")
    profile = RELATION_PROFILES.get(relation_type, RELATION_PROFILES["romance"])
    city1 = (payload.get("city1") or "").strip()
    city2 = (payload.get("city2") or "").strip()
    name1 = (payload.get("name1") or "").strip()
    name2 = (payload.get("name2") or "").strip()
    timezone1 = (payload.get("timezone1") or "UTC").strip()
    timezone2 = (payload.get("timezone2") or "UTC").strip()

    sun1 = planet_longitude(date1, swe.SUN)
    sun2 = planet_longitude(date2, swe.SUN)
    moon1 = planet_longitude(date1, swe.MOON)
    moon2 = planet_longitude(date2, swe.MOON)
    venus1 = planet_longitude(date1, swe.VENUS)
    venus2 = planet_longitude(date2, swe.VENUS)
    mars1 = planet_longitude(date1, swe.MARS)
    mars2 = planet_longitude(date2, swe.MARS)

    sun_sign1, sun_elem1 = zodiac_from_longitude(sun1)
    sun_sign2, sun_elem2 = zodiac_from_longitude(sun2)
    moon_sign1, _ = zodiac_from_longitude(moon1)
    moon_sign2, _ = zodiac_from_longitude(moon2)

    life1 = life_path_number(date1)
    life2 = life_path_number(date2)
    destiny1 = destiny_number(name1)
    destiny2 = destiny_number(name2)
    chinese1 = chinese_data(date1)
    chinese2 = chinese_data(date2)

    venus_aspect = nearest_aspect(venus1, venus2)
    mars_aspect = nearest_aspect(mars1, mars2)
    moon_aspect = nearest_aspect(moon1, moon2)

    total_score = (
        profile["base"]
        + score_by_elements(sun_elem1, sun_elem2)
        + score_by_numerology(life1, life2)
        + score_by_chinese(chinese1, chinese2)
        + aspect_score(venus_aspect, mars_aspect, moon_aspect)
    )
    total_score = max(30, min(100, total_score))
    current_year = datetime.now(timezone.utc).year
    pyear1 = personal_year(date1, current_year)
    pyear2 = personal_year(date2, current_year)

    compatibility_vector = {
        "emotional": max(35, min(100, 55 + (12 - int(moon_aspect[1])) * 3)),
        "communication": max(35, min(100, 50 + score_by_elements(sun_elem1, sun_elem2) * 2)),
        "passion": max(35, min(100, 52 + (12 - int(mars_aspect[1])) * 3)),
        "stability": max(35, min(100, 48 + score_by_numerology(life1, life2) * 2)),
    }
    pair_flags = relationship_flags(sun_elem1, sun_elem2, venus_aspect, mars_aspect, moon_aspect, life1, life2)
    areas = area_scores(compatibility_vector, venus_aspect, mars_aspect, moon_aspect)
    best_days, energy_trend = best_days_for_pair(venus1, venus2, moon_aspect[1])

    return {
        "total": total_score,
        "relationProfile": profile,
        "western": {
            "sign1": sun_sign1,
            "sign2": sun_sign2,
            "element1": sun_elem1,
            "element2": sun_elem2,
            "venusAspect": aspect_text(venus_aspect[0]),
            "marsAspect": aspect_text(mars_aspect[0]),
            "elementDynamics": element_relation_text(sun_elem1, sun_elem2),
        },
        "chinese": {
            "first": chinese1,
            "second": chinese2,
        },
        "numerology": {
            "lifePath1": life1,
            "lifePath2": life2,
            "destiny1": destiny1,
            "destiny2": destiny2,
            "personalYear1": pyear1,
            "personalYear2": pyear2,
        },
        "bonus": {
            "moon1": moon_sign1,
            "moon2": moon_sign2,
            "moonAspect": aspect_text(moon_aspect[0]),
        },
        "birthMeta": {
            "city1": city1,
            "city2": city2,
            "timezone1": timezone1,
            "timezone2": timezone2,
            "utc1": date1.isoformat(),
            "utc2": date2.isoformat(),
        },
        "insights": {
            "strengths": profile["strengths"][:2],
            "growth": profile["growth"][:2],
            "weeklyAdvice": "Запланируйте один честный разговор и одно приятное совместное действие на этой неделе.",
            "conflictTip": f'Зона напряжения чаще всего проявляется через аспект Венеры ({aspect_text(venus_aspect[0])}) и Марса ({aspect_text(mars_aspect[0])}). Используйте формат: факт -> чувство -> просьба.',
            "forecastTip": build_forecast(total_score),
            "funTip": "Создайте PNG-карту пары и делитесь результатом в соцсетях для сравнения с друзьями.",
        },
        "advanced": {
            "planetPositions": {
                "first": {
                    "sun": round(sun1, 2),
                    "moon": round(moon1, 2),
                    "venus": round(venus1, 2),
                    "mars": round(mars1, 2),
                },
                "second": {
                    "sun": round(sun2, 2),
                    "moon": round(moon2, 2),
                    "venus": round(venus2, 2),
                    "mars": round(mars2, 2),
                },
            },
            "aspects": {
                "venus": {"name": aspect_text(venus_aspect[0]), "orb": round(venus_aspect[1], 2)},
                "mars": {"name": aspect_text(mars_aspect[0]), "orb": round(mars_aspect[1], 2)},
                "moon": {"name": aspect_text(moon_aspect[0]), "orb": round(moon_aspect[1], 2)},
            },
            "compatibilityVector": {
                "emotional": compatibility_vector["emotional"],
                "communication": compatibility_vector["communication"],
                "passion": compatibility_vector["passion"],
                "stability": compatibility_vector["stability"],
            },
            "timeline": {
                "m3": "Первые 3 месяца: настройка привычек и границ.",
                "m6": "Через 6 месяцев: укрепление ролей и общего ритма.",
                "m12": "Через 12 месяцев: переход на новый уровень доверия при регулярном диалоге.",
            },
            "chineseDynamics": chinese_relation_text(chinese1, chinese2),
            "pairFlags": pair_flags,
            "areaScores": areas,
            "bestDays": best_days,
            "energyTrend": energy_trend,
        },
    }


@app.get("/")
def index() -> Any:
    return send_from_directory(BASE_DIR, "index.html")


@app.post("/api/compatibility")
def compatibility() -> Any:
    payload = request.get_json(silent=True) or {}
    required = ("birth1", "birth2")
    if any(not payload.get(key) for key in required):
        return jsonify({"error": "Поля birth1 и birth2 обязательны"}), 400
    try:
        result = build_compatibility(payload)
    except Exception as exc:
        return jsonify({"error": f"Не удалось рассчитать совместимость: {exc}"}), 500
    return jsonify(result)


def notify_telegram(lead: Lead) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    text = (
        "Новая заявка на экспертный разбор\n"
        f"Имя: {lead.name}\n"
        f"Контакт: {lead.contact}\n"
        f"Сообщение: {lead.message or '-'}"
    )
    try:
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=8)
        print(f"Telegram notification sent: {resp.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")


def notify_crm_webhook(payload: dict[str, Any]) -> None:
    if not CRM_WEBHOOK_URL:
        return
    requests.post(CRM_WEBHOOK_URL, json=payload, timeout=8)


@app.post("/api/leads")
def leads() -> Any:
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    contact = (payload.get("contact") or "").strip()
    message = (payload.get("message") or "").strip()
    if not name or not contact:
        return jsonify({"error": "Введите имя и контакт"}), 400

    with Session(engine) as session:
        lead = Lead(
            name=name,
            contact=contact,
            message=message,
            context=payload.get("context", {}),
        )
        session.add(lead)
        session.commit()
        session.refresh(lead)

    outbound_payload = {
        "id": lead.id,
        "created_at": lead.created_at.isoformat(),
        "name": lead.name,
        "contact": lead.contact,
        "message": lead.message,
        "context": lead.context,
    }
    try:
        notify_telegram(lead)
    except Exception:
        pass
    try:
        notify_crm_webhook(outbound_payload)
    except Exception:
        pass
    return jsonify({"ok": True, "message": "Заявка отправлена"})


@app.get("/api/leads")
def get_leads() -> Any:
    limit = min(200, max(1, int(request.args.get("limit", "50"))))
    with Session(engine) as session:
        rows = session.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(limit)).all()
    data = [
        {
            "id": row.id,
            "created_at": row.created_at.isoformat(),
            "name": row.name,
            "contact": row.contact,
            "message": row.message,
            "context": row.context,
        }
        for row in rows
    ]
    return jsonify({"items": data})


@app.get("/leads")
def leads_page() -> Any:
    return """<!doctype html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Заявки</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a162e; color: #e8e4f5; }
        h1 { color: #a78bfa; }
        .lead { background: #2a2040; padding: 16px; margin: 10px 0; border-radius: 10px; }
        .lead strong { color: #a78bfa; }
        .empty { color: #9a94b8; font-style: italic; }
    </style>
</head>
<body>
    <h1>Заявки на экспертный разбор</h1>
    <div id="leads"></div>
    <script>
        fetch('/api/leads').then(r=>r.json()).then(d=>{
            const div = document.getElementById('leads');
            if(!d.items.length) { div.innerHTML = '<p class="empty">Заявок пока нет</p>'; return; }
            div.innerHTML = d.items.map(l=>`
                <div class="lead">
                    <strong>#${l.id}</strong> ${l.created_at}<br>
                    <strong>Имя:</strong> ${l.name}<br>
                    <strong>Контакт:</strong> ${l.contact}<br>
                    <strong>Сообщение:</strong> ${l.message || '—'}
                </div>
            `).join('');
        });
    </script>
</body>
</html>"""


def call_deepseek(messages: list[dict[str, str]], session_id: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "Извините, чат временно недоступен. Оставьте заявку на персональный разбор."

    all_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    stored = chat_history.get(session_id, [])
    for msg in stored[-10:]:
        all_messages.append(msg)
    for msg in messages:
        all_messages.append(msg)

    try:
        print(f"Calling DeepSeek API... key={DEEPSEEK_API_KEY[:10]}...")
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": all_messages,
                "temperature": 0.7,
                "max_tokens": 600,
            },
            timeout=30,
        )
        print(f"DeepSeek response status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"DeepSeek response text: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return f"Не удалось получить ответ. Попробуйте ещё раз."


@app.post("/api/chat")
def chat() -> Any:
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    session_id = (payload.get("session_id") or "default").strip()

    if not message:
        return jsonify({"error": "Введите сообщение"}), 400

    if session_id not in chat_history:
        chat_history[session_id] = []
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            text = f"💬 Новый вопрос эксперту:\n{message[:200]}"
            try:
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
            except Exception:
                pass

    user_msg = {"role": "user", "content": message}
    chat_history[session_id].append(user_msg)

    reply = call_deepseek([user_msg], session_id)

    assistant_msg = {"role": "assistant", "content": reply}
    chat_history[session_id].append(assistant_msg)

    return jsonify({"reply": reply})


@app.get("/<path:path>")
def static_proxy(path: str) -> Any:
    return send_from_directory(BASE_DIR, path)


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=debug)
