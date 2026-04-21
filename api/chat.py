import os
import json
from typing import Any
from dotenv import load_dotenv
load_dotenv()

import requests

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()

SYSTEM_PROMPT = """Ты — опытный эксперт-коуч по отношениям с 15-летним стажем. Ты помогаешь людям разобраться в их отношениях, даёшь мудрые и тёплые советы. Твой стиль общения — как опытный друг, который искренне заботится. Ты используешь нумерологию и астрологию как инструменты самопознания, но фокусируешься на психологии отношений и практических советах. Отвечай на русском языке, будто ты живой человек — не как робот. Будь конкретным, задавай уточняющие вопросы. Избегай общих фраз типа "всё будет хорошо"."""


def call_deepseek(messages):
    if not DEEPSEEK_API_KEY:
        return "Извините, чат временно недоступен. Оставьте заявку на персональный разбор."

    all_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    all_messages.extend(messages)

    try:
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
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Не удалось получить ответ. Попробуйте ещё раз."


def handler(request):
    try:
        payload = json.loads(request.body) if request.body else {}
    except:
        payload = {}
    
    message = (payload.get("message") or "").strip()
    if not message:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Введите сообщение"})}

    user_msg = {"role": "user", "content": message}
    reply = call_deepseek([user_msg])

    return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"reply": reply})}