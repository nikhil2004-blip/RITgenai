# LibraMind — Complete Project Guide & Architectural Blueprint

> **Autonomous AI Virtual Librarian with Agentic Tool-Calling, Policy RAG, and Real-Time Vector Search**

---

## 1. Executive Summary & Core Idea

### The Problem
Traditional college library systems (OPAC) suffer from significant friction:
1. **Keyword Inelasticity:** Keyword search fails completely on intent-driven queries (e.g., *"give me an easy start for machine learning"* or *"books with good interview problems"*).
2. **Administrative Queuing:** Students wait in physical lines for repetitive inquiries: due dates, active fines, book availability, and policy clarifications.
3. **Information Asymmetry:** Library policy manuals (fines, loss penalties, timings) are buried in physical notices or lengthy PDFs that students rarely read.

### The Solution: LibraMind
**LibraMind** is an intelligent, autonomous virtual librarian designed for 24/7 college library operations. It bridges natural human language (English, Hindi, Hinglish, Kannada) with deterministic database transactions. 

Unlike naive chatbots that hallucinate information, LibraMind enforces **Zero Hallucination** by grounding every response in live SQL records and semantic vector chunks via **Agentic Function Calling**.

---

## 2. Technical Stack

| Layer | Technology | Justification |
|---|---|---|
| **User Interface** | Streamlit (Multi-Page Architecture) | Rapid, responsive, native Python UI with reactive session states and embedded Plotly dashboards. |
| **Language Model (LLM)** | Groq API (`openai/gpt-oss-120b`) | Ultra-low latency inference (~500 tokens/sec) with robust JSON function-calling schema adherence. |
| **Speech-to-Text (STT)** | Groq Whisper (`whisper-large-v3-turbo`) | High-accuracy multilingual audio transcription natively supported via Streamlit's `st.audio_input`. |
| **Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`) | Compact (384-dimensional), fast local embedding model running on CPU without cloud egress costs. |
| **Vector Database** | ChromaDB (`PersistentClient`) | Local disk-persisted vector store supporting filtered vector queries and metadata attachments. |
| **Relational Database** | SQLite3 (`Row` factory, WAL mode) | ACID-compliant, zero-dependency embedded database storing books, members, loans, reservations, and chat logs. |
| **Visualization** | Plotly Express | Interactive, customizable horizontal bar charts, donut charts, and time-series line graphs. |

---

## 3. High-Level Architecture & Data Flow

```
                      ┌────────────────────────────────────────┐
                      │             Student / User             │
                      │   (Text Query or 🎤 Voice Input)       │
                      └──────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │         Streamlit Web Client           │
                      │  app.py | 1_Catalog.py | 2_Admin.py    │
                      └──────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │               agent.py                 │
                      │    (Groq LLM Tool-Calling Loop)        │
                      └─────────┬────────────────────┬─────────┘
                                │                    │
         Function Call Request  │                    │ Direct Policy / Catalog Lookups
                                ▼                    ▼
        ┌────────────────────────────────┐   ┌────────────────────────────────┐
        │            tools.py            │   │             rag.py             │
        │   - issue_book                 │   │ - semantic_search_books        │
        │   - return_book                │   │ - search_policies              │
        │   - renew_book                 │   │ - add_book_to_index            │
        │   - check_availability         │   └───────────────┬────────────────┘
        │   - calculate_fine             │                   │
        └───────────────┬────────────────┘                   │
                        │                                    │
                        ▼                                    ▼
        ┌────────────────────────────────┐   ┌────────────────────────────────┐
        │       SQLite Database          │   │      ChromaDB Vector Store     │
        │         (library.db)           │   │         (chroma_db/)           │
        │ books, members, loans,         │   │ Collections:                   │
        │ reservations, chat_logs        │   │ 1. "books" (embeddings)       │
        └────────────────────────────────┘   │ 2. "policies" (chunked rules)  │
                                             └────────────────────────────────┘
