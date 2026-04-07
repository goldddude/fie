"""
Vercel serverless function entry point — MongoDB backend
"""
import os
import sys

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from flask import Flask, send_from_directory
from flask_cors import CORS

# Create Flask app
static_folder = os.path.join(BASE_DIR, 'src', 'static')
app = Flask(__name__, static_folder=static_folder, static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vercel-secret-key')

# Initialize CORS
CORS(app)

# Initialize MongoDB connection
from src.database import get_db
with app.app_context():
    try:
        get_db()
    except Exception as e:
        print(f"⚠️  MongoDB init warning: {e}")

# Register blueprints
from src.api.students import students_bp
from src.api.nfc import nfc_bp
from src.api.attendance import attendance_bp
from src.api.faculty import faculty_bp

app.register_blueprint(students_bp,   url_prefix='/api/students')
app.register_blueprint(nfc_bp,        url_prefix='/api/nfc')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(faculty_bp,    url_prefix='/api/faculty')

# Frontend routes
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# Vercel requires the WSGI app to be named 'handler'
handler = app
