import sqlite3
import os

conn = sqlite3.connect('student_feedback.db')
c = conn.cursor()

for table in ['complaints', 'predictions', 'upload_sessions']:
    print(f'=== {table} ===')
    c.execute(f'PRAGMA table_info({table})')
    cols = c.fetchall()
    for col in cols:
        print(f'  {col}')
    c.execute(f'SELECT COUNT(*) FROM {table}')
    cnt = c.fetchone()[0]
    print(f'  ROW COUNT: {cnt}')
    c.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?", (table,))
    idxs = c.fetchall()
    print(f'  INDEXES: {idxs}')
    print()

print('=== UPLOAD SESSIONS STATUS ===')
c.execute('SELECT id, filename, processing_status, total_rows FROM upload_sessions ORDER BY id DESC LIMIT 10')
rows = c.fetchall()
for r in rows:
    print(r)
    
print()
print('=== PREDICTION UMAP COVERAGE ===')
c.execute('SELECT COUNT(*) FROM predictions WHERE umap_x IS NOT NULL')
umap_count = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM predictions')
total_preds = c.fetchone()[0]
print(f'Predictions with UMAP: {umap_count}/{total_preds}')

print()
print('=== SENTIMENT DISTRIBUTION ===')
c.execute("SELECT sentiment, COUNT(*) FROM predictions GROUP BY sentiment")
for r in c.fetchall():
    print(r)

print()
print('=== CACHE FILES ===')
cache_dir = os.path.join('app', 'data', 'cache')
if os.path.exists(cache_dir):
    for f in os.listdir(cache_dir):
        fpath = os.path.join(cache_dir, f)
        size = os.path.getsize(fpath)
        print(f'{f}: {size} bytes')
else:
    print(f'Cache dir not found at: {cache_dir}')
    # Try alternate path
    alt = os.path.join('data', 'cache')
    if os.path.exists(alt):
        print(f'Found at: {alt}')
        for f in os.listdir(alt):
            size = os.path.getsize(os.path.join(alt, f))
            print(f'{f}: {size} bytes')

conn.close()
print('Done.')
