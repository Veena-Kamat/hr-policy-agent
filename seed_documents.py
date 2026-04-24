"""
seed_documents.py
Auto-seeds all Novaris policy documents if the knowledge base is empty.
Called at startup via the Procfile — safe to run every time (idempotent).
"""

import sys, os, sqlite3, datetime, shutil

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'db', 'policy.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
DOC_DIR    = os.path.join(BASE_DIR, 'documents')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs('db', exist_ok=True)

sys.path.insert(0, BASE_DIR)
from rag.chunker import extract_and_chunk
from rag.retriever import Retriever

DOCUMENTS = [
    {'file': 'Novaris_Solutions_HR_Handbook.docx',          'category': 'HR Handbook'},
    {'file': 'Novaris_Leave_Attendance_Policy.docx',        'category': 'Leave & Attendance'},
    {'file': 'Novaris_Working_Hours_Policy.docx',           'category': 'Working Hours & Overtime'},
    {'file': 'Novaris_Benefits_Compensation_Policy.docx',   'category': 'Benefits & Compensation'},
    {'file': 'Novaris_Code_of_Conduct.docx',                'category': 'Code of Conduct'},
    {'file': 'Novaris_Grievance_Disciplinary_Policy.docx',  'category': 'Grievance & Disciplinary'},
]

def init_db(conn):
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL, original_name TEXT NOT NULL,
        category TEXT NOT NULL, upload_date TEXT NOT NULL,
        chunk_count INTEGER DEFAULT 0)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL, content TEXT NOT NULL,
        page_num INTEGER, chunk_index INTEGER,
        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE)''')
    conn.commit()

def already_seeded(conn):
    count = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    return count > 0

def seed():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if already_seeded(conn):
        print("Knowledge base already seeded — skipping.")
        conn.close()
        return

    print("Seeding knowledge base from bundled documents...")
    total_chunks = 0

    for doc in DOCUMENTS:
        src = os.path.join(DOC_DIR, doc['file'])
        if not os.path.exists(src):
            print(f"  MISSING: {doc['file']} — skipping")
            continue

        ext       = os.path.splitext(src)[1].lower()
        safe_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{doc['file']}"
        dest      = os.path.join(UPLOAD_DIR, safe_name)
        shutil.copy2(src, dest)

        chunks = extract_and_chunk(dest, ext)
        if not chunks:
            print(f"  WARNING: No text from {doc['file']}")
            continue

        cur = conn.execute(
            'INSERT INTO documents (filename, original_name, category, upload_date, chunk_count) VALUES (?,?,?,?,?)',
            (safe_name, doc['file'], doc['category'],
             datetime.datetime.now().strftime('%d %b %Y, %H:%M'), len(chunks))
        )
        conn.executemany(
            'INSERT INTO chunks (doc_id, content, page_num, chunk_index) VALUES (?,?,?,?)',
            [(cur.lastrowid, c['content'], c.get('page'), c['index']) for c in chunks]
        )
        conn.commit()
        total_chunks += len(chunks)
        print(f"  OK  {doc['file']} — {len(chunks)} chunks")

    conn.close()
    print(f"\nBuilding TF-IDF index ({total_chunks} chunks)...")
    Retriever(DB_PATH).rebuild_index()
    print("Knowledge base ready.\n")

if __name__ == '__main__':
    seed()
