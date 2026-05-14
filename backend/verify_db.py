import sqlite3

def check_db():
    conn = sqlite3.connect('student_feedback.db')
    cursor = conn.cursor()
    
    tables = ['upload_sessions', 'complaints', 'predictions']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Table {table}: {count} rows")
        
    cursor.execute("PRAGMA table_info(upload_sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Columns in upload_sessions: {columns}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
