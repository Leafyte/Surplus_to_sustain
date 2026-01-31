from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import joblib
import os
from datetime import datetime, timedelta
import json
from functools import wraps
from prediction import predict_yield, get_confidence
USE_ML_PREDICTION = True

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database setup
def get_db():
    """Connect to SQLite database"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with enhanced tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            phone TEXT,
            full_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            profile_image TEXT DEFAULT 'default.png',
            user_type TEXT DEFAULT 'farmer',
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Crops table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            variety TEXT,
            area REAL NOT NULL,
            planting_date DATE NOT NULL,
            expected_harvest_date DATE,
            actual_harvest_date DATE,
            soil_type TEXT,
            irrigation_type TEXT,
            season TEXT,
            expected_consumption REAL,
            predicted_yield REAL,
            predicted_surplus REAL,
            actual_yield REAL,
            actual_surplus REAL,
            status TEXT DEFAULT 'planned',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES users (id)
        )
    ''')
    
    # Buyers table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            buyer_type TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            latitude REAL,
            longitude REAL,
            capacity_tons REAL,
            price_per_kg REAL,
            specialty_crops TEXT,
            rating REAL DEFAULT 0,
            total_transactions INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Transactions table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            quantity_tons REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            total_amount REAL NOT NULL,
            transaction_date DATE DEFAULT CURRENT_DATE,
            delivery_date DATE,
            status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'pending',
            rating INTEGER,
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crop_id) REFERENCES crops (id),
            FOREIGN KEY (buyer_id) REFERENCES buyers (id),
            FOREIGN KEY (farmer_id) REFERENCES users (id)
        )
    ''')
    
    # Storage bookings table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS storage_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            crop_id INTEGER NOT NULL,
            storage_hub_id INTEGER NOT NULL,
            quantity_tons REAL NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            cost_per_kg_month REAL,
            total_cost REAL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES users (id),
            FOREIGN KEY (crop_id) REFERENCES crops (id),
            FOREIGN KEY (storage_hub_id) REFERENCES buyers (id)
        )
    ''')
    
    # Waste flows table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waste_flows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            waste_type TEXT NOT NULL,
            quantity_tons REAL NOT NULL,
            destination_id INTEGER,
            processing_date DATE,
            co2_saved REAL,
            compost_generated REAL,
            status TEXT DEFAULT 'pending',
            qr_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crop_id) REFERENCES crops (id),
            FOREIGN KEY (farmer_id) REFERENCES users (id),
            FOREIGN KEY (destination_id) REFERENCES buyers (id)
        )
    ''')
    
    # Notifications table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            action_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Weather data cache (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            date DATE NOT NULL,
            temperature REAL,
            rainfall REAL,
            humidity REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(location, date)
        )
    ''')
    
    # Insert enhanced sample buyers
    cursor.execute("SELECT COUNT(*) as count FROM buyers")
    if cursor.fetchone()['count'] == 0:
        sample_buyers = [
            ('ABC Pickle Factory', 'Processor', '9988776655', 'abc@factory.com', 'Plot 45, MIDC Area', 'Nashik', 'Maharashtra', '422010', 19.9975, 73.7898, 50, 15, '["tomato", "onion", "chili"]', 4.5, 120),
            ('Green Valley Processing', 'Processor', '9988776656', 'info@greenvalley.com', 'Kharadi Industrial', 'Pune', 'Maharashtra', '411014', 18.5511, 73.9470, 80, 12, '["tomato", "potato", "cabbage"]', 4.2, 95),
            ('Fresh Storage Hub', 'Storage', '9988776657', 'storage@fresh.com', 'Cold Chain Complex', 'Nashik', 'Maharashtra', '422011', 20.0063, 73.7630, 100, 1.5, '["all"]', 4.7, 200),
            ('Hope Food Bank', 'NGO', '9988776658', 'hope@foodbank.org', 'Gandhi Nagar', 'Mumbai', 'Maharashtra', '400001', 18.9388, 72.8354, 30, 0, '["all"]', 4.9, 45),
            ('Metro Fresh Market', 'Retailer', '9988776659', 'metro@fresh.com', 'Market Yard', 'Pune', 'Maharashtra', '411037', 18.4977, 73.8536, 25, 18, '["tomato", "onion", "cabbage", "cauliflower"]', 4.3, 150),
            ('EcoCompost Solutions', 'Compost', '9988776660', 'eco@compost.com', 'Industrial Estate', 'Nashik', 'Maharashtra', '422007', 19.9872, 73.7840, 40, 2, '["all"]', 4.4, 80),
            ('Farm2Table Retail', 'Retailer', '9988776661', 'info@farm2table.com', 'Commercial Street', 'Mumbai', 'Maharashtra', '400020', 18.9647, 72.8258, 35, 20, '["all"]', 4.6, 180),
            ('Cattle Feed Industries', 'Animal Feed', '9988776662', 'cattle@feed.com', 'Hadapsar', 'Pune', 'Maharashtra', '411028', 18.5018, 73.9263, 60, 3, '["potato", "cabbage", "damaged"]', 4.1, 60),
            ('Premium Processors Ltd', 'Processor', '9988776663', 'premium@processors.com', 'MIDC Taloja', 'Navi Mumbai', 'Maharashtra', '410208', 19.0330, 73.1030, 100, 16, '["tomato", "chili"]', 4.5, 140),
            ('Community Cold Storage', 'Storage', '9988776664', 'community@storage.com', 'Viman Nagar', 'Pune', 'Maharashtra', '411014', 18.5679, 73.9143, 75, 1.2, '["all"]', 4.8, 220),
            ('Organic Waste Solutions', 'Compost', '9988776665', 'organic@waste.com', 'Bhosari', 'Pune', 'Maharashtra', '411026', 18.6298, 73.8502, 50, 2.5, '["all"]', 4.3, 70),
            ('City Fresh Supermarket', 'Retailer', '9988776666', 'city@fresh.com', 'Deccan Gymkhana', 'Pune', 'Maharashtra', '411004', 18.5196, 73.8553, 30, 19, '["all"]', 4.4, 160),
        ]
        cursor.executemany('''INSERT INTO buyers 
            (name, buyer_type, phone, email, address, city, state, pincode, latitude, longitude, 
             capacity_tons, price_per_kg, specialty_crops, rating, total_transactions) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', sample_buyers)
    
    conn.commit()
    conn.close()

#init_db()

# Load ML model
#MODEL_PATH = 'model.pkl'
#model = None
#if os.path.exists(MODEL_PATH):
#    try:
#       model = joblib.load(MODEL_PATH)
#    except:
#        print("Model couldn't be loaded. Using simple prediction.")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper Functions
def create_notification(user_id, title, message, notification_type='info', action_url=None):
    """Create a notification for user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO notifications (user_id, title, message, type, action_url)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, title, message, notification_type, action_url))
    conn.commit()
    conn.close()

