import smtplib
from email.message import EmailMessage

# ... (define msg, sender, recipient) ...


def send_email(subject, body, to_email):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = '<your_email@example.com>'
        msg['To'] = to_email


        with smtplib.SMTP("smtp.mailtrap.io", 587) as server:
            server.starttls() # Secure the connection
            server.login("35ac86847482e9", "e4ff68eb89fada")
            server.send_message(msg)
            print("Email sent successfully!")
    except smtplib.SMTPServerDisconnected as e:
        print(f"Server disconnected unexpectedly: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


send_email("Test Subject", "This is a test email body.", "olu@example.com")   