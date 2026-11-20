# LibraMind — AI Virtual Librarian

An intelligent virtual librarian featuring autonomous tool calling over SQLite, semantic book and policy RAG, and voice interaction.

## Quick Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your `GROQ_API_KEY`
3. `python seed.py`
4. `streamlit run app.py`

## Sample Queries
- "Is Clean Code available?"
- "What books do I have issued?"
- "Issue Modern Operating Systems for me"
- "What is the fine for returning an overdue book?"
- "Recommend 3 machine learning books for beginners"
- "Mujhe python sikhni hai, kaunsi book padhu?"

## Architecture
Streamlit UI (Chat, Catalog, Admin Dashboard) ➔ Groq LLM Agent (Tool Calling) ➔ SQLite3 Database & ChromaDB Vector Store with Groq Whisper STT.
