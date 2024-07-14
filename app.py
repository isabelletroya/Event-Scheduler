from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
import psycopg2
import webbrowser
from threading import Timer
import random
import string
import secrets
from datetime import datetime, date


# print(secrets.token_hex(16))


app = Flask(__name__)



app.secret_key = "5e66e548473d806f843bf77b19811602"  # Necessary for session management

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

def get_friends(username):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.friend_id, f.name, f.phone_number 
        FROM event_scheduling.friends f
        JOIN event_scheduling.users_have_friends uhf ON f.phone_number = uhf.phone_number
        WHERE uhf.user_id = %s;
    """, (username,))
    friends = cursor.fetchall()
    cursor.close()
    conn.close()
    return friends


def generate_event_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


def user_info_check(username, password):
    conn = connect_to_db()
    cursor = conn.cursor()
    
    info_query = "SELECT * FROM event_scheduling.users WHERE user_id = %s AND password = %s;"
    cursor.execute(info_query, (username, password))
    
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result


@app.route('/new_event', methods=['GET', 'POST'])
def new_event():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        event_id = generate_event_id()
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        invited_members = request.form.getlist('invited_members')

        conn = connect_to_db()
        cursor = conn.cursor()

        insert_event_query = """
        INSERT INTO event_scheduling.events (event_id, event_name, event_date, event_time, admin_id)
        VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(insert_event_query, (event_id, event_name, event_date, event_time, username))

        insert_attendee_query = "INSERT INTO event_scheduling.users_attend_events (user_id, event_id) VALUES (%s, %s);"

        # Ensure the event creator is also added to the users_attend_events
        cursor.execute(insert_attendee_query, (username, event_id))

        for user_id in invited_members:
            if user_id != username:  # Avoid inserting the event creator twice
                cursor.execute(insert_attendee_query, (user_id, event_id))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Event created successfully!', 'success')
        return redirect(url_for('index'))

    event_id = generate_event_id()
    friends = get_friends(username)

    return render_template('new_event.html', event_id=event_id, friends=friends)



# Route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    # global username
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        
        user_info = user_info_check(username, password)
        
        if user_info:
            session['username'] = username
            session['admin_id'] = username
            return redirect(url_for('index'))  # Redirect to home page after successful login
# Redirect to home page after successful login
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

