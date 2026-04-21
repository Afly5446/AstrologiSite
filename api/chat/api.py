import json
from dotenv import load_dotenv
import os
import requests
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

SYSTEM_PROMPT = """Ты — опытный эксперт-коуч по отношениям. Даёшь тёплые, конкретные советы. Отвечай на русском как друг."""

def handler(req):
    try:
        payload = json.loads(req.body) if req.body else {}
    except:
        payload = {}
    
    message = (payload.get("message") or "").strip()
    if not message:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Введите сообщение"})}
    
    if not DEEPSEEK_API_KEY:
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"reply": "Чат временно недоступен. Оставьте заявку."})}
    
    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message}], "temperature": 0.7, "max_tokens": 500},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"Не удалось получить ответ. Попробуйте ещё раз."
    
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"reply": reply})}