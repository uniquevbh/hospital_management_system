from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timedelta
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import db, User, Doctor, Patient, Department, Appointment, Treatment, DoctorAvailability

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hospital-management-secret-key-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration (for password reset)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Update with your email
app.config['MAIL_PASSWORD'] = 'your-app-password'     # Update with your app password

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_tables():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(role='admin').first():
            admin_user = User(
                username='admin',
                email='admin@hospital.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin_user)
            
            departments = [
                Department(name='Cardiology', description='Heart and cardiovascular diseases'),
                Department(name='Neurology', description='Brain and nervous system disorders'),
                Department(name='Pediatrics', description='Child healthcare'),
                Department(name='Orthopedics', description='Bone and joint diseases'),
                Department(name='Dermatology', description='Skin diseases and treatments'),
                Department(name='General Medicine', description='General health issues and common diseases')
            ]
            db.session.add_all(departments)
            db.session.commit()
            print("✅ Admin user created: username='admin', password='admin123'")
            print("✅ Sample departments created")

# Store reset tokens (in production, use Redis or database)
reset_tokens = {}

def send_reset_email(user_email, reset_token):
    """Send password reset email (simplified version)"""
    try:
        # In a real application, you would send an actual email
        # For demo purposes, we'll just print the reset link
        reset_link = f"http://localhost:5000/reset-password/{reset_token}"
        print(f"Password reset link for {user_email}: {reset_link}")
        
        # For actual email sending (uncomment and configure):
        '''
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = user_email
        msg['Subject'] = 'Password Reset Request - Hospital Management System'
        
        body = f"""
        Hello,
        
        You requested a password reset for your Hospital Management System account.
        
        Please click the following link to reset your password:
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        Hospital Management System Team
        """
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        '''
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            reset_tokens[reset_token] = {
                'user_id': user.id,
                'expires': datetime.utcnow() + timedelta(hours=1)
            }
            
            # Send reset email
            if send_reset_email(user.email, reset_token):
                flash('Password reset instructions have been sent to your email.', 'info')
            else:
                flash('Failed to send email. Please try again.', 'danger')
        else:
            flash('No account found with that email address.', 'danger')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Check if token is valid
    token_data = reset_tokens.get(token)
    if not token_data or token_data['expires'] < datetime.utcnow():
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('forgot_password'))
    
    user = User.query.get(token_data['user_id'])
    if not user:
        flash('Invalid user.', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('reset_password.html', token=token)
        
        # Update password
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        # Remove used token
        reset_tokens.pop(token, None)
        
        flash('Password reset successfully! You can now login with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register_patient'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register_patient'))
        
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='patient'
        )
        db.session.add(user)
        db.session.flush()
        
        # Handle optional fields safely
        dob = request.form.get('dob')
        date_of_birth = None
        if dob:
            try:
                date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                # If date format is invalid, set to None
                date_of_birth = None
        
        patient = Patient(
            user_id=user.id,
            phone=request.form.get('phone', ''),
            date_of_birth=date_of_birth,
            blood_group=request.form.get('blood_group', ''),
            address=request.form.get('address', '')
        )
        db.session.add(patient)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    # Pass today's date for the date picker max attribute
    today = date.today().isoformat()
    return render_template('register_patient.html', today=today)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    stats = {
        'doctors': Doctor.query.filter_by(is_active=True).count(),
        'patients': Patient.query.filter_by(is_active=True).count(),
        'appointments': Appointment.query.count(),
        'departments': Department.query.count()
    }
    
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, appointments=recent_appointments)

@app.route('/admin/doctors')
@login_required
def admin_doctors():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    doctors = Doctor.query.all()
    departments = Department.query.all()
    return render_template('admin/doctors.html', doctors=doctors, departments=departments)

@app.route('/admin/add_doctor', methods=['POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    username = request.form['username']
    email = request.form['email']
    specialization = request.form['specialization']
    department_id = request.form['department_id']
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(
        username=username,
        email=email,
        password=generate_password_hash('doctor123'),
        role='doctor'
    )
    db.session.add(user)
    db.session.flush()
    
    # FIXED: Handle license number properly - set to None if empty
    license_number = request.form.get('license_number', '').strip()
    if not license_number:
        license_number = None
    
    doctor = Doctor(
        user_id=user.id,
        department_id=department_id,
        specialization=specialization,
        license_number=license_number,  # This will be None if empty
        experience=request.form.get('experience', type=int),
        consultation_fee=request.form.get('consultation_fee', 0.0, type=float)
    )
    db.session.add(doctor)
    db.session.commit()
    
    flash('Doctor added successfully! Default password: doctor123', 'success')
    return jsonify({'success': True})

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found', 'danger')
        return redirect(url_for('logout'))
    
    today = date.today()
    todays_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, 
        appointment_date=today
    ).order_by(Appointment.appointment_time).all()
    
    next_week = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date.between(today, next_week),
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    return render_template('doctor/dashboard.html', 
                         doctor=doctor,
                         todays_appointments=todays_appointments,
                         upcoming_appointments=upcoming_appointments)

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found', 'danger')
        return redirect(url_for('logout'))
    
    upcoming_appointments = Appointment.query.filter_by(
        patient_id=patient.id,
        status='Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.status.in_(['Completed', 'Cancelled'])
    ).order_by(Appointment.appointment_date.desc()).all()
    
    departments = Department.query.all()
    
    return render_template('patient/dashboard.html',
                         patient=patient,
                         upcoming_appointments=upcoming_appointments,
                         past_appointments=past_appointments,
                         departments=departments)

@app.route('/search_doctors')
@login_required
def search_doctors():
    specialization = request.args.get('specialization', '')
    date_str = request.args.get('date', '')
    
    query = Doctor.query.filter_by(is_active=True)
    
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f'%{specialization}%'))
    
    doctors = query.all()
    
    if date_str:
        try:
            search_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            available_doctors = []
            for doctor in doctors:
                availability = DoctorAvailability.query.filter_by(
                    doctor_id=doctor.id,
                    date=search_date,
                    is_available=True
                ).first()
                if availability:
                    available_doctors.append(doctor)
            doctors = available_doctors
        except ValueError:
            pass
    
    results = []
    for doctor in doctors:
        results.append({
            'id': doctor.id,
            'name': doctor.user.username,
            'specialization': doctor.specialization,
            'department': doctor.department.name,
            'experience': doctor.experience,
            'consultation_fee': doctor.consultation_fee
        })
    
    return jsonify(results)

