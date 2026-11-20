"""
2_Admin_Dashboard.py – Librarian administration, analytics, and bulk Excel import.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

from db import get_conn
from config import FINE_PER_DAY
import rag
from theme import apply_theme

st.set_page_config(page_title="Admin Dashboard - LibraMind", page_icon="📊", layout="wide")
apply_theme()

st.title("📊 Librarian Admin Dashboard")
st.caption("Circulation analytics, catalog management, and bulk Excel catalog importation.")

# ---------------------------------------------------------------------------
# Cached Data Loaders (ttl=10)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=10)
def load_kpis_and_overdue():
    conn = get_conn()
    cur = conn.cursor()

    # Total books count
    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_copies), 0) FROM books")
    total_titles, total_copies = cur.fetchone()

    # Total registered members
    cur.execute("SELECT COUNT(*) FROM members")
    total_members = cur.fetchone()[0]

    # Active loans count
    cur.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL")
    active_loans = cur.fetchone()[0]

    # Loans list for overdue calculation and pending fines
    cur.execute("""
        SELECT l.id, m.name as member_name, b.title as book_title, l.issued_on, l.due_on, l.returned_on, l.fine_amount, l.fine_paid
        FROM loans l
        JOIN members m ON l.member_id = m.id
        JOIN books b ON l.book_id = b.id
    """)
    all_loans = [dict(r) for r in cur.fetchall()]
    conn.close()

    today = date.today()
    overdue_loans_list = []
    total_fines = 0.0

    for loan in all_loans:
        if loan["returned_on"] is None:
            due_d = date.fromisoformat(loan["due_on"])
            if today > due_d:
                days_overdue = (today - due_d).days
                fine = days_overdue * FINE_PER_DAY
                total_fines += fine
                overdue_loans_list.append({
                    "Member": loan["member_name"],
                    "Book": loan["book_title"],
                    "Due Date": loan["due_on"],
                    "Days Overdue": days_overdue,
                    "Fine (Rs.)": fine
                })
        else:
            if not loan["fine_paid"] and loan["fine_amount"]:
                total_fines += loan["fine_amount"]

    overdue_df = pd.DataFrame(overdue_loans_list)
    return {
        "total_books": total_titles,
        "total_copies": total_copies,
        "total_members": total_members,
        "active_loans": active_loans,
        "overdue_count": len(overdue_loans_list),
        "total_fines": round(total_fines, 2),
        "overdue_df": overdue_df
    }


@st.cache_data(ttl=10)
def load_chart_data():
    conn = get_conn()

    # 1. Top 10 most borrowed books
    top_books_df = pd.read_sql_query("""
        SELECT b.title as Title, COUNT(l.id) as BorrowCount
        FROM loans l
        JOIN books b ON l.book_id = b.id
        GROUP BY b.id
        ORDER BY BorrowCount DESC
        LIMIT 10
    """, conn)

    # 2. Loans by subject
    loans_by_subject_df = pd.read_sql_query("""
        SELECT b.subject as Subject, COUNT(l.id) as LoanCount
        FROM loans l
        JOIN books b ON l.book_id = b.id
        GROUP BY b.subject
        ORDER BY LoanCount DESC
    """, conn)

    # 3. Loans issued per day over the last 30 days
    loans_per_day_df = pd.read_sql_query("""
        SELECT issued_on as IssueDate, COUNT(id) as LoansIssued
        FROM loans
        WHERE issued_on >= date('now', '-30 days')
        GROUP BY issued_on
        ORDER BY issued_on ASC
    """, conn)

    conn.close()
    return top_books_df, loans_by_subject_df, loans_per_day_df


stats = load_kpis_and_overdue()
top_books_df, loans_by_subject_df, loans_per_day_df = load_chart_data()

# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Volumes", f"{stats['total_books']}")
kpi2.metric("Active Loans", f"{stats['active_loans']}")
kpi3.metric("Overdue Loans", f"{stats['overdue_count']}")
kpi4.metric("Pending Fines", f"Rs. {stats['total_fines']:.0f}")
kpi5.metric("Members", f"{stats['total_members']}")

st.divider()

# ---------------------------------------------------------------------------
# Plotly Charts with Aesthetic Color Palette
# ---------------------------------------------------------------------------
st.subheader("📈 Circulation & Activity Insights")
c_left, c_right = st.columns(2)

WARM_PALETTE = ["#7A5B40", "#A48062", "#C9AC91", "#5C4633", "#9B8371", "#8C6D53", "#B59980"]

with c_left:
    if not top_books_df.empty:
        fig_bar = px.bar(
            top_books_df,
            x="BorrowCount",
            y="Title",
            orientation="h",
            title="Top 10 Most Borrowed Books",
            labels={"BorrowCount": "Total Loans", "Title": "Book Title"},
            color="BorrowCount",
            color_continuous_scale=["#DFD5C6", "#7A5B40"]
        )
        fig_bar.update_layout(
            yaxis=dict(autorange="reversed"),
            showlegend=False,
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No borrow records available.")

with c_right:
    if not loans_by_subject_df.empty:
        fig_pie = px.pie(
            loans_by_subject_df,
            names="Subject",
            values="LoanCount",
            title="Loans Distribution by Subject",
            hole=0.4,
            color_discrete_sequence=WARM_PALETTE
        )
        fig_pie.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No loan distribution available.")

if not loans_per_day_df.empty:
    fig_line = px.line(
        loans_per_day_df,
        x="IssueDate",
        y="LoansIssued",
        title="Loans Issued per Day (Last 30 Days)",
        markers=True,
        labels={"IssueDate": "Date", "LoansIssued": "Loans Issued"},
        color_discrete_sequence=["#7A5B40"]
    )
    fig_line.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Overdue Loans Table
# ---------------------------------------------------------------------------
st.subheader("⚠️ Overdue Accounts")
if not stats["overdue_df"].empty:
    st.dataframe(stats["overdue_df"], use_container_width=True, hide_index=True)
else:
    st.success("🎉 All loans are currently within their due dates!")

st.divider()

# ---------------------------------------------------------------------------
# Catalog Management: Bulk Excel/CSV Import & Manual Single Book Add
# ---------------------------------------------------------------------------
st.subheader("📚 Catalog Management")

tab_bulk, tab_single = st.tabs(["📁 Bulk Import (Excel / CSV)", "➕ Add Single Book"])

with tab_bulk:
    st.write("Upload a spreadsheet to import books in bulk. Each row will be automatically inserted and embedded into the vector search index.")

    template_path = Path(__file__).parent.parent / "data" / "sample_books.xlsx"
    if template_path.exists():
        with open(template_path, "rb") as f:
            st.download_button(
                label="📥 Download Sample Excel Template",
                data=f.read(),
                file_name="library_books_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download a pre-formatted Excel template with sample book records"
            )

    uploaded_file = st.file_uploader(
        "Choose an Excel (.xlsx) or CSV file",
        type=["xlsx", "csv"],
        help="Columns: title, author, subject, description, isbn (opt), published_year (opt), language (opt), copies (opt)"
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".xlsx"):
                import_df = pd.read_excel(uploaded_file)
            else:
                import_df = pd.read_csv(uploaded_file)

            # Normalize column names
            col_map = {str(c).strip().lower(): c for c in import_df.columns}
            
            def get_val(row, *aliases):
                for a in aliases:
                    if a in col_map:
                        val = row[col_map[a]]
                        return val if pd.notna(val) else None
                return None

            st.write(f"**Preview of {len(import_df)} book(s) detected:**")
            st.dataframe(import_df.head(10), use_container_width=True)

            if st.button(f"🚀 Import & Index {len(import_df)} Books", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()

                conn = get_conn()
                cur = conn.cursor()
                imported_count = 0

                for idx, (_, row) in enumerate(import_df.iterrows()):
                    title = get_val(row, "title", "book_title", "name")
                    author = get_val(row, "author", "authors", "writer")
                    subject = get_val(row, "subject", "category", "genre") or "General"
                    description = get_val(row, "description", "summary", "overview") or ""
                    isbn = get_val(row, "isbn")
                    year = get_val(row, "published_year", "year", "pub_year") or date.today().year
                    language = get_val(row, "language", "lang") or "English"
                    copies = int(get_val(row, "copies", "total_copies", "count") or 2)

                    if not title or not author:
                        continue

                    # Insert into SQLite
                    cur.execute("""
                        INSERT INTO books (title, author, subject, isbn, description, published_year, language, total_copies, available_copies)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (str(title).strip(), str(author).strip(), str(subject).strip(), str(isbn).strip() if isbn else None, str(description).strip(), int(year), str(language).strip(), copies, copies))
                    
                    new_id = cur.lastrowid

                    # Embed in ChromaDB
                    rag.add_book_to_index({
                        "id": new_id,
                        "title": str(title).strip(),
                        "author": str(author).strip(),
                        "subject": str(subject).strip(),
                        "description": str(description).strip()
                    })

                    imported_count += 1
                    progress_bar.progress((idx + 1) / len(import_df))
                    status_text.text(f"Imported and embedded: {title} ({idx + 1}/{len(import_df)})")

                conn.commit()
                conn.close()

                st.cache_data.clear()
                status_text.empty()
                progress_bar.empty()
                st.success(f"🎉 Successfully imported and indexed {imported_count} new books into the catalog and vector store!")
                st.rerun()

        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")

