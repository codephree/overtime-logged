from flask import render_template, request, redirect, url_for, send_file, flash
from app.main import bp
from datetime import date
from io import BytesIO
import pandas as pd
from app.extensions import db
import datetime
from flask_login import login_required, current_user
from app.helpers import log_action, send_approval_email
from app.models import OvertimeEntry, User

entries = []  # simple in-memory storage; replace with DB for production


@bp.route('/log', methods=['GET', 'POST'])
@login_required
def log_overtime():
    if request.method == 'POST':
        # collect form data
        current_time = datetime.datetime.now()

        approval_manager_id = request.form.get('approval_manager_id')
        if approval_manager_id:
            try:
                approval_manager_id = int(approval_manager_id)
            except ValueError:
                approval_manager_id = None

        entry =  OvertimeEntry(
            employee_id=request.form['employee_id'],
            date=request.form['date'],
            hours=request.form['hours'],
            description=request.form['description'],
            approved_by=approval_manager_id,
            status='pending'
        )

        # print(entry)
        db.session.add(entry)
        db.session.commit()
       
        send_approval_email(entry.id)
       
        flash('Overtime entry logged successfully!', 'success')
        log_action(f"User {current_user.name} logged overtime entry for {entry.date} ({entry.hours} hours)")
        
        return redirect(url_for('main.view_entries'))
    
    managers = User.query.filter(User.role.ilike('%manager%')).order_by(User.name).all()
    return render_template('log.html', managers=managers)


@bp.route('/entries')
@login_required
def view_entries():
    # prepare filter params
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    employee_name = request.args.get('employee_name')
    assigned = request.args.get('assigned')

    user_role = (current_user.role or '').strip().lower()
    is_manager = 'manager' in user_role
    is_super_admin = 'super' in user_role
    can_review_entries = is_manager or is_super_admin

    if can_review_entries:
        query = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id)

        if is_manager and not is_super_admin:
            if assigned not in ['all', 'mine']:
                assigned = 'mine'
            if assigned == 'mine':
                query = query.filter(OvertimeEntry.approved_by == current_user.id)
            employees = User.query.filter(~User.role.ilike('%manager%')).order_by(User.name).all()
        else:
            assigned = 'all'
            employees = User.query.order_by(User.name).all()

        entries = query.all()
    else:
        assigned = 'all'
        entries = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id).filter(OvertimeEntry.employee_id == current_user.id).all()
        employees = []

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

    if employee_name and can_review_entries:
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
        assigned=assigned,
        page=page,
        per_page=per_page,
        total_entries=total_items,
        total_pages=total_pages,
        can_review_entries=can_review_entries,
        is_manager=is_manager,
        is_super_admin=is_super_admin
    )


@bp.route('/entries/<int:entry_id>/approve', methods=['POST'])
@login_required
def approve_entry(entry_id):
    user_role = (current_user.role or '').strip().lower()
    if 'manager' not in user_role and 'super' not in user_role:
        log_action(f"Unauthorized approval attempt by user {current_user.name} on entry {entry_id}", success=False)
        return {'success': False, 'message': 'Only managers or super admins can approve entries'}, 403
    
    entry = OvertimeEntry.query.get_or_404(entry_id)
    data = request.get_json() or {}
    approved_hours = data.get('approved_hours', entry.hours)
    
    entry.status = 'approved'
    entry.approved_hours = approved_hours
    entry.approved_by = current_user.id
    entry.updated_at = datetime.datetime.now()
    db.session.commit()
    approver_label = 'Super admin' if 'super' in user_role else 'Manager'
    log_action(f"{approver_label} {current_user.name} approved entry {entry_id} for employee ID {entry.employee_id} with approved hours {approved_hours}")
    return {'success': True, 'message': 'Entry approved', 'entry_id': entry_id, 'status': entry.status, 'approved_hours': entry.approved_hours}


@bp.route('/download')
@login_required
def download_entries():
    # optionally apply same filter as view
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    employee_name = request.args.get('employee_name')
    assigned = request.args.get('assigned')

    user_role = (current_user.role or '').strip().lower()
    is_manager = 'manager' in user_role
    is_super_admin = 'super' in user_role
    can_review_entries = is_manager or is_super_admin

    if can_review_entries:
        query = db.session.query(OvertimeEntry, User).join(User, OvertimeEntry.employee_id == User.id)
        if is_manager and not is_super_admin:
            if assigned not in ['all', 'mine']:
                assigned = 'mine'
            if assigned == 'mine':
                query = query.filter(OvertimeEntry.approved_by == current_user.id)
        filtered = query.all()
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
    
    if employee_name and can_review_entries:
        entries = [e for e in entries if e['employee_name'] == employee_name]
    
    # Convert back to format expected by pandas
    filtered = [(e['series_id'], e['employee_name'], e['email'], e['date'], e['approved_hours'] or e['hours'], e['description'], e['status']) for e in entries]
    
    df = pd.DataFrame(filtered, columns=['Employee Number', 'Employee Name', 'Email', 'Date', 'Hours', 'Description', 'Status'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Overtime')
    output.seek(0)
    excelfile = f"overtime_entries_{current_user.name}.xlsx"
    log_action(f"User {current_user.name} downloaded entries with filters - Start: {start}, End: {end}, Employee: {employee_name}")
    return send_file(output, download_name=excelfile, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')   