import datetime
import csv

from app.auth import bp as auth
from flask import render_template, redirect, url_for, flash, request
from app.models import User, OTP, LoginAttempt, Configuration, OvertimeEntry
from app.extensions import db, login_manager
from app.helpers import send_mail_flask   
from flask_login import login_user, logout_user, login_required, current_user
import random
import uuid
from app.helpers import admin_required, log_action, send_otp_email, sysadmin_required


@auth.route('/login')
def login():
    if current_user.is_authenticated:
        log_action(f"User {current_user.name} accessed login page while already authenticated", success=False)
        return redirect(url_for('index'))
        log_action(f"User {current_user.name} accessed login page")
    return render_template('auth/login.html')

@auth.route('/send-otp', methods=['POST'])
def send_otp():
    # Implementation for sending OTP
    # This is a simplified example - you would typically integrate with an SMS or email service to send the OTP to the user
   if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return {'success': False, 'message': 'User not found'}, 404
        # Generate OTP and save to database
        # otp_code =   #'123456'  # In a real application, generate a random OTP
        otp_code = '{:06d}'.format(random.randint(0, 999999))
        otp_entry = OTP(user_id=user.id, otp_code=otp_code, expires_at=datetime.datetime.now() + datetime.timedelta(minutes=5))
        db.session.add(otp_entry)
        db.session.commit()
        # Add your OTP sending logic here
        send_otp_email(user_id=user.id, otp_code=otp_code)
        log_action(f"Sent OTP to user {user.name} ({user.email}) for login attempt")
        return {'success': True, 'message': 'OTP sent successfully', 'name': user.name}

@auth.route('/verify-otp', methods=['POST'])
def verify_otp():
    # Implementation for verifying OTP
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        otp_code = data.get('otp')
        user = User.query.filter_by(email=email).first()
        
        if not user:
            log_action(f"Attempt to verify OTP for non-existent user {email}", success=False)
            return {'success': False, 'message': 'User not found'}, 404
        otp_entry = OTP.query.filter_by(user_id=user.id, otp_code=otp_code).first()

        # print(f"Verifying OTP for user {email}: {otp_code} (found entry: {otp_entry})")  # Debugging statement   
        if not otp_entry or otp_entry.expires_at < datetime.datetime.now():
            log_action(f"Attempt to verify OTP for user {email} failed: Invalid or expired OTP", success=False)
            return {'success': False, 'message': 'Invalid or expired OTP'}, 400
        
        # OTP is valid - log the user in (this is a simplified example)
        log_action(f"User {user.name} successfully verified OTP and logged in")
        login = login_user(user)
        # next_page = request.args.get('next')
        # return redirect(next_page or url_for('index'))
        if login:
            # Log successful login attempt
            attempt = LoginAttempt(user_id=user.id, successful=True, ip_address=request.remote_addr)
            log_action(f"User {user.name} logged in successfully from IP {request.remote_addr}")
            db.session.add(attempt)
            db.session.commit()
            
            #delete the OTP entry after successful verification
            OTP.query.filter_by(id=otp_entry.id).delete()
              # In a real application, you would set a session or token here
              
            return {'success': True, 'message': 'OTP verified successfully'}
        else:
            # Log failed login attempt
            attempt = LoginAttempt(user_id=user.id, successful=False, ip_address=request.remote_addr)
            log_action(f"User {user.name} failed to log in from IP {request.remote_addr}")
            db.session.add(attempt)
            db.session.commit()
            return {'success': False, 'message': 'Login failed'}, 500



@auth.route('/logout')
@login_required
def logout():
    log_action(f"User {current_user.name} logged out")
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))


@auth.route('/users')
@login_required
@admin_required
def users():
    
    # admin_required(lambda: None)  # Ensure only admins can access this route
    # query all users except the current user and display in a simple template
    all_users = User.query.filter(User.id != current_user.id)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = max(1, min(per_page, 50))

    pagination = all_users.order_by(User.id).paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    log_action(f"Admin {current_user.name} accessed user management page, page {page}, per_page {per_page}")
    return render_template('users.html', users=users, pagination=pagination, per_page=per_page, uuid=uuid.uuid4())


