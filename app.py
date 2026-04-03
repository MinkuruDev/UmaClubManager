import os
import csv
import sqlite3
import firebase_admin
from werkzeug.utils import secure_filename
from util import process_fan_data
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize Firebase
try:
    cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    db = None

# Initialize SQLite functions
def get_sqlite_db():
    conn = sqlite3.connect('backup.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    conn = get_sqlite_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            ingame_id TEXT PRIMARY KEY,
            ingame_name TEXT NOT NULL,
            discord_id TEXT,
            discord_username TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS fan_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT NOT NULL,
            day_start INTEGER NOT NULL,
            day_end INTEGER NOT NULL,
            daily_fan INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS member_exemptions (
            ingame_id TEXT PRIMARY KEY,
            reason TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS member_extras (
            ingame_id TEXT,
            month_year TEXT,
            extra INTEGER,
            PRIMARY KEY(ingame_id, month_year)
        )
    ''')
    conn.commit()
    conn.close()

# Auto-initialize sqlite on load
init_sqlite()

@app.route('/')
def index():
    members = []
    if db:
        try:
            users_ref = db.collection('members')
            docs = users_ref.stream()
            for doc in docs:
                data = doc.to_dict()
                data['firebase_id'] = doc.id
                members.append(data)
        except Exception as e:
            print(f"Error reading from Firebase: {e}")
            # Fallback to local sqlite
            conn = get_sqlite_db()
            members_rows = conn.execute('SELECT * FROM members').fetchall()
            members = [dict(row) for row in members_rows]
            conn.close()
    else:
        # Fallback to local sqlite
        conn = get_sqlite_db()
        members_rows = conn.execute('SELECT * FROM members').fetchall()
        members = [dict(row) for row in members_rows]
        conn.close()

    return render_template('index.html', members=members)

@app.route('/add', methods=['POST'])
def add_member():
    ingame_id = request.form.get('ingame_id')
    ingame_name = request.form.get('ingame_name')
    discord_id = request.form.get('discord_id')
    discord_username = request.form.get('discord_username')

    data = {
        'ingame_id': ingame_id,
        'ingame_name': ingame_name,
        'discord_id': discord_id,
        'discord_username': discord_username
    }

    # Save to Firebase
    if db:
        try:
            # We'll use the ingame_id as the document ID for uniqueness
            db.collection('members').document(ingame_id).set(data)
        except Exception as e:
            print(f"Error writing to Firebase: {e}")

    # Backup to SQLite
    try:
        conn = get_sqlite_db()
        conn.execute('''
            INSERT OR REPLACE INTO members (ingame_id, ingame_name, discord_id, discord_username)
            VALUES (?, ?, ?, ?)
        ''', (ingame_id, ingame_name, discord_id, discord_username))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error writing to SQLite: {e}")

    return redirect(url_for('index'))

@app.route('/delete/<ingame_id>', methods=['POST'])
def delete_member(ingame_id):
    # Delete from Firebase
    if db:
        try:
            db.collection('members').document(ingame_id).delete()
        except Exception as e:
            print(f"Error deleting from Firebase: {e}")

    # Delete from SQLite backup
    try:
        conn = get_sqlite_db()
        conn.execute('DELETE FROM members WHERE ingame_id = ?', (ingame_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error deleting from SQLite: {e}")

    return redirect(url_for('index'))

@app.route('/fans')
def fans():
    month = request.args.get('month')
    fan_data_dir = 'fan_data'
    os.makedirs(fan_data_dir, exist_ok=True)
    
    # Get available months
    available_months = []
    for f in os.listdir(fan_data_dir):
        if f.endswith('.csv'):
            available_months.append(f.replace('.csv', ''))
    available_months.sort(reverse=True)

    reqs = []
    latest_day = 0
    fan_rows = []

    if month:
        reqs, latest_day, fan_rows = process_fan_data(month, fan_data_dir=fan_data_dir, db_path='backup.db')

    return render_template('fans.html', 
        available_months=available_months, 
        selected_month=month, 
        reqs=reqs,
        latest_day=latest_day,
        fan_rows=fan_rows
    )

@app.route('/add_requirement', methods=['POST'])
def add_requirement():
    month = request.form.get('month')
    try:
        day_start = int(request.form.get('day_start'))
        day_end = int(request.form.get('day_end'))
        daily_fan = int(request.form.get('daily_fan'))
        
        conn = get_sqlite_db()
        conn.execute('''
            INSERT INTO fan_requirements (month_year, day_start, day_end, daily_fan)
            VALUES (?, ?, ?, ?)
        ''', (month, day_start, day_end, daily_fan))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding requirement: {e}")

    return redirect(url_for('fans', month=month))

@app.route('/delete_requirement/<int:req_id>', methods=['POST'])
def delete_requirement(req_id):
    month = request.args.get('month')
    try:
        conn = get_sqlite_db()
        conn.execute('DELETE FROM fan_requirements WHERE id = ?', (req_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error deleting requirement: {e}")
        
    return redirect(url_for('fans', month=month))

@app.route('/set_exemption', methods=['POST'])
def set_exemption():
    month = request.args.get('month')
    ingame_id = request.form.get('ingame_id')
    reason = request.form.get('reason')
    
    try:
        conn = get_sqlite_db()
        if reason:
            conn.execute('''
                INSERT OR REPLACE INTO member_exemptions (ingame_id, reason)
                VALUES (?, ?)
            ''', (ingame_id, reason))
        else:
            conn.execute('DELETE FROM member_exemptions WHERE ingame_id = ?', (ingame_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error handling exemption: {e}")
        
    return redirect(url_for('fans', month=month))

@app.route('/set_extra', methods=['POST'])
def set_extra():
    month = request.args.get('month')
    ingame_id = request.form.get('ingame_id')
    extra_str = request.form.get('extra')
    
    try:
        conn = get_sqlite_db()
        if extra_str and extra_str.strip() and extra_str.lstrip('-').isdigit():
            extra = int(extra_str)
            conn.execute('''
                INSERT OR REPLACE INTO member_extras (ingame_id, month_year, extra)
                VALUES (?, ?, ?)
            ''', (ingame_id, month, extra))
        else:
            conn.execute('DELETE FROM member_extras WHERE ingame_id = ? AND month_year = ?', (ingame_id, month))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error handling extra: {e}")
        
    return redirect(url_for('fans', month=month))

@app.route('/send_discord', methods=['POST'])
def send_discord():
    month = request.args.get('month')
    if not month:
        return redirect(url_for('fans'))
        
    import json
    fan_rows_json = request.form.get('fan_rows_json')
    if fan_rows_json:
        fan_rows = json.loads(fan_rows_json)
        webhook_url = os.environ.get("DISCORD_WEBHOOK")
        from discord_bot import send_fan_report
        send_fan_report(fan_rows, webhook_url)
        
    return redirect(url_for('fans', month=month))

@app.route('/upload_fans', methods=['POST'])
def upload_fans():
    year = request.form.get('year')
    month = request.form.get('month')
    file = request.files.get('file')

    if year and month and file and file.filename.endswith('.csv'):
        month_str = str(month).zfill(2)
        filename = f"{year}{month_str}.csv"
        
        fan_data_dir = 'fan_data'
        os.makedirs(fan_data_dir, exist_ok=True)
        filepath = os.path.join(fan_data_dir, filename)
        file.save(filepath)
        return redirect(url_for('fans', month=f"{year}{month_str}"))

    return redirect(url_for('fans'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
