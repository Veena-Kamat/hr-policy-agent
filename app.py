"""
HR Policy Q&A Agent — Dubai, UAE
Flask application with RAG pipeline + Claude API
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
import sqlite3
import datetime
from rag.chunker import extract_and_chunk
from rag.retriever import Retriever
from rag.agent import ask_policy_agent
from rag.user_profile import USER_PROFILE

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DB_PATH'] = 'db/policy.db'

os.makedirs('uploads', exist_ok=True)
os.makedirs('db', exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}

POLICY_CATEGORIES = [
    "UAE Labour Law / MOHRE",
    "HR Handbook",
    "Visa & Immigration",
    "Emiratisation & WPS",
    "Benefits & Compensation",
    "Code of Conduct",
    "Health & Safety",
    "General Policy",
]


def init_db():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            filename     TEXT    NOT NULL,
            original_name TEXT   NOT NULL,
            category     TEXT    NOT NULL,
            upload_date  TEXT    NOT NULL,
            chunk_count  INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id      INTEGER NOT NULL,
            content     TEXT    NOT NULL,
            page_num    INTEGER,
            chunk_index INTEGER,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


init_db()
retriever = Retriever(app.config['DB_PATH'])


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def chat():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    docs = conn.execute(
        'SELECT category, COUNT(*) as cnt FROM documents GROUP BY category'
    ).fetchall()
    total_docs = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    conn.close()
    return render_template('chat.html', categories=docs, total_docs=total_docs,
                           policy_categories=POLICY_CATEGORIES, user=USER_PROFILE)


@app.route('/admin')
def admin():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    docs = conn.execute(
        'SELECT * FROM documents ORDER BY upload_date DESC'
    ).fetchall()
    total_chunks = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
    conn.close()
    return render_template('admin.html', documents=docs,
                           policy_categories=POLICY_CATEGORIES,
                           total_chunks=total_chunks)


@app.route('/admin/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    category = request.form.get('category', 'General Policy')

    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported file type: {ext}. Use PDF, DOCX, or TXT.'}), 400

    # Save file with timestamp prefix to avoid collisions
    safe_name = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    file.save(filepath)

    # Extract text and chunk
    try:
        chunks = extract_and_chunk(filepath, ext)
    except Exception as e:
        os.remove(filepath)
        return jsonify({'error': f'Failed to process document: {str(e)}'}), 500

    if not chunks:
        os.remove(filepath)
        return jsonify({'error': 'No readable text found in document.'}), 400

    # Persist to database
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        '''INSERT INTO documents (filename, original_name, category, upload_date, chunk_count)
           VALUES (?, ?, ?, ?, ?)''',
        (safe_name, file.filename, category,
         datetime.datetime.now().strftime('%d %b %Y, %H:%M'), len(chunks))
    )
    doc_id = cur.lastrowid
    conn.executemany(
        'INSERT INTO chunks (doc_id, content, page_num, chunk_index) VALUES (?, ?, ?, ?)',
        [(doc_id, c['content'], c.get('page'), c['index']) for c in chunks]
    )
    conn.commit()
    conn.close()

    # Rebuild TF-IDF index
    retriever.rebuild_index()

    return jsonify({
        'success': True,
        'doc_id': doc_id,
        'chunks': len(chunks),
        'filename': file.filename
    })


@app.route('/admin/delete/<int:doc_id>', methods=['POST'])
def delete_document(doc_id):
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.execute("PRAGMA foreign_keys = ON")
    row = conn.execute(
        'SELECT filename FROM documents WHERE id = ?', (doc_id,)
    ).fetchone()
    if row:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
        if os.path.exists(filepath):
            os.remove(filepath)
    conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()

    retriever.rebuild_index()
    return redirect(url_for('admin'))


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    history  = data.get('history', [])

    if not question:
        return jsonify({'error': 'No question provided'}), 400

    # Retrieve top-k relevant chunks
    chunks = retriever.retrieve(question, top_k=5)

    if not chunks:
        return jsonify({
            'answer': (
                "I don't have policy documents loaded yet to answer your question. "
                "Please ask your HR administrator to upload the relevant policy documents "
                "via the Admin Portal, then try again."
            ),
            'sources': []
        })

    # Generate answer via Claude
    result = ask_policy_agent(question, chunks, history)
    return jsonify(result)


@app.route('/leave')
def leave():
    return render_template('leave.html', user=USER_PROFILE)

@app.route('/pay')
def pay():
    return render_template('pay.html', user=USER_PROFILE)

@app.route('/hours')
def hours():
    return render_template('hours.html', user=USER_PROFILE)

@app.route('/exit')
def exit_page():
    return render_template('exit.html')

@app.route('/grievance')
def grievance():
    return render_template('grievance.html', user=USER_PROFILE)

@app.route('/api/stats')
def stats():
    conn = sqlite3.connect(app.config['DB_PATH'])
    total_docs   = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    total_chunks = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
    cats = conn.execute(
        'SELECT category, COUNT(*) FROM documents GROUP BY category'
    ).fetchall()
    conn.close()
    return jsonify({
        'total_docs': total_docs,
        'total_chunks': total_chunks,
        'categories': dict(cats)
    })



@app.route('/download/<category>')
def download_by_category(category):
    """Download the first document matching a category."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    row = conn.execute(
        "SELECT filename, original_name FROM documents WHERE category = ? LIMIT 1",
        (category,)
    ).fetchone()
    conn.close()
    if not row:
        return "Document not found", 404
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
    if not os.path.exists(filepath):
        return "File not found on server", 404
    return send_file(filepath, as_attachment=True, download_name=row[1])


@app.route('/download-by-id/<int:doc_id>')
def download_by_id(doc_id):
    """Download a document by its ID."""
    conn = sqlite3.connect(app.config['DB_PATH'])
    row = conn.execute(
        "SELECT filename, original_name FROM documents WHERE id = ?",
        (doc_id,)
    ).fetchone()
    conn.close()
    if not row:
        return "Document not found", 404
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
    if not os.path.exists(filepath):
        return "File not found on server", 404
    return send_file(filepath, as_attachment=True, download_name=row[1])


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)
