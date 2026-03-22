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

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# home route for testing purposes   

@app.route('/')
@login_required
def index():
    # Determine view type based on user role
    is_manager = current_user.role and 'manager' in current_user.role.lower()
    
    if is_manager:
        # Manager view: all overtime analytics
        total_entries = OvertimeEntry.query.count()
        total_hours = db.session.query(func.sum(OvertimeEntry.hours)).scalar() or 0
        total_hours = float(total_hours)
        
        pending_entries = OvertimeEntry.query.filter_by(status='pending').count()
        approved_entries = OvertimeEntry.query.filter_by(status='approved').count()
        
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        month_end = datetime(now.year, now.month, 28) if now.month < 12 else datetime(now.year + 1, 1, 1)
        
        this_month_hours = db.session.query(func.sum(OvertimeEntry.hours)).filter(
            OvertimeEntry.date >= month_start.isoformat().split('T')[0],
            OvertimeEntry.date < month_end.isoformat().split('T')[0]
        ).scalar() or 0
        this_month_hours = float(this_month_hours)
        
        top_users = db.session.query(User.name, func.sum(OvertimeEntry.hours).label('total_hours')).join(
            OvertimeEntry, OvertimeEntry.employee_id == User.id
        ).filter(
            OvertimeEntry.date >= month_start.isoformat().split('T')[0],
            OvertimeEntry.date < month_end.isoformat().split('T')[0]
        ).group_by(User.id).order_by(func.sum(OvertimeEntry.hours).desc()).limit(5).all()
        
        top_users = [{'name': u[0], 'hours': float(u[1])} for u in top_users]
        
        recent_entries = db.session.query(OvertimeEntry, User).join(
            User, OvertimeEntry.employee_id == User.id
        ).order_by(OvertimeEntry.date.desc()).limit(5).all()
        
        recent_entries = [{
            'employee_name': e[1].name,
            'date': e[0].date,
            'hours': e[0].hours,
            'status': e[0].status
        } for e in recent_entries]
        
        return render_template('index.html',
                              is_manager=True,
                              total_entries=total_entries,
                              total_hours=total_hours,
                              pending_entries=pending_entries,
                              approved_entries=approved_entries,
                              this_month_hours=this_month_hours,
                              top_users=top_users,
                              recent_entries=recent_entries)
    else:
        # Staff view: personal entries only
        personal_entries = OvertimeEntry.query.filter_by(employee_id=current_user.id).all()
        personal_total_hours = sum(e.hours for e in personal_entries) if personal_entries else 0
        personal_pending = sum(1 for e in personal_entries if e.status == 'pending')
        personal_approved = sum(1 for e in personal_entries if e.status == 'approved')
        
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        month_end = datetime(now.year, now.month, 28) if now.month < 12 else datetime(now.year + 1, 1, 1)
        
        personal_month_hours = sum(e.hours for e in personal_entries 
                                   if month_start.isoformat().split('T')[0] <= e.date < month_end.isoformat().split('T')[0]) if personal_entries else 0
        
        recent_personal = sorted(personal_entries, key=lambda x: x.date, reverse=True)[:5]
        recent_personal = [{
            'date': e.date,
            'hours': e.hours,
            'description': e.description,
            'status': e.status
        } for e in recent_personal]
        
        return render_template('index.html',
                              is_manager=False,
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
    return render_template('error/500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error/403.html'), 403

# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0', port=int(os.environ.get('PORT', 19029)))

