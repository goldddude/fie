"""
MongoDB NFC Service
NFC tag registration using PyMongo
"""
from src.database import get_db, to_object_id, to_str_id
from src.utils.validators import validate_nfc_tag
from src.services.student_service import _StudentProxy


class NFCService:
    """Service class for NFC tag management (MongoDB backend)"""

    @staticmethod
    def register_tag(student_id, nfc_tag_id):
        is_valid, error = validate_nfc_tag(nfc_tag_id)
        if not is_valid:
            return False, error

        try:
            db = get_db()
            oid = to_object_id(student_id)
            student = db.students.find_one({'_id': oid})
            if not student:
                return False, "Student not found"

            tag = nfc_tag_id.strip()

            # Check if tag is already used by another student
            existing = db.students.find_one({'nfc_tag_id': tag})
            if existing and str(existing['_id']) != str(student_id):
                return False, f"NFC tag already registered to {existing.get('name')} ({existing.get('register_number')})"

            db.students.update_one({'_id': oid}, {'$set': {'nfc_tag_id': tag}})
            student['nfc_tag_id'] = tag
            return True, _StudentProxy(student)

        except Exception as e:
            return False, f"Error registering NFC tag: {str(e)}"

    @staticmethod
    def unregister_tag(student_id):
        try:
            db = get_db()
            oid = to_object_id(student_id)
            student = db.students.find_one({'_id': oid})
            if not student:
                return False, "Student not found"
            if not student.get('nfc_tag_id'):
                return False, "Student does not have an NFC tag registered"

            db.students.update_one({'_id': oid}, {'$set': {'nfc_tag_id': None}})
            return True, "NFC tag unregistered successfully"

        except Exception as e:
            return False, f"Error unregistering NFC tag: {str(e)}"

    @staticmethod
    def get_student_by_tag(nfc_tag_id):
        db = get_db()
        doc = db.students.find_one({'nfc_tag_id': nfc_tag_id.strip()})
        return _StudentProxy(doc) if doc else None

    @staticmethod
    def is_tag_registered(nfc_tag_id):
        db = get_db()
        return db.students.find_one({'nfc_tag_id': nfc_tag_id.strip()}) is not None
