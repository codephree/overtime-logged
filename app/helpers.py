from flask_mail import Message
from app.extensions import mail
import smtplib
from functools import wraps
from flask import abort, flash, redirect, url_for, render_template
from flask_login import current_user
from log_symbols import LogSymbols
import logging
from app.models import User, OvertimeEntry, OTP, Configuration


def _current_role():
    return (getattr(current_user, 'role', '') or '').strip().lower()


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        role = _current_role()
        if not current_user.is_authenticated or ('manager' not in role and 'super' not in role):
            flash('503: Access denied: Managers or super admins only.', 'error')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    
    return wrapper


def sysadmin_required(func):
     @wraps(func)
     def wrapper(*args, **kwargs):
        role = _current_role()
        if not current_user.is_authenticated or 'super' not in role:
            flash('503: Access denied: Super users only.', 'error')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    
     return wrapper


def log_action(action, success=True):
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(message)s')
    symbol = LogSymbols.SUCCESS if success else LogSymbols.ERROR
    logging.info(f"{symbol} {action}")


def send_mail_flask(to, subject, data):
    # Example using Flask-Mail
    msg = Message(subject, sender="Overtime Tracker <overtimetracker@example.com>", recipients=[to])
    html_body = render_template('email.html', **data)  # Pass any necessary variables to the template
    msg.html = html_body
    # # Send the email using Flask-Mail
    mail.send(msg)

# def load_configuration():
#         config = Configuration.query.all()
        
#         configs = [{
#             'title': c[o].va 
#         } for c in config]

    #     entries = [{
    #     'id': e[0].id,
    #     'employee_id': e[1].id,
    #     'employee_name': e[1].name,
    #     'email': e[1].email,
    #     'date': e[0].date,
    #     'hours': e[0].hours,
    #     'approved_hours': e[0].approved_hours,
    #     'description': e[0].description,
    #     'status': e[0].status if hasattr(e[0], 'status') else 'pending',
    #     'series_id': e[1].sid
    # } for e in filtered]


def send_approval_email(entry_id):
    """Send approval notification email to the assigned manager"""
    entry = OvertimeEntry.query.get(entry_id)
    if not entry or not entry.approved_by:
        return False

    manager = User.query.get(entry.approved_by)
    if not manager:
        return False

    employee = User.query.get(entry.employee_id)
    if not employee:
        return False

    subject = f"Overtime Approval Needed: {employee.name} - {entry.date}"

    # Render HTML template
    html_body = render_template(
        'email/manager_approval.html',
        manager=manager,
        employee=employee,
        entry=entry,
        subject=subject   
    )

    # Create and send email
    msg = Message(
        subject=subject,
        recipients=[manager.email],
        html=html_body,
        sender="Overtime Tracker <overtimetracker@example.com>"
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send approval email: {e}")
        return False


def send_otp_email(user_id, otp_code):
    """Send OTP verification email to the user"""
    user = User.query.get(user_id)
    if not user:
        return False

    subject = "Your OTP Code - Secure Access"

    # Render HTML template
    html_body = render_template(
        'email/otp.html',
        user=user,
        otp_code=otp_code,
        subject=subject
    )

    # Create and send email
    msg = Message(
        subject=subject,
        recipients=[user.email],
        html=html_body,
        sender="Overtime Tracker <overtimetracker@example.com>"
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False

