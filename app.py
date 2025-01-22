from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = '123456'

# database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_exam_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Flask-migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    course = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    grade = db.Column(db.String(10), nullable=False)

    student = db.relationship('Student', backref='results')
    exam = db.relationship('Exam', backref='results')

# API Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')

    if role == 'admin':
        return render_template('home.html', role='admin')
    elif role == 'student':
        return render_template('home.html', role='student')
    else:
        flash('Invalid role detected. Please log in again.', 'danger')
        return redirect(url_for('logout'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/signup')
def signup():
    flash('Student signup is not allowed. Only the admin can add new students.', 'warning')
    return redirect(url_for('login'))



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        students = Student.query.all()
        return render_template('admin_dashboard.html', students=students)
    flash('Access denied: Admins only.', 'danger')
    return redirect(url_for('home'))

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        course = request.form['course']
        username = request.form['username']
        password = request.form['password']

        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists.', 'warning')
            return redirect(url_for('add_student'))

        # Create User and Student records
        new_user = User(username=username, email=email, password=password, role='student')
        db.session.add(new_user)
        db.session.commit()

        new_student = Student(name=name, email=email, course=course, user_id=new_user.id)
        db.session.add(new_student)
        db.session.commit()

        flash(f'Student {name} added successfully with username: {username}', 'success')
        return render_template('add_student.html')

    return render_template('add_student.html')


@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))

    student = Student.query.get_or_404(id)

    if request.method == 'POST':
        student.name = request.form['name']
        student.email = request.form['email']
        student.course = request.form['course']

        db.session.commit()
        flash('Student updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))

    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/add_exam', methods=['GET', 'POST'])
def add_exam():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        subject = request.form['subject']
        date = request.form['date']
        time = request.form['time']
        
        new_exam = Exam(subject=subject, date=date, time=time)
        db.session.add(new_exam)
        db.session.commit()
        flash('Exam added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_exam.html')

@app.route('/assign_result', methods=['GET', 'POST'])
def assign_result():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))

    students = Student.query.all()
    exams = Exam.query.all()

    if request.method == 'POST':
        student_id = request.form['student_id']
        exam_id = request.form['exam_id']
        grade = request.form['grade']

        # Check if results already exists
        existing_result = Result.query.filter_by(student_id=student_id, exam_id=exam_id).first()
        if existing_result:
            flash('Result for this student and exam already exists.', 'warning')
        else:
            # save the new result
            new_result = Result(student_id=student_id, exam_id=exam_id, grade=grade)
            db.session.add(new_result)
            db.session.commit()
            flash('Result assigned successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('assign_result.html', students=students, exams=exams)


@app.route('/results')
def view_results():
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Access denied: Students only.', 'danger')
        return redirect(url_for('login'))

    # Get the students details
    user_id = session['user_id']
    student = Student.query.filter_by(user_id=user_id).first()

    if not student:
        flash('No student record found for this account.', 'danger')
        return redirect(url_for('home'))

    # Get the student's results
    results = Result.query.filter_by(student_id=student.id).all()
    return render_template('view_results.html', results=results)


@app.route('/delete_result/<int:id>', methods=['POST'])
def delete_result(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))

    result = Result.query.get_or_404(id)
    db.session.delete(result)
    db.session.commit()
    flash('Result deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/profile')
def view_profile():
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Access denied: Students only.', 'danger')
        return redirect(url_for('login'))

    # Get the student's profile
    user_id = session['user_id']
    student = Student.query.filter_by(user_id=user_id).first()

    if not student:
        flash('No profile found for this account.', 'danger')
        return redirect(url_for('home'))

    return render_template('profile.html', student=student)

@app.route('/exams')
def view_exams():
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Access denied: Students only.', 'danger')
        return redirect(url_for('login'))

    exams = Exam.query.order_by(Exam.date).all()
    return render_template('exams.html', exams=exams)


# Initialize the database
with app.app_context():
    if not os.path.exists('student_exam_system.db'):
        db.create_all()
  
    # Create the admin account at startup
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', password='admin123', role='admin')
        db.session.add(admin)
        db.session.commit()
        print("Admin account created: Username='admin', Password='admin123', Email='admin@sample.com'")


# Main function
if __name__ == '__main__':
    app.run(debug=True)
