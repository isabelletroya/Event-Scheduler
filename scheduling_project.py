import psycopg2

# PostgreSQL connection parameters
conn_params = {
    "host": "localhost",
    "database": "Scheduling",
    "user": "postgres",
    "password": "sebastian2001",
    "port": "5432"  # Default PostgreSQL port
}

# Connect to PostgreSQL
try:
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()

    # Example query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version}")

    # Add more database operations here

except psycopg2.Error as e:
    print(f"Error connecting to PostgreSQL: {e}")

finally:
    if 'conn' in locals():
        conn.close()
