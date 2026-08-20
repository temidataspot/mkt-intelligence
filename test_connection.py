# test_connection.py
# Purpose: verify that Python can successfully connect to my Postgres database.

import os                      # lets me read environment variables
import psycopg2                # the library that lets Python talk to Postgres
from dotenv import load_dotenv # lets me load variables from my .env file

# Load the variables from .env into the environment
load_dotenv()

# Read each connection detail from the environment (set in .env)
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

try:
    # Attempt to connect to Postgres using the details above
    connection = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
    )

    print("Postgres connection successful")

    # Open a cursor (send SQL commands and get results back)
    cursor = connection.cursor()

    # Run a simple test query to double-check everything works
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"Postgres version: {db_version[0]}")

    # Clean up: close the cursor and connection
    cursor.close()
    connection.close()

except Exception as e:
    print("❌ Connection failed.")
    print(e)