def get_unread_notifications(user_id):
    """Get unread notifications count"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0',
                  (user_id,))
    count = cursor.fetchone()['count']
    conn.close()
    return count

def predict_yield_advanced(crop_name, area, soil_type, season, irrigation):
    """Enhanced prediction using ML module"""
    if USE_ML_PREDICTION:
        return predict_yield(
            crop_name=crop_name,
            area=area,
            soil_type=soil_type,
            season=season,
            irrigation_type=irrigation
        )
    else:
        return simple_prediction_enhanced(crop_name, area, irrigation)

def simple_prediction_enhanced(crop_name, area, irrigation='drip'):
    """Enhanced simple prediction"""
    avg_yields = {
        'tomato': 5.5, 'onion': 4.5, 'potato': 6.5, 'wheat': 3.5, 'rice': 5.0,
        'cabbage': 4.0, 'cauliflower': 3.8, 'brinjal': 4.2, 'chili': 2.5
    }
    
    irrigation_multiplier = {
        'drip': 1.2, 'sprinkler': 1.1, 'flood': 1.0, 'rainfed': 0.85
    }
    
    base_yield = avg_yields.get(crop_name.lower(), 4.0)
    multiplier = irrigation_multiplier.get(irrigation.lower(), 1.0)
    
    return area * base_yield * multiplier

def calculate_expected_harvest_date(planting_date, crop_name):
    """Calculate expected harvest date based on crop type"""
    growth_periods = {
        'tomato': 75, 'onion': 120, 'potato': 90, 'wheat': 120, 'rice': 120,
        'cabbage': 70, 'cauliflower': 75, 'brinjal': 60, 'chili': 80
    }
    
    days = growth_periods.get(crop_name.lower(), 90)
    harvest_date = datetime.strptime(planting_date, '%Y-%m-%d') + timedelta(days=days)
    return harvest_date.strftime('%Y-%m-%d')

def get_weather_forecast(location):
    """Simulate weather forecast (replace with real API in production)"""
    return {
        'temperature': 28.5,
        'rainfall': 450,
        'humidity': 65,
        'forecast': 'Favorable conditions for growth'
    }

# ==================== ROUTES ====================

@app.route('/')
def home():
    """Enhanced homepage"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE user_type = "farmer"')
    total_farmers = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM crops')
    total_crops = cursor.fetchone()['count']
    
    cursor.execute('SELECT SUM(predicted_surplus) as total FROM crops WHERE predicted_surplus IS NOT NULL')
    result = cursor.fetchone()
    total_surplus = result['total'] if result['total'] else 0
    
    cursor.execute('SELECT COUNT(*) as count FROM transactions')
    total_transactions = cursor.fetchone()['count']
    
    conn.close()
    
    return render_template('home.html',
                         total_farmers=total_farmers,
                         total_crops=total_crops,
                         total_surplus=round(total_surplus, 2),
                         total_transactions=total_transactions)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Enhanced registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        full_name = request.form.get('full_name', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', 'Maharashtra').strip()
        
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''INSERT INTO users 
                            (username, email, password, phone, full_name, city, state, last_login)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (username, email, hashed_password, phone, full_name, city, state, datetime.now()))
            conn.commit()
            user_id = cursor.lastrowid
            
            create_notification(user_id, 
                              'Welcome to Surplus-to-Sustain! 🌾',
                              'Start by adding your first crop to get surplus predictions.',
                              'success',
                              url_for('add_crop'))
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                flash('Username already exists. Please choose another.', 'danger')
            elif 'email' in str(e):
                flash('Email already registered. Please use another email.', 'danger')
            else:
                flash('Registration failed. Please try again.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                         (datetime.now(), user['id']))
            conn.commit()
            
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name'] or user['username']
            session['user_type'] = user['user_type']
            
            flash(f'Welcome back, {session["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
        
        conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''SELECT * FROM crops WHERE farmer_id = ? 
                     ORDER BY created_at DESC LIMIT 6''', 
                  (session['user_id'],))
    crops = cursor.fetchall()
    
    cursor.execute('''SELECT 
                        COUNT(*) as total_crops,
                        SUM(predicted_surplus) as total_surplus,
                        SUM(CASE WHEN predicted_surplus > 3 THEN 1 ELSE 0 END) as high_surplus_count,
                        SUM(predicted_yield) as total_yield
                      FROM crops WHERE farmer_id = ?''',
                  (session['user_id'],))
    stats = cursor.fetchone()
    
    cursor.execute('''SELECT t.*, b.name as buyer_name, c.crop_name
                     FROM transactions t
                     JOIN buyers b ON t.buyer_id = b.id
                     JOIN crops c ON t.crop_id = c.id
                     WHERE t.farmer_id = ?
                     ORDER BY t.created_at DESC LIMIT 5''',
                  (session['user_id'],))
    transactions = cursor.fetchall()
    
    cursor.execute('''SELECT * FROM notifications 
                     WHERE user_id = ? AND is_read = 0
                     ORDER BY created_at DESC LIMIT 5''',
                  (session['user_id'],))
    notifications = cursor.fetchall()
    
    conn.close()
    
    total_surplus = stats['total_surplus'] or 0
    total_saved = total_surplus * 0.75
    co2_prevented = total_saved * 2.5
    extra_income = total_saved * 1000 * 7
    
    return render_template('dashboard.html',
                         crops=crops,
                         total_crops=stats['total_crops'],
                         total_surplus=round(total_surplus, 2),
                         high_surplus_count=stats['high_surplus_count'],
                         total_saved=round(total_saved, 2),
                         co2_prevented=round(co2_prevented, 2),
                         extra_income=round(extra_income, 0),
                         transactions=transactions,
                         notifications=notifications,
                         unread_count=len(notifications))

@app.route('/add_crop', methods=['GET', 'POST'])
@login_required
def add_crop():
    if request.method == 'POST':
        crop_name = request.form['crop_name']
        variety = request.form.get('variety', '')
        area = float(request.form['area'])
        planting_date = request.form['planting_date']
        soil_type = request.form.get('soil_type', 'loamy')
        irrigation_type = request.form.get('irrigation_type', 'drip')
        season = request.form.get('season', 'kharif')
        expected_consumption = float(request.form.get('expected_consumption', 0))
        notes = request.form.get('notes', '')
        
        expected_harvest_date = calculate_expected_harvest_date(planting_date, crop_name)
        predicted_yield = predict_yield_advanced(crop_name, area, soil_type, season, irrigation_type)
        predicted_surplus = max(0, predicted_yield - expected_consumption)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO crops (farmer_id, crop_name, variety, area, planting_date, 
                             expected_harvest_date, soil_type, irrigation_type, season,
                             expected_consumption, predicted_yield, predicted_surplus, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], crop_name, variety, area, planting_date, 
              expected_harvest_date, soil_type, irrigation_type, season,
              expected_consumption, predicted_yield, predicted_surplus, notes, 'planned'))
        conn.commit()
        crop_id = cursor.lastrowid
        conn.close()
        
        if predicted_surplus > 3:
            create_notification(session['user_id'],
                              f'High Surplus Alert! 🚨',
                              f'Your {crop_name} crop has {predicted_surplus:.1f} tons predicted surplus. Take action now!',
                              'warning',
                              url_for('crop_detail', crop_id=crop_id))
        
        flash(f'Crop added! Predicted surplus: {predicted_surplus:.2f} tons', 'success')
        return redirect(url_for('crop_detail', crop_id=crop_id))
    
    return render_template('add_crop.html')

@app.route('/crop/<int:crop_id>')
@login_required
def crop_detail(crop_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM crops WHERE id = ? AND farmer_id = ?', 
                  (crop_id, session['user_id']))
    crop = cursor.fetchone()
    
    if not crop:
        flash('Crop not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    specialty_filter = f'%"{crop["crop_name"]}"%'
    cursor.execute('''SELECT * FROM buyers 
                     WHERE (specialty_crops LIKE ? OR specialty_crops LIKE '%"all"%')
                     AND is_verified = 1
                     ORDER BY rating DESC, total_transactions DESC
                     LIMIT 8''',
                  (specialty_filter,))
    buyers = cursor.fetchall()
    
    cursor.execute('''SELECT t.*, b.name as buyer_name
                     FROM transactions t
                     JOIN buyers b ON t.buyer_id = b.id
                     WHERE t.crop_id = ?
                     ORDER BY t.created_at DESC''',
                  (crop_id,))
    transactions = cursor.fetchall()
    
    weather = get_weather_forecast(crop['crop_name'])
    
    conn.close()
    
    surplus = crop['predicted_surplus'] or 0
    if surplus > 3:
        surplus_level = 'HIGH'
        surplus_class = 'danger'
        recommendations = [
            {'icon': '📞', 'title': 'Pre-book Processors', 'desc': 'Contact top-rated processors immediately', 'priority': 'high'},
            {'icon': '🏪', 'title': 'Reserve Storage', 'desc': 'Book community cold storage space now', 'priority': 'high'},
            {'icon': '🤝', 'title': 'Coordinate Donation', 'desc': 'Arrange NGO pickup for tax benefits', 'priority': 'medium'},
            {'icon': '♻️', 'title': 'Plan Composting', 'desc': 'Schedule waste-to-compost for remainder', 'priority': 'low'}
        ]
    elif surplus > 1:
        surplus_level = 'MODERATE'
        surplus_class = 'warning'
        recommendations = [
            {'icon': '🏪', 'title': 'Contact Markets', 'desc': 'Reach out to local retailers and markets', 'priority': 'high'},
            {'icon': '🏭', 'title': 'Find Processors', 'desc': 'Check with food processing units', 'priority': 'medium'},
            {'icon': '🤝', 'title': 'Consider Donation', 'desc': 'Donate excess for social impact', 'priority': 'low'}
        ]
    else:
        surplus_level = 'LOW'
        surplus_class = 'success'
        recommendations = [
            {'icon': '🛒', 'title': 'Normal Sale', 'desc': 'Proceed with regular market sale', 'priority': 'high'},
            {'icon': '💰', 'title': 'Best Price', 'desc': 'Wait for optimal market prices', 'priority': 'medium'}
        ]
    
    return render_template('crop_detail.html',
                         crop=crop,
                         buyers=buyers,
                         transactions=transactions,
                         weather=weather,
                         surplus_level=surplus_level,
                         surplus_class=surplus_class,
                         recommendations=recommendations)

@app.route('/crops')
@login_required
def crop_list():
    filter_status = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'recent')
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM crops WHERE farmer_id = ?'
    params = [session['user_id']]
    
    if filter_status != 'all':
        query += ' AND status = ?'
        params.append(filter_status)
    
    if sort_by == 'recent':
        query += ' ORDER BY created_at DESC'
    elif sort_by == 'surplus_high':
        query += ' ORDER BY predicted_surplus DESC'
    elif sort_by == 'harvest_date':
        query += ' ORDER BY expected_harvest_date ASC'
    
    cursor.execute(query, params)
    crops = cursor.fetchall()
    conn.close()
    
    return render_template('crop_list.html', crops=crops, filter_status=filter_status, sort_by=sort_by)

@app.route('/delete_crop/<int:crop_id>')
@login_required
def delete_crop(crop_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM crops WHERE id = ? AND farmer_id = ?', 
                  (crop_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Crop deleted successfully.', 'info')
    return redirect(url_for('crop_list'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/buyers')
@login_required
def buyers_list():
    """Buyers list page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM buyers WHERE is_verified = 1 ORDER BY rating DESC')
    buyers = cursor.fetchall()
    conn.close()
    return render_template('buyers_list.html', buyers=buyers)

@app.route('/impact')
@login_required
def impact():
    """Impact dashboard page"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''SELECT 
                        SUM(predicted_surplus) as total_surplus,
                        COUNT(*) as total_crops
                      FROM crops WHERE farmer_id = ?''',
                  (session['user_id'],))
    stats = cursor.fetchone()
    
    conn.close()
    
    total_surplus = stats['total_surplus'] or 0
    food_saved = total_surplus * 0.75
    co2_prevented = food_saved * 2.5
    compost_generated = total_surplus * 0.15
    
    return render_template('impact.html',
                         food_saved=round(food_saved, 2),
                         co2_prevented=round(co2_prevented, 2),
                         compost_generated=round(compost_generated, 2),
                         total_crops=stats['total_crops'])

@app.route('/notifications')
@login_required
def notifications_page():
    """Notifications page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM notifications 
                     WHERE user_id = ?
                     ORDER BY created_at DESC''',
                  (session['user_id'],))
    notifications = cursor.fetchall()
    conn.close()
    return render_template('notifications.html', notifications=notifications)

@app.route('/mark_notification_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
                  (notification_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('notifications_page'))

@app.route('/transactions')
@login_required
def transactions():
    """Transactions page"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''SELECT t.*, b.name as buyer_name, c.crop_name
                     FROM transactions t
                     JOIN buyers b ON t.buyer_id = b.id
                     JOIN crops c ON t.crop_id = c.id
                     WHERE t.farmer_id = ?
                     ORDER BY t.created_at DESC''',
                  (session['user_id'],))
    transactions = cursor.fetchall()
    conn.close()
    return render_template('transactions.html', transactions=transactions)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit profile page"""
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        pincode = request.form.get('pincode', '').strip()
        
        cursor.execute('''UPDATE users 
                         SET full_name = ?, email = ?, phone = ?, address = ?, city = ?, state = ?, pincode = ?
                         WHERE id = ?''',
                      (full_name, email, phone, address, city, state, pincode, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user)

@app.route('/update_crop_status/<int:crop_id>/<status>')
@login_required
def update_crop_status(crop_id, status):
    """Update crop status"""
    valid_statuses = ['planned', 'growing', 'harvested', 'sold']
    if status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('crop_detail', crop_id=crop_id))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE crops SET status = ?, updated_at = ? WHERE id = ? AND farmer_id = ?',
                  (status, datetime.now(), crop_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash(f'Crop status updated to {status}!', 'success')
    return redirect(url_for('crop_detail', crop_id=crop_id))

# API Endpoints
@app.route('/api/crop_stats')
@login_required
def api_crop_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''SELECT crop_name, COUNT(*) as count, SUM(predicted_surplus) as surplus
                     FROM crops WHERE farmer_id = ?
                     GROUP BY crop_name''',
                  (session['user_id'],))
    data = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in data])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)