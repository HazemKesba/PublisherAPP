import pyodbc

connection_string = (
    r'DRIVER={ODBC Driver 18 for SQL Server};'
    r'SERVER=Dodo-PC;'
    r'DATABASE=PublisherDB;'
    r'Trusted_Connection=yes;'
    r'Encrypt=yes;'
    r'TrustServerCertificate=yes;'
)

def get_db():
    """Dependency: opens a fresh connection per request, closes it when done."""
    conn = pyodbc.connect(connection_string)
    try:
        yield conn
    finally:
        conn.close()