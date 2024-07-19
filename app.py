from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
import psycopg2
import webbrowser
from threading import Timer
import random
import string
import secrets
from datetime import datetime, date
import bcrypt


app = Flask(__name__)
app.debug = False

app.secret_key = "5e66e548473d806f843bf77b19811602"  # Necessary for session management

# Database connection configuration
db_config = {
    "host": "localhost",
    "database": "Scheduling",
    "user": "postgres",
    "password": "sebastian2001",
}

# Establish a connection to the database and return the connection 
def connect_to_db():
    conn = psycopg2.connect(**db_config)
    return conn

# Generate a random alphanumeric ID of given length
def generate_event_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_random_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

# check that the info inputted is valid and correc within the user table
def user_info_check(username, password):
    conn = connect_to_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * 
    FROM event_scheduling.users 
    WHERE user_id = %s AND password = %s;
    """, (username, password))
    
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result

# get the list of friends for the user logged in
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


# create a new event
@app.route('/new_event', methods=['GET', 'POST'])
def new_event():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    
    error = None  # Initialize error variable
    event_id = generate_event_id()
    friends = []

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        invited_members = request.form.getlist('invited_members')

        conn = connect_to_db()
        cursor = conn.cursor()

        try:
            # Insert into events table
            cursor.execute("""
            INSERT INTO event_scheduling.events (event_id, event_name, event_date, event_time, admin_id)
            VALUES (%s, %s, %s, %s, %s);
            """, (event_id, event_name, event_date, event_time, username))

            # Insert into users_attend_events table
            cursor.execute("""
            INSERT INTO event_scheduling.users_attend_events (user_id, event_id) 
            VALUES (%s, %s);
            """, (username, event_id))

            # Add all the invited members into the users_attend_events
            insert_attendee_query = """
            INSERT INTO event_scheduling.users_attend_events (user_id, event_id) 
            VALUES (%s, %s);
            """
            for user_id in invited_members:
                if user_id != username:  # Avoid inserting the event creator twice
                    cursor.execute(insert_attendee_query, (user_id, event_id))

            conn.commit()

        except Exception as e:
            error = str(e)  # Capture the error message

        finally:
            cursor.close()
            conn.close()

        if error:
            # If there is an error, re-render the form with the error message
            friends = get_friends(username)
            return render_template('new_event.html', error=error, event_id=event_id, friends=friends)

        return redirect(url_for('index'))

    # Fetch the list of friends for the user
    friends = get_friends(username)

    return render_template('new_event.html', event_id=event_id, friends=friends, error=error)



# login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    # global username
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # get user info
        user_info = user_info_check(username, password)
        
        if user_info:
            session['username'] = username
            session['admin_id'] = username
            return redirect(url_for('index')) 
        else:
            error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

# logout the user
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin_id', None)
    return redirect(url_for('login'))

# Registering for an account
@app.route('/new_register', methods=['GET', 'POST'])
def new_register():
    # error = None
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        name = request.form['name']
        birthday = request.form['birthday']
        email = request.form['email']
        phone_number = request.form['phone_number']
        
        # Validate phone number length
        if len(phone_number) != 10:
            error = 'Phone number must be exactly 10 digits long.'
            return render_template('new_register.html', error=error)
        
        conn = connect_to_db()
        cursor = conn.cursor()
        
        try:
            # Calculate age from birthday
            birth_date = datetime.strptime(birthday, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            # if age < 15:
            #     error = 'You must be at least 15 years old to register.'
            #     return render_template('new_register.html', error=error)
            
            # Insert into users table
            cursor.execute("""
            INSERT INTO event_scheduling.users (user_id, password, name, birthday, email, phone_number, age) 
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (user_id, password, name, birthday, email, phone_number, age,))
            
            conn.commit()
            
            return redirect(url_for('login'))
        
        # except psycopg2.IntegrityError as e:
        #     conn.rollback()
        #     if 'event_scheduling.check_user_id_exists' in str(e):
        #         error = 'Username Unavailable. Please provide another.'
        #     elif 'event_scheduling.check_phone_number_exists' in str(e):
        #         error = 'Invalid phone number. Please try a new one.'
        #     elif 'event_scheduling.check_email_exists' in str(e):
        #         error = 'Email already exists. Please use a different email.'
        #     elif 'event_scheduling.check_user_age' in str(e):
        #         error = 'You must be at least 15 years old to register.'
        #     else:
        #         error = 'Error registering user: ' + str(e) 
        #     return render_template('new_register.html', error=error)

        except Exception as e:
            error = str(e)
        finally:
            cursor.close()
            conn.close()
            
        if error:
        # If there is an error, re-render the form with the error message
            return render_template('new_register.html', error=error)

    
    return render_template('new_register.html')


