import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()




def send_email(name, email, message):
    """Реальная отправка письма через SMTP."""
    smtp_server = os.getenv("SMTP_SERVER")
    port_value = os.getenv("SMTP_PORT")
    # ✅ Безопасная конвертация
    try:
        smtp_port = int(port_value) if port_value else 587
    except ValueError:
        smtp_port = 587
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    recipient = os.getenv("RECIPIENT_EMAIL", sender_email)

    msg = MIMEText(f"От: {name}\nEmail: {email}\nСообщение: {message}", "plain", "utf-8")
    msg["Subject"] = "Новое сообщение с формы"
    msg["From"] = sender_email
    msg["To"] = recipient

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")
        return False
