from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

# ===== Flask App Setup =====
app = Flask(__name__, template_folder='../templates')  # templates folder is one level up
app.secret_key = "scenthood_secret_key"

# ===== Database Config =====
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/scenthood'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ===== Models =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    perfumes = db.relationship('Perfume', backref='owner', lazy=True)
    history = db.relationship('RecommendationHistory', backref='user', lazy=True)

class Perfume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    brand = db.Column(db.String(100))
    name = db.Column(db.String(100))
    notes = db.Column(db.String(200))
    scent_type = db.Column(db.String(50))

class RecommendationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    perfume_id = db.Column(db.Integer, db.ForeignKey('perfume.id'), nullable=True)
    mood = db.Column(db.String(50))
    occasion = db.Column(db.String(50))
    time = db.Column(db.String(50))
    weather = db.Column(db.String(50))
    ai_reason = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# ===== Create Tables =====
with app.app_context():
    db.create_all()

# ===== Routes =====

# Landing Page
@app.route('/')
def landing():
    return render_template('index.html')

# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            return "Passwords do not match!"

        if User.query.filter_by(email=email).first():
            return "Email already registered!"

        hashed_pw = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('registration.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials!"

    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    perfumes = Perfume.query.filter_by(user_id=user_id).all()
    history = RecommendationHistory.query.filter_by(user_id=user_id).order_by(RecommendationHistory.date.desc()).all()
    return render_template('dashboard.html', perfumes=perfumes, history=history)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Perfume Collection Page
@app.route('/collections', methods=['GET', 'POST'])
def collections():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        brand = request.form['brand']
        notes = request.form['notes']
        scent_type = request.form['scent_type']

        perfume = Perfume(user_id=session['user_id'], name=name, brand=brand, notes=notes, scent_type=scent_type)
        db.session.add(perfume)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('collections.html')

# Discover / Mood Questionnaire
@app.route('/discover', methods=['GET', 'POST'])
def discover():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        mood = request.form['mood']
        occasion = request.form['occasion']
        time_of_day = request.form['time']
        weather = request.form['weather']

        user_perfumes = Perfume.query.filter_by(user_id=session['user_id']).all()
        recommended = []
        if user_perfumes:
            recommended.append(random.choice(user_perfumes).name)

        # Save to history
        for perfume_name in recommended:
            history = RecommendationHistory(
                user_id=session['user_id'],
                mood=mood,
                occasion=occasion,
                time=time_of_day,
                weather=weather
            )
            db.session.add(history)
        db.session.commit()

        session['recommended'] = recommended
        return redirect(url_for('recommendation'))

    return render_template('discover.html')

# Recommendation Page
@app.route('/recommendation')
def recommendation():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    recommended_perfumes = session.get('recommended', [])
    return render_template('recommendation.html', perfumes=recommended_perfumes)

# ===== Run App =====
if __name__ == '__main__':
    app.run(debug=True)