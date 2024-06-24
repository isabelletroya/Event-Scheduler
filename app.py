from flask import Flask, render_template, redirect, url_for, request
import psycopg2
import webbrowser
from threading import Timer

app = Flask(__name__)

# Database connection configuration
db_config = {
    "host": "localhost",
    "database": "Scheduling",
    "user": "postgres",
    "password": "sebastian2001",
}

def connect_to_db():
    conn = psycopg2.connect(**db_config)
    return conn

# Route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = connect_to_db()
        cursor = conn.cursor()
        
        # Example validation (replace with actual logic)
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            return redirect(url_for('index'))  # Redirect to home page after login
    return render_template('login.html', error=error)

# Route for registration page
@app.route('/new_register')
def new_register():
    return render_template('new_register.html')

# Route for home page
@app.route('/')
def index():
    conn = connect_to_db()
    cursor = conn.cursor()

    # Example query to fetch data
    cursor.execute("SELECT * FROM event_scheduling.users;")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('index.html', data=data)

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/login')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True)
