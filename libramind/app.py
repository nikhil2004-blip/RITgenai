"""
app.py – Streamlit UI for LibraMind Virtual Librarian.
"""
import os
from datetime import datetime
import hashlib
import streamlit as st

from config import GROQ_API_KEY, DB_PATH
from db import get_conn, init_db
from agent import run_agent
import tools
import voice
from theme import apply_theme

# ---------------------------------------------------------------------------
# Page Configuration & Aesthetic Theme
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LibraMind",
    page_icon="📚",
    layout="wide"
)
apply_theme()


# ---------------------------------------------------------------------------
# Deployment Self-Healing: Ensure Database & Seed Data Exist
# ---------------------------------------------------------------------------
def ensure_db_ready():
    if not os.path.exists(DB_PATH):
        try:
            import seed
        except Exception:
            init_db()
    else:
        try:
            conn = get_conn()
            count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            conn.close()
            if count == 0:
                import seed
        except Exception:
            pass


ensure_db_ready()

# ---------------------------------------------------------------------------
# API Key Verification
# ---------------------------------------------------------------------------
if not GROQ_API_KEY:
    st.error("⚠️ GROQ_API_KEY is missing! Please configure it in your `.env` or Streamlit Cloud Secrets.")
    st.stop()


# ---------------------------------------------------------------------------
# Database Helper for Members & Chat Logs
# ---------------------------------------------------------------------------
def load_members():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, department, year, email FROM members ORDER BY id ASC")
    members = [dict(r) for r in cur.fetchall()]
    conn.close()
    return members


def log_message(member_id: int, role: str, content: str):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO chat_logs (member_id, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (member_id, role, content, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_welcome_messages(m_id: int, m_name: str):
    loan_info = tools.get_my_loans(m_id)
    active_cnt = loan_info.get("total_active_loans", 0)
    overdue_cnt = sum(1 for l in loan_info.get("active_loans", []) if l.get("is_overdue"))
    msg = f"Hello **{m_name}**! You currently have **{active_cnt} active loan(s)**."
    if overdue_cnt > 0:
        msg += f" ⚠️ **Attention:** You have **{overdue_cnt} overdue book(s)** with accumulating fines. Please return or renew them."
    msg += " How can I help you in the library today?"
    return [{"role": "assistant", "content": msg}]


members_list = load_members()
if not members_list:
    st.error("No members found in database. Initializing seed data...")
    import seed
    members_list = load_members()

# ---------------------------------------------------------------------------
# Sidebar Setup
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📚 **LibraMind**")
    st.caption("Intelligent Virtual Librarian")

    # Member Selector
    member_names = {f"{m['name']} ({m['department']} - Yr {m['year']})": m for m in members_list}
    selected_label = st.selectbox("Current Student", list(member_names.keys()))
    selected_member = member_names[selected_label]
    member_id = selected_member["id"]
    member_name = selected_member["name"]

    # Reset chat on member switch
    if st.session_state.get("current_member_id") != member_id:
        st.session_state.current_member_id = member_id
        st.session_state.messages = get_welcome_messages(member_id, member_name)

    st.divider()

    # View Toggle
    view_mode = st.radio("Portal View", ["Student Portal", "Librarian Portal"], index=0)
    if view_mode == "Librarian Portal":
        st.switch_page("pages/2_Admin_Dashboard.py")

    st.divider()

    # Clear Chat
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = get_welcome_messages(member_id, member_name)
        st.rerun()

    st.markdown("### 💡 Quick Queries")
    example_prompts = [
        "Is Clean Code available?",
        "What books do I have issued?",
        "Recommend a machine learning book for beginners",
        "What is the fine for losing a book?"
    ]

    clicked_example = None
    for prompt in example_prompts:
        if st.button(prompt, use_container_width=True, key=f"ex_{prompt}"):
            clicked_example = prompt

# ---------------------------------------------------------------------------
# Main Chat Interface
# ---------------------------------------------------------------------------
st.title(f"Welcome, {member_name}")
st.markdown("Ask anything about book availability, issues, renewals, returns, fines, recommendations, or library policies.")

if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = get_welcome_messages(member_id, member_name)

# Display conversation history with clean aesthetic avatars
for msg in st.session_state.messages:
    avatar = "🏛️" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("tool_trace"):
            with st.expander("🛠️ How I got this (Agent Trace)"):
                st.json(msg["tool_trace"])

# VOICE INPUT (Phase 4)
voice_text = None
if hasattr(st, "audio_input"):
    st.caption("🎙️ Voice Inquiry")
    audio_val = st.audio_input("Record your question", label_visibility="collapsed")
    if audio_val is not None:
        raw_bytes = audio_val.read()
        if raw_bytes:
            audio_hash = hashlib.md5(raw_bytes).hexdigest()
            if st.session_state.get("last_audio_hash") != audio_hash:
                st.session_state["last_audio_hash"] = audio_hash
                with st.spinner("Transcribing your audio inquiry..."):
                    transcribed = voice.transcribe(raw_bytes)
                    if transcribed:
                        voice_text = transcribed

# Handle text input, example query button, voice input, or prefilled question from catalog page
prefilled_query = st.session_state.pop("prefilled_question", None)
user_query = st.chat_input("Ask in English / हिंदी / Hinglish / ಕನ್ನಡ...")
prompt_to_send = prefilled_query or clicked_example or voice_text or user_query

if prompt_to_send:
    # 1. Display and log user message
    st.session_state.messages.append({"role": "user", "content": prompt_to_send})
    log_message(member_id, "user", prompt_to_send)

    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt_to_send)

    # 2. Generate response with agent
    with st.chat_message("assistant", avatar="🏛️"):
        with st.spinner("Consulting library records..."):
            reply_text, tool_trace = run_agent(
                st.session_state.messages,
                member_id=member_id,
                member_name=member_name
            )

        st.markdown(reply_text)
        if tool_trace:
            with st.expander("🛠️ How I got this (Agent Trace)"):
                st.json(tool_trace)

    # 3. Save assistant message and log to DB
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply_text,
        "tool_trace": tool_trace
    })
    log_message(member_id, "assistant", reply_text)
