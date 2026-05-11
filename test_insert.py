import pyodbc

conn_str = (
    r'DRIVER={ODBC Driver 18 for SQL Server};'
    r'SERVER=Dodo-PC;'
    r'DATABASE=PublisherDB;'
    r'Trusted_Connection=yes;'
    r'Encrypt=yes;'
    r'TrustServerCertificate=yes;'
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("INSERT INTO AUTHOR (NAME, BIOGRAPHY, ROYALTY_PERCENTAGE) VALUES (?, ?, ?)", 'Test', 'Bio', 10.5)
conn.commit()
cursor.execute("SELECT SCOPE_IDENTITY()")
print('Success! ID:', cursor.fetchone()[0])
conn.close()