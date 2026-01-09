from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# ======================
# APP SETUP
# ======================

app = Flask(__name__)
app.secret_key = "scenthood_secret_key"

# ======================
# DATABASE CONFIG
# ======================

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@localhost/scenthood'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ======================
# MODELS
# ======================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    perfumes = db.relationship('Perfume', backref='owner', lazy=True)
    history = db.relationship('RecommendationHistory', backref='user', lazy=True)


class Perfume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    brand = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(200))        # comma separated
    scent_type = db.Column(db.String(50))    # woody, fresh, spicy, etc.


class RecommendationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    perfume_id = db.Column(db.Integer, db.ForeignKey('perfume.id'), nullable=False)

    mood = db.Column(db.String(50))
    occasion = db.Column(db.String(50))
    time_of_day = db.Column(db.String(50))
    weather = db.Column(db.String(50))

    confidence = db.Column(db.Float)
    ai_reason = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ======================
# UTILITY: AUTH CHECK
# ======================

def login_required():
    return 'user_id' in session

# ======================
# RECOMMENDATION ENGINE
# ======================

def recommend_perfume(perfumes, mood, occasion, time_of_day, weather):
    best_score = -1
    best_perfume = None
    best_reason = ""

    for p in perfumes:
        score = 0.0
        reasons = []

        scent = (p.scent_type or "").lower()
        notes = (p.notes or "").lower()

        if mood == "confident" and "woody" in scent:
            score += 0.3
            reasons.append("woody scents boost confidence")

        if mood == "romantic" and "sweet" in notes:
            score += 0.3
            reasons.append("sweet notes feel romantic")

        if occasion == "office" and "fresh" in scent:
            score += 0.2
            reasons.append("fresh scents suit office wear")

        if time_of_day == "evening" and "spicy" in notes:
            score += 0.2
            reasons.append("spicy notes work well in evenings")

        if weather == "cool" and "amber" in notes:
            score += 0.2
            reasons.append("amber notes perform well in cool weather")

        if score > best_score:
            best_score = score
            best_perfume = p
            best_reason = ", ".join(reasons) if reasons else "Balanced everyday scent"

    return best_perfume, round(best_score, 2), best_reason

# ======================
# ROUTES
# ======================

@app.route('/')
def landing():
    return render_template('index.html')

# ---------- REGISTER ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        existing = User.query.filter_by(email=request.form['email']).first()
        if existing:
            return "Email already registered"

        hashed_pw = generate_password_hash(request.form['password'])

        user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=hashed_pw
        )
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# ---------- LOGIN ----------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()

        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))

        return "Invalid credentials"

    return render_template('login.html')

# ---------- DASHBOARD ----------

@app.route('/dashboard')
def dashboard():
    if not login_required():
        return redirect(url_for('login'))

    perfumes = Perfume.query.filter_by(user_id=session['user_id']).all()
    history = RecommendationHistory.query.filter_by(
        user_id=session['user_id']
    ).order_by(RecommendationHistory.created_at.desc()).all()

    return render_template('dashboard.html', perfumes=perfumes, history=history)

# ---------- COLLECTIONS ----------

@app.route('/collections', methods=['GET', 'POST'])
def collections():
    if not login_required():
        return redirect(url_for('login'))

    if request.method == 'POST':
        brand = request.form['brand']
        name = request.form['name']
        notes = request.form['notes']
        scent = request.form['scent']

        perfume = Perfume(
            user_id=session['user_id'],
            brand=brand,
            name=name,
            notes=notes,
            scent_type=scent
        )
        db.session.add(perfume)
        db.session.commit()

        return redirect(url_for('collections'))

    perfumes = Perfume.query.filter_by(user_id=session['user_id']).all()
    return render_template('collections.html', perfumes=perfumes)

# ---------- DISCOVER ----------

@app.route('/discover', methods=['GET', 'POST'])
def discover():
    if not login_required():
        return redirect(url_for('login'))

    if request.method == 'POST':
        mood = request.form['mood']
        occasion = request.form['occasion']
        time_of_day = request.form['time']
        weather = request.form['weather']

        perfumes = Perfume.query.filter_by(user_id=session['user_id']).all()
        if not perfumes:
            return "No perfumes in collection"

        best_perfume, confidence, reason = recommend_perfume(
            perfumes, mood, occasion, time_of_day, weather
        )

        history = RecommendationHistory(
            user_id=session['user_id'],
            perfume_id=best_perfume.id,
            mood=mood,
            occasion=occasion,
            time_of_day=time_of_day,
            weather=weather,
            confidence=confidence,
            ai_reason=reason
        )

        db.session.add(history)
        db.session.commit()

        session['last_recommendation_id'] = history.id
        return redirect(url_for('recommendation'))

    return render_template('discover.html')

# ---------- RECOMMENDATION ----------

@app.route('/recommendation')
def recommendation():
    if not login_required():
        return redirect(url_for('login'))

    history_id = session.get('last_recommendation_id')
    if not history_id:
        return redirect(url_for('dashboard'))

    history = RecommendationHistory.query.get(history_id)
    perfume = Perfume.query.get(history.perfume_id)

    return render_template(
        'recommendation.html',
        perfume=perfume,
        confidence=history.confidence,
        reason=history.ai_reason
    )

# ---------- LOGOUT ----------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ======================
# RUN
# ======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)