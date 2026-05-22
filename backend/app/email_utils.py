from app.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_password_reset(email_to: str, token: str):
    """
    Envia un correo con el token o link para reset de contraseña.
    Usa la configuracion SMTP del sistema (SMTP_USER, SMTP_PASSWORD).
    """
    smtp_user = settings.smtp_user
    smtp_password = settings.smtp_password
    if not smtp_password:
        print("WARNING: SMTP_PASSWORD no configurado. No se puede enviar el correo a:", email_to)
        return False

    link = f"{settings.cors_origins[0]}/reset-password?token={token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Recuperación de Contraseña - Denarius"
    msg["From"] = smtp_user
    msg["To"] = email_to

    text = f"Hola,\n\nPara resetear su contraseña, haga click en el siguiente enlace:\n{link}\n\nSi no solicitó esto, ignore este correo."
    
    html = f"""
    <html>
      <body>
        <p>Hola,</p>
        <p>Para resetear su contraseña, haga click en el siguiente enlace:</p>
        <p><a href="{link}">Resetear mi contraseña</a></p>
        <p>Si no solicitó esto, ignore este correo.</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_to, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False
