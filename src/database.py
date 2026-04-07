"""
MongoDB Connection Manager
Central place to get the database instance (PyMongo)
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from datetime import datetime

_client = None
_db = None


def get_db():
    """Return the active MongoDB database instance, creating it if needed."""
    global _client, _db

    if _db is not None:
        return _db

    mongo_uri = os.environ.get('MONGODB_URI', '')
    if not mongo_uri:
        raise RuntimeError(
            "MONGODB_URI is not set. Add it to your .env file.\n"
            "Example: MONGODB_URI=mongodb+srv://user:pass@cluster0.xxx.mongodb.net/tapsyncpro"
        )

    # Append DB name if not present in URI
    db_name = os.environ.get('MONGO_DB_NAME', 'tapsyncpro')

    _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    _db = _client[db_name]

    # Create indexes on first connection
    _ensure_indexes(_db)

    print(f"✅ Connected to MongoDB — database: {db_name}")
    return _db


def _ensure_indexes(db):
    """Create indexes for performance & uniqueness."""
    try:
        db.students.create_index('register_number', unique=True)
        db.students.create_index('nfc_tag_id', sparse=True)
        db.students.create_index('section')

        db.attendance.create_index('student_id')
        db.attendance.create_index('date')
        db.attendance.create_index('recorded_by')
        db.attendance.create_index('subject')
        db.attendance.create_index([('student_id', 1), ('timestamp', -1)])

        db.faculty.create_index('email', unique=True)
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")


# ── Helpers ──────────────────────────────────────────────────────────────────

def to_str_id(obj_id):
    """Convert ObjectId → str safely."""
    if obj_id is None:
        return None
    return str(obj_id)


def to_object_id(str_id):
    """Convert str → ObjectId safely, returns None on failure."""
    try:
        return ObjectId(str_id)
    except Exception:
        return None