from datetime import datetime

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
        
        try:
            # Check if the username already exists
            cursor.execute("SELECT 1 FROM event_scheduling.users WHERE user_id = %s;", (user_id,))
            if cursor.fetchone() is not None:
                error = 'Username Unavailable. Please provide another.'
                return render_template('new_register.html', error=error)
            
            # Calculate age from birthday
            birth_date = datetime.strptime(birthday, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            # Insert into users table
            insert_query = """
            INSERT INTO event_scheduling.users (user_id, password, name, birthday, email, phone_number, age) 
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(insert_query, (user_id, password, name, birthday, email, phone_number, age))
            
            # # Insert into friends table
            # insert_query2 = """
            # INSERT INTO event_scheduling.friends (user_id, name, friend_id, age, phone_number) 
            # VALUES (%s, %s, %s, %s, %s)
            # ON CONFLICT DO NOTHING;
            # """
            # cursor.execute(insert_query2, (user_id, name, user_id, age, phone_number))
            
            conn.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            flash(f'Error registering user: {e}', 'error')
            return redirect(url_for('new_register'))
        
        finally:
            cursor.close()
            conn.close()
    
    return render_template('new_register.html')

@app.route('/delete_account', methods=['POST'])
def delete_account():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Remove from users_have_friends table
        cursor.execute("""
            DELETE FROM event_scheduling.users_have_friends
            WHERE user_id = %s OR phone_number IN (
                SELECT phone_number FROM event_scheduling.users WHERE user_id = %s
            );
        """, (username, username))

        # Remove from friends table
        cursor.execute("""
            DELETE FROM event_scheduling.friends
            WHERE user_id = %s OR friend_id = %s;
        """, (username, username))

        # Remove user account
        cursor.execute("""
            DELETE FROM event_scheduling.users
            WHERE user_id = %s;
        """, (username,))

        conn.commit()
        session.pop('username', None)
        flash('Account deleted successfully!', 'success')
    except Exception as e:
        flash('Error deleting account: {}'.format(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('login'))


@app.route('/delete_event/<event_id>', methods=['POST'])
def delete_event(event_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Check if the current user is the admin of the event
        cursor.execute("SELECT admin_id FROM event_scheduling.events WHERE event_id = %s;", (event_id,))
        admin_id = cursor.fetchone()[0]

        if username != admin_id:
            flash('You do not have permission to delete this event.', 'error')
            return redirect(url_for('index'))

        # Delete from users_attend_events table
        cursor.execute("DELETE FROM event_scheduling.users_attend_events WHERE event_id = %s;", (event_id,))

        # Delete from events table
        cursor.execute("DELETE FROM event_scheduling.events WHERE event_id = %s;", (event_id,))

        conn.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        flash('Error deleting event: {}'.format(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))



@app.route('/edit_event/<event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    username = session.get('username')

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        invited_members = request.form.getlist('invited_members')

        conn = connect_to_db()
        cursor = conn.cursor()

        update_event_query = """
        UPDATE event_scheduling.events
        SET event_name = %s, event_date = %s, event_time = %s
        WHERE event_id = %s;
        """
        cursor.execute(update_event_query, (event_name, event_date, event_time, event_id))

        delete_old_attendees = "DELETE FROM event_scheduling.users_attend_events WHERE event_id = %s;"
        cursor.execute(delete_old_attendees, (event_id,))

        insert_attendee_query = "INSERT INTO event_scheduling.users_attend_events (user_id, event_id) VALUES (%s, %s);"
        for user_id in invited_members:
            cursor.execute(insert_attendee_query, (user_id, event_id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('index'))

    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT event_name, event_date, event_time, admin_id FROM event_scheduling.events WHERE event_id = %s;", (event_id,))
    event = cursor.fetchone()

    cursor.execute("SELECT user_id FROM event_scheduling.users_attend_events WHERE event_id = %s;", (event_id,))
    invited_members = [row[0] for row in cursor.fetchall()]

    friends = get_friends(username)

    cursor.close()
    conn.close()

    # Check if the current user can edit this event
    can_edit = (username == event[3])

    return render_template('edit_event.html', event_id=event_id, event=event, invited_members=invited_members, friends=friends, can_edit=can_edit)

@app.route('/edit_user_info', methods=['GET', 'POST'])
def edit_user_info():
    username = session.get('username')
    if request.method == 'POST':
        name = request.form['name']
        birthday = request.form['birthday']
        email = request.form['email']
        phone_number = request.form['phone_number']

        conn = connect_to_db()
        cursor = conn.cursor()

        update_user_query = """
        UPDATE event_scheduling.users
        SET name = %s, birthday = %s, email = %s, phone_number = %s
        WHERE user_id = %s;
        """
        cursor.execute(update_user_query, (name, birthday, email, phone_number, username))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('index'))

    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, birthday, email, phone_number FROM event_scheduling.users WHERE user_id = %s;", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('edit_user_info.html', user=user)


@app.route('/search_friends', methods=['POST'])
def search_friends():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    search_query = request.form['search_query']
    
    conn = connect_to_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, name 
        FROM event_scheduling.users 
        WHERE user_id != %s AND (user_id ILIKE %s OR name ILIKE %s)
    """, (username, f"%{search_query}%", f"%{search_query}%"))
    
    search_results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('search_results.html', search_results=search_results)


@app.route('/remove_friend/<friend_id>', methods=['POST'])
def remove_friend(friend_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Retrieve friend's phone number from the users table
        cursor.execute("""
            SELECT phone_number
            FROM event_scheduling.users
            WHERE user_id = %s;
        """, (friend_id,))
        friend_phone_number = cursor.fetchone()

        if friend_phone_number is None:
            flash('Friend not found.', 'error')
            return redirect(url_for('index'))

        friend_phone_number = friend_phone_number[0]

        # Remove from users_have_friends table
        cursor.execute("""
            DELETE FROM event_scheduling.users_have_friends
            WHERE user_id = %s AND phone_number = %s;
        """, (username, friend_phone_number))

        # Remove from friends table
        cursor.execute("""
            DELETE FROM event_scheduling.friends
            WHERE user_id = %s AND friend_id = %s;
        """, (username, friend_id))

        conn.commit()
        flash('Friend removed successfully!', 'success')
    except Exception as e:
        flash('Error removing friend: {}'.format(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))



@app.route('/add_friend/<friend_id>', methods=['POST'])
def add_friend(friend_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Retrieve friend's name, phone number, and birthday from the users table
        cursor.execute("""
            SELECT name, phone_number, birthday
            FROM event_scheduling.users
            WHERE user_id = %s;
        """, (friend_id,))
        friend_info = cursor.fetchone()
        

        if friend_info is None:
            flash('Friend not found.', 'error')
            return redirect(url_for('index'))

        friend_name, friend_phone_number, friend_birthday = friend_info
        print(f"Retrieved friend info: {friend_info}")

        # Check if friend_birthday is a string or datetime.date object and handle accordingly
        if isinstance(friend_birthday, date):
            friend_birth_date = friend_birthday
        else:
            friend_birth_date = datetime.strptime(friend_birthday, "%Y-%m-%d")
        
        today = datetime.today()
        friend_age = today.year - friend_birth_date.year - ((today.month, today.day) < (friend_birth_date.month, friend_birth_date.day))
        print(f"Calculated friend age: {friend_age}")

        # Insert user_id, friend's name, friend_id, friend's age, and friend's phone number into the friends table
        cursor.execute("""
            INSERT INTO event_scheduling.friends (user_id, name, friend_id, age, phone_number)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (username, friend_name, friend_id, friend_age, friend_phone_number))
        friends_inserted = cursor.rowcount
        print(f"Friends inserted: {friends_inserted}")

        # Insert into users_have_friends table
        cursor.execute("""
            INSERT INTO event_scheduling.users_have_friends (user_id, phone_number)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
        """, (username, friend_phone_number))
        users_have_friends_inserted = cursor.rowcount
        print(f"Users_have_friends inserted: {users_have_friends_inserted}")

        conn.commit()
        
        if friends_inserted == 0 or users_have_friends_inserted == 0:
            flash('Friend already added or other conflict.', 'warning')
        else:
            flash('Friend added successfully!', 'success')
    except Exception as e:
        print(f"Error adding friend: {e}")
        flash(f'Error adding friend: {e}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))



@app.route('/')
def index():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    # Fetch user data
    cursor.execute("SELECT * FROM event_scheduling.users WHERE user_id = %s;", (username,))
    data = cursor.fetchall()

    # Fetch events data where the user is an attendee but not an admin
    cursor.execute("""
        SELECT e.event_id, e.event_name, e.event_date, e.event_time
        FROM event_scheduling.users_attend_events uae
        JOIN event_scheduling.events e ON uae.event_id = e.event_id
        WHERE uae.user_id = %s AND e.admin_id != %s;
    """, (username, username))
    user_events = cursor.fetchall()

    # Fetch events data where the user is the admin
    cursor.execute("""
        SELECT e.event_id, e.event_name, e.event_date, e.event_time
        FROM event_scheduling.events e
        WHERE e.admin_id = %s;
    """, (username,))
    created_events = cursor.fetchall()

    # Fetch friends data
    friends = get_friends(username)

    cursor.close()
    conn.close()

    return render_template('index.html', data=data, user_events=user_events, created_events=created_events, friends=friends)

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/login')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True)



