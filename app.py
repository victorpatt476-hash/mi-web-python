import os
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.getenv('SECRET_KEY', 'super-secret-key-blue-demon-2026')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if not DATABASE_URL:
        return None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, username FROM users WHERE id = %s;', (user_id,))
        u = cur.fetchone()
        cur.close()
        conn.close()
        if u:
            return User(u[0], u[1])
    except Exception as e:
        print(f"Error cargando usuario: {e}")
    return None

def init_db():
    if not DATABASE_URL:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('CREATE TABLE IF NOT EXISTS stats (id SERIAL PRIMARY KEY, page_views INT DEFAULT 0);')
    cur.execute('SELECT COUNT(*) FROM stats;')
    if cur.fetchone()[0] == 0:
        cur.execute('INSERT INTO stats (page_views) VALUES (0);')
    
    cur.execute('CREATE TABLE IF NOT EXISTS subscribers (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    cur.execute('CREATE TABLE IF NOT EXISTS trades (id SERIAL PRIMARY KEY, asset VARCHAR(50) NOT NULL, type VARCHAR(10) NOT NULL, entry_price NUMERIC NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    cur.execute('CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL);')
    
    # Nuevas tablas para bots e inteligencia
    cur.execute("CREATE TABLE IF NOT EXISTS instagram_queue (id SERIAL PRIMARY KEY, media_title VARCHAR(255), status VARCHAR(50) DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    cur.execute('CREATE TABLE IF NOT EXISTS global_intel (id SERIAL PRIMARY KEY, keyword VARCHAR(255), data_snippet TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    cur.execute('CREATE TABLE IF NOT EXISTS security_logs (id SERIAL PRIMARY KEY, event_type VARCHAR(100), details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')

    cur.execute('SELECT COUNT(*) FROM users WHERE username = %s;', ('admin',))
    if cur.fetchone()[0] == 0:
        hashed_pw = generate_password_hash('bluedemon2026')
        cur.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s);', ('admin', hashed_pw))

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
@login_required
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
@login_required
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
@login_required
def tools():
    ig_posts = []
    intel_data = []
    sec_logs = []
    if DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, media_title, status, created_at FROM instagram_queue ORDER BY id DESC LIMIT 5;')
            ig_posts = cur.fetchall()
            cur.execute('SELECT id, keyword, data_snippet, created_at FROM global_intel ORDER BY id DESC LIMIT 5;')
            intel_data = cur.fetchall()
            cur.execute('SELECT id, event_type, details, created_at FROM security_logs ORDER BY id DESC LIMIT 5;')
            sec_logs = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error cargando herramientas: {e}")
    return render_template('tools.html', ig_posts=ig_posts, intel_data=intel_data, sec_logs=sec_logs)

@app.route('/tools/ig/add', methods=['POST'])
@login_required
def add_ig_post():
    title = request.form.get('title')
    if title and DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO instagram_queue (media_title, status) VALUES (%s, %s);", (title, 'Ready to Upload'))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error en IG queue: {e}")
    return redirect(url_for('tools'))

@app.route('/tools/intel/add', methods=['POST'])
@login_required
def add_intel():
    keyword = request.form.get('keyword')
    snippet = request.form.get('snippet')
    if keyword and snippet and DATABASE_URL:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO global_intel (keyword, data_snippet) VALUES (%s, %s);', (keyword, snippet))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error en Intel: {e}")
    return redirect(url_for('tools'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if DATABASE_URL:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('SELECT id, username, password_hash FROM users WHERE username = %s;', (username,))
                user_data = cur.fetchone()
                
                if user_data and check_password_hash(user_data[2], password):
                    cur.execute('INSERT INTO security_logs (event_type, details) VALUES (%s, %s);', ('SUCCESSFUL_LOGIN', f'User {username} logged in.'))
                    conn.commit()
                    cur.close()
                    conn.close()

                    user_obj = User(user_data[0], user_data[1])
                    login_user(user_obj)
                    return redirect(url_for('trading'))
                else:
                    cur.execute('INSERT INTO security_logs (event_type, details) VALUES (%s, %s);', ('FAILED_LOGIN', f'Failed attempt for: {username}'))
                    conn.commit()
                    cur.close()
                    conn.close()
                    flash('Usuario o contraseña incorrectos', 'danger')
            except Exception as e:
                print(f"Error en login: {e}")
                
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
