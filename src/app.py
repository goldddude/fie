"""
Flask Application Factory — MongoDB backend
"""
import os
from flask import Flask, send_from_directory
from flask_cors import CORS


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    CORS(app)

    # Initialize MongoDB
    from src.database import get_db
    with app.app_context():
        try:
            get_db()
        except Exception as e:
            print(f"⚠️  MongoDB warning: {e}")

    # Register blueprints
    from src.api.students import students_bp
    from src.api.nfc import nfc_bp
    from src.api.attendance import attendance_bp
    from src.api.faculty import faculty_bp

    app.register_blueprint(students_bp,   url_prefix='/api/students')
    app.register_blueprint(nfc_bp,        url_prefix='/api/nfc')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(faculty_bp,    url_prefix='/api/faculty')

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app
