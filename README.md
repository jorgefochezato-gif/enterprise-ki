# 🧠 Enterprise Knowledge Intelligence (EKI)

> **An AI-powered knowledge base that lets your team ask questions in plain English and get cited answers from your own documents.**

Built for: sales demos to business stakeholders + technical handoff to IT teams.

---

## What It Does

Upload your company documents (PDFs, Word docs, text files). Ask questions in plain English. Get precise, cited answers — powered by Claude AI — without any data leaving your environment.

| Feature | Detail |
|---------|--------|
| 📄 **Ingests** | PDF, DOCX, TXT, Markdown |
| 🔍 **Retrieves** | Semantic similarity search (not keyword) |
| 🧠 **Answers** | Claude claude-sonnet-4-20250514 with strict grounding |
| 📎 **Cites sources** | Every answer references the source documents |
| 🔒 **Private** | Embeddings computed locally; only query + context sent to Claude |
| 🔮 **Extensible** | Architecture ready for email, wikis, ticket systems |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│         (Upload · Chat · Library · Settings)            │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │   Document Engine     │
         │  (LangChain + local   │
         │   SentenceTransformer)│
         └───────────┬───────────┘
                     │ embed
         ┌───────────▼───────────┐
         │     ChromaDB          │  ← local vector store
         │  (persistent disk)    │
         └───────────┬───────────┘
                     │ top-k chunks
         ┌───────────▼───────────┐
         │     Q&A Engine        │
         │  (Anthropic Claude)   │  ← only this touches external API
         └───────────────────────┘
```

**Key design decisions for IT teams:**
- Embedding model runs **100% locally** (no data sent to third parties for indexing)
- ChromaDB is **file-based** (no database server to manage)
- Only the query + retrieved text chunks are sent to Claude API
- All documents stored in `data/uploads/` — easy backup/audit

---

## Quick Start — GitHub Codespaces

### Step 1: Fork / Clone the Repository

```bash
# If you have the files locally:
git init
git add .
git commit -m "Initial EKI MVP"
gh repo create enterprise-ki --public --source=. --push
```

### Step 2: Open in Codespaces

1. Go to your GitHub repository
2. Click **Code → Codespaces → Create codespace on main**
3. Wait ~2 minutes for the container to build (installs all dependencies automatically via `postCreateCommand`)

### Step 3: Set Your Anthropic API Key

**Option A — Codespace Secrets (recommended, persists across sessions):**
1. Go to [github.com/settings/codespaces](https://github.com/settings/codespaces)
2. Click **New secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your key from [console.anthropic.com](https://console.anthropic.com)
5. Select your repository under "Repository access"
6. Rebuild the codespace (or just set it in the app's Settings tab for now)

**Option B — In-app (session only):**
1. Open the app → ⚙️ Settings → paste your key there

**Option C — .env file (local dev only, never commit this):**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env
export $(cat .env)
```

### Step 4: Run the App

```bash
streamlit run app.py
```

Streamlit will print a URL like `http://localhost:8501`. In Codespaces, the **Ports** tab (bottom panel) will show a forwarded public URL — click the globe icon to open it.

---

## Local Development Setup

```bash
# 1. Python 3.11+ required
python --version

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."   # Windows: set ANTHROPIC_API_KEY=...

# 5. Run
streamlit run app.py
```

---

## Project Structure

```
enterprise-ki/
├── app.py                        # Main Streamlit application
├── requirements.txt              # Python dependencies
├── .devcontainer/
│   └── devcontainer.json        # Codespace config (auto-install, port forward)
├── .streamlit/
│   └── config.toml              # Theme & server settings
├── src/
│   ├── document_engine.py       # Ingestion, chunking, embedding, retrieval
│   └── qa_engine.py             # Claude-powered Q&A with streaming
└── data/                        # Created at runtime
    ├── uploads/                 # Raw uploaded files
    ├── vectorstore/             # ChromaDB files (persistent)
    └── document_metadata.json   # Document registry
```

---

## Dependency Notes for IT Teams

All packages are pinned in `requirements.txt`. Key ones:

| Package | Version | Role |
|---------|---------|------|
| `streamlit` | 1.35 | Web UI framework |
| `anthropic` | 0.28 | Claude API client |
| `langchain` | 0.2 | Document loading & text splitting |
| `langchain-chroma` | 0.1 | ChromaDB integration |
| `chromadb` | 0.5 | Local vector database |
| `sentence-transformers` | 3.0 | Local embedding model (~80 MB, downloads once) |
| `pypdf` | 4.2 | PDF parsing |
| `python-docx` | 1.1 | DOCX parsing |

**First run note:** `sentence-transformers` downloads the `all-MiniLM-L6-v2` model (~80 MB) on first use. This is cached locally. In Codespaces, it downloads automatically.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ANTHROPIC_API_KEY not set` | Add to Codespace secrets or paste in ⚙️ Settings |
| Port 8501 not accessible | Check Codespace **Ports** tab → set visibility to Public |
| `sentence-transformers` download slow | First-time only; cached afterward |
| ChromaDB error on first run | Delete `data/vectorstore/` and restart |
| PDF parsing fails | Ensure PDF is not password-protected |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |

---

## Roadmap

- [ ] **v1.1** — Email connector (Outlook/Gmail via OAuth)
- [ ] **v1.2** — Confluence / Notion wiki sync  
- [ ] **v1.3** — Jira / ServiceNow ticket ingestion
- [ ] **v1.4** — Slack / Teams message archive
- [ ] **v2.0** — Role-based document access control
- [ ] **v2.1** — Multi-tenant organization support
- [ ] **v2.2** — Analytics dashboard (query volume, top topics)
- [ ] **v2.3** — On-premise LLM option (Ollama / local models)

---

## Security Notes

- API key is never stored on disk by the app (session memory only unless using env var)
- Documents are stored locally in `data/uploads/` — restrict filesystem access as needed
- ChromaDB data in `data/vectorstore/` can be backed up like any directory
- For production: add authentication layer (Streamlit Cloud supports Google/GitHub SSO)

---

*Built with Streamlit · LangChain · ChromaDB · Anthropic Claude*