```

---

## 4. The 3 GenAI Concepts Implemented

### Concept 1: Autonomous Agent Tool-Calling (Function Calling)
- Instead of asking the LLM to invent catalog answers, the LLM is given 11 strict **JSON Schema Tools** (`tools.TOOL_SCHEMAS`).
- When a user asks: *"Is Clean Code available?"*, the LLM emits a structured JSON payload:
  ```json
  {"name": "check_availability", "arguments": {"title": "Clean Code"}}
  ```
- The local Python runtime intercepts this, executes `tools.dispatch()`, queries the SQLite database, and injects the raw result back as a role `tool` message.
- The LLM receives the factual data and drafts a polite, conversational answer.
- **Safety Gate:** Write operations (`issue_book`, `return_book`, `renew_book`, `reserve_book`) run in two stages:
  1. `confirmed=false`: Previews the action and tells the user: *"Confirm issue of book X until date Y? (Yes/No)"*.
  2. `confirmed=true`: Executes only after the user explicitly assents.

### Concept 2: Retrieval-Augmented Generation (RAG) for Policies
- Library policies (`borrowing_rules.md`, `fines.md`, `lost_or_damaged.md`, etc.) are pre-chunked into ~400-character windows with 50-character overlap.
- Chunks are vectorized using `all-MiniLM-L6-v2` and indexed in ChromaDB's `"policies"` collection with source file metadata.
- When a student asks: *"What happens if I lose a book?"*, `rag.search_policies()` retrieves the top 3 semantically relevant chunks.
- The LLM synthesizes the answer exclusively from those chunks and cites the policy document name.

### Concept 3: Hybrid Semantic Search & Personalized Recommendations
- **Search:** Combines exact substring matching (`LIKE %query%`) with dense vector similarity (`all-MiniLM-L6-v2`). Exact matches appear first, followed by semantic matches.
- **Recommendations:** `recommend_books()` extracts the member's borrowing history, constructs a combined interest query, retrieves candidate books from ChromaDB, filters out previously read titles, and returns the top 3 along with an explainable `why` reasoning string.

---

## 5. Complete Database Schema (SQLite)

```sql
-- Books catalog with copy tracking
CREATE TABLE books (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    author           TEXT NOT NULL,
    subject          TEXT NOT NULL,
    isbn             TEXT,
    description      TEXT,
    published_year   INTEGER,
    language         TEXT DEFAULT 'English',
    total_copies     INTEGER DEFAULT 1,
    available_copies INTEGER DEFAULT 1
);

-- Registered student/faculty members
CREATE TABLE members (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    department TEXT NOT NULL,
    year       INTEGER,
    joined_on  TEXT NOT NULL
);

-- Circulation records with fine tracking
CREATE TABLE loans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id     INTEGER NOT NULL REFERENCES members(id),
    book_id       INTEGER NOT NULL REFERENCES books(id),
    issued_on     TEXT NOT NULL,
    due_on        TEXT NOT NULL,
    returned_on   TEXT,
    renewed_count INTEGER DEFAULT 0,
    fine_amount   REAL DEFAULT 0,
    fine_paid     INTEGER DEFAULT 0
);

-- Out-of-stock queue
CREATE TABLE reservations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id   INTEGER NOT NULL REFERENCES members(id),
    book_id     INTEGER NOT NULL REFERENCES books(id),
    reserved_on TEXT NOT NULL,
    status      TEXT DEFAULT 'active' -- active / fulfilled / cancelled
);

-- Full conversational audit trail
CREATE TABLE chat_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id  INTEGER REFERENCES members(id),
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

---

## 6. Business Logic & Constraints Enforced

1. **Loan Duration:** 14 days from issue date.
2. **Maximum Active Loans:** 3 books per member. A 4th issue request is automatically rejected.
3. **Renewals:** Allowed only once (+7 days), provided:
   - The book is not overdue.
   - No other student has placed an active reservation on that book.
4. **Fines:** ₹2 per book per day past the due date.
5. **Borrowing Block Threshold:** If a member has accumulated unpaid fines exceeding **₹50**, all new book issues are blocked.
6. **Reference Category Restriction:** Books with `subject = 'Reference'` cannot be issued outside the library.
7. **Reservation Holding Period:** When an out-of-stock book is returned, it is held for **2 days** for the next person in the reservation queue.

---

## 7. Project Structure

