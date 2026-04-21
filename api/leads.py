import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
import requests

DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(Path(__file__).resolve().parent.parent / 'backend' / 'leads.db').as_posix()}")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
CRM_WEBHOOK_URL = os.getenv("CRM_WEBHOOK_URL", "").strip()

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

def handler(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body) if request.body else {}
        except:
            payload = {}
        name = (payload.get("name") or "").strip()
        contact = (payload.get("contact") or "").strip()
        message = (payload.get("message") or "").strip()
        
        if not name or not contact:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Введите имя и контакт"})}
        
        # Save to database
        try:
            engine = create_engine(DB_URL, future=True)
            Base.metadata.create_all(engine)
            with Session(engine) as session:
                lead = Lead(name=name, contact=contact, message=message, context=payload.get("context", {}))
                session.add(lead)
                session.commit()
        except Exception as e:
            pass
        
        # Send Telegram notification
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            text = f"Новая заявка\nИмя: {name}\nКонтакт: {contact}\nСообщение: {message or '-'}"
            try:
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=5)
            except:
                pass
        
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"ok": True, "message": "Заявка отправлена"})}
    
    # GET request - return leads list
    limit = 50
    try:
        engine = create_engine(DB_URL, future=True)
        with Session(engine) as session:
            rows = session.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(limit)).all()
            data = [{"id": r.id, "created_at": r.created_at.isoformat(), "name": r.name, "contact": r.contact, "message": r.message, "context": r.context} for r in rows]
    except:
        data = []
    
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"items": data})}