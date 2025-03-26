from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, time
import os
import logging
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure CORS based on environment
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, resources={r"/api/*": {"origins": ["https://sp-frontend.onrender.com"]}})
else:
    CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO if os.environ.get('FLASK_ENV') == 'production' else logging.DEBUG)
logger = logging.getLogger(__name__)

# Database configuration
database_url = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Task(db.Model):
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))    
    task_type = db.Column(db.String(50))
    subject = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.title}>'

class Exam(db.Model):
    __tablename__ = 'exam'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    module_number = db.Column(db.String(20), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    seat_number = db.Column(db.String(20), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Course(db.Model):
    __tablename__ = 'course'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(20), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    slots = db.Column(db.String(50), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject_name,
            'subject_code': self.subject_code,
            'room_number': self.room_number,
            'slots': self.slots,
            'credits': self.credits
        }

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    slot = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Attendance {self.course_id} {self.date} {self.slot}>'

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, DELETE')
    return response

@app.route('/')
def home():
    return jsonify({'message': 'Server is running'}), 200

@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        due_date = datetime.strptime(data['dueDate'], '%Y-%m-%d').date()
        
        new_task = Task(
            title=data['title'],
            detail=data['detail'],
            due_date=due_date,
            start_time=data.get('startTime', ''),
            end_time=data.get('endTime', ''),
            task_type=data['type'],
            subject=data['subject']
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'message': 'Task created successfully',
            'task': {
                'id': new_task.id,
                'title': new_task.title,
                'detail': new_task.detail,
                'dueDate': new_task.due_date.strftime('%Y-%m-%d'),
                'startTime': new_task.start_time,
                'endTime': new_task.end_time,
                'type': new_task.task_type,
                'subject': new_task.subject
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    logger.debug(f"Received GET request with params: {request.args}")
    date_filter = request.args.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            tasks = Task.query.filter_by(due_date=filter_date).all()
        except ValueError as e:
            logger.error(f"Invalid date format: {str(e)}")
            return jsonify({'error': 'Invalid date format'}), 400
    else:
        tasks = Task.query.all()
    
    result = [{
        'id': task.id,
        'title': task.title,
        'detail': task.detail,
        'dueDate': task.due_date.strftime('%Y-%m-%d'),
        'startTime': task.start_time,
        'endTime': task.end_time,
        'type': task.task_type,
        'subject': task.subject
    } for task in tasks]
    
    logger.debug(f"Returning {len(result)} tasks")
    return jsonify(result)

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    logger.debug(f"Received DELETE request for task ID: {task_id}")
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    logger.debug(f"Deleted task ID: {task_id}")
    return jsonify({'message': 'Task deleted successfully'})

@app.route('/api/exams', methods=['POST'])
def create_exam():
    logger.debug(f"Received POST request with data: {request.json}")
    try:
        data = request.json
        if not data:
            raise ValueError("No JSON data received")

        required_fields = ['subject', 'moduleNumber', 'examDate', 'startTime', 'duration', 'seatNumber', 'roomNumber']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        exam_date = datetime.strptime(data['examDate'], '%Y-%m-%d').date()
        
        new_exam = Exam(
            subject=data['subject'],
            module_number=data['moduleNumber'],
            exam_date=exam_date,
            start_time=data['startTime'],
            duration=int(data['duration']),
            seat_number=data['seatNumber'],
            room_number=data['roomNumber']
        )
        
        logger.debug(f"Creating exam: {new_exam}")
        db.session.add(new_exam)
        db.session.commit()
        logger.info(f"Created exam with ID: {new_exam.id}")
        
        return jsonify({
            'message': 'Exam created successfully',
            'id': new_exam.id,
            'exam': {
                'id': new_exam.id,
                'subject': new_exam.subject,
                'moduleNumber': new_exam.module_number,
                'examDate': new_exam.exam_date.strftime('%Y-%m-%d'),
                'startTime': new_exam.start_time,
                'duration': new_exam.duration,
                'seatNumber': new_exam.seat_number,
                'roomNumber': new_exam.room_number
            }
        }), 201
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating exam: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f"Failed to create exam: {str(e)}"}), 500

@app.route('/api/exams', methods=['GET'])
def get_exams():
    logger.debug("Received GET request for exams")
    try:
        exams = Exam.query.all()
        result = [{
            'id': exam.id,
            'subject': exam.subject,
            'moduleNumber': exam.module_number,
            'examDate': exam.exam_date.strftime('%Y-%m-%d'),
            'startTime': exam.start_time,
            'duration': exam.duration,
            'seatNumber': exam.seat_number,
            'roomNumber': exam.room_number
        } for exam in exams]
        
        logger.debug(f"Returning {len(result)} exams")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching exams: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/exams/<int:exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    logger.debug(f"Received DELETE request for exam ID: {exam_id}")
    try:
        exam = Exam.query.get_or_404(exam_id)
        db.session.delete(exam)
        db.session.commit()
        logger.debug(f"Deleted exam ID: {exam_id}")
        return jsonify({'message': 'Exam deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting exam: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        courses = Course.query.all()
        return jsonify([course.to_dict() for course in courses])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses', methods=['POST'])
def create_course():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['subject_name', 'subject_code', 'room_number', 'slots', 'credits']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        course = Course(
            subject_name=data['subject_name'],
            subject_code=data['subject_code'],
            room_number=data['room_number'],
            slots=data['slots'],
            credits=data['credits']
        )
        db.session.add(course)
        db.session.commit()
        
        # Return the course data in the same format as get_courses
        return jsonify({
            'id': course.id,
            'subject_name': course.subject_name,
            'subject_code': course.subject_code,
            'room_number': course.room_number,
            'slots': course.slots,
            'credits': course.credits
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    try:
        course = Course.query.get_or_404(course_id)
        db.session.delete(course)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['course_id', 'date', 'slot']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Convert date string to date object
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        # Check if attendance already exists
        existing = Attendance.query.filter_by(
            course_id=data['course_id'],
            date=date,
            slot=data['slot']
        ).first()
        
        if existing:
            # If exists, delete it (unmark attendance)
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'message': 'Attendance unmarked successfully'}), 200
        else:
            # If doesn't exist, create new attendance
            attendance = Attendance(
                course_id=data['course_id'],
                date=date,
                slot=data['slot']
            )
            db.session.add(attendance)
            db.session.commit()
            return jsonify({'message': 'Attendance marked successfully'}), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/<date>', methods=['GET'])
def get_attendance(date):
    try:
        # Convert date string to date object
        query_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Get all attendance records for the date
        attendances = Attendance.query.filter_by(date=query_date).all()
        
        return jsonify([{
            'course_id': att.course_id,
            'slot': att.slot,
            'date': att.date.strftime('%Y-%m-%d')
        } for att in attendances])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 error: {request.url}")
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables without dropping
    app.run(debug=True, host='127.0.0.1', port=5500) 
