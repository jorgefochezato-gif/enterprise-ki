"""
Enterprise Knowledge Intelligence — Main Streamlit App
"""

import os
import sys
import time
from pathlib import Path

import streamlit as st

# ── path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))
from document_engine import (
    ingest_file,
    get_document_list,
    delete_document,
    retrieve_context,
    get_stats,
)
from qa_engine import stream_answer, validate_api_key

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Knowledge Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
  }

  /* Dark sidebar */
  [data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2330;
  }
  [data-testid="stSidebar"] * {
    color: #c9d1e0 !important;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #f8f9fc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem;
  }

  /* Chat messages */
  .chat-user {
    background: #1a56db;
    color: white;
    border-radius: 12px 12px 4px 12px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    max-width: 80%;
    margin-left: auto;
    font-size: 0.95rem;
  }
  .chat-assistant {
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 12px 12px 12px 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    max-width: 85%;
    font-size: 0.95rem;
    font-family: 'IBM Plex Sans', sans-serif;
  }

  /* Source badge */
  .source-badge {
    display: inline-block;
    background: #e0f2fe;
    color: #0369a1;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
    margin: 2px;
  }

  /* Document card */
  .doc-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #1a56db;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
  }

  /* Header */
  .eki-header {
    background: linear-gradient(135deg, #0f1117 0%, #1a2035 100%);
    color: white;
    padding: 1.5rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
  }
  .eki-header h1 { color: white; margin: 0; font-size: 1.6rem; font-weight: 600; }
  .eki-header p  { color: #8892a4; margin: 0.25rem 0 0; font-size: 0.9rem; }

  .badge {
    background: #1a56db22;
    color: #1a56db;
    border: 1px solid #1a56db44;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  /* Hide default Streamlit elements */
  #MainMenu, footer { visibility: hidden; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── session state init ─────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"

# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧠 EKI Platform")
    st.markdown("**Enterprise Knowledge Intelligence**")
    st.divider()

    nav = st.radio(
        "Navigation",
        ["💬 Ask Questions", "📁 Document Library", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.divider()

    # Quick stats
    stats = get_stats()
    st.markdown("**Knowledge Base**")
    st.markdown(f"📄 **{stats['total_documents']}** documents")
    st.markdown(f"🧩 **{stats['total_chunks']}** indexed chunks")

    if stats["document_types"]:
        types_str = " · ".join(
            f"{t}: {c}" for t, c in stats["document_types"].items()
        )
        st.caption(types_str)

    st.divider()
    st.caption("Powered by Claude claude-sonnet-4-20250514")
    st.caption("v1.0 MVP · Generic Enterprise")


# ══════════════════════════════════════════════════════════════════════════════
# TAB: ASK QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
if nav == "💬 Ask Questions":

    st.markdown("""
    <div class="eki-header">
      <span class="badge">AI Assistant</span>
      <h1>🧠 Ask Your Knowledge Base</h1>
      <p>Ask anything about your uploaded documents. The AI retrieves relevant content and generates a grounded answer with citations.</p>
    </div>
    """, unsafe_allow_html=True)

    # API key check
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error(
            "⚠️ **ANTHROPIC_API_KEY not found.** "
            "Go to ⚙️ Settings to configure it, or set it in your Codespace secrets."
        )
        st.stop()

    # No docs uploaded yet
    doc_list = get_document_list()
    if not doc_list:
        st.info("📭 Your knowledge base is empty. Go to **📁 Document Library** to upload files first.")
        st.stop()

    # ── Chat history display ──────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for turn in st.session_state.chat_history:
            if turn["role"] == "user":
                st.markdown(
                    f'<div class="chat-user">🙋 {turn["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-assistant">🧠 {turn["content"]}</div>',
                    unsafe_allow_html=True,
                )
                # Show source badges if available
                if "sources" in turn:
                    for src in turn["sources"]:
                        st.markdown(
                            f'<span class="source-badge">📎 {src}</span>',
                            unsafe_allow_html=True,
                        )

    st.divider()

    # ── Input ─────────────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_question = st.text_input(
            "Your question",
            placeholder="e.g. What is the refund policy? / Who is the IT security contact?",
            label_visibility="collapsed",
            key="question_input",
        )
    with col_btn:
        ask_btn = st.button("Ask →", type="primary", use_container_width=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    # ── Process question ──────────────────────────────────────────────────────
    if ask_btn and user_question.strip():
        with st.spinner("Searching knowledge base…"):
            chunks = retrieve_context(user_question, k=6)

        st.session_state.chat_history.append(
            {"role": "user", "content": user_question}
        )

        # Show retrieved sources (transparency panel)
        if chunks:
            with st.expander(f"🔍 Retrieved {len(chunks)} relevant passages", expanded=False):
                for i, c in enumerate(chunks, 1):
                    st.markdown(
                        f"**[{i}] {c['source']}** — relevance: `{c['relevance']:.0%}`"
                    )
                    st.caption(c["content"][:300] + "…" if len(c["content"]) > 300 else c["content"])
                    st.divider()

        # Stream the answer
        answer_placeholder = st.empty()
        full_answer = ""

        with answer_placeholder.container():
            st.markdown("**🧠 Assistant:**")
            answer_box = st.empty()

            try:
                for token in stream_answer(
                    user_question, chunks, st.session_state.chat_history[:-1]
                ):
                    full_answer += token
                    answer_box.markdown(full_answer + "▌")
                answer_box.markdown(full_answer)
            except Exception as e:
                full_answer = f"❌ Error: {e}"
                answer_box.markdown(full_answer)

        unique_sources = list({c["source"] for c in chunks})
        st.session_state.chat_history.append(
            {"role": "assistant", "content": full_answer, "sources": unique_sources}
        )
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB: DOCUMENT LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "📁 Document Library":

    st.markdown("""
    <div class="eki-header">
      <span class="badge">Knowledge Base</span>
      <h1>📁 Document Library</h1>
      <p>Upload, manage, and inspect the documents that power your knowledge base.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload section ────────────────────────────────────────────────────────
    st.subheader("Upload Documents")
    uploaded_files = st.file_uploader(
        "Drop files here or click to browse",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, TXT, MD. Max 200 MB per file.",
    )

    if uploaded_files:
        if st.button(f"⬆️ Index {len(uploaded_files)} file(s)", type="primary"):
            progress = st.progress(0)
            for i, f in enumerate(uploaded_files):
                with st.spinner(f"Processing {f.name}…"):
                    success, msg = ingest_file(f)
                    if success:
                        st.success(msg)
                    else:
                        st.warning(msg)
                progress.progress((i + 1) / len(uploaded_files))
            st.rerun()

    st.divider()

    # ── Document list ─────────────────────────────────────────────────────────
    doc_list = get_document_list()
    st.subheader(f"Indexed Documents ({len(doc_list)})")

    if not doc_list:
        st.info("No documents yet. Upload files above to get started.")
    else:
        # Stats row
        stats = get_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("Documents", stats["total_documents"])
        c2.metric("Total Chunks", stats["total_chunks"])
        c3.metric("File Types", len(stats["document_types"]))

        st.markdown("")

        type_colors = {"PDF": "🔴", "DOCX": "🔵", "TXT": "🟢", "MD": "🟡"}

        for doc in doc_list:
            col_info, col_meta, col_del = st.columns([4, 3, 1])
            icon = type_colors.get(doc.get("file_type", ""), "⚪")
            with col_info:
                st.markdown(
                    f'<div class="doc-card">'
                    f'<strong>{icon} {doc["name"]}</strong><br>'
                    f'<small style="color:#64748b">'
                    f'{doc["file_type"]} · {doc["size_bytes"] / 1024:.1f} KB · '
                    f'{doc["chunk_count"]} chunks · {doc["page_count"]} pages'
                    f'</small></div>',
                    unsafe_allow_html=True,
                )
            with col_meta:
                ingested = doc["ingested_at"][:10]
                st.caption(f"Indexed: {ingested}")
                st.caption(f"ID: `{doc['id']}`")
            with col_del:
                if st.button("🗑️", key=f"del_{doc['id']}", help="Remove from knowledge base"):
                    ok, msg = delete_document(doc["id"])
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    st.rerun()

    st.divider()

    # ── Roadmap callout ───────────────────────────────────────────────────────
    st.markdown("#### 🔮 Planned Connectors")
    cols = st.columns(4)
    connectors = [
        ("📧", "Email / Outlook", "Q3 2025"),
        ("📝", "Confluence / Wiki", "Q3 2025"),
        ("🎫", "Jira / ServiceNow", "Q4 2025"),
        ("💬", "Slack / Teams", "Q4 2025"),
    ]
    for col, (icon, name, eta) in zip(cols, connectors):
        with col:
            st.markdown(
                f"""
                <div style="border:1px dashed #cbd5e1;border-radius:8px;
                     padding:0.75rem;text-align:center;background:#f8fafc">
                  <div style="font-size:1.5rem">{icon}</div>
                  <div style="font-weight:600;font-size:0.85rem">{name}</div>
                  <div style="color:#94a3b8;font-size:0.75rem">{eta}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB: SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "⚙️ Settings":

    st.markdown("""
    <div class="eki-header">
      <span class="badge">Configuration</span>
      <h1>⚙️ Settings</h1>
      <p>Configure API credentials and review system architecture.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── API Key ───────────────────────────────────────────────────────────────
    st.subheader("🔑 Anthropic API Key")

    current_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if current_key:
        masked = current_key[:8] + "•" * (len(current_key) - 12) + current_key[-4:]
        st.success(f"API key loaded from environment: `{masked}`")
        if st.button("🔍 Test Connection"):
            with st.spinner("Testing…"):
                ok, msg = validate_api_key()
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    else:
        st.warning("No API key found in environment.")
        new_key = st.text_input(
            "Enter your Anthropic API key",
            type="password",
            placeholder="sk-ant-…",
        )
        if new_key and st.button("Save for this session"):
            os.environ["ANTHROPIC_API_KEY"] = new_key
            st.success("Key saved for this session. For persistence, add it to Codespace Secrets.")
            st.rerun()

    st.divider()

    # ── Architecture ──────────────────────────────────────────────────────────
    st.subheader("🏗️ System Architecture")
    st.markdown("""
    | Layer | Technology | Purpose |
    |-------|-----------|---------|
    | **Frontend** | Streamlit | UI, file upload, chat interface |
    | **Embedding** | `all-MiniLM-L6-v2` (local) | Convert text chunks to vectors |
    | **Vector Store** | ChromaDB (local) | Semantic similarity search |
    | **LLM** | Claude claude-sonnet-4-20250514 | Grounded answer generation |
    | **Orchestration** | LangChain | Document loading, chunking, retrieval |
    | **Storage** | Local filesystem | Uploaded files + metadata |
    """)

    st.divider()

    # ── How it works ──────────────────────────────────────────────────────────
    st.subheader("⚙️ How It Works")
    st.markdown("""
    **Ingestion pipeline:**
    1. File is uploaded and saved to `data/uploads/`
    2. LangChain loads and parses the document (PDF/DOCX/TXT)
    3. Text is split into overlapping chunks (~800 tokens, 120 overlap)
    4. Each chunk is embedded using a local sentence-transformer model
    5. Vectors are stored in ChromaDB with source metadata

    **Query pipeline:**
    1. User question is embedded using the same model
    2. ChromaDB returns the top-6 most semantically similar chunks
    3. Chunks + question are sent to Claude with a strict grounding prompt
    4. Claude generates a cited answer using only retrieved content
    5. Sources are displayed below the answer for transparency
    """)

    st.divider()

    # ── Environment info ──────────────────────────────────────────────────────
    st.subheader("🖥️ Environment")
    import platform
    st.code(
        f"Python: {platform.python_version()}\n"
        f"OS: {platform.system()} {platform.release()}\n"
        f"Vectorstore: data/vectorstore/\n"
        f"Uploads: data/uploads/",
        language="text",
    )