# PRD: LibraMind — AI-Powered Virtual Librarian for Intelligent Library Assistance

## 1. Overview
LibraMind is a GenAI-based virtual librarian for a college library. Students talk to it in natural language (English / Hindi / Hinglish, text or voice) and it does real work: finds books, checks availability, issues/returns/renews/reserves books, calculates fines, recommends books, and answers library policy questions. Librarians get a dashboard with live analytics.

It combines three GenAI concepts: **(1) Agentic tool calling** over a real database, **(2) RAG** over library policy documents using embeddings, **(3) Semantic search + LLM reasoning** for recommendations. Optional: voice input and multilingual replies.

## 2. Problem Statement
Students waste time on manual catalog search and queue at the desk for simple queries (availability, due dates, fines, rules). Keyword search fails for vague requests like "something easy to start machine learning". Librarians have no quick insight into demand and overdue books.

## 3. Goals
- Answer library queries 24/7 in natural language with zero hallucination about catalog/loan data.
- Perform transactions (issue, return, renew, reserve) safely through tool calls.
- Give personalized, explained recommendations.
- Give the librarian a simple analytics dashboard.
- Runs fully locally with a free Groq API key, setup under 5 minutes.

Non-goals: payments, real barcode hardware, real authentication/OAuth, multi-library support.

## 4. Users
- **Student (member):** searches, asks policies, manages own loans. Demo login = pick a member from dropdown.
- **Librarian (admin):** views dashboard, adds books, sees overdue list.

