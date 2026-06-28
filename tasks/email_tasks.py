from celery_app import celery_app
import smtplib
from email.mime.text import MIMEText

@celery_app.task
def send_otp_email(to_email: str,otp_code: str):
    message = MIMEText(f"Your OTP code is :{otp_code}")
    message["Subject"]="Your verification code"
    message["From"]="noreply@authsystem.com"
    message["To"]= to_email

    with smtplib.SMTP("localhost",1025) as server:
        server.send_message(message)

    return f"OTP sent to {to_email}"