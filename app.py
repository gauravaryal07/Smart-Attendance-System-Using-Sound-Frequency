import pyotp, qrcode, numpy as np, sounddevice as sd
import threading, time, sys, os
import pandas as pd
from flask import Flask, request, jsonify, send_file, render_template
from database import db, User, Attendance, bcrypt

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt.init_app(app)

SECRET_KEY = "SUPERSECRETBASE32KEY"
FREQ = 18000
FS = 44100
totp = pyotp.TOTP(SECRET_KEY, interval=30)
keep_beeping = True

# --- Sound Beacon Logic ---
def run_beacon():
    global keep_beeping
    while True:
        token = totp.now()
        if not os.path.exists('static'): os.makedirs('static')
        qrcode.make(token).save("static/current_qr.png")
        
        start_time = time.time()
        while time.time() - start_time < 30:
            if keep_beeping:
                duration = 0.2
                t = np.linspace(0, duration, int(FS * duration), False)
                envelope = np.hanning(len(t))
                tone = 0.35 * np.sin(FREQ * t * 2 * np.pi) * envelope
                sd.play(tone, FS)
                time.sleep(0.3)
            else:
                sd.stop()
                time.sleep(1)

# --- Routes ---

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/setup')
def setup():
    db.create_all()
    if not User.query.filter_by(username="gaurav").first():
        u = User(id=101, username="gaurav", name="Gaurav Aryal")
        u.set_password("pass123")
        db.session.add(u)
        db.session.commit()
    return "Database and Admin User Ready."

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        return jsonify({"status": "success", "user_id": user.id, "name": user.name})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/mark_present', methods=['POST'])
def mark_present():
    global keep_beeping
    data = request.json
    user_id, token, method = data.get('user_id'), data.get('token'), data.get('method')

    if totp.verify(token, valid_window=1):
        keep_beeping = False  # STOP BEEPING ON SUCCESS
        today = time.strftime('%Y-%m-%d')
        existing = Attendance.query.filter_by(user_id=user_id, date=today).first()
        
        if not existing:
            new_entry = Attendance(user_id=user_id, method=method)
            db.session.add(new_entry)
            db.session.commit()
            return jsonify({"status": "success", "message": f"Present via {method}"})
        return jsonify({"status": "already_marked", "message": "Already marked"})
    
    return jsonify({"status": "error", "message": "Invalid Token"}), 400

@app.route('/clear_attendance', methods=['POST', 'GET'])
def clear_attendance():
    try:
        db.session.query(Attendance).delete()
        db.session.commit()
        return jsonify({"status": "success", "message": "Records cleared!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/export_attendance_json')
def export_attendance_json():
    records = db.session.query(Attendance.user_id, User.name, Attendance.timestamp, Attendance.method).join(User).all()
    return jsonify([{"ID": r[0], "Name": r[1], "Timestamp": r[2].isoformat(), "Method": r[3]} for r in records])

@app.route('/reset_beacon', methods=['POST', 'GET'])
def reset_beacon():
    global keep_beeping
    keep_beeping = True
    return jsonify({"status": "Beeping resumed"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    threading.Thread(target=run_beacon, daemon=True).start()
    app.run(port=5000, debug=False)