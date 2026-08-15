from __future__ import annotations

import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Alert, Notification


def send_alert_notifications(db: Session, alert: Alert) -> None:
    site = Notification(alert_id=alert.id, channel="site", sent=True)
    db.add(site)
    message = EmailMessage()
    message["Subject"] = f"期刊提醒：{alert.paper_title}"
    message["From"] = settings.smtp_from
    message["To"] = settings.smtp_user or settings.smtp_from
    message.set_content(f"{alert.paper_title}\n{alert.paper_url or ''}\n匹配关键词：{alert.matched_keywords or ''}")
    email = Notification(alert_id=alert.id, channel="email", sent=False)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user and settings.smtp_password:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        email.sent = True
    except Exception as exc:
        email.error = str(exc)
    db.add(email)
    db.commit()

