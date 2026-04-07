"""
Attendance Management API
REST endpoints for attendance operations
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
        
        # Can provide either student_id or nfc_tag_id
        student_id = data.get('student_id')
        nfc_tag_id = data.get('nfc_tag_id')
        faculty_name = data.get('faculty_name', 'Unknown Faculty')
        section = data.get('section')  # Section like S-01, S-02
        subject = data.get('subject')  # Subject name
        
        # If NFC tag provided, get student ID
        if nfc_tag_id and not student_id:
            student = NFCService.get_student_by_tag(nfc_tag_id)
            if not student:
                return jsonify({'error': 'No student found with this NFC tag'}), 404
            student_id = student.id
        
        if not student_id:
            return jsonify({'error': 'student_id or nfc_tag_id is required'}), 400
        
        success, result = AttendanceService.record_attendance(
            student_id, 
            faculty_name, 
            section=section, 
            subject=subject
        )
        
        if success:
            return jsonify({
                'message': 'Attendance recorded successfully',
                'attendance': result.to_dict()
            }), 201
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/student/<int:student_id>', methods=['GET'])
def get_student_attendance(student_id):
    """Get attendance history for a student"""
    try:
        limit = request.args.get('limit', type=int)
        records = AttendanceService.get_attendance_by_student(student_id, limit)
        
        return jsonify({
            'count': len(records),
            'attendance': [r.to_dict() for r in records]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/recent', methods=['GET'])
def get_recent_attendance():
    """Get recent attendance records"""
    try:
        limit = request.args.get('limit', 50, type=int)
        records = AttendanceService.get_recent_attendance(limit)
        
        return jsonify({
            'count': len(records),
            'attendance': [r.to_dict() for r in records]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/date', methods=['GET'])
def get_attendance_by_date():
    """Get attendance for a specific date"""
    try:
        date_str = request.args.get('date')
        
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = None  # Defaults to today
        
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
        from src.models import Attendance, Student
        faculty = request.args.get('faculty')
        subject = request.args.get('subject')
        date    = request.args.get('date')
        section = request.args.get('section')

        from src.models import db
        query = Attendance.query

        if faculty:
            query = query.filter(Attendance.recorded_by == faculty)
        if subject:
            query = query.filter(Attendance.subject == subject)
        if date:
            query = query.filter(Attendance.date == date)  # stored as string
        if section:
            query = query.join(Student, Attendance.student_id == Student.id).filter(Student.section == section)

        records = query.order_by(Attendance.timestamp.desc()).all()

        result = []
        for r in records:
            d = r.to_dict()
            d['section'] = r.student.section if r.student else None
            result.append(d)

        return jsonify({'count': len(result), 'attendance': result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/close-session', methods=['POST'])
def close_session():
    """Close an attendance session (mark all records as closed)"""
    try:
        from src.models import Attendance, db
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        faculty_name = data.get('faculty_name')
        subject      = data.get('subject')
        date         = data.get('date')  # string "YYYY-MM-DD"

        if not all([faculty_name, subject, date]):
            return jsonify({'error': 'faculty_name, subject, and date are required'}), 400

        # date is stored as a string in the DB — compare as string directly
        records = Attendance.query.filter(
            Attendance.recorded_by == faculty_name,
            Attendance.subject     == subject,
            Attendance.date        == date,
        ).all()

        if not records:
            return jsonify({'error': 'No session records found for this faculty/subject/date'}), 404

        closed_count = 0
        for record in records:
            try:
                record.session_closed = True
                closed_count += 1
            except Exception:
                pass  # column may not exist on old DBs

        db.session.commit()

        return jsonify({'message': 'Session closed successfully', 'closed_count': closed_count}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/<int:attendance_id>', methods=['DELETE'])
def delete_attendance(attendance_id):
    """Delete an individual attendance record"""
    try:
        from src.models import Attendance, db
        record = Attendance.query.get(attendance_id)
        if not record:
            return jsonify({'error': 'Attendance record not found'}), 404
        db.session.delete(record)
        db.session.commit()
        return jsonify({'message': 'Attendance record deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