@app.route('/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    if current_user.role != 'patient':
        return jsonify({'error': 'Access denied'}), 403
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        return jsonify({'error': 'Patient profile not found'}), 400
    
    doctor_id = request.form['doctor_id']
    appointment_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    appointment_time = datetime.strptime(request.form['time'], '%H:%M').time()
    symptoms = request.form.get('symptoms', '')
    
    existing_appointment = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status='Booked'
    ).first()
    
    if existing_appointment:
        return jsonify({'error': 'Slot already booked'}), 400
    
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        symptoms=symptoms
    )
    
    db.session.add(appointment)
    db.session.commit()
    
    flash('Appointment booked successfully!', 'success')
    return jsonify({'success': True})

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check if the current user owns this appointment or is admin
    if current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if appointment.patient_id != patient.id:
            flash('You can only cancel your own appointments', 'danger')
            return redirect(url_for('patient_dashboard'))
    
    elif current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        if appointment.doctor_id != doctor.id:
            flash('You can only cancel appointments assigned to you', 'danger')
            return redirect(url_for('doctor_dashboard'))
    
    elif current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Update appointment status to Cancelled
    appointment.status = 'Cancelled'
    db.session.commit()
    
    flash('Appointment cancelled successfully!', 'success')
    
    # Redirect based on user role
    if current_user.role == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    else:
        return redirect(url_for('admin_dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)



@app.route('/complete_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def complete_appointment(appointment_id):
    if current_user.role != 'doctor':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    # Check if the doctor owns this appointment
    if appointment.doctor_id != doctor.id:
        flash('You can only complete appointments assigned to you', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    # Update appointment status to Completed
    appointment.status = 'Completed'
    
    # Create treatment record
    treatment = Treatment(
        appointment_id=appointment.id,
        diagnosis=request.form['diagnosis'],
        prescription=request.form['prescription'],
        notes=request.form.get('notes', '')
    )
    
    db.session.add(treatment)
    db.session.commit()
    
    flash('Appointment marked as completed! Treatment details saved.', 'success')
    return redirect(url_for('doctor_dashboard'))





@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    stats = {
        'doctors': Doctor.query.filter_by(is_active=True).count(),
        'patients': Patient.query.filter_by(is_active=True).count(),
        'appointments': Appointment.query.count(),
        'departments': Department.query.count()
    }
    
    # Today's statistics
    today = date.today()
    today_stats = {
        'new_patients': Patient.query.filter(
            Patient.user.has(User.created_at >= datetime.combine(today, datetime.min.time()))
        ).count(),
        'todays_appointments': Appointment.query.filter_by(appointment_date=today).count(),
        'completed_appointments': Appointment.query.filter_by(
            appointment_date=today, 
            status='Completed'
        ).count()
    }
    
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         appointments=recent_appointments,
                         today_stats=today_stats)







@app.route('/admin/reset_database', methods=['POST'])
@login_required
def reset_database():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    try:
        db.drop_all()
        db.create_all()

        # recreate admin & departments
        create_tables()  

        flash('Database reset successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error while resetting database.', 'danger')
        print(e)

    return redirect(url_for('admin_dashboard'))



@app.route('/admin/reset_database', methods=['POST'])
@login_required
def reset_database():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    confirm_code = request.form.get('confirm_code', '').strip()
    if confirm_code != 'RESET':
        flash('Reset cancelled: confirmation text incorrect.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        # Drop all tables and recreate
        db.drop_all()
        db.create_all()
        # recreate admin & sample data (call your existing helper)
        create_tables()
        flash('Database reset successfully!', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Database reset failed')
        flash('Error while resetting database. See server logs.', 'danger')

    return redirect(url_for('admin_dashboard'))



# --- ADD THIS TO app.py (server-side) ---
from flask import current_app

@app.route('/admin/reset_database', methods=['POST'])
@login_required
def reset_database():
    # Only admin allowed
    if not current_user or current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    # Confirmation check
    confirm_code = request.form.get('confirm_code', '').strip()
    if confirm_code != 'RESET':
        flash('Reset cancelled: type RESET to confirm.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        # Drop all tables and recreate schema
        db.drop_all()
        db.create_all()

        # Re-create admin and default data (uses your helper)
        # Make sure create_tables() exists in your app.py
        create_tables()

        flash('Database reset successfully! Default admin and sample data recreated.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Database reset failed")
        flash('Error while resetting database. Check server logs.', 'danger')

    return redirect(url_for('admin_dashboard'))
# --- END ROUTE ---