@auth.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '').strip()

    if not name or not email or not role:
        log_action(f"Admin {current_user.name} attempted to update user {user_id} with invalid data", success=False)
        return {'success': False, 'message': 'Name, email, and role are required.'}, 400

    existing = User.query.filter(User.email == email, User.id != user_id).first()
    if existing:
        log_action(f"Admin {current_user.name} attempted to update user {user_id} with email {email} that already exists for another user", success=False)
        return {'success': False, 'message': 'Email already exists for another user.'}, 400

    user.name = name
    user.email = email
    user.role = role
    db.session.commit()
    log_action(f"Admin {current_user.name} updated user {user_id} - new name: {name}, new email: {email}, new role: {role}")
    return {'success': True, 'message': 'User updated successfully.', 'user': {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}}


def cleanup_user_constraints(user_ids):
    """Remove or detach dependent records before deleting users."""
    if not user_ids:
        return

    OvertimeEntry.query.filter(OvertimeEntry.approved_by.in_(user_ids)).update(
        {OvertimeEntry.approved_by: None},
        synchronize_session=False
    )
    OvertimeEntry.query.filter(OvertimeEntry.employee_id.in_(user_ids)).delete(synchronize_session=False)
    OTP.query.filter(OTP.user_id.in_(user_ids)).delete(synchronize_session=False)
    LoginAttempt.query.filter(LoginAttempt.user_id.in_(user_ids)).delete(synchronize_session=False)


@auth.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if current_user.id == user_id:
        log_action(f"Admin {current_user.name} attempted to delete themselves (user ID {user_id})", success=False)
        return {'success': False, 'message': 'Cannot delete yourself.'}, 403

    user = User.query.get_or_404(user_id)

    try:
        cleanup_user_constraints([user.id])
        db.session.delete(user)
        db.session.commit()
        log_action(f"Admin {current_user.name} deleted user {user_id} and related records")
        return {'success': True, 'message': 'User deleted successfully.', 'id': user_id}
    except Exception as e:
        db.session.rollback()
        log_action(f"Admin {current_user.name} failed to delete user {user_id}: {str(e)}", success=False)
        return {'success': False, 'message': 'Failed to delete user and related records.'}, 500


@auth.route('/users/delete-bulk', methods=['POST'])
@login_required
@admin_required
def delete_bulk_users():
    data = request.get_json(silent=True) or {}
    ids = data.get('user_ids', [])
    if not ids:
        return {'success': False, 'message': 'No user IDs provided.'}, 400

    ids = [int(uid) for uid in ids if str(uid).isdigit()]
    if current_user.id in ids:
        return {'success': False, 'message': 'Cannot delete yourself.'}, 403

    users_to_delete = User.query.filter(User.id.in_(ids), User.id != current_user.id).all()
    deleted_ids = [u.id for u in users_to_delete]

    if not deleted_ids:
        return {'success': False, 'message': 'No valid users found to delete.'}, 404

    try:
        cleanup_user_constraints(deleted_ids)
        for user in users_to_delete:
            db.session.delete(user)
        db.session.commit()
        log_action(f"Admin {current_user.name} deleted users in bulk with related records: {deleted_ids}")
        return {'success': True, 'message': f'Deleted {len(deleted_ids)} users.', 'deleted_ids': deleted_ids}
    except Exception as e:
        db.session.rollback()
        log_action(f"Admin {current_user.name} failed bulk delete for users {deleted_ids}: {str(e)}", success=False)
        return {'success': False, 'message': 'Failed to delete selected users and related records.'}, 500

# 4040423194
# 4040423194

# 1RCT-7344252