# Deleting an account
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
    except Exception as e:
        error = str(e)
    finally:
        cursor.close()
        conn.close()
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('login.html', error=error)

    return redirect(url_for('login'))

# Delete an event
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
    except Exception as e:
        error = str(e)
    finally:
        cursor.close()
        conn.close()
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('index.html', error=error)

    return redirect(url_for('index'))

# edit created event
@app.route('/edit_event/<event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    username = session.get('username')
    error = None  # Initialize error variable
    event = None
    invited_members = []
    friends = get_friends(username)
    can_edit = False

    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        invited_members = request.form.getlist('invited_members')

        conn = connect_to_db()
        cursor = conn.cursor()

        try:
            # Update the event content in the events table
            cursor.execute("""
            UPDATE event_scheduling.events
            SET event_name = %s, event_date = %s, event_time = %s
            WHERE event_id = %s;
            """, (event_name, event_date, event_time, event_id))

            # Remove old attendees
            cursor.execute("""
            DELETE FROM event_scheduling.users_attend_events WHERE event_id = %s;
            """, (event_id,))

            # Insert updated attendees
            insert_attendee_query = """
            INSERT INTO event_scheduling.users_attend_events (user_id, event_id) VALUES (%s, %s);
            """
            for user_id in invited_members:
                cursor.execute(insert_attendee_query, (user_id, event_id))

            conn.commit()

        except Exception as e:
            error = str(e)  # Capture the error message

        finally:
            cursor.close()
            conn.close()

        if error:
            # When an error occurs, just return the current data and error message
            return render_template('index.html', error=error)

        return redirect(url_for('index'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Retrieve event details
        cursor.execute("""
        SELECT event_name, event_date, event_time, admin_id FROM event_scheduling.events WHERE event_id = %s;
        """, (event_id,))
        event = cursor.fetchone()

        if event:
            cursor.execute("""
            SELECT user_id FROM event_scheduling.users_attend_events WHERE event_id = %s;
            """, (event_id,))
            invited_members = [row[0] for row in cursor.fetchall()]

            # Check if the current user can edit this event
            can_edit = (username == event[3])

    except Exception as e:
        error = str(e)  # Capture the error message

    finally:
        cursor.close()
        conn.close()

    return render_template('edit_event.html', error=error, event_id=event_id, event=event, invited_members=invited_members, friends=friends, can_edit=can_edit)

@app.route('/edit_user_info', methods=['GET', 'POST'])
def edit_user_info():
    username = session.get('username')
    if request.method == 'POST':
        name = request.form['name']
        birthday = request.form['birthday']
        email = request.form['email']
        phone_number = request.form['phone_number']
        
        # Validate phone number length
        if len(phone_number) != 10:
            error = 'Phone number must be exactly 10 digits long.'
            return render_template('edit_user_info.html', error=error, user=(name, birthday, email, phone_number))
        
        conn = connect_to_db()
        cursor = conn.cursor()

        try:
            # Update user information
            cursor.execute("""
            UPDATE event_scheduling.users
            SET name = %s, birthday = %s, email = %s, phone_number = %s
            WHERE user_id = %s;
            """, (name, birthday, email, phone_number, username))

            conn.commit()
            return redirect(url_for('index'))
        
        except Exception as e:
            error = str(e)  # Capture the error message

        finally:
            cursor.close()
            conn.close()
    
    # GET method to display current user info
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT name, birthday, email, phone_number 
    FROM event_scheduling.users 
    WHERE user_id = %s;
    """, (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('edit_user_info.html', user=user, error = error)




# look up friends within the database
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
        FROM event_scheduling.friend_search 
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
    print(friend_id)
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
    except Exception as e:
        error = str(e)
    finally:
        cursor.close()
        conn.close()
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('index.html', error=error)

    return redirect(url_for('index'))

# add a friend to friends list
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
        
    except Exception as e:
        error = str(e)
    finally:
        cursor.close()
        conn.close()
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('index.html', error=error)

    return redirect(url_for('index'))
import logging

# creating posts for events
@app.route('/create_post', methods=['POST'])
def create_post():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    event_id = request.form.get('event_id')
    post_content = request.form.get('post_content')

    # Generate a random ID for post_id (assuming you have a function generate_random_id())
    post_id = generate_random_id()

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Insert new post into the database
        cursor.execute("""
        INSERT INTO event_scheduling.posts (user_id, event_id, post_content, post_time, post_id)
        VALUES (%s, %s, %s, NOW(), %s);
        """, (username, event_id, post_content, post_id))
        
        cursor.execute("""
        INSERT INTO event_scheduling.events_have_posts (event_id, post_id)
        VALUES (%s, %s);
        """, (event_id, post_id))
        
        conn.commit()

        flash('Post created successfully!', 'success')
    except Exception as e:
        error = str(e)
    finally:
        cursor.close()
        conn.close()
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('index.html', error=error)

    return redirect(url_for('index'))
# getting post info that connects to what events her user is attending or events they created
@app.route('/feed')
def feed():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # getting posts from events where user is invited or is the admin
                
        cursor.execute("""
        SELECT DISTINCT p.post_content, 
                        p.post_time, 
                        e.event_name, 
                        u.name AS user_name
        FROM event_scheduling.posts p
        JOIN event_scheduling.events_have_posts ep ON p.post_id = ep.post_id
        JOIN event_scheduling.events e ON ep.event_id = e.event_id
        LEFT JOIN event_scheduling.users_attend_events uae ON e.event_id = uae.event_id
        LEFT JOIN event_scheduling.users u ON p.user_id = u.user_id
        WHERE (uae.user_id = %s OR e.admin_id = %s)
        ORDER BY p.post_time DESC;
        """, (username, username))
        post = cursor.fetchall()


        return render_template('feed.html', post=post)
    except Exception as e:
            error = str(e)
    finally:
        cursor.close()
        conn.close()
        
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('index.html', error=error)

    return redirect(url_for('index'))



@app.route('/')
def index():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Getting user data from the view
        cursor.execute("SELECT name, phone_number, birthday, email FROM event_scheduling.user_view WHERE user_id = %s;", (username,))
        data = cursor.fetchall()
        print(data)

        # Get events data where the user is an attendee but not an admin
        cursor.execute("""
            SELECT e.event_id, e.event_name, e.event_date, e.event_time
            FROM event_scheduling.users_attend_events uae
            JOIN event_scheduling.events e ON uae.event_id = e.event_id
            WHERE uae.user_id = %s AND e.admin_id != %s;
        """, (username, username))
        user_events = cursor.fetchall()

        # Get events data where the user is the admin
        cursor.execute("""
        SELECT event_id, event_name, event_date, event_time
        FROM event_scheduling.admin_event_view
        WHERE admin_id = %s;
         """, (username,))
        created_events = cursor.fetchall()

        # Fetch friends data
        friends = get_friends(username)

        return render_template('index.html', data=data, user_events=user_events, created_events=created_events, friends=friends)
    except Exception as e:
            error = str(e)
    finally:
        cursor.close()
        conn.close()
        
    if error:
    # If there is an error, re-render the form with the error message
        return render_template('login.html', error=error)

    return redirect(url_for('login'))



def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/login')

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True)



