"""
Attendance Management Service
Business logic for attendance operations
"""
from datetime import datetime, timedelta
from src.models import db, Attendance, Student
from sqlalchemy import func
from collections import defaultdict


class AttendanceService:
    """Service class for attendance management"""
    
    @staticmethod
    def record_attendance(student_id, faculty_name, section=None, subject=None):
        """
        Record attendance for a student
        
        Args:
            student_id: ID of the student
            faculty_name: Name of the faculty recording attendance
            section: Section (e.g., S-01, S-02)
            subject: Subject name
            
        Returns:
            tuple: (success, message_or_attendance)
        """
        try:
            # Verify student exists
            student = Student.query.get(student_id)
            if not student:
                return False, "Student not found"
            
            # Check if already marked today (prevent duplicates within 1 hour)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_attendance = Attendance.query.filter(
                Attendance.student_id == student_id,
                Attendance.timestamp >= one_hour_ago
            ).first()
            
            if recent_attendance:
                return False, f"Attendance already recorded for {student.name} at {recent_attendance.timestamp.strftime('%H:%M:%S')}"
            
            # Create attendance record
            attendance = Attendance(
                student_id=student_id,
                recorded_by=faculty_name,
                section=section,
                subject=subject
            )
            
            db.session.add(attendance)
            db.session.commit()
            
            return True, attendance
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error recording attendance: {str(e)}"
    
    @staticmethod
    def get_attendance_by_student(student_id, limit=None):
        """
        Get attendance records for a student
        
        Args:
            student_id: ID of the student
            limit: Maximum number of records to return (optional)
            
        Returns:
            List of attendance records
        """
        query = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.timestamp.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_recent_attendance(limit=50):
        """
        Get recent attendance records across all students
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of attendance records
        """
        return Attendance.query.order_by(Attendance.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_attendance_by_date(date=None):
        """
        Get attendance records for a specific date
        
        Args:
            date: Date object (defaults to today)
            
        Returns:
            List of attendance records
        """
        if date is None:
            date = datetime.utcnow().date()
        
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        return Attendance.query.filter(
            Attendance.timestamp >= start_of_day,
            Attendance.timestamp <= end_of_day
        ).order_by(Attendance.timestamp.desc()).all()
    
    @staticmethod
    def get_attendance_stats():
        """
        Get attendance statistics
        
        Returns:
            Dictionary with statistics
        """
        total_students = Student.query.count()
        total_records = Attendance.query.count()
        
        # Today's attendance
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        today_count = Attendance.query.filter(Attendance.timestamp >= start_of_day).count()
        
        # Unique students who attended today
        today_students = db.session.query(Attendance.student_id).filter(
            Attendance.timestamp >= start_of_day
        ).distinct().count()
        
        return {
            'total_students': total_students,
            'total_attendance_records': total_records,
            'today_attendance_count': today_count,
            'today_unique_students': today_students,
            'today_percentage': round((today_students / total_students * 100) if total_students > 0 else 0, 2)
        }

    @staticmethod
    def get_section_attendance_stats():
        """
        Get attendance percentage for each section.
        For each section, compute:
          - Total students enrolled
          - Number of unique class dates that had attendance recorded for this section
          - Average attendance percentage per class day
          - Today's attendance percentage
        Returns:
            List of dicts with section stats
        """
        # Get all students grouped by section
        students = Student.query.all()
        section_students = defaultdict(list)
        for s in students:
            section_students[s.section].append(s.id)

        # Get all attendance records
        records = Attendance.query.all()

        # Group attendance by section and date
        # key: (section, date_str) -> set of student_ids present
        section_date_present = defaultdict(lambda: defaultdict(set))
        for r in records:
            sec = r.section or (r.student.section if r.student else None)
            if not sec:
                continue
            date_key = r.timestamp.strftime('%Y-%m-%d') if r.timestamp else (r.date or 'unknown')
            section_date_present[sec][date_key].add(r.student_id)

        today_str = datetime.utcnow().strftime('%Y-%m-%d')

        result = []
        for section in sorted(section_students.keys()):
            s_ids = set(section_students[section])
            total = len(s_ids)
            if total == 0:
                continue

            date_map = section_date_present.get(section, {})
            num_classes = len(date_map)

            # Average attendance percent across all class days
            if num_classes > 0:
                daily_pcts = [
                    len(present & s_ids) / total * 100
                    for present in date_map.values()
                ]
                avg_pct = round(sum(daily_pcts) / len(daily_pcts), 1)
            else:
                avg_pct = 0.0

            # Today's attendance
            today_present = date_map.get(today_str, set())
            today_pct = round(len(today_present & s_ids) / total * 100, 1)

            # Per-student attendance percentage
            student_stats = []
            for sid in s_ids:
                student_obj = Student.query.get(sid)
                attended = sum(1 for present in date_map.values() if sid in present)
                stu_pct = round((attended / num_classes * 100) if num_classes > 0 else 0, 1)
                student_stats.append({
                    'id': sid,
                    'name': student_obj.name if student_obj else 'Unknown',
                    'register_number': student_obj.register_number if student_obj else '',
                    'has_nfc': student_obj.nfc_tag_id is not None if student_obj else False,
                    'attendance_pct': stu_pct,
                    'attended': attended,
                    'total_classes': num_classes
                })

            student_stats.sort(key=lambda x: x['register_number'])

            result.append({
                'section': section,
                'total_students': total,
                'total_classes': num_classes,
                'avg_attendance_pct': avg_pct,
                'today_attendance_pct': today_pct,
                'today_present': len(today_present & s_ids),
                'students': student_stats
            })

        return result
