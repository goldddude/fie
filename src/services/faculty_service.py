"""
MongoDB Faculty Service
Faculty authentication using PyMongo
"""
from datetime import datetime, timedelta
import secrets
import random
from src.database import get_db


def _faculty_to_dict(doc):
    if doc is None:
        return None
    return {
        'id': str(doc.get('_id', '')),
        'name': doc.get('name', ''),
        'email': doc.get('email', ''),
        'sections': doc.get('sections', ''),
    }


class _FacultyProxy:
    """Thin proxy so service returns objects with .to_dict()."""
    def __init__(self, doc):
        self._doc = doc
        self.id = str(doc.get('_id', ''))
        self.name = doc.get('name', '')
        self.email = doc.get('email', '')
        self.otp = doc.get('otp')
        self.otp_created_at = doc.get('otp_created_at')
        self.remember_token = doc.get('remember_token')
        self.remember_expires = doc.get('remember_expires')
        self.sections = doc.get('sections', '')

    def to_dict(self):
        return _faculty_to_dict(self._doc)


class FacultyService:
    """Service class for faculty operations (MongoDB backend)"""

    @staticmethod
    def generate_otp(email, name=None):
        try:
            db = get_db()
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

            faculty = db.faculty.find_one({'email': email})

            if not faculty:
                if not name:
                    return False, "Name is required for new faculty"
                doc = {
                    'name': name,
                    'email': email,
                    'otp': otp,
                    'otp_created_at': datetime.utcnow(),
                    'remember_token': None,
                    'remember_expires': None,
                    'sections': '',
                }
                db.faculty.insert_one(doc)
            else:
                db.faculty.update_one(
                    {'email': email},
                    {'$set': {'otp': otp, 'otp_created_at': datetime.utcnow()}}
                )

            print(f"📧 OTP for {email}: {otp}")
            return True, otp

        except Exception as e:
            return False, str(e)

    @staticmethod
    def verify_otp(email, otp, remember_me=False):
        try:
            db = get_db()
            faculty = db.faculty.find_one({'email': email})

            if not faculty:
                return False, "Faculty not found"
            if not faculty.get('otp'):
                return False, "No OTP generated. Please request a new one"

            otp_created = faculty.get('otp_created_at')
            if otp_created and (datetime.utcnow() - otp_created) > timedelta(minutes=10):
                return False, "OTP expired. Please request a new one"

            if faculty.get('otp') != otp:
                return False, "Invalid OTP"

            update = {'otp': None, 'otp_created_at': None}
            token = None
            if remember_me:
                token = secrets.token_urlsafe(32)
                update['remember_token'] = token
                update['remember_expires'] = datetime.utcnow() + timedelta(days=30)

            db.faculty.update_one({'email': email}, {'$set': update})
            faculty.update(update)
            return True, (_FacultyProxy(faculty), token)

        except Exception as e:
            return False, str(e)

    @staticmethod
    def verify_remember_token(email, token):
        try:
            db = get_db()
            faculty = db.faculty.find_one({'email': email})
            if not faculty:
                return False, "Faculty not found"
            if not faculty.get('remember_token') or faculty['remember_token'] != token:
                return False, "Invalid token"
            expires = faculty.get('remember_expires')
            if expires and expires < datetime.utcnow():
                return False, "Token expired. Please login again"
            return True, _FacultyProxy(faculty)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def logout(email):
        try:
            db = get_db()
            db.faculty.update_one(
                {'email': email},
                {'$set': {'remember_token': None, 'remember_expires': None}}
            )
            return True
        except Exception:
            return False

    @staticmethod
    def get_faculty_by_email(email):
        db = get_db()
        doc = db.faculty.find_one({'email': email})
        return _FacultyProxy(doc) if doc else None

    @staticmethod
    def update_sections(email, sections):
        try:
            db = get_db()
            faculty = db.faculty.find_one({'email': email})
            if not faculty:
                return False, "Faculty not found"
            if isinstance(sections, list):
                sections = ','.join(sections)
            db.faculty.update_one({'email': email}, {'$set': {'sections': sections}})
            faculty['sections'] = sections
            return True, _FacultyProxy(faculty)
        except Exception as e:
            return False, str(e)
