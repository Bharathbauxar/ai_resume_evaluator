from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class JobRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    skills = db.relationship('Skill', backref='job_role', lazy=True, cascade="all, delete")
    resumes = db.relationship('ResumeUpload', backref='job_role', lazy=True, cascade="all, delete")

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_role_id = db.Column(db.Integer, db.ForeignKey('job_role.id'), nullable=False)

class ResumeUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    job_role_id = db.Column(db.Integer, db.ForeignKey('job_role.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
