import pyodbc

connection_string = (
    r'DRIVER={ODBC Driver 18 for SQL Server};'
    r'SERVER=.\SQLEXPRESS;'
    r'DATABASE=PublisherDB;'
    r'Trusted_Connection=yes;'
    r'Encrypt=yes;'
    r'TrustServerCertificate=yes;'
)

db_connection = None

def get_connection():
    global db_connection
    if db_connection is None or db_connection.closed:
        db_connection = pyodbc.connect(connection_string)
    return db_connection

def close_connection():
    global db_connection
    if db_connection or not db_connection.closed:
        db_connection.close()

def get_db():
    global db_connection
    if db_connection is None or db_connection.closed:
        db_connection = pyodbc.connect(connection_string)
    yield db_connection