```
libramind/
├── .streamlit/
│   └── config.toml          # Light mode enforcement & typography palette
├── data/
│   ├── policies/            # 6 Policy Markdown files for RAG
│   │   ├── borrowing_rules.md
│   │   ├── conduct.md
│   │   ├── digital_resources.md
│   │   ├── fines.md
│   │   ├── lost_or_damaged.md
│   │   └── timings_membership.md
│   ├── sample_books.xlsx    # Template for bulk catalog upload
│   └── sample_books.csv
├── pages/
│   ├── 1_Catalog.py         # Searchable catalog with book inspection
│   └── 2_Admin_Dashboard.py # Analytics KPIs, Plotly charts, bulk Excel upload
├── agent.py                 # Multi-step Groq function-calling loop
├── app.py                   # Main chat page, voice recorder, member selector
├── config.py                # Portable paths, cloud secrets fallback, constants
├── db.py                    # SQLite schema initialization and connection pool
├── rag.py                   # SentenceTransformers + ChromaDB persistent vector store
├── seed.py                  # Database populator (73 books, 18 students, 32 loans)
├── theme.py                 # High-contrast literary warm beige aesthetic styling
├── voice.py                 # Groq Whisper STT transcription module
├── requirements.txt         # Project dependencies
├── .env.example             # Template for API credentials
└── README.md                # Quickstart documentation
```

---

## 8. How to Deploy (Step-by-Step)

### Option A: Streamlit Community Cloud (Recommended & Free)

1. **Push Code to GitHub:**
   ```bash
   cd "c:\Users\Nikhil Kumar Yadav\Desktop\genai"
   git init
   git add libramind/
   git commit -m "Deploy LibraMind AI Librarian"
   # Push to your GitHub repo
   git remote add origin https://github.com/your-username/libramind.git
   git branch -M main
   git push -u origin main
   ```

2. **Connect to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
   - Click **"Create app"** ➔ Select your repository.
   - Set **Main file path** to: `libramind/app.py`.

3. **Configure Secrets:**
   - In App Settings ➔ **Secrets**, paste:
     ```toml
     GROQ_API_KEY = "gsk_your_actual_groq_api_key"
     LLM_MODEL = "openai/gpt-oss-120b"
     ```
   - Click **Save & Deploy**.

4. **Self-Healing Automation:**
   - `app.py` automatically detects if the database is unseeded on cloud boot and executes `seed.py` dynamically. No manual terminal commands needed!

---

## 9. Viva / Presentation Q&A Cheat Sheet

**Q1: How do you prevent LLM hallucinations about books we don't own?**  
*Answer:* The LLM has zero knowledge of the catalog in its system prompt. It is strictly instructed to query tools (`search_books`, `check_availability`) before asserting any factual statement. If the database returns empty, the model is constrained to say *"I couldn't find that in our library"* and suggest alternatives.

**Q2: Why use both SQLite and ChromaDB? Why not just one database?**  
*Answer:* SQLite guarantees relational integrity, ACID compliance, and exact calculations (loan due dates, fine sums, foreign keys). ChromaDB specializes in high-dimensional vector similarity for unstructured semantic searches (vague queries and policy paragraphs). Using both is standard **hybrid architecture**.

**Q3: How does the voice transcription work?**  
*Answer:* Streamlit's `st.audio_input` captures WAV audio bytes from the user's microphone. We compute an MD5 hash of the audio buffer in session state to prevent accidental reprocessing on UI reruns. The audio buffer is sent to Groq Whisper (`whisper-large-v3-turbo`) which transcribes it with sub-second latency.

**Q4: How does write-action confirmation protect the user?**  
*Answer:* Any transaction altering state (`issue_book`, `return_book`, `renew_book`, `reserve_book`) requires two phases. On `confirmed=false`, the tool returns a preview summary. The agent displays this to the user and waits for affirmative intent before executing with `confirmed=true`.

**Q5: How does the Excel bulk upload sync with AI vector search?**  
*Answer:* In `pages/2_Admin_Dashboard.py`, when an Excel file is uploaded, pandas parses each row into the SQLite `books` table. Immediately in the same loop, `rag.add_book_to_index()` embeds the title, author, subject, and description into ChromaDB. The book becomes searchable via natural language instantly without restarting the server.
