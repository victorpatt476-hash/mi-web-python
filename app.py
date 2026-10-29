import os
from flask import Flask, render_template, request, redirect, url_for
import psycopg2

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    if not DATABASE_URL:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabla de visitas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id SERIAL PRIMARY KEY,
            page_views INT DEFAULT 0
        );
    ''')
    cur.execute('SELECT COUNT(*) FROM stats;')
    if cur.fetchone()[0] == 0:
        cur.execute('INSERT INTO stats (page_views) VALUES (0);')
    
    # Tabla de suscriptores
    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Tabla de trades / operaciones
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            asset VARCHAR(50) NOT NULL,
            type VARCHAR(10) NOT NULL,
            entry_price NUMERIC NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"Error inicializando base de datos: {e}")

@app.route('/')
def home():
    views = 0
    if DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('UPDATE stats SET page_views = page_views + 1 WHERE id = 1 RETURNING page_views;')
            views = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error al actualizar contador: {e}")
            
    return render_template('index.html', visits=views)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    if email and DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO subscribers (email) VALUES (%s) ON CONFLICT (email) DO NOTHING;', (email,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error guardando email: {e}")
    return redirect(url_for('home'))

@app.route('/trading')
def trading():
    trades = []
    if DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, asset, type, entry_price, created_at FROM trades ORDER BY id DESC;')
            trades = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error cargando trades: {e}")
    return render_template('trading.html', trades=trades)

@app.route('/trading/add', methods=['POST'])
def add_trade():
    asset = request.form.get('asset')
    t_type = request.form.get('type')
    entry = request.form.get('entry_price')
    if asset and t_type and entry and DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO trades (asset, type, entry_price) VALUES (%s, %s, %s);', (asset, t_type, entry))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error guardando trade: {e}")
    return redirect(url_for('trading'))

@app.route('/tools')
def tools():
    return render_template('tools.ht