## 5. Tech Stack
| Layer | Choice |
|---|---|
| UI | Streamlit (multi-page: Chat, Browse Catalog, Admin Dashboard) |
| LLM | Groq API, model `llama-3.3-70b-versatile` (tool calling) |
| Speech-to-text | Groq `whisper-large-v3-turbo` via `st.audio_input` (optional feature) |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` |
| Vector store | ChromaDB (persistent, local). Fallback if install fails: numpy cosine similarity |
| Database | SQLite via `sqlite3` |
| Charts | Plotly or Streamlit native charts |
| Config | `python-dotenv`, `.env` with `GROQ_API_KEY` |

## 6. Features

### F1. Conversational Agent (core)
Chat UI with message history. The LLM decides which tool to call, executes it, then answers using the tool result. Multi-step reasoning allowed (max 5 tool iterations per user message).

### F2. Agent Tools (function calling)
| Tool | Args | Behavior |
|---|---|---|
| `search_books` | query, subject?, available_only? | Semantic search over book titles/descriptions (embeddings) + keyword fallback. Returns top 5 with availability |
| `get_book_details` | book_id | Full details, copies available, reservation queue length |
| `check_availability` | book_id or title | Copies available, and expected due date of the earliest return if none |
| `issue_book` | member_id, book_id | Checks: max 3 active loans, no unpaid fine above Rs. 50, copies available. Due date = today + 14 days |
| `return_book` | member_id, book_id | Marks returned, calculates fine, restores copy, notifies the next reservation holder |
| `renew_book` | member_id, book_id | Allowed once, +7 days, only if no pending reservation and not overdue |
| `reserve_book` | member_id, book_id | Adds to queue if no copies available |
| `get_my_loans` | member_id | Active loans with due dates, overdue flags, current fine |
| `calculate_fine` | member_id | Total pending fine, per-book breakdown |
| `recommend_books` | member_id, preference_text | Uses member borrowing history + preference text, embeddings similarity, returns 3 books with a reason each |
| `search_policies` | question | RAG: retrieves top 3 policy chunks from ChromaDB; LLM answers only from them |

The current `member_id` is injected by the app from the session (the user never types it, and the LLM must not ask for it).

### F3. Policy RAG
Library policies stored in `data/policies/*.md` (borrowing rules, fines, lost books, timings, membership, digital resources, code of conduct). Chunked (~300 chars, overlap 50), embedded, stored in ChromaDB. Answers must show source file name.

### F4. Safety and Guardrails
- Answer about books/loans only from tool results. If not found: "I couldn't find that in our library" + closest alternatives.
- Write actions (issue, return, renew, reserve) require an explicit user confirmation message before the tool is called ("Confirm issue of X? yes/no").
- Refuse off-topic requests politely (a librarian only).
- Never reveal other members' data.
- Handle tool errors and Groq rate limits gracefully (retry once, then a friendly message).

### F5. Multilingual and Voice (bonus, build after core works)
- Reply in the same language the user writes (English, Hindi, Hinglish, Kannada). Tool arguments stay in English.
- Mic button using `st.audio_input`; audio sent to Groq Whisper; transcript placed in chat as the user message.

### F6. Browse Catalog page
Searchable/filterable table (subject, author, availability), book detail expander, "Ask LibraMind about this book" shortcut.

### F7. Admin Dashboard page
- KPIs: total books, active loans, overdue loans, total pending fines, active members.
- Charts: top 10 most borrowed books, loans per subject, loans per day (last 30 days).
- Overdue table with member name, book, days overdue, fine.
- Add new book form (also embeds it in vector store).
- Sidebar toggle: "Student view / Librarian view".

### F8. Transparency panel
Under each assistant reply, an expander "How I got this" showing tools called, arguments, and raw results. Helps demo and viva.

## 7. Data Model (SQLite)
- `books(id, title, author, subject, isbn, description, total_copies, available_copies, published_year, language)`
- `members(id, name, email, department, year, joined_on)`
- `loans(id, member_id, book_id, issued_on, due_on, returned_on, renewed_count, fine_paid)`
- `reservations(id, member_id, book_id, reserved_on, status)` status: active / fulfilled / cancelled
- `chat_logs(id, member_id, role, content, created_at)`

Fine = Rs. 2 per day per book after due date. Max 3 active loans. Loan period 14 days, one renewal of 7 days.

## 8. Seed Data (generated by `seed.py`)
- 60 realistic books across: DSA, OS, DBMS, Networks, AI, ML, Deep Learning, NLP, Software Engineering, Python, Java, Web Dev, Maths, Self-help, Fiction. Each with a 1-2 line description (needed for semantic search).
- 8 members with Indian names across CSE/ISE/ECE.
- 25 loans with mixed states: active, returned, overdue (some overdue by 3 to 20 days), and 3 reservations.
- 7 policy markdown files in `data/policies/`.

## 9. Architecture
```
Streamlit UI (Chat | Catalog | Admin)
        |
   agent.py  -- Groq LLM (tool-calling loop, max 5 iterations)
        |
   tools.py  -- 11 tool functions -- db.py (SQLite)
        |
   rag.py    -- ChromaDB + sentence-transformers (books + policies collections)
        |
   voice.py  -- Groq Whisper
```
Project structure:
```
libramind/
  app.py                  # Streamlit entry, chat page
  pages/1_Catalog.py
  pages/2_Admin_Dashboard.py
  agent.py  tools.py  db.py  rag.py  voice.py  config.py
  seed.py
  data/policies/*.md
  tests/eval_queries.py   # 20 test queries with expected tool + pass/fail report
  requirements.txt  .env.example  README.md
```

## 10. System Prompt (for the agent)
You are LibraMind, the virtual librarian of the college library. Use tools for every fact about books, loans, fines, and policies; never guess. Ask the user to confirm before any issue/return/renew/reserve. If something is not found, say so and suggest alternatives. Reply in the user's language, short and friendly, with availability and due dates when relevant. Stay on library topics only.

## 11. Non-Functional Requirements
- Response time under 5 s for typical queries.
- App starts with `streamlit run app.py` after `python seed.py`.
- No hardcoded secrets. Clear error if `GROQ_API_KEY` is missing.
- Code commented and modular, easy to explain in viva.

## 12. Acceptance Criteria
1. "Is Clean Code available?" returns correct data from DB, with alternatives if 0 copies.
2. "Mujhe machine learning shuru karni hai, kya padhu?" returns 3 explained recommendations in Hinglish.
3. "Issue Deep Learning for me" asks for confirmation, then issues; DB updated; a 4th active loan is refused with a reason.
4. Returning an overdue book calculates the correct fine (Rs. 2 x days).
5. "What is the fine for losing a book?" answered via RAG with the source file shown.
6. "Do you have a book on Quantum Physics?" does not hallucinate.
7. Admin dashboard charts render with seeded data.
8. Voice input transcribes and works end to end (bonus).
9. `tests/eval_queries.py` passes at least 17/20.

## 13. Evaluation Plan (for report)
- Tool selection accuracy on 20 test queries.
- Hallucination test: 5 queries about non-existent books/policies.
- Latency measured per query.
- Small user test with 5 classmates (ease of use rating 1 to 5).

## 14. Future Scope
Barcode/cover scan using a vision model, email/WhatsApp due reminders, collaborative-filtering recommendations, integration with a real library system (Koha), digital book Q&A with citations.

## 15. Build Order (one night)
1. db.py + seed.py + policies (30 min)
2. tools.py + rag.py (45 min)
3. agent.py + chat UI + transparency panel (45 min)
4. Catalog + Admin pages (30 min)
5. Voice + multilingual (20 min)
6. Eval script + README + screenshots (20 min)
