from __future__ import annotations

import json
import os
import time
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
# Меньше max_tokens и короче история — быстрее ответ API (меньше генерируемого текста).
def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(lo, min(hi, int(raw)))
    except ValueError:
        return default


DEEPSEEK_CHAT_MAX_TOKENS = _int_env("DEEPSEEK_CHAT_MAX_TOKENS", 400, 120, 800)
DEEPSEEK_CHAT_HISTORY_MSGS = _int_env("DEEPSEEK_CHAT_HISTORY_MSGS", 12, 4, 24)

SYSTEM_PROMPT = """Ты — опытный эксперт-коуч по отношениям с 15-летним стажем. Ты помогаешь людям разобраться в их отношениях, даёшь мудрые и тёплые советы. Твой стиль общения — как опытный друг, который искренне заботится. Ты используешь нумерологию и астрологию как инструменты самопознания, но фокусируешься на психологии отношений и практических советах. Отвечай на русском языке, будто ты живой человек — не как робот. Будь конкретным, задавай уточняющие вопросы. Избегай общих фраз типа "всё будет хорошо"."""

CHAT_SYSTEM_SUFFIX = (
    "Формат: кратко — до 3–5 абзацев или маркированный список, суммарно примерно до 900 символов. "
    "Без длинных вступлений и без повторения уже сказанного. Один уточняющий вопрос в конце — по желанию."
)

chat_history: dict[str, list[dict[str, str]]] = {}


