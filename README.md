# PolicyIQ — HR Policy Q&A Agent
### Dubai, UAE · Built with Flask + Claude API

An employee-facing HR Policy Q&A assistant powered by **Retrieval-Augmented Generation (RAG)**.
HR admins upload policy documents; employees ask questions in plain English and receive
grounded, cited answers sourced directly from the uploaded policies.

---

## Architecture

```
hr-policy-agent/
├── app.py                  # Flask routes & app config
├── requirements.txt
├── rag/
│   ├── chunker.py          # PDF/DOCX/TXT extraction + chunking
│   ├── retriever.py        # TF-IDF index + cosine similarity retrieval
│   └── agent.py            # Claude API integration + system prompt
├── templates/
│   ├── base.html           # Shared nav, design tokens, toast
│   ├── chat.html           # Employee Q&A interface
│   └── admin.html          # Document upload + management portal
├── uploads/                # Raw uploaded policy files (auto-created)
└── db/
    ├── policy.db           # SQLite: documents + chunks
    └── tfidf_index.pkl     # Serialised TF-IDF vectoriser + matrix
```

### RAG Pipeline

```
PDF/DOCX/TXT
    │
    ▼ chunker.py
Text extraction  →  Clean text  →  500-word chunks (75-word overlap)
    │
    ▼ SQLite
Chunks stored with doc_id, page_num, category
    │
    ▼ retriever.py (on query)
TF-IDF vectorise query  →  Cosine similarity  →  Top-5 chunks
    │
    ▼ agent.py
Build context prompt  →  Claude claude-sonnet-4-20250514  →  Cited answer
```

---

## Setup

### 1. Clone & install
```bash
git clone <your-repo>
cd hr-policy-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set your API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run
```bash
python app.py
```
App runs on **http://localhost:5002**

---

## Usage

### Admin Portal — `/admin`
1. Open the Admin Portal
2. Drag & drop or select a PDF/DOCX/TXT policy document
3. Select the **Policy Category** (UAE Labour Law, HR Handbook, Visa & Immigration, etc.)
4. Click **Upload & Index Document** — the RAG index rebuilds automatically
5. Repeat for all your policy documents

**Recommended documents to upload:**
- UAE Labour Law (Federal Decree-Law No. 33 of 2021)
- Company HR Handbook
- Visa & Immigration SOP
- Emiratisation & WPS compliance guidelines
- Benefits & Compensation policy
- Employee Code of Conduct

### Employee Chat — `/`
Employees can ask questions in plain English such as:
- *"What is my annual leave entitlement?"*
- *"How is end of service gratuity calculated?"*
- *"What documents do I need for visa renewal?"*
- *"Can I carry forward unused leave?"*

Answers include **source citations** showing which document the answer came from.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| TF-IDF retrieval (no vector DB) | Lightweight, no external dependencies, works well for structured policy docs |
| SQLite storage | Zero-config, portable, sufficient for 100s of policy documents |
| Claude API called only at answer generation | All retrieval is deterministic; Claude used only where natural language understanding is essential |
| 500-word chunks, 75-word overlap | Balances context preservation with retrieval precision |
| Session-based multi-turn history | Employees can ask follow-up questions; no user accounts needed |

---

## Deployment

### Railway
```bash
# Add Procfile
echo "web: python app.py" > Procfile
# Push to Railway, set ANTHROPIC_API_KEY env var
```

### Environment variables required
- `ANTHROPIC_API_KEY` — your Anthropic API key

---

## Portfolio Notes

This project demonstrates:
- **RAG pipeline from scratch** — chunking, TF-IDF indexing, cosine retrieval, Claude generation
- **UAE/Dubai domain expertise** — MOHRE, Emiratisation, WPS, EOSG context baked into system prompt
- **Production architecture** — SQLite persistence, pickle serialisation, stateless Flask routes
- **Two-interface design** — Admin document management + Employee self-service
