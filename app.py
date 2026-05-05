import os
from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    future_opportunities = db.Column(db.Text, nullable=False)
    max_applicants = db.Column(db.String(100), nullable=True)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('admin.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not name or not email or not password:
        return jsonify({'error': 'Missing fields'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
    if Admin.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
        
    hashed_pw = generate_password_hash(password)
    new_admin = Admin(name=name, email=email, password=hashed_pw)
    db.session.add(new_admin)
    db.session.commit()
    
    return jsonify({'message': 'Account created successfully'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', False)
    
    admin = Admin.query.filter_by(email=email).first()
    if not admin or not check_password_hash(admin.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401
        
    session['admin_id'] = admin.id
    if remember:
        session.permanent = True
    
    return jsonify({'message': 'Login successful', 'email': admin.email})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('admin_id', None)
    return jsonify({'message': 'Logged out'})

@app.route('/api/forgot', methods=['POST'])
def forgot():
    data = request.json
    email = data.get('email')
    admin = Admin.query.filter_by(email=email).first()
    if admin:
        token = str(uuid.uuid4())
        admin.reset_token = token
        admin.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        print(f"Password reset link for {email}: http://127.0.0.1:5000/api/reset/{token}")
    return jsonify({'message': 'If an account exists, a reset link was sent.'})

@app.route('/api/opportunities', methods=['GET'])
def get_opportunities():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin_id = session['admin_id']
    opps = Opportunity.query.filter_by(admin_id=admin_id).all()
    
    return jsonify([{
        'id': o.id,
        'name': o.name,
        'duration': o.duration,
        'start_date': o.start_date,
        'description': o.description,
        'skills': o.skills,
        'category': o.category,
        'future_opportunities': o.future_opportunities,
        'max_applicants': o.max_applicants
    } for o in opps])

@app.route('/api/opportunities', methods=['POST'])
def add_opportunity():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    required_fields = ['name', 'duration', 'start_date', 'description', 'skills', 'category', 'future_opportunities']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Missing {field}'}), 400
            
    opp = Opportunity(
        admin_id=session['admin_id'],
        name=data['name'],
        duration=data['duration'],
        start_date=data['start_date'],
        description=data['description'],
        skills=data['skills'],
        category=data['category'],
        future_opportunities=data['future_opportunities'],
        max_applicants=data.get('max_applicants')
    )
    db.session.add(opp)
    db.session.commit()
    return jsonify({'message': 'Opportunity added successfully'})

@app.route('/api/opportunities/<int:id>', methods=['PUT'])
def edit_opportunity(id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    opp = Opportunity.query.filter_by(id=id, admin_id=session['admin_id']).first()
    if not opp:
        return jsonify({'error': 'Not found'}), 404
        
    data = request.json
    for key in ['name', 'duration', 'start_date', 'description', 'skills', 'category', 'future_opportunities']:
        if data.get(key):
            setattr(opp, key, data[key])
            
    if 'max_applicants' in data:
        opp.max_applicants = data['max_applicants']
        
    db.session.commit()
    return jsonify({'message': 'Opportunity updated successfully'})

@app.route('/api/opportunities/<int:id>', methods=['DELETE'])
def delete_opportunity(id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    opp = Opportunity.query.filter_by(id=id, admin_id=session['admin_id']).first()
    if not opp:
        return jsonify({'error': 'Not found'}), 404
        
    db.session.delete(opp)
    db.session.commit()
    return jsonify({'message': 'Opportunity deleted successfully'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
