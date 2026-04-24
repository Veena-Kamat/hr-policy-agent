"""
rag/retriever.py
TF-IDF based retrieval engine.
Builds an index over all policy chunks stored in SQLite and returns
the top-k most relevant chunks for a given query.
"""

import sqlite3
import pickle
import os
import logging

logger = logging.getLogger(__name__)

INDEX_PATH = 'db/tfidf_index.pkl'


class Retriever:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.vectorizer = None
        self.matrix = None
        self.chunk_ids: list[int] = []
        self._load_or_build()

    # ── Public ───────────────────────────────────────────────────────────────

    def rebuild_index(self):
        """Re-read all chunks from the DB and rebuild the TF-IDF index."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            raise ImportError("scikit-learn is required: pip install scikit-learn")

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT id, content FROM chunks ORDER BY id').fetchall()
        conn.close()

        if not rows:
            self.vectorizer = None
            self.matrix = None
            self.chunk_ids = []
            if os.path.exists(INDEX_PATH):
                os.remove(INDEX_PATH)
            return

        self.chunk_ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=25_000,
            sublinear_tf=True,
            stop_words='english',
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform(texts)

        with open(INDEX_PATH, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'matrix': self.matrix,
                'chunk_ids': self.chunk_ids,
            }, f)

        logger.info(f"TF-IDF index rebuilt: {len(rows)} chunks indexed.")

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Return up to top_k chunks most relevant to `query`.
        Each dict has: content, page_num, original_name, category
        """
        if self.vectorizer is None or self.matrix is None:
            return []

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
        except ImportError:
            return []

        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix).flatten()

        # Take top_k indices with score > threshold
        top_indices = np.argsort(scores)[::-1][:top_k * 2]   # fetch extra, filter below
        top_indices = [i for i in top_indices if scores[i] > 0.02][:top_k]

        if not top_indices:
            return []

        top_chunk_ids = [self.chunk_ids[i] for i in top_indices]

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        results = []
        for cid in top_chunk_ids:
            row = conn.execute('''
                SELECT c.content, c.page_num, d.original_name, d.category
                FROM   chunks c
                JOIN   documents d ON c.doc_id = d.id
                WHERE  c.id = ?
            ''', (cid,)).fetchone()
            if row:
                results.append(dict(row))
        conn.close()

        return results

    # ── Private ──────────────────────────────────────────────────────────────

    def _load_or_build(self):
        if os.path.exists(INDEX_PATH):
            try:
                with open(INDEX_PATH, 'rb') as f:
                    data = pickle.load(f)
                self.vectorizer = data['vectorizer']
                self.matrix     = data['matrix']
                self.chunk_ids  = data['chunk_ids']
                logger.info(f"TF-IDF index loaded: {len(self.chunk_ids)} chunks.")
                return
            except Exception as e:
                logger.warning(f"Failed to load TF-IDF index: {e}. Rebuilding…")

        self.rebuild_index()
