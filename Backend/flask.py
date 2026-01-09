from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "scenthood_secret_key"

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/scenthood'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= MODELS =================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

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
    perfume_name = db.Column(db.String(100))
    mood = db.Column(db.String(50))
    occasion = db.Column(db.String(50))
    time = db.Column(db.String(50))
    weather = db.Column(db.String(50))
    date = db.Column(db.DateTime, default=datetime.utcnow)

# ================= ROUTES =================

@app.route('/')
def landing():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        user = User(name=request.form['name'], email=request.form['email'], password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    perfumes = Perfume.query.filter_by(user_id=session['user_id']).all()
    history = RecommendationHistory.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', perfumes=perfumes, history=history)

@app.route('/collections', methods=['GET', 'POST'])
def collections():
    if request.method == 'POST':
        for i in range(len(request.form.getlist('brand'))):
            perfume = Perfume(
                user_id=session['user_id'],
                brand=request.form.getlist('brand')[i],
                name=request.form.getlist('name')[i],
                notes=request.form.getlist('notes')[i],
                scent_type=request.form.getlist('scent')[i]
            )
            db.session.add(perfume)
        db.session.commit()
        return redirect(url_for('discover'))
    return render_template('collections.html')

@app.route('/discover', methods=['GET', 'POST'])
def discover():
    if request.method == 'POST':
        # Simple AI logic placeholder
        perfume = Perfume.query.filter_by(user_id=session['user_id']).first()
        history = RecommendationHistory(
            user_id=session['user_id'],
            perfume_name=perfume.name,
            mood=request.form['mood'],
            occasion=request.form['occasion'],
            time=request.form['time'],
            weather=request.form['weather']
        )
        db.session.add(history)
        db.session.commit()
        return redirect(url_for('recommendation'))
    return render_template('discover.html')

@app.route('/recommendation')
def recommendation():
    perfumes = Perfume.query.filter_by(user_id=session['user_id']).all()
    return render_template('recommendation.html', perfumes=perfumes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)