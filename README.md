# 🏛️ LibraMind — AI Virtual Librarian & Intelligent Library System

LibraMind is an autonomous GenAI-powered virtual librarian web application built with Streamlit, Groq LLM tool calling, SQLite, ChromaDB vector search, and Whisper speech-to-text.

## 🚀 Quick Start (Local Setup)

1. **Clone repository:**
   ```bash
   git clone <your-repo-url>
   cd genai/libramind
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   copy .env.example .env
   # Add your free Groq API key in .env (https://console.groq.com/keys)
   ```

4. **Initialize Database & Seed Data:**
   ```bash
   python seed.py
   ```

5. **Launch Application:**
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Deploy to Streamlit Community Cloud

1. Push this repository to your GitHub.
2. Sign in to [share.streamlit.io](https://share.streamlit.io).
3. Click **"New App"**:
   - **Repository:** `your-username/your-repo`
   - **Branch:** `main` (or `master`)
   - **Main file path:** `libramind/app.py`
4. In **Advanced Settings ➔ Secrets**, add:
   ```toml
   GROQ_API_KEY = "gsk_your_groq_api_key_here"
   ```
5. Click **Deploy!** The application self-heals and auto-initializes the database and vector indexes on first startup.

---

## 📖 Complete Documentation
For in-depth viva preparation, data flow diagrams, system architecture, and tech stack details, see [PROJECT_GUIDE.md](file:///libramind/PROJECT_GUIDE.md).
