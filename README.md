# Overtime Logged (OT)

A Flask-based overtime tracking application with user roles (staff/managers), approvals, analytics dashboards, searchable manager filtering, and beautiful Tailwind UI.

## Features
- Login / logout / role-based access
- Staff: submit overtime entries
- Manager: review, adjust approved hours, approve entries
- Manager search by employee and date filters
- Entry status tracking (pending/approved)
- Personal and team analytics dashboards
- Pagination, CSV/XLSX export
- Flask-Toastr notifications for app alerts
- Error templates (400/403/404/500)

## Tech stack
- Python 3.11+ (recommended)
- Flask
- SQLAlchemy
- Flask-Migrate
- Flask-Login
- Tailwind CSS
- Toastify JS
- SQLite (default)

## Install
1. Clone repository
```bash
cd /c/project
git clone <repo-url> ot
cd ot
```

2. Create/Open virtual environment
```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
# OR for Unix:
# source .venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set environment
```bash
set FLASK_APP=app
set FLASK_ENV=development
# powershell: $env:FLASK_APP='app'; $env:FLASK_ENV='development'
```

5. Database migrations
```bash
flask db init   # only first time
flask db migrate -m "Initial schema"
flask db upgrade
```

6. Run server
```bash
flask run --port=10010
```

7. Open browser
- `http://127.0.0.1:10010`

## Default data
- No seed data included by default.
- Create a manager and staff user through registration or seed script.

## App structure
- `app/__init__.py`: Flask app and routes
- `app/models.py`: DB models (User, OvertimeEntry, OTP)
- `app/main/routes.py`: main pages, entries, approvals
- `app/auth/routes.py`: user management
- `app/templates/`: Jinja2 templates
- `app/static/` (if present): static assets

## Manager workflow
1. Login as manager
2. Go to `View Entries`
3. Use employee search and date filters
4. Click `Request Approval` to open modal
5. Adjust `Approved Hours`, hit `Approve`

## Staff workflow
1. Login as staff
2. Go to `Log Overtime`
3. Fill form, submit
4. View approval status on dashboard

## Toast notifications
- Built with Flask-Toastr in `app/templates/base.html`
- All Flask flash messages are now auto-converted to toast notifications.

## Error pages
- Routes use custom templates under `app/templates/error/` for HTTP codes 400, 403, 404, 500.

## Notes
- Ensure `pandas` + `openpyxl` are installed for export features.
- If app raises `ModuleNotFoundError: pandas`, run `pip install pandas openpyxl`.

## License
MIT
