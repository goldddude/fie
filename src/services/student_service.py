"""
MongoDB Student Service
All student CRUD operations using PyMongo
"""
from datetime import datetime
from bson import ObjectId
from src.database import get_db, to_str_id, to_object_id
from src.utils.validators import validate_student_data
import re


def _student_to_dict(doc):
    """Convert a MongoDB student document to a plain dict."""
    if doc is None:
        return None
    return {
        'id': to_str_id(doc.get('_id')),
        'name': doc.get('name', ''),
        'register_number': doc.get('register_number', ''),
        'section': doc.get('section', ''),
        'department': doc.get('department', ''),
        'duration': doc.get('duration', ''),
        'nfc_tag_id': doc.get('nfc_tag_id'),
        'created_at': doc.get('created_at', datetime.utcnow()).isoformat(),
    }


class _StudentProxy:
    """Thin proxy so service returns objects with .to_dict() — keeps API routes unchanged."""
    def __init__(self, doc):
        self._doc = doc
        self.id = to_str_id(doc.get('_id'))
        self.name = doc.get('name', '')
        self.register_number = doc.get('register_number', '')
        self.section = doc.get('section', '')
        self.department = doc.get('department', '')
        self.duration = doc.get('duration', '')
        self.nfc_tag_id = doc.get('nfc_tag_id')

    def to_dict(self):
        return _student_to_dict(self._doc)


class StudentService:
    """Service class for student management (MongoDB backend)"""

    @staticmethod
    def create_student(data):
        is_valid, error = validate_student_data(data)
        if not is_valid:
            return False, error

        try:
            db = get_db()
            reg = data['register_number'].strip()

            if db.students.find_one({'register_number': reg}):
                return False, f"Student with register number {reg} already exists"

            doc = {
                'name': data['name'].strip(),
                'register_number': reg,
                'section': data['section'].strip(),
                'department': data['department'].strip(),
                'duration': data['duration'].strip(),
                'nfc_tag_id': None,
                'created_at': datetime.utcnow(),
            }
            result = db.students.insert_one(doc)
            doc['_id'] = result.inserted_id
            return True, _StudentProxy(doc)

        except Exception as e:
            return False, f"Error creating student: {str(e)}"

    @staticmethod
    def bulk_create_students(students_data):
        success_count = 0
        failed_count = 0
        errors = []

        for idx, data in enumerate(students_data):
            success, result = StudentService.create_student(data)
            if success:
                success_count += 1
            else:
                failed_count += 1
                errors.append({
                    'row': idx + 2,
                    'register_number': data.get('register_number', 'N/A'),
                    'error': result,
                })

        return success_count, failed_count, errors

    @staticmethod
    def get_student_by_id(student_id):
        db = get_db()
        oid = to_object_id(student_id)
        doc = db.students.find_one({'_id': oid}) if oid else db.students.find_one({'_id': student_id})
        return _StudentProxy(doc) if doc else None

    @staticmethod
    def get_student_by_register_number(register_number):
        db = get_db()
        doc = db.students.find_one({'register_number': register_number})
        return _StudentProxy(doc) if doc else None

    @staticmethod
    def get_all_students(filters=None):
        db = get_db()
        query = {}

        if filters:
            if filters.get('section'):
                query['section'] = filters['section']
            if filters.get('department'):
                query['department'] = filters['department']
            if filters.get('duration'):
                query['duration'] = filters['duration']
            if 'has_nfc' in filters:
                if filters['has_nfc']:
                    query['nfc_tag_id'] = {'$ne': None, '$exists': True}
                else:
                    query['$or'] = [{'nfc_tag_id': None}, {'nfc_tag_id': {'$exists': False}}]

        docs = list(db.students.find(query).sort('register_number', 1))
        return [_StudentProxy(d) for d in docs]

    @staticmethod
    def search_students(search_term):
        db = get_db()
        pattern = re.compile(search_term, re.IGNORECASE)
        docs = list(db.students.find({
            '$or': [
                {'name': {'$regex': pattern}},
                {'register_number': {'$regex': pattern}},
            ]
        }).sort('register_number', 1))
        return [_StudentProxy(d) for d in docs]

    @staticmethod
    def delete_student(student_id):
        try:
            db = get_db()
            oid = to_object_id(student_id)
            result = db.students.delete_one({'_id': oid})
            if result.deleted_count == 0:
                return False, "Student not found"
            # Also delete their attendance records
            db.attendance.delete_many({'student_id': student_id})
            return True, "Student deleted successfully"
        except Exception as e:
            return False, f"Error deleting student: {str(e)}"
