from flask_mail import Message
from app.extensions import mail
import smtplib
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from log_symbols import LogSymbols
import logging

def send_mail(to, subject, body):
    #  e4ff68eb89fada
    # Placeholder function for sending email
    with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
        server.starttls()
        server.login("35ac86847482e9", "e4ff68eb89fada")
        sender = "Overtime Tracker <overtimetracker@example.com>"
        message = f"""\
                    Subject: {subject}
                    To: {to}
                    From: {sender}{body}"""
        server.sendmail(sender, to, message)    

    # print(f"Sending email to {to} with subject '{subject}' and body:\n{body}")

def send_mail_flask(to, subject, body, user):
    # Example using Flask-Mail
    msg = Message(subject, sender="Overtime Tracker <overtimetracker@example.com>", recipients=[to])
    msg.body = generate_html_message(subject, body, user)
    msg.html = generate_html_message(subject, body, user)
    # Send the email using Flask-Mail
    mail.send(msg)


def generate_html_message(subject, body, user):
    return f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f9f9f9;
                    color: #333;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #007BFF;
                }}
                p {{
                    font-size: 16px;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: #007BFF; text-align: center;">Overtime Tracker</h1>
                <p>Dear {user.name},</p>
                <p class="mt-4 mb-4">There's an attempt to login to your account:</p>
                <p>{body}</p>
                <p class="mt-4">If this was you, please ignore this email. If you did not attempt to login, we recommend changing your password immediately.</p>
                <p class="mt-4">Best regards,<br>Overtime Tracker Team</p>
            </div>
        </body>
    </html>
    """

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'manager':
            # abort(403)  # Forbidden
            flash('503: Access denied: Managers only.', 'error')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    
    return wrapper


def log_action(action, success=True):
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(message)s')
    symbol = LogSymbols.SUCCESS if success else LogSymbols.ERROR
    logging.info(f"{symbol} {action}")

    
