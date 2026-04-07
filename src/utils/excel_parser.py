"""
Excel/CSV file parsing utilities — no pandas dependency
Uses only openpyxl and csv (both safe for Vercel)
"""
import csv
from io import BytesIO, StringIO


def parse_student_file(file_path, file_type='excel'):
    """
    Parse Excel or CSV file containing student data.
    Returns: (True, list_of_dicts) or (False, error_message)
    """
    try:
        required = ['name', 'register_number', 'section', 'department', 'duration']

        if file_type == 'csv':
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = [h.strip().lower().replace(' ', '_') for h in reader.fieldnames or []]
                rows = list(reader)
        else:
            from openpyxl import load_workbook
            wb = load_workbook(filename=file_path, read_only=True)
            ws = wb.active
            header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
            headers = [str(h).strip().lower().replace(' ', '_') for h in header_row if h]
            rows = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                if any(cell for cell in row):
                    rows.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})

        missing = [c for c in required if c not in headers]
        if missing:
            return False, f"Missing required columns: {', '.join(missing)}"

        students = []
        for row in rows:
            name = row.get('name')
            reg  = row.get('register_number')
            if not name or not reg:
                continue
            students.append({
                'name': str(name).strip(),
                'register_number': str(reg).strip(),
                'section': str(row.get('section', '')).strip(),
                'department': str(row.get('department', '')).strip(),
                'duration': str(row.get('duration', '')).strip(),
            })

        if not students:
            return False, "No valid student data found in file"
        return True, students

    except Exception as e:
        return False, f"Error parsing file: {str(e)}"