with tab_single:
    with st.form("add_single_book_form", clear_on_submit=True):
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            title = st.text_input("Title *")
            author = st.text_input("Author *")
            subject = st.text_input("Subject * (e.g. AI, DSA, Web Dev)")
            isbn = st.text_input("ISBN")
        with f_c2:
            year = st.number_input("Published Year", min_value=1900, max_value=2100, value=date.today().year)
            language = st.selectbox("Language", ["English", "Hindi", "Other"], index=0)
            copies = st.number_input("Copies *", min_value=1, max_value=50, value=2)

        description = st.text_area("Detailed Description & Summary * (Used for semantic search)")
        submitted = st.form_submit_button("Add Book & Index in Vector Store", use_container_width=True)

        if submitted:
            if not title or not author or not subject:
                st.error("Title, Author, and Subject are required fields.")
            else:
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO books (title, author, subject, isbn, description, published_year, language, total_copies, available_copies)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        title.strip(),
                        author.strip(),
                        subject.strip(),
                        isbn.strip() if isbn else None,
                        description.strip(),
                        int(year),
                        language,
                        int(copies),
                        int(copies)
                    ))
                    new_book_id = cur.lastrowid
                    conn.commit()
                    conn.close()

                    # Vector indexing
                    rag.add_book_to_index({
                        "id": new_book_id,
                        "title": title.strip(),
                        "author": author.strip(),
                        "subject": subject.strip(),
                        "description": description.strip()
                    })

                    st.cache_data.clear()
                    st.success(f"✅ '{title}' added and indexed successfully with {copies} copies (ID: {new_book_id})!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add book: {str(e)}")
