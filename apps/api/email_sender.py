"""Email sending via SMTP. Falls back to console output in dev mode."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import settings


def send_verification_email(to_email: str, code: str) -> bool:
    subject = f"[UI2PSD] 인증번호: {code}"
    html = f"""
    <div style="font-family: sans-serif; max-width: 400px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">UI2PSD Studio</h2>
        <p>회원가입 인증번호</p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; padding: 20px; background: #f3f4f6; border-radius: 8px; text-align: center;">
            {code}
        </div>
        <p style="color: #6b7280; font-size: 14px; margin-top: 16px;">
            이 인증번호는 5분간 유효합니다.<br>
            본인이 요청하지 않았다면 이 이메일을 무시하세요.
        </p>
    </div>
    """

    if not settings.smtp_host or not settings.smtp_user:
        print(f"[DEV] Verification code for {to_email}: {code}")
        return False  # indicates dev mode

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"UI2PSD <{settings.smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    return True