@auth.route('/users/import', methods=['POST'])
@login_required
@admin_required
def import_users():
    file = request.files.get('user_file')
    if not file or file.filename == '':
        flash('No CSV file selected for upload.', 'error')
        return redirect(url_for('auth.users'))

    try:
        content = file.stream.read().decode('utf-8').splitlines()
        reader = csv.DictReader(content)

        created = 0
        skipped = 0
        for row in reader:
            email = (row.get('email') or '').strip()
            name = (row.get('name') or '').strip()
            username = (row.get('username') or '').strip()  # optional, not used in this example
            sid = (row.get('sid') or '').strip()  # optional, not used in this example
            role = (row.get('role') or '').strip()  # optional, not used in this example
            password = (row.get('password') or '').strip()  # optional, not used in this example
            if not email or not name:
                skipped += 1
                continue

            existing = User.query.filter_by(email=email).first()
            if existing:
                skipped += 1
                continue

            new_user = User(email=email, name=name, username=username, password=password, sid=sid, role=role)
            db.session.add(new_user)
            created += 1

        db.session.commit()
        log_action(f"Admin {current_user.name} imported users: {created} created, {skipped} skipped")
        flash(f'Successfully imported {created} users. Skipped {skipped}.', 'success')
    except Exception as e:
        db.session.rollback()
        log_action(f"Admin {current_user.name} failed to import users: {str(e)}", success=False)
        flash(f'Import failed: {str(e)}', 'error')

    return redirect(url_for('auth.users'))


# user loader from flask login session management
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth.route('/settings', methods=['GET', 'POST'])
@login_required
@sysadmin_required
def settings():
    """Configuration settings management page"""
    if request.method == 'POST':
        # Handle form submission
        app_name = request.form.get('app_name', '').strip()
        app_heading = request.form.get('app_heading', '').strip()
        primary_color = request.form.get('primary_color', '').strip()
        company_name = request.form.get('company_name', '').strip()
        company_email = request.form.get('company_email', '').strip()
        footer_text = request.form.get('footer_text', '').strip()

        try:
            # Define config fields to update
            config_updates = {
                'app_name': app_name or 'Overtime Tracker',
                'app_heading': app_heading or 'Overtime Management System',
                'primary_color': primary_color or '#4FB477',
                'company_name': company_name or 'Your Company',
                'company_email': company_email or 'info@example.com',
                'footer_text': footer_text or 'Overtime Tracker © 2025'
            }

            for key, value in config_updates.items():
                config = Configuration.query.filter_by(name=key).first()
                if config:
                    config.value = value
                else:
                    config = Configuration(name=key, value=value)
                    db.session.add(config)

            db.session.commit()
            log_action(f"Admin {current_user.name} updated application settings")
            flash('Configuration updated successfully!', 'success')
            return redirect(url_for('auth.settings'))

        except Exception as e:
            db.session.rollback()
            log_action(f"Admin {current_user.name} failed to update settings: {str(e)}", success=False)
            flash(f'Error updating configuration: {str(e)}', 'error')

    # Get current settings
    settings_dict = {}
    config_entries = Configuration.query.all()
    for config in config_entries:
        settings_dict[config.name] = config.value

    # Set defaults if not found
    defaults = {
        'app_name': 'Overtime Tracker',
        'app_heading': 'Overtime Management System',
        'primary_color': '#4FB477',
        'company_name': 'Your Company',
        'company_email': 'info@example.com',
        'footer_text': 'Overtime Tracker © 2025'
    }

    for key, value in defaults.items():
        if key not in settings_dict:
            settings_dict[key] = value

    log_action(f"Admin {current_user.name} accessed application settings page")
    return render_template('settings.html', settings=settings_dict)

@auth.route('/register', methods=['POST'])
@login_required
@admin_required
def register():
    if request.method == 'POST':
        # data = request.get_json()
        email = request.form.get('email')
        username = request.form.get('username')
        role = request.form.get('role')
        name = request.form.get('name')
        sid = request.form.get('sid')
        password = 'randompassword'  # In a real application, you would generate a secure random password or allow the user to set it
        user = User.query.filter_by(email=email).first()
        if user:
            return {'success': False, 'message': 'User already exists'}, 400
        user = User(email=email, name=name, username=username, role=role, sid=sid, password=password)
        db.session.add(user)
        db.session.commit()
        log_action(f"New user registered: {name} ({email})")
        return redirect(url_for('auth.users'))
    
    # return render_template('auth/register.html')
