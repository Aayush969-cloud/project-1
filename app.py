from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config.from_object('config.Config')

# Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Dummy user database for simplicity
users_db = {
    "user1": {
        "password": generate_password_hash("securepassword123"),
        "email_verified": True
    }
}

pending_verification = {}  # Temporary store for unverified users

# Home route
@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

# Login route with rate limiting
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Limits login attempts to 5 per minute
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users_db:
            user = users_db[username]
            if not user['email_verified']:
                flash('Email not verified. Please verify before logging in.', 'danger')
                return redirect(url_for('login'))
            
            if check_password_hash(user['password'], password):
                session['username'] = username
                flash('Login successful', 'success')
                return redirect(url_for('home'))
        
        flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        if username in users_db:
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        if not validate_input(username):
            flash('Invalid username. Only alphanumeric and underscores are allowed.', 'danger')
            return redirect(url_for('register'))
        
        verification_code = send_verification_email(email)
        pending_verification[username] = {
            "password": generate_password_hash(password),
            "email": email,
            "verification_code": verification_code
        }
        
        flash('A verification email has been sent. Please verify your email.', 'info')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Email verification route
@app.route('/verify_email/<username>/<code>')
def verify_email(username, code):
    if username in pending_verification:
        user = pending_verification[username]
        if user['verification_code'] == code:
            users_db[username] = {
                "password": user['password'],
                "email_verified": True
            }
            pending_verification.pop(username)
            flash('Email verified successfully. You can now log in.', 'success')
            return redirect(url_for('login'))
    
    flash('Invalid or expired verification link.', 'danger')
    return redirect(url_for('register'))

# Input validation (simple example)
def validate_input(data):
    if re.match(r'^[A-Za-z0-9_]+$', data):
        return True
    return False

# Send verification email
def send_verification_email(email):
    sender_email = "your_email@example.com"
    sender_password = "your_email_password"
    verification_code = "12345"  # Replace with a random generator for production
    verification_link = f"http://127.0.0.1:5000/verify_email/{email}/{verification_code}"
    
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = email
    message['Subject'] = "Verify Your Email"
    
    body = f"Click the following link to verify your email: {verification_link}"
    message.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, message.as_string())
        server.quit()
        return verification_code
    except Exception as e:
        print("Error sending email:", e)
        return None

if __name__ == '__main__':
    app.run(debug=True)
