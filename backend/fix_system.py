"""
System fix script:
1. Mark stuck reviews.csv session as failed (unblocks re-upload attempt prevention)
2. Add missing index on upload_sessions.filename
3. Add missing index on upload_sessions.processing_status
"""
import sqlite3

conn = sqlite3.connect('student_feedback.db')
c = conn.cursor()

# 1. Fix stuck session (reviews.csv is stuck at "processing" — this would block
#    duplicate detection from catching future uploads since it's not "completed")
c.execute(
    "UPDATE upload_sessions SET processing_status='failed' WHERE filename='reviews.csv' AND processing_status='processing'"
)
print(f"Fixed stuck sessions: {c.rowcount} rows updated")

# 2. Add index on upload_sessions.filename for fast duplicate detection
existing_indexes = c.execute(
    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='upload_sessions'"
).fetchall()
existing_names = {r[0] for r in existing_indexes}

if 'ix_upload_sessions_filename' not in existing_names:
    c.execute("CREATE INDEX ix_upload_sessions_filename ON upload_sessions(filename)")
    print("Added index: ix_upload_sessions_filename")
else:
    print("Index ix_upload_sessions_filename already exists")

if 'ix_upload_sessions_processing_status' not in existing_names:
    c.execute("CREATE INDEX ix_upload_sessions_processing_status ON upload_sessions(processing_status)")
    print("Added index: ix_upload_sessions_processing_status")
else:
    print("Index ix_upload_sessions_processing_status already exists")

# 3. Add composite index on predictions for analytics queries
pred_indexes = c.execute(
    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='predictions'"
).fetchall()
pred_names = {r[0] for r in pred_indexes}

if 'ix_predictions_cluster_sentiment' not in pred_names:
    c.execute("CREATE INDEX ix_predictions_cluster_sentiment ON predictions(cluster_id, sentiment)")
    print("Added index: ix_predictions_cluster_sentiment")
else:
    print("Index ix_predictions_cluster_sentiment already exists")

if 'ix_predictions_umap' not in pred_names:
    c.execute("CREATE INDEX ix_predictions_umap ON predictions(umap_x, umap_y)")
    print("Added index: ix_predictions_umap")
else:
    print("Index ix_predictions_umap already exists")

conn.commit()

# 4. Verify final state
print("\n=== VERIFICATION ===")
c.execute("SELECT id, filename, processing_status FROM upload_sessions")
for r in c.fetchall():
    print(r)

print("\nAll fixes applied successfully.")
conn.close()
