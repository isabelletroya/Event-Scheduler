from flask import Flask, render_template
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
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True)
