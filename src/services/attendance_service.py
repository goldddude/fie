"""
MongoDB Attendance Service
All attendance CRUD operations using PyMongo
"""
from datetime import datetime
from collections import defaultdict
from bson import ObjectId
from src.database import get_db, to_str_id, to_object_id


def _att_to_dict(doc, student_doc=None):
    """Convert a MongoDB attendance document to a plain dict."""
    if doc is None:
        return None
    ts = doc.get('timestamp', datetime.utcnow())
    student_name = doc.get('student_name', '')
    register_number = doc.get('register_number', '')
    section = doc.get('section', '')

    if student_doc:
        student_name = student_doc.get('name', student_name)
        register_number = student_doc.get('register_number', register_number)
        section = student_doc.get('section', section)

    return {
        'id': to_str_id(doc.get('_id')),
        'student_id': doc.get('student_id', ''),
        'student_name': student_name,
        'register_number': register_number,
        'recorded_by': doc.get('recorded_by', ''),
        'section': section,
        'subject': doc.get('subject', ''),
        'date': doc.get('date', ts.strftime('%Y-%m-%d') if ts else ''),
        'class_time': doc.get('class_time', ''),
        'timestamp': ts.isoformat() if isinstance(ts, datetime) else str(ts),
        'session_closed': doc.get('session_closed', False),
    }


class _AttProxy:
    """Thin proxy so service returns objects with .to_dict() — keeps API routes unchanged."""
    def __init__(self, doc, student_doc=None):
        self._doc = doc
        self._student = student_doc
        self.id = to_str_id(doc.get('_id'))
        self.student_id = doc.get('student_id', '')
        self.recorded_by = doc.get('recorded_by', '')
        self.section = doc.get('section', '')
        self.subject = doc.get('subject', '')
        self.date = doc.get('date', '')
        self.class_time = doc.get('class_time', '')
        ts = doc.get('timestamp')
        self.timestamp = ts if isinstance(ts, datetime) else datetime.utcnow()
        self.session_closed = doc.get('session_closed', False)

    def to_dict(self):
        return _att_to_dict(self._doc, self._student)


class AttendanceService:
    """Service class for attendance management (MongoDB backend)"""

    @staticmethod
    def record_attendance(student_id, faculty_name, section=None, subject=None,
                          date=None, class_time=None):
        try:
            db = get_db()

            # Verify student exists
            oid = to_object_id(student_id)
            student = db.students.find_one({'_id': oid}) if oid else None
            if not student:
                return False, "Student not found"

            # Prevent duplicate within the SAME session only
            # A session is uniquely identified by: student + date + section + subject + class_time
            today_str = date or datetime.utcnow().strftime('%Y-%m-%d')
            session_query = {
                'student_id': str(student_id),
                'date': today_str,
                'section': section or student.get('section', ''),
                'subject': subject or '',
                'class_time': class_time or '',
            }
            existing = db.attendance.find_one(session_query)
            if existing:
                ts = existing.get('timestamp', datetime.utcnow())
                return False, f"Already recorded for {student.get('name')} in this session (recorded at {ts.strftime('%H:%M:%S')})"

            doc = {
                'student_id': str(student_id),
                'student_name': student.get('name', ''),
                'register_number': student.get('register_number', ''),
                'recorded_by': faculty_name,
                'section': section or student.get('section', ''),
                'subject': subject or '',
                'date': today_str,
                'class_time': class_time or '',
                'timestamp': datetime.utcnow(),
                'session_closed': False,
            }
            result = db.attendance.insert_one(doc)
            doc['_id'] = result.inserted_id
            return True, _AttProxy(doc, student)

        except Exception as e:
            return False, f"Error recording attendance: {str(e)}"

    @staticmethod
    def get_attendance_by_student(student_id, limit=None):
        db = get_db()
        cursor = db.attendance.find({'student_id': str(student_id)}).sort('timestamp', -1)
        if limit:
            cursor = cursor.limit(limit)
        docs = list(cursor)
        return [_AttProxy(d) for d in docs]

    @staticmethod
    def get_recent_attendance(limit=50):
        db = get_db()
        docs = list(db.attendance.find().sort('timestamp', -1).limit(limit))
        return [_AttProxy(d) for d in docs]

    @staticmethod
    def get_attendance_by_date(date=None):
        db = get_db()
        if date is None:
            date = datetime.utcnow().date()
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        docs = list(db.attendance.find({'date': date_str}).sort('timestamp', -1))
        return [_AttProxy(d) for d in docs]

    @staticmethod
    def get_attendance_stats():
        db = get_db()
        total_students = db.students.count_documents({})
        total_records  = db.attendance.count_documents({})

        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        today_count = db.attendance.count_documents({'date': today_str})

        today_students = len(db.attendance.distinct('student_id', {'date': today_str}))

        return {
            'total_students': total_students,
            'total_attendance_records': total_records,
            'today_attendance_count': today_count,
            'today_unique_students': today_students,
            'today_percentage': round(
                (today_students / total_students * 100) if total_students > 0 else 0, 2
            ),
        }

    @staticmethod
    def get_section_attendance_stats():
        db = get_db()

        # Students by section
        students = list(db.students.find({}))
        section_students = defaultdict(list)
        for s in students:
            section_students[s.get('section', '')].append(str(s['_id']))

        # Attendance records
        records = list(db.attendance.find({}))

        # Group: section → date → set of student_ids
        section_date_present = defaultdict(lambda: defaultdict(set))
        for r in records:
            sec = r.get('section', '')
            date_key = r.get('date') or (r['timestamp'].strftime('%Y-%m-%d') if r.get('timestamp') else 'unknown')
            if sec:
                section_date_present[sec][date_key].add(r.get('student_id', ''))

        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        result = []

        for section in sorted(section_students.keys()):
            if not section:
                continue
            s_ids = set(section_students[section])
            total = len(s_ids)
            if total == 0:
                continue

            date_map = section_date_present.get(section, {})
            num_classes = len(date_map)

            avg_pct = 0.0
            if num_classes > 0:
                daily = [len(present & s_ids) / total * 100 for present in date_map.values()]
                avg_pct = round(sum(daily) / len(daily), 1)

            today_present = date_map.get(today_str, set())
            today_pct = round(len(today_present & s_ids) / total * 100, 1)

            # Per-student stats
            student_stats = []
            student_map = {str(s['_id']): s for s in students}
            for sid in s_ids:
                stu = student_map.get(sid)
                attended = sum(1 for present in date_map.values() if sid in present)
                stu_pct = round((attended / num_classes * 100) if num_classes > 0 else 0, 1)
                student_stats.append({
                    'id': sid,
                    'name': stu.get('name', 'Unknown') if stu else 'Unknown',
                    'register_number': stu.get('register_number', '') if stu else '',
                    'has_nfc': bool(stu.get('nfc_tag_id')) if stu else False,
                    'attendance_pct': stu_pct,
                    'attended': attended,
                    'total_classes': num_classes,
                })
            student_stats.sort(key=lambda x: x['register_number'])

            result.append({
                'section': section,
                'total_students': total,
                'total_classes': num_classes,
                'avg_attendance_pct': avg_pct,
                'today_attendance_pct': today_pct,
                'today_present': len(today_present & s_ids),
                'students': student_stats,
            })

        return result
