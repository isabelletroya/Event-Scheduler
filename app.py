from flask import Flask, render_template, redirect, url_for, request
import psycopg2
import webbrowser
from threading import Timer
import random
import string

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

def user_info_check(username, password):
    conn = connect_to_db()
    cursor = conn.cursor()
    
    info_query = "SELECT * FROM event_scheduling.users WHERE user_id = %s AND password = %s;"
    cursor.execute(info_query, (username, password))
    
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result

# Route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_info = user_info_check(username, password)
        
        if user_info:
            return redirect(url_for('index'))  # Redirect to home page after successful login
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

# Route for registration page
@app.route('/new_register', methods=['GET', 'POST'])
def new_register():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        name = request.form['name']
        birthday = request.form['birthday']
        email = request.form['email']
        phone_number = request.form['phone_number']
        
        conn = connect_to_db()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO event_scheduling.users (user_id, password, name, birthday, email, phone_number)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (user_id, password, name, birthday, email, phone_number))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return redirect(url_for('login'))
    
    return render_template('new_register.html')


def get_friends():
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name FROM event_scheduling.users")
    friends = cursor.fetchall()
    cursor.close()
    conn.close()
    return friends

def generate_event_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

@app.route('/new_event', methods=['GET', 'POST'])
def new_event():
    if request.method == 'POST':
        event_id = request.form['event_id']
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        invited_members = request.form.getlist('invited_members')
        attending_members = request.form['attending_members']
        
        conn = connect_to_db()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO event_scheduling.events (event_id, event_name, event_date, event_time, invited_members, attending_members)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (event_id, event_name, event_date, event_time, ','.join(invited_members), attending_members))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        
        
        return redirect(url_for('index'))
    
    event_id = generate_event_id()
    friends = get_friends()
    return render_template('new_event.html', event_id=event_id, friends=friends)


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
