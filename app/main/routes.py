from flask import render_template, request, redirect, url_for, send_file, flash
from app.main import bp
from datetime import date
from io import BytesIO
import pandas as pd
from app.extensions import db
import datetime
from flask_login import login_required, current_user
from app.helpers import log_action

from app.models import OvertimeEntry, User

entries = []  # simple in-memory storage; replace with DB for production


@bp.route('/log', methods=['GET', 'POST'])
@login_required
def log_overtime():
    if request.method == 'POST':
        # collect form data
        current_time = datetime.datetime.now()

        entry =  OvertimeEntry(
            employee_id=request.form['employee_id'],
            date=request.form['date'],
            hours=request.form['hours'],
            description=request.form['description'],
            # creeated_at=current_time,
            # updated_at=current_time
        )
        # print(entry)
        db.session.add(entry)
        db.session.commit()
        flash('Overtime entry logged successfully!', 'success')
        log_action(f"User {current_user.name} logged overtime entry for {entry.date} ({entry.hours} hours)")
        return redirect(url_for('main.view_entries'))
    
    user = User.query.all()
    # print(datetime.datetime.now())
    return render_template('log.html', user=user)


@bp.route('/entries')
@login_required
def view_entries():
    # query all entries with user info for only the current user if not manager, otherwise all entries
    if current_user.role == 'manager':
        entries = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id).all()
        employees = User.query.filter(User.role != 'manager').order_by(User.name).all()  # Get all non-manager employees for filter
    else:
        entries = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id).filter(OvertimeEntry.employee_id == current_user.id).all()
        employees = []  # Staff don't need employee filter
    entries = [{
        'id': e[0].id,
        'employee_id': e[1].id,
        'employee_name': e[1].name,
        'email': e[1].email,
        'date': e[0].date,
        'hours': e[0].hours,
        'approved_hours': e[0].approved_hours,
        'description': e[0].description,
        'status': e[0].status if hasattr(e[0], 'status') else 'pending',
        'series_id': e[1].sid
    } for e in entries]

    start = request.args.get('start_date')
    end = request.args.get('end_date')
    employee_name = request.args.get('employee_name')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    filtered = entries
    if start or end:
        def in_range(e):
            try:
                d = date.fromisoformat(e['date'])
            except Exception:
                return False
            if start:
                try:
                    sd = date.fromisoformat(start)
                except Exception:
                    sd = None
                if sd and d < sd:
                    return False
            if end:
                try:
                    ed = date.fromisoformat(end)
                except Exception:
                    ed = None
                if ed and d > ed:
                    return False
            return True
        filtered = [e for e in entries if in_range(e)]

    # Filter by employee name if specified (only for managers)
    if employee_name and current_user.role == 'manager':
        filtered = [e for e in filtered if e['employee_name'] == employee_name]

    total_items = len(filtered)
    per_page = max(1, min(per_page, 50))
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages or 1))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paged_entries = filtered[start_idx:end_idx]
    log_action(f"User {current_user.name} viewed entries page {page} with filters - Start: {start}, End: {end}, Employee: {employee_name}")
    return render_template(
        'entries.html',
        entries=paged_entries,
        employees=employees,
        start_date=start,
        end_date=end,
        employee_name=employee_name,
        page=page,
        per_page=per_page,
        total_entries=total_items,
        total_pages=total_pages
    )


@bp.route('/entries/<int:entry_id>/approve', methods=['POST'])
@login_required
def approve_entry(entry_id):
    if current_user.role != 'manager':
        log_action(f"Unauthorized approval attempt by user {current_user.name} on entry {entry_id}", success=False)
        return {'success': False, 'message': 'Only managers can approve entries'}, 403
    
    entry = OvertimeEntry.query.get_or_404(entry_id)
    data = request.get_json()
    approved_hours = data.get('approved_hours', entry.hours)
    
    entry.status = 'approved'
    entry.approved_hours = approved_hours
    entry.approved_by = current_user.id
    entry.updated_at = datetime.datetime.now()
    db.session.commit()
    log_action(f"Manager {current_user.name} approved entry {entry_id} for employee ID {entry.employee_id} with approved hours {approved_hours}")
    return {'success': True, 'message': 'Entry approved', 'entry_id': entry_id, 'status': entry.status, 'approved_hours': entry.approved_hours}


@bp.route('/download')
@login_required
def download_entries():
    # optionally apply same filter as view
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    employee_name = request.args.get('employee_name')
    
    # Get entries based on user role
    if current_user.role == 'manager':
        filtered = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id).all()
    else:
        filtered = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id).filter(OvertimeEntry.employee_id == current_user.id).all()
    
    # Convert to dict format for filtering
    entries = [{
        'id': e[0].id,
        'employee_id': e[1].id,
        'employee_name': e[1].name,
        'email': e[1].email,
        'date': e[0].date,
        'hours': e[0].hours,
        'approved_hours': e[0].approved_hours,
        'description': e[0].description,
        'status': e[0].status if hasattr(e[0], 'status') else 'pending',
        'series_id': e[1].sid
    } for e in filtered]
    
    # Apply date filters
    if start or end:
        def in_range(e):
            try:
                d = date.fromisoformat(e['date'])
            except Exception:
                return False
            if start:
                try:
                    sd = date.fromisoformat(start)
                except Exception:
                    sd = None
                if sd and d < sd:
                    return False
            if end:
                try:
                    ed = date.fromisoformat(end)
                except Exception:
                    ed = None
                if ed and d > ed:
                    return False
            return True
        entries = [e for e in entries if in_range(e)]
    
    # Apply employee filter for managers
    if employee_name and current_user.role == 'manager':
        entries = [e for e in entries if e['employee_name'] == employee_name]
    
    # Convert back to format expected by pandas
    filtered = [(e['id'], e['employee_name'], e['email'], e['date'], e['approved_hours'] or e['hours'], e['description'], e['status']) for e in entries]
    
    df = pd.DataFrame(filtered, columns=['ID', 'Employee Name', 'Email', 'Date', 'Hours', 'Description', 'Status'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Overtime')
    output.seek(0)
    flash('Overtime entries downloaded successfully!', 'success')
    log_action(f"User {current_user.name} downloaded entries with filters - Start: {start}, End: {end}, Employee: {employee_name}")
    return send_file(output, download_name='overtime_entries.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')   