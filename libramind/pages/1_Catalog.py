"""
1_Catalog.py – Searchable and filterable library catalog with book inspection.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from db import get_conn
from theme import apply_theme

st.set_page_config(page_title="Catalog - LibraMind", page_icon="📖", layout="wide")
apply_theme()

with st.sidebar:
    st.markdown("## 📖 **LibraMind Catalog**")
    st.caption("Book Discovery & Inventory")
    if st.button("💬 Go to Student Chat", use_container_width=True):
        st.switch_page("app.py")
    if st.button("📊 Go to Admin Dashboard", use_container_width=True):
        st.switch_page("pages/2_Admin_Dashboard.py")
    st.divider()

st.title("📖 Library Catalog")
st.caption("Search, filter, and inspect the library's physical and digital volumes.")

# Load catalog data
conn = get_conn()
df = pd.read_sql_query("SELECT * FROM books ORDER BY title ASC", conn)
res_df = pd.read_sql_query(
    "SELECT book_id, COUNT(*) as active_res FROM reservations WHERE status='active' GROUP BY book_id",
    conn
)
conn.close()

res_map = dict(zip(res_df["book_id"], res_df["active_res"])) if not res_df.empty else {}

# Filters
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    search_query = st.text_input("🔍 Search by Title or Author", "").strip().lower()
with col2:
    all_subjects = sorted(df["subject"].dropna().unique().tolist())
    selected_subjects = st.multiselect("Filter by Subject", all_subjects, default=[])
with col3:
    st.write("")
    st.write("")
    available_only = st.checkbox("Available only", value=False)

# Apply filters
filtered_df = df.copy()
if search_query:
    filtered_df = filtered_df[
        filtered_df["title"].str.lower().str.contains(search_query, na=False) |
        filtered_df["author"].str.lower().str.contains(search_query, na=False)
    ]
if selected_subjects:
    filtered_df = filtered_df[filtered_df["subject"].isin(selected_subjects)]
if available_only:
    filtered_df = filtered_df[filtered_df["available_copies"] > 0]

# Display table
filtered_df["Copies (Avail/Total)"] = (
    filtered_df["available_copies"].astype(str) + " / " + filtered_df["total_copies"].astype(str)
)
display_df = filtered_df[["title", "author", "subject", "Copies (Avail/Total)", "published_year"]].rename(
    columns={"title": "Title", "author": "Author", "subject": "Subject", "published_year": "Year"}
)

st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🔍 Inspect Book Details")

if not filtered_df.empty:
    book_options = {f"{r['title']} — {r['author']}": r for _, r in filtered_df.iterrows()}
    chosen_label = st.selectbox("Select a book to view summary:", list(book_options.keys()))
    book = book_options[chosen_label]

    active_res = res_map.get(book["id"], 0)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"**Description & Summary:**")
        st.write(book["description"] or "No description available.")
        st.markdown(
            f"**ISBN:** `{book['isbn'] or 'N/A'}` &nbsp;|&nbsp; **Language:** {book['language']} &nbsp;|&nbsp; "
            f"**Subject:** {book['subject']} &nbsp;|&nbsp; **Published Year:** {book['published_year']}"
        )
    with c2:
        avail_str = (
            f"🟢 **{book['available_copies']} of {book['total_copies']}** available"
            if book["available_copies"] > 0
            else "🔴 **0 available** (Checked out)"
        )
        st.markdown(f"**Status:** {avail_str}")
        st.markdown(f"**Active Reservations:** {active_res}")

        if st.button("💬 Ask LibraMind about this book", use_container_width=True):
            st.session_state["prefilled_question"] = f"Is '{book['title']}' available? Can you tell me about it?"
            st.switch_page("app.py")
else:
    st.info("No books match the current filters.")
