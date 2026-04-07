"""
Attendance Management API
REST endpoints for attendance operations (MongoDB backend)
"""
from flask import Blueprint, request, jsonify
from src.services.attendance_service import AttendanceService
from src.services.nfc_service import NFCService
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/record', methods=['POST'])
def record_attendance():
    """Record attendance for a student"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        student_id  = data.get('student_id')
        nfc_tag_id  = data.get('nfc_tag_id')
        faculty_name = data.get('faculty_name', 'Unknown Faculty')
        section     = data.get('section')
        subject     = data.get('subject')
        date        = data.get('date') or data.get('currentDate')
        class_time  = data.get('class_time') or data.get('currentTime')

        if nfc_tag_id and not student_id:
            student = NFCService.get_student_by_tag(nfc_tag_id)
            if not student:
                return jsonify({'error': 'No student found with this NFC tag'}), 404
            student_id = student.id

        if not student_id:
            return jsonify({'error': 'student_id or nfc_tag_id is required'}), 400

        success, result = AttendanceService.record_attendance(
            student_id, faculty_name,
            section=section, subject=subject,
            date=date, class_time=class_time
        )

        if success:
            return jsonify({'message': 'Attendance recorded successfully', 'attendance': result.to_dict()}), 201
        else:
            return jsonify({'error': result}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/student/<student_id>', methods=['GET'])
def get_student_attendance(student_id):
    """Get attendance history for a student"""
    try:
        limit = request.args.get('limit', type=int)
        records = AttendanceService.get_attendance_by_student(student_id, limit)
        return jsonify({'count': len(records), 'attendance': [r.to_dict() for r in records]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/recent', methods=['GET'])
def get_recent_attendance():
    """Get recent attendance records"""
    try:
        limit = request.args.get('limit', 50, type=int)
        records = AttendanceService.get_recent_attendance(limit)
        return jsonify({'count': len(records), 'attendance': [r.to_dict() for r in records]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/date', methods=['GET'])
def get_attendance_by_date():
    """Get attendance for a specific date"""
    try:
        date_str = request.args.get('date')
        date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        records = AttendanceService.get_attendance_by_date(date)
        return jsonify({
            'date': date.isoformat() if date else datetime.utcnow().date().isoformat(),
            'count': len(records),
            'attendance': [r.to_dict() for r in records]
        }), 200
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get attendance statistics"""
    try:
        stats = AttendanceService.get_attendance_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/section-stats', methods=['GET'])
def get_section_stats():
    """Get per-section attendance percentage statistics"""
    try:
        stats = AttendanceService.get_section_attendance_stats()
        return jsonify({'sections': stats}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/by-session', methods=['GET'])
def get_by_session():
    """Get attendance filtered by faculty / subject / date / section"""
    try:
        from src.database import get_db
        db = get_db()

        faculty = request.args.get('faculty')
        subject = request.args.get('subject')
        date    = request.args.get('date')
        section = request.args.get('section')

        query = {}
        if faculty:
            query['recorded_by'] = faculty
        if subject:
            query['subject'] = subject
        if date:
            query['date'] = date
        if section:
            query['section'] = section

        docs = list(db.attendance.find(query).sort('timestamp', -1))
        result = []
        for d in docs:
            rec = {
                'id': str(d.get('_id', '')),
                'student_id': d.get('student_id', ''),
                'student_name': d.get('student_name', ''),
                'register_number': d.get('register_number', ''),
                'recorded_by': d.get('recorded_by', ''),
                'section': d.get('section', ''),
                'subject': d.get('subject', ''),
                'date': d.get('date', ''),
                'class_time': d.get('class_time', ''),
                'timestamp': d['timestamp'].isoformat() if d.get('timestamp') else '',
                'session_closed': d.get('session_closed', False),
            }
            result.append(rec)

        return jsonify({'count': len(result), 'attendance': result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/close-session', methods=['POST'])
def close_session():
    """Close an attendance session"""
    try:
        from src.database import get_db
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        faculty_name = data.get('faculty_name')
        subject      = data.get('subject')
        date         = data.get('date')

        if not all([faculty_name, subject, date]):
            return jsonify({'error': 'faculty_name, subject, and date are required'}), 400

        result = db.attendance.update_many(
            {'recorded_by': faculty_name, 'subject': subject, 'date': date},
            {'$set': {'session_closed': True}}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'No session records found for this faculty/subject/date'}), 404

        return jsonify({'message': 'Session closed successfully', 'closed_count': result.modified_count}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/<attendance_id>', methods=['DELETE'])
def delete_attendance(attendance_id):
    """Delete an individual attendance record"""
    try:
        from src.database import get_db, to_object_id
        db = get_db()
        oid = to_object_id(attendance_id)
        result = db.attendance.delete_one({'_id': oid})
        if result.deleted_count == 0:
            return jsonify({'error': 'Attendance record not found'}), 404
        return jsonify({'message': 'Attendance record deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
