from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
from config import Config
from app.main import bp as main_bp
from app.auth import bp as auth_bp
from app.extensions import db, migrate, login_manager, mail
from flask_login import current_user, login_required
from app.models import OvertimeEntry, User
from sqlalchemy import func
from datetime import datetime, timedelta
from flask_toastr import Toastr

# Initialize Flask application
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)    
migrate.init_app(app, db)
mail.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Initialize Flask-Toastr
toastr = Toastr(app)


# Disable the app's default logger
# app.logger.disabled = True

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# home route for testing purposes   

@app.route('/')
@login_required
def index():
    # Determine user role and prepare dashboard context
    user_role = (current_user.role or '').strip().lower()
    is_manager = 'manager' in user_role
    is_super_admin = 'super_admin' in user_role
    is_admin_dashboard = is_manager or is_super_admin


    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    month_end = datetime(now.year + 1, 1, 1) if now.month == 12 else datetime(now.year, now.month + 1, 1)
    month_start_str = month_start.date().isoformat()
    month_end_str = month_end.date().isoformat()

    if is_admin_dashboard:
        entries_query = OvertimeEntry.query
        if is_manager and not is_super_admin:
            entries_query = entries_query.filter(OvertimeEntry.approved_by == current_user.id)

        total_entries = entries_query.count()
        pending_entries = entries_query.filter_by(status='pending').count()
        approved_entries = entries_query.filter_by(status='approved').count()

        total_hours_query = db.session.query(func.sum(OvertimeEntry.hours))
        if is_manager and not is_super_admin:
            total_hours_query = total_hours_query.filter(OvertimeEntry.approved_by == current_user.id)
        total_hours = float(total_hours_query.scalar() or 0)

        this_month_query = db.session.query(func.sum(OvertimeEntry.hours)).filter(
            OvertimeEntry.date >= month_start_str,
            OvertimeEntry.date < month_end_str
        )
        if is_manager and not is_super_admin:
            this_month_query = this_month_query.filter(OvertimeEntry.approved_by == current_user.id)
        this_month_hours = float(this_month_query.scalar() or 0)

        top_users_query = db.session.query(
            User.name,
            func.sum(OvertimeEntry.hours).label('total_hours')
        ).join(
            OvertimeEntry, OvertimeEntry.employee_id == User.id
        ).filter(
            OvertimeEntry.date >= month_start_str,
            OvertimeEntry.date < month_end_str
        )
        if is_manager and not is_super_admin:
            top_users_query = top_users_query.filter(OvertimeEntry.approved_by == current_user.id)

        top_users = top_users_query.group_by(User.id, User.name).order_by(
            func.sum(OvertimeEntry.hours).desc()
        ).limit(5).all()

        top_users = [{'name': user_name, 'hours': float(hours or 0)} for user_name, hours in top_users]

        recent_entries_query = db.session.query(OvertimeEntry, User).join(
            User, OvertimeEntry.employee_id == User.id
        )
        if is_manager and not is_super_admin:
            recent_entries_query = recent_entries_query.filter(OvertimeEntry.approved_by == current_user.id)

        recent_entries = recent_entries_query.order_by(OvertimeEntry.date.desc()).limit(5).all()
        recent_entries = [{
            'employee_name': user.name,
            'date': entry.date,
            'hours': entry.approved_hours or entry.hours,
            'status': entry.status
        } for entry, user in recent_entries]

        dashboard_context = {
            'is_manager': is_manager,
            'is_super_admin': is_super_admin,
            'current_user_name': current_user.name,
            'total_entries': total_entries,
            'total_hours': total_hours,
            'pending_entries': pending_entries,
            'approved_entries': approved_entries,
            'this_month_hours': this_month_hours,
            'top_users': top_users,
            'recent_entries': recent_entries
        }

        if is_super_admin:
            dashboard_context.update({
                'total_users': User.query.count(),
                'manager_count': User.query.filter(User.role.ilike('%manager%')).count(),
                'staff_count': User.query.filter(
                    ~User.role.ilike('%manager%'),
                    ~User.role.ilike('%super%')
                ).count()
            })

        return render_template('index.html', **dashboard_context)

    personal_entries = OvertimeEntry.query.filter_by(employee_id=current_user.id).all()
    personal_total_hours = sum(e.hours for e in personal_entries) if personal_entries else 0
    personal_pending = sum(1 for e in personal_entries if e.status == 'pending')
    personal_approved = sum(1 for e in personal_entries if e.status == 'approved')

    personal_month_hours = sum(
        e.hours for e in personal_entries
        if month_start_str <= e.date < month_end_str
    ) if personal_entries else 0

    recent_personal = sorted(personal_entries, key=lambda x: x.date, reverse=True)[:5]
    recent_personal = [{
        'date': e.date,
        'hours': e.hours,
        'description': e.description,
        'status': e.status
    } for e in recent_personal]

    return render_template('index.html',
                          is_manager=False,
                          is_super_admin=False,
                          current_user_name=current_user.name,
                          personal_entries_count=len(personal_entries),
                          personal_total_hours=personal_total_hours,
                          personal_pending=personal_pending,
                          personal_approved=personal_approved,
                          personal_month_hours=personal_month_hours,
                          recent_personal=recent_personal)



# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error/500.html', error=e), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error/403.html'), 403

# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0', port=int(os.environ.get('PORT', 19029)))

