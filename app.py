from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from PyPDF2 import PdfReader
from docx import Document
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Configure upload and database
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume_evaluator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ========== MODELS ==========
class JobRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    skills = db.relationship('Skill', backref='job_role', cascade="all, delete-orphan")
    resumes = db.relationship('Resume', backref='job_role', cascade="all, delete-orphan")

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_role_id = db.Column(db.Integer, db.ForeignKey('job_role.id'), nullable=False)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    job_role_id = db.Column(db.Integer, db.ForeignKey('job_role.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ========== UTILITY ==========
def extract_text(file):
    filename = file.filename.lower()
    if filename.endswith('.pdf'):
        reader = PdfReader(file)
        return ' '.join([page.extract_text() or '' for page in reader.pages])
    elif filename.endswith('.docx'):
        doc = Document(file)
        return '\n'.join([p.text for p in doc.paragraphs])
    elif filename.endswith('.txt'):
        return file.read().decode('utf-8')
    return ""

# ========== ROUTES ==========

@app.route('/')
def index():
    job_roles = JobRole.query.all()
    resumes = Resume.query.order_by(Resume.timestamp.desc()).all()
    is_admin = session.get('is_admin', False)
    return render_template('index.html', job_roles=job_roles, resumes=resumes, is_admin=is_admin)

@app.route('/evaluate', methods=['POST'])
def evaluate():
    resume = request.files['resume']
    job_role_id = request.form.get('job_role_id')
    job_role = JobRole.query.get(job_role_id)

    if not job_role:
        return jsonify({'error': 'Invalid job role'}), 400

    skills_required = [skill.name.lower() for skill in job_role.skills]
    content = extract_text(resume).lower()

    matched = [skill for skill in skills_required if skill in content]
    missing = [skill for skill in skills_required if skill not in content]
    percent = round((len(matched) / len(skills_required)) * 100, 2) if skills_required else 0

    # Save file
    filename = secure_filename(resume.filename)
    resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    resume.save(resume_path)

    # Save to DB
    saved_resume = Resume(filename=filename, job_role_id=job_role.id)
    db.session.add(saved_resume)
    db.session.commit()

    return jsonify({
        "matched_skills": matched,
        "missing_skills": missing,
        "match_percentage": percent
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ========== ADMIN LOGIN ==========
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # Simple static credentials (for demo)
    if username == 'admin' and password == 'admin123':
        session['is_admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

# ========== ADMIN: JOB ROLE ==========
@app.route('/add_job_role', methods=['POST'])
def add_job_role():
    if not session.get('is_admin'): return "Unauthorized", 401
    name = request.form.get('job_role_name')
    if name:
        db.session.add(JobRole(name=name))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_job_role/<int:id>', methods=['POST'])
def edit_job_role(id):
    if not session.get('is_admin'): return "Unauthorized", 401
    new_name = request.form.get('new_name')
    role = JobRole.query.get(id)
    if role and new_name:
        role.name = new_name
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_job_role/<int:id>')
def delete_job_role(id):
    if not session.get('is_admin'): return "Unauthorized", 401
    role = JobRole.query.get(id)
    if role:
        db.session.delete(role)
        db.session.commit()
    return redirect(url_for('index'))

# ========== ADMIN: SKILLS ==========
@app.route('/add_skill', methods=['POST'])
def add_skill():
    if not session.get('is_admin'): return "Unauthorized", 401
    name = request.form.get('skill_name')
    job_role_id = request.form.get('job_role_id')
    if name and job_role_id:
        db.session.add(Skill(name=name, job_role_id=job_role_id))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_skill/<int:id>', methods=['POST'])
def edit_skill(id):
    if not session.get('is_admin'): return "Unauthorized", 401
    new_name = request.form.get('new_name')
    skill = Skill.query.get(id)
    if skill and new_name:
        skill.name = new_name
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_skill/<int:id>')
def delete_skill(id):
    if not session.get('is_admin'): return "Unauthorized", 401
    skill = Skill.query.get(id)
    if skill:
        db.session.delete(skill)
        db.session.commit()
    return redirect(url_for('index'))

# ========== ADMIN: RESUME ==========
@app.route('/delete_resume/<int:id>', methods=['POST'])
def delete_resume(id):
    if not session.get('is_admin'): return "Unauthorized", 401
    resume = Resume.query.get(id)
    if resume:
        path = os.path.join(app.config['UPLOAD_FOLDER'], resume.filename)
        if os.path.exists(path):
            os.remove(path)
        db.session.delete(resume)
        db.session.commit()
    return redirect(url_for('index'))

# ========== RUN ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
