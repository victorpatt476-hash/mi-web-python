import os
from flask import Flask, render_template, request, redirect, url_for
import psycopg2

app = Flask(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    if not DATABASE_URL:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabla de contador
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
