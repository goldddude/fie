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


def _build_uri():
    """
    Build a properly RFC-3986 encoded MongoDB URI.
    Priority:
      1. MONGODB_URI  — used as-is (you are responsible for encoding)
      2. MONGO_USER + MONGO_PASS + MONGO_HOST — auto-encoded with urllib
    """
    import urllib.parse

    # Option 1: full URI already provided
    uri = os.environ.get('MONGODB_URI', '').strip()
    if uri:
        return uri

    # Option 2: build from parts (auto-encodes special chars like @, #, %)
    user  = os.environ.get('MONGO_USER', '').strip()
    pwd   = os.environ.get('MONGO_PASS', '').strip()
    host  = os.environ.get('MONGO_HOST', '').strip()  # e.g. cluster0.xsq4hkp.mongodb.net
    app   = os.environ.get('MONGO_APP',  'Cluster0').strip()

    if user and pwd and host:
        enc_user = urllib.parse.quote_plus(user)
        enc_pass = urllib.parse.quote_plus(pwd)   # safely encodes @, #, % etc.
        db_name  = os.environ.get('MONGO_DB_NAME', 'Tapsyncpro')
        return f"mongodb+srv://{enc_user}:{enc_pass}@{host}/{db_name}?appName={app}"

    raise RuntimeError(
        "MongoDB credentials not set.\n"
        "Add ONE of the following to your .env / Vercel env vars:\n\n"
        "  Option A — Full URI:\n"
        "    MONGODB_URI=mongodb+srv://user:pass@host/dbname?appName=Cluster0\n\n"
        "  Option B — Separate parts (handles special chars automatically):\n"
        "    MONGO_USER=sudhama07pmk_db_user\n"
        "    MONGO_PASS=trinity@07\n"
        "    MONGO_HOST=cluster0.xsq4hkp.mongodb.net\n"
    )


def get_db():
    """Return the active MongoDB database instance, creating it if needed."""
    global _client, _db

    if _db is not None:
        return _db

    mongo_uri = _build_uri()
    db_name   = os.environ.get('MONGO_DB_NAME', 'Tapsyncpro')

    _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
    _db     = _client[db_name]

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