BASE_DIR = Path(__file__).resolve().parent.parent
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(Path(__file__).resolve().parent / 'leads.db').as_posix()}")
CRM_WEBHOOK_URL = os.getenv("CRM_WEBHOOK_URL", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


def _telegram_proxy_dict() -> dict[str, str] | None:
    raw = (
        os.getenv("TELEGRAM_HTTPS_PROXY", "").strip()
        or os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
    )
    if not raw:
        return None
    return {"http": raw, "https": raw}


def telegram_api_send(payload: dict[str, Any]) -> tuple[bool, str]:
    """Вызов sendMessage с повторами. Возвращает (успех, текст ошибки)."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN не задан"
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
            last_err = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
        except Exception as exc:
            last_err = str(exc)
        if attempt < 2:
            time.sleep(0.6 * (2**attempt))
    return False, last_err


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


def _telegram_failure_log_path() -> Path:
    custom = os.getenv("LEAD_TELEGRAM_FALLBACK_LOG", "").strip()
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parent / "telegram_failed_leads.jsonl"


def append_telegram_failure_backup(lead: Lead, reason: str) -> None:
    """Резервная копия заявки, если Telegram недоступен (база уже сохранила лид)."""
    record = {
        "id": lead.id,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "name": lead.name,
        "contact": lead.contact,
        "message": lead.message,
        "context": lead.context if isinstance(lead.context, dict) else {},
        "telegram_error": reason[:500],
    }
    path = _telegram_failure_log_path()
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Заявка #{lead.id} продублирована в файл: {path}")
    except OSError as exc:
        print(f"Не удалось записать резервный лог заявок: {exc}")


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


def extended_synastry_bonus(
    mercury_a: tuple[str, float],
    jupiter_a: tuple[str, float],
    saturn_a: tuple[str, float],
) -> int:
    """Дополнительный вклад Меркурия, Юпитера и Сатурна (мягче личных планет)."""

    def pts(asp: tuple[str, float]) -> int:
        weights = {
            "trine": 5,
            "sextile": 4,
            "conjunction": 4,
            "opposition": 2,
            "square": 2,
            "neutral": 3,
        }
        base = weights.get(asp[0], 3)
        return max(0, base - int(asp[1] // 5))

    total = pts(mercury_a) + pts(jupiter_a) + pts(saturn_a)
    return min(24, total)


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
    mercury_aspect: tuple[str, float],
    jupiter_aspect: tuple[str, float],
    saturn_aspect: tuple[str, float],
) -> dict[str, list[str]]:
    green_flags = [
        f"Стихии {sun_elem1}/{sun_elem2}: {element_relation_text(sun_elem1, sun_elem2).lower()}",
        f"Лунный аспект ({aspect_text(moon_aspect[0])}, орб {round(moon_aspect[1], 1)}°) поддерживает эмоциональное понимание.",
        f"Меркурий в синастрии ({aspect_text(mercury_aspect[0])}, орб {round(mercury_aspect[1], 1)}°) задаёт тон диалогу и договорённостям.",
        f"ЧЖП {life1} и {life2}: есть потенциал договоренностей через осознанный диалог.",
    ]
    red_flags = [
        f"Аспект Марса ({aspect_text(mars_aspect[0])}, орб {round(mars_aspect[1], 1)}°) может усиливать резкость в спорах.",
        f"Аспект Венеры ({aspect_text(venus_aspect[0])}, орб {round(venus_aspect[1], 1)}°) требует внимания к ожиданиям и проявлению чувств.",
        f"Юпитер ({aspect_text(jupiter_aspect[0])}) и Сатурн ({aspect_text(saturn_aspect[0])}) задают масштаб и границы союза — полезно обсуждать цели и ответственность явно.",
        "При стрессе возможен разный темп решений, важно заранее согласовать правила обсуждения конфликтов.",
    ]
    return {"green": green_flags, "red": red_flags}


def area_scores(
    vector: dict[str, int],
    venus_aspect: tuple[str, float],
    mars_aspect: tuple[str, float],
    moon_aspect: tuple[str, float],
    mercury_aspect: tuple[str, float],
    jupiter_aspect: tuple[str, float],
    saturn_aspect: tuple[str, float],
) -> dict[str, int]:
    sex_bonus = 5 if mars_aspect[0] in {"trine", "sextile", "conjunction"} else -3
    life_bonus = 4 if moon_aspect[0] in {"trine", "sextile", "conjunction"} else 0
    money_bonus = 4 if venus_aspect[0] in {"trine", "sextile"} else -2
    merc_bonus = 3 if mercury_aspect[0] in {"trine", "sextile", "conjunction"} else (-2 if mercury_aspect[0] in {"square", "opposition"} else 0)
    goals_bonus = 3 if jupiter_aspect[0] in {"trine", "sextile", "conjunction"} else 0
    goals_bonus += 2 if saturn_aspect[0] in {"trine", "sextile"} else (-2 if saturn_aspect[0] in {"square", "opposition"} else 0)
    return {
        "быт": max(35, min(100, int((vector["stability"] + vector["communication"]) / 2 + life_bonus))),
        "секс": max(35, min(100, int((vector["passion"] + vector["emotional"]) / 2 + sex_bonus))),
        "деньги": max(35, min(100, int((vector["stability"] + vector["communication"]) / 2 + money_bonus))),
        "коммуникация": max(35, min(100, vector["communication"] + merc_bonus)),
        "цели": max(35, min(100, int((vector["stability"] + vector["communication"]) / 2 + 2 + goals_bonus))),
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
    mercury1 = planet_longitude(date1, swe.MERCURY)
    mercury2 = planet_longitude(date2, swe.MERCURY)
    jupiter1 = planet_longitude(date1, swe.JUPITER)
    jupiter2 = planet_longitude(date2, swe.JUPITER)
    saturn1 = planet_longitude(date1, swe.SATURN)
    saturn2 = planet_longitude(date2, swe.SATURN)

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
    mercury_aspect = nearest_aspect(mercury1, mercury2)
    jupiter_aspect = nearest_aspect(jupiter1, jupiter2)
    saturn_aspect = nearest_aspect(saturn1, saturn2)

    syn_extra = extended_synastry_bonus(mercury_aspect, jupiter_aspect, saturn_aspect)

    total_score = (
        profile["base"]
        + score_by_elements(sun_elem1, sun_elem2)
        + score_by_numerology(life1, life2)
        + score_by_chinese(chinese1, chinese2)
        + aspect_score(venus_aspect, mars_aspect, moon_aspect)
        + syn_extra
    )
    total_score = max(30, min(100, total_score))
    current_year = datetime.now(timezone.utc).year
    pyear1 = personal_year(date1, current_year)
    pyear2 = personal_year(date2, current_year)

    harmonious = {"trine", "sextile", "conjunction"}
    tense = {"square", "opposition"}
    merc_comm_adj = (
        10
        if mercury_aspect[0] in harmonious
        else (-8 if mercury_aspect[0] in tense else 2)
    )
    merc_comm_adj -= int(mercury_aspect[1] // 6)
    stab_adj = (5 if jupiter_aspect[0] in harmonious else -2 if jupiter_aspect[0] in tense else 0) + (
        4 if saturn_aspect[0] in harmonious else -4 if saturn_aspect[0] in tense else 1
    )
    stab_adj -= int((jupiter_aspect[1] + saturn_aspect[1]) // 12)

    compatibility_vector = {
        "emotional": max(35, min(100, 55 + (12 - int(moon_aspect[1])) * 3)),
        "communication": max(
            35,
            min(100, 50 + score_by_elements(sun_elem1, sun_elem2) * 2 + merc_comm_adj),
        ),
        "passion": max(35, min(100, 52 + (12 - int(mars_aspect[1])) * 3)),
        "stability": max(
            35,
            min(100, 48 + score_by_numerology(life1, life2) * 2 + stab_adj),
        ),
    }
    pair_flags = relationship_flags(
        sun_elem1,
        sun_elem2,
        venus_aspect,
        mars_aspect,
        moon_aspect,
        life1,
        life2,
        mercury_aspect,
        jupiter_aspect,
        saturn_aspect,
    )
    areas = area_scores(
        compatibility_vector,
        venus_aspect,
        mars_aspect,
        moon_aspect,
        mercury_aspect,
        jupiter_aspect,
        saturn_aspect,
    )
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
            "mercuryAspect": aspect_text(mercury_aspect[0]),
            "jupiterAspect": aspect_text(jupiter_aspect[0]),
            "saturnAspect": aspect_text(saturn_aspect[0]),
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
                    "mercury": round(mercury1, 2),
                    "venus": round(venus1, 2),
                    "mars": round(mars1, 2),
                    "jupiter": round(jupiter1, 2),
                    "saturn": round(saturn1, 2),
                },
                "second": {
                    "sun": round(sun2, 2),
                    "moon": round(moon2, 2),
                    "mercury": round(mercury2, 2),
                    "venus": round(venus2, 2),
                    "mars": round(mars2, 2),
                    "jupiter": round(jupiter2, 2),
                    "saturn": round(saturn2, 2),
                },
            },
            "aspects": {
                "venus": {"name": aspect_text(venus_aspect[0]), "orb": round(venus_aspect[1], 2)},
                "mars": {"name": aspect_text(mars_aspect[0]), "orb": round(mars_aspect[1], 2)},
                "moon": {"name": aspect_text(moon_aspect[0]), "orb": round(moon_aspect[1], 2)},
                "mercury": {"name": aspect_text(mercury_aspect[0]), "orb": round(mercury_aspect[1], 2)},
                "jupiter": {"name": aspect_text(jupiter_aspect[0]), "orb": round(jupiter_aspect[1], 2)},
                "saturn": {"name": aspect_text(saturn_aspect[0]), "orb": round(saturn_aspect[1], 2)},
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


@app.get("/favicon.ico")
def favicon_ico() -> Any:
    """Браузеры часто запрашивают /favicon.ico до загрузки HTML; отдаём тот же SVG."""
    return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")


def _telegram_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_lead_telegram_message(
    name: str,
    contact: str,
    body: str,
    context: dict[str, Any] | None,
    *,
    lead_id: int | None = None,
    at: datetime | None = None,
) -> str:
    lines: list[str] = []
    header = "📋 <b>Новая заявка</b>"
    if lead_id is not None:
        header += f" <code>#{lead_id}</code>"
    lines.append(header)
    if at is not None:
        utc = at.astimezone(timezone.utc) if at.tzinfo else at.replace(tzinfo=timezone.utc)
        lines.append(f"🕐 {utc.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")
    lines.append(f"<b>Имя:</b> {_telegram_escape(name)}")
    lines.append(f"<b>Контакт:</b> {_telegram_escape(contact)}")
    msg = body or "—"
    if len(msg) > 2800:
        msg = msg[:2797] + "…"
    lines.append(f"<b>Сообщение:</b> {_telegram_escape(msg)}")
    ctx = context or {}
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
            lines.append(f"• Балл совместимости: {_telegram_escape(str(score))}")
        if rel:
            lines.append(f"• Тип связи: {_telegram_escape(rel)}")
        if c1 or c2:
            lines.append(f"• Города: {_telegram_escape(c1 or '—')} / {_telegram_escape(c2 or '—')}")
        if tz1 or tz2:
            lines.append(f"• Часовые пояса: {_telegram_escape(tz1 or '—')} / {_telegram_escape(tz2 or '—')}")
    text = "\n".join(lines)
    if len(text) > 4090:
        text = text[:4087] + "…"
    return text


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
    text = format_lead_telegram_message(
        lead.name,
        lead.contact,
        lead.message or "",
        lead.context if isinstance(lead.context, dict) else {},
        lead_id=lead.id,
        at=lead.created_at,
    )
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    ok, err = telegram_api_send(payload)
    if ok:
        print("Telegram: уведомление о заявке отправлено")
        return
    print(
        "Telegram недоступен (сеть/VPN/блокировка). "
        "Заявка сохранена в базе; см. /leads. Ошибка: "
        + err[:300]
    )
    append_telegram_failure_backup(lead, err)


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
    notify_telegram(lead)
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Заявки — экспертный разбор</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/styles.css" />
</head>
<body class="mystic-body">
<div class="decor-stars mystic-stars-static" aria-hidden="true"></div>
<div class="decor-moon" aria-hidden="true"></div>
<main class="page inner-page leads-shell">
    <header class="inner-page-header card">
        <nav class="nav-row">
            <a class="nav-back" href="/index.html">← На калькулятор</a>
            <button type="button" class="btn secondary btn-compact" id="leadThemeToggle" aria-label="Сменить тему">Тема</button>
        </nav>
        <p class="tag">CRM</p>
        <h1 class="page-title">Заявки на экспертный разбор</h1>
        <p class="subtitle prose-intro leads-intro">
            Все заявки хранятся здесь и в базе данных на сервере, даже если уведомление в Telegram не дошло.
            При сбое Telegram дубликат может писаться в файл <code>backend/telegram_failed_leads.jsonl</code>.
        </p>
    </header>
    <section class="card content-section">
        <div id="leads"></div>
    </section>
</main>
<script>
(function(){
var saved = localStorage.getItem('compat-theme');
var light = window.matchMedia('(prefers-color-scheme: light)').matches;
document.documentElement.setAttribute('data-theme', saved || (light ? 'light' : 'dark'));
document.getElementById('leadThemeToggle').addEventListener('click', function(){
var cur = document.documentElement.getAttribute('data-theme')||'dark';
var next = cur === 'dark' ? 'light' : 'dark';
document.documentElement.setAttribute('data-theme', next);
localStorage.setItem('compat-theme', next);
});
})();
fetch('/api/leads').then(function(r){ return r.json(); }).then(function(d){
var div = document.getElementById('leads');
if(!d.items||!d.items.length){ div.innerHTML = '<p class="leads-empty">Заявок пока нет</p>'; return; }
div.innerHTML = d.items.map(function(l){ return `
<div class="lead-card"><strong>#${l.id}</strong> · ${l.created_at}<br>
<strong>Имя:</strong> ${escapeHtml(l.name)}<br>
<strong>Контакт:</strong> ${escapeHtml(l.contact)}<br>
<strong>Сообщение:</strong> ${escapeHtml(l.message||'—')}
</div>`; }).join('');
}).catch(function(){ document.getElementById('leads').innerHTML='<p class="leads-empty">Не удалось загрузить заявки</p>'; });
function escapeHtml(s){ var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
</script>
</body>
</html>"""


def call_deepseek(messages: list[dict[str, str]], session_id: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "Извините, чат временно недоступен. Оставьте заявку на персональный разбор."

    system_full = f"{SYSTEM_PROMPT}\n\n{CHAT_SYSTEM_SUFFIX}"
    all_messages: list[dict[str, str]] = [{"role": "system", "content": system_full}]
    stored = chat_history.get(session_id, [])
    for msg in stored[-DEEPSEEK_CHAT_HISTORY_MSGS:]:
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
                "temperature": 0.65,
                "max_tokens": DEEPSEEK_CHAT_MAX_TOKENS,
                "top_p": 0.9,
            },
            timeout=45,
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
            telegram_api_send(
                {"chat_id": TELEGRAM_CHAT_ID, "text": f"💬 Новый вопрос эксперту:\n{message[:200]}"}
            )

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
