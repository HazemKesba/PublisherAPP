import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

connection_string = (
    f'DRIVER={{ODBC Driver 18 for SQL Server}};'
    f'SERVER={os.getenv("DB_SERVER")};'
    f'DATABASE={os.getenv("DB_NAME")};'
    f'Trusted_Connection=yes;'
    f'Encrypt=yes;'
    f'TrustServerCertificate=yes;'
)

def get_db():
    conn = pyodbc.connect(connection_string)
    try:
        yield conn
    finally:
        conn.close()