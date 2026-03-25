from app.extensions import db
from datetime import date, datetime
from flask_login import UserMixin

class OvertimeEntry(db.Model):
    __tablename__ = 'ot_overtime_entries'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.String(20), nullable=False)
    hours = db.Column(db.Float, nullable=False)
    approved_hours = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())

    # Foreign keys
    employee_id = db.Column(db.Integer, db.ForeignKey('ot_users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('ot_users.id'), nullable=True)

    # ✅ foreign_keys specified on both, back_populates names match User model exactly
    employee = db.relationship('User', foreign_keys=[employee_id], back_populates='overtime_entries')
    approver = db.relationship('User', foreign_keys=[approved_by], back_populates='approved_entries')

    def __repr__(self):
        return f'<OvertimeEntry {self.employee_id} - {self.date}>'


class User(UserMixin, db.Model):
    __tablename__ = 'ot_users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sid = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(100), nullable=False, default='staff')
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())
    department = db.Column(db.String(100), nullable=True)

    # ✅ back_populates names match OvertimeEntry model exactly
    overtime_entries = db.relationship('OvertimeEntry', foreign_keys='OvertimeEntry.employee_id', back_populates='employee')
    approved_entries = db.relationship('OvertimeEntry', foreign_keys='OvertimeEntry.approved_by', back_populates='approver')    

    def __repr__(self):
        return f'<User {self.username} ({self.email})>'
    

class OTP(db.Model):
    __tablename__ = 'ot_otps'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('ot_users.id'), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    
    user = db.relationship('User', backref=db.backref('otps', lazy=True))

    def __repr__(self):
        return f'<OTP {self.otp_code} for User {self.user_id}>'


class LoginAttempt(db.Model):
    __tablename__ = 'ot_login_attempts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('ot_users.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    successful = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # supports IPv6

    user = db.relationship('User', backref=db.backref('login_attempts', lazy=True))

    def __repr__(self):
        return f'<LoginAttempt User {self.user_id} at {self.timestamp} - {"Success" if self.successful else "Failure"}>'
    

  