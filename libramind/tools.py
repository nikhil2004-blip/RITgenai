"""
tools.py – Library business tools for virtual librarian.
All functions take member_id as first argument and return a JSON-serializable dict.
Never raises exceptions (returns {"error": "..."}).
"""
from datetime import date, timedelta
import json
import sqlite3
from typing import Dict, Any, List, Optional, Union

from db import get_conn
from config import LOAN_DAYS, RENEW_DAYS, MAX_LOANS, FINE_PER_DAY, FINE_BLOCK_LIMIT
import rag


# ---------------------------------------------------------------------------
# Fine & Resolution Helpers
# ---------------------------------------------------------------------------
def _resolve_book(book_ident: Any, cur) -> Optional[sqlite3.Row]:
    """Resolve a book by integer ID, string ID, or title matching."""
    if book_ident is None:
        return None
    try:
        bid = int(book_ident)
        cur.execute("SELECT * FROM books WHERE id = ?", (bid,))
        row = cur.fetchone()
        if row:
            return row
    except (ValueError, TypeError):
        pass

    t_str = str(book_ident).strip()
    if not t_str:
        return None

    cur.execute("SELECT * FROM books WHERE title = ? LIMIT 1", (t_str,))
    row = cur.fetchone()
    if row:
        return row

    cur.execute("SELECT * FROM books WHERE title LIKE ? LIMIT 1", (f"%{t_str}%",))
    return cur.fetchone()


def pending_fine(member_id: int) -> float:
    """
    pending_fine = sum(fine_amount of returned loans with fine_paid=0) + live fine of active overdue loans.
    """
    today_iso = date.today().isoformat()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT COALESCE(SUM(fine_amount), 0) FROM loans 
               WHERE member_id = ? AND returned_on IS NOT NULL AND fine_paid = 0""",
            (member_id,)
        )
        returned_unpaid = float(cur.fetchone()[0] or 0.0)

        cur.execute(
            """SELECT due_on FROM loans 
               WHERE member_id = ? AND returned_on IS NULL AND due_on < ?""",
            (member_id, today_iso)
        )
        active_overdue = cur.fetchall()
        active_live = 0.0
        today_date = date.today()
        for row in active_overdue:
            due_d = date.fromisoformat(row["due_on"])
            days = (today_date - due_d).days
            if days > 0:
                active_live += days * FINE_PER_DAY

        return round(returned_unpaid + active_live, 2)
    except Exception:
        return 0.0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Book Discovery Tools
# ---------------------------------------------------------------------------
def search_books(
    member_id: int,
    query: str = "",
    subject: Optional[str] = None,
    available_only: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Search catalog using LIKE match + semantic vector search.
    Returns up to 5 matching books.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        q_clean = str(query or "").strip()

        # Handle empty query gracefully
        if not q_clean:
            cur.execute(
                """SELECT id, title, author, subject, available_copies, total_copies 
                   FROM books ORDER BY available_copies DESC LIMIT 5"""
            )
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return {"books": rows}

        # 1. Exact / Substring matches via LIKE
        like_pattern = f"%{q_clean}%"
        cur.execute(
            """SELECT id, title, author, subject, available_copies, total_copies 
               FROM books 
               WHERE title LIKE ? OR author LIKE ?""",
            (like_pattern, like_pattern)
        )
        like_rows = [dict(r) for r in cur.fetchall()]
        like_ids = {r["id"] for r in like_rows}

        # 2. Semantic search for top 8
        sem_results = rag.semantic_search_books(q_clean, k=8)
        sem_ids = [book_id for book_id, _ in sem_results if book_id not in like_ids]

        sem_rows = []
        if sem_ids:
            placeholders = ",".join("?" for _ in sem_ids)
            cur.execute(
                f"""SELECT id, title, author, subject, available_copies, total_copies 
                   FROM books WHERE id IN ({placeholders})""",
                sem_ids
            )
            sem_map = {r["id"]: dict(r) for r in cur.fetchall()}
            for bid in sem_ids:
                if bid in sem_map:
                    sem_rows.append(sem_map[bid])

        conn.close()

        combined = like_rows + sem_rows

        if subject:
            sub_lower = str(subject).strip().lower()
            combined = [b for b in combined if b["subject"].lower() == sub_lower]

        if available_only:
            combined = [b for b in combined if b["available_copies"] > 0]

        return {"books": combined[:5]}
    except Exception as e:
        return {"error": str(e)}


def get_book_details(member_id: int, book_id: Any = None, **kwargs) -> Dict[str, Any]:
    """Full details of a book, copies available, and active reservation count."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        book_row = _resolve_book(book_id, cur)
        if not book_row:
            conn.close()
            return {"error": f"Book '{book_id}' not found."}

        book = dict(book_row)
        cur.execute(
            "SELECT COUNT(*) FROM reservations WHERE book_id = ? AND status = 'active'",
            (book["id"],)
        )
        active_reservations = cur.fetchone()[0]

        cur.execute(
            """SELECT MIN(due_on) FROM loans 
               WHERE book_id = ? AND returned_on IS NULL""",
            (book["id"],)
        )
        min_due = cur.fetchone()[0]
        conn.close()

        book["active_reservations"] = active_reservations
        book["earliest_due_on"] = min_due
        return {"book": book}
    except Exception as e:
        return {"error": str(e)}


def check_availability(member_id: int, title: str = "", **kwargs) -> Dict[str, Any]:
    """Check availability by title (or ID) with earliest return date and reservation queue."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        row = _resolve_book(title, cur)
        if not row:
            conn.close()
            return {"error": f"Book '{title}' not found in the library catalog."}

        res = dict(row)
        if res["available_copies"] == 0:
            cur.execute(
                """SELECT MIN(due_on) FROM loans 
                   WHERE book_id = ? AND returned_on IS NULL""",
                (res["id"],)
            )
            res["earliest_due_on"] = cur.fetchone()[0]

            cur.execute(
                """SELECT COUNT(*) FROM reservations 
                   WHERE book_id = ? AND status = 'active'""",
                (res["id"],)
            )
            res["active_reservations"] = cur.fetchone()[0]

        conn.close()
        return res
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Loan Management Tools (Write actions require confirmation)
# ---------------------------------------------------------------------------
def issue_book(member_id: int, book_id: Any = None, confirmed: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Issue a book for 14 days.
    Checks: book exists, available_copies>0, member active loans < MAX_LOANS,
    member doesn't already hold it, pending_fine <= FINE_BLOCK_LIMIT, subject != 'Reference'.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        book = _resolve_book(book_id, cur)
        if not book:
            conn.close()
            return {"error": f"Book '{book_id}' not found."}

        actual_book_id = book["id"]

        if book["subject"] == "Reference":
            conn.close()
            return {"error": f"'{book['title']}' is a Reference book and cannot be issued outside the library."}

        if book["available_copies"] <= 0:
            conn.close()
            return {"error": f"No copies of '{book['title']}' are currently available for issue."}

        # Check active loans count
        cur.execute(
            "SELECT COUNT(*) FROM loans WHERE member_id = ? AND returned_on IS NULL",
            (member_id,)
        )
        active_loans_count = cur.fetchone()[0]
        if active_loans_count >= MAX_LOANS:
            conn.close()
            return {"error": f"Maximum limit of {MAX_LOANS} active loans reached. Please return a book first."}

        # Check if member already has this book issued
        cur.execute(
            "SELECT id FROM loans WHERE member_id = ? AND book_id = ? AND returned_on IS NULL",
            (member_id, actual_book_id)
        )
        if cur.fetchone():
            conn.close()
            return {"error": f"You already have an active loan for '{book['title']}'."}

        # Check pending fines
        p_fine = pending_fine(member_id)
        if p_fine > FINE_BLOCK_LIMIT:
            conn.close()
            return {
                "error": f"Borrowing blocked: pending fines of Rs. {p_fine:.2f} exceed the limit of Rs. {FINE_BLOCK_LIMIT}."
            }

        due_date = (date.today() + timedelta(days=LOAN_DAYS)).isoformat()

        if not confirmed:
            conn.close()
            return {
                "status": "needs_confirmation",
                "summary": f"Issue '{book['title']}' to member #{member_id} for {LOAN_DAYS} days (due {due_date})?"
            }

        # Execute issue
        today_iso = date.today().isoformat()
        cur.execute(
            """INSERT INTO loans (member_id, book_id, issued_on, due_on, returned_on, renewed_count, fine_amount, fine_paid)
               VALUES (?, ?, ?, ?, NULL, 0, 0, 0)""",
            (member_id, actual_book_id, today_iso, due_date)
        )
        cur.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
            (actual_book_id,)
        )
        cur.execute(
            """UPDATE reservations SET status = 'fulfilled' 
               WHERE member_id = ? AND book_id = ? AND status = 'active'""",
            (member_id, actual_book_id)
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Successfully issued '{book['title']}'. Due on {due_date}.",
            "due_on": due_date
        }
    except Exception as e:
        return {"error": str(e)}


def return_book(member_id: int, book_id: Any = None, confirmed: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Return a borrowed book, calculate overdue fine, increment copies,
    and alert if another member has an active reservation.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        book = _resolve_book(book_id, cur)
        if not book:
            conn.close()
            return {"error": f"Book '{book_id}' not found."}

        actual_book_id = book["id"]

        cur.execute(
            """SELECT * FROM loans 
               WHERE member_id = ? AND book_id = ? AND returned_on IS NULL 
               ORDER BY issued_on ASC LIMIT 1""",
            (member_id, actual_book_id)
        )
        loan = cur.fetchone()
        if not loan:
            conn.close()
            return {"error": f"No active loan found for '{book['title']}' under your account."}

        today_date = date.today()
        due_d = date.fromisoformat(loan["due_on"])
        overdue_days = max(0, (today_date - due_d).days)
        fine = overdue_days * FINE_PER_DAY

        if not confirmed:
            conn.close()
            summary = f"Return '{book['title']}'."
            if overdue_days > 0:
                summary += f" Overdue by {overdue_days} days. Fine applicable: Rs. {fine}."
            else:
                summary += " On-time return, no fine."
            summary += " Please confirm return."
            return {"status": "needs_confirmation", "summary": summary}

        today_iso = today_date.isoformat()
        cur.execute(
            """UPDATE loans SET returned_on = ?, fine_amount = ? WHERE id = ?""",
            (today_iso, fine, loan["id"])
        )
        cur.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
            (actual_book_id,)
        )

        cur.execute(
            """SELECT r.id, m.name FROM reservations r 
               JOIN members m ON r.member_id = m.id 
               WHERE r.book_id = ? AND r.status = 'active' 
               ORDER BY r.reserved_on ASC LIMIT 1""",
            (actual_book_id,)
        )
        next_res = cur.fetchone()
        conn.commit()
        conn.close()

        res_msg = f"Successfully returned '{book['title']}'."
        if fine > 0:
            res_msg += f" Overdue fine recorded: Rs. {fine}."
        if next_res:
            res_msg += f" Note: This copy is reserved for {next_res['name']} and will be held for 2 days."

        return {
            "status": "success",
            "fine": fine,
            "overdue_days": overdue_days,
            "message": res_msg
        }
    except Exception as e:
        return {"error": str(e)}


def renew_book(member_id: int, book_id: Any = None, confirmed: bool = False, **kwargs) -> Dict[str, Any]:
    """Renew loan for 7 days if renewed_count==0, not overdue, and no reservation queue."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        book = _resolve_book(book_id, cur)
        if not book:
            conn.close()
            return {"error": f"Book '{book_id}' not found."}

        actual_book_id = book["id"]

        cur.execute(
            """SELECT * FROM loans 
               WHERE member_id = ? AND book_id = ? AND returned_on IS NULL LIMIT 1""",
            (member_id, actual_book_id)
        )
        loan = cur.fetchone()
        if not loan:
            conn.close()
            return {"error": f"No active loan found for '{book['title']}'."}

        if loan["renewed_count"] > 0:
            conn.close()
            return {"error": f"'{book['title']}' has already been renewed once. Multiple renewals are not allowed."}

        today_date = date.today()
        due_d = date.fromisoformat(loan["due_on"])
        if today_date > due_d:
            conn.close()
            return {"error": f"Cannot renew '{book['title']}' because it is overdue. Please return the book and clear fines."}

        cur.execute(
            """SELECT COUNT(*) FROM reservations 
               WHERE book_id = ? AND member_id != ? AND status = 'active'""",
            (actual_book_id, member_id)
        )
        if cur.fetchone()[0] > 0:
            conn.close()
            return {"error": f"Cannot renew '{book['title']}': another member has placed a reservation on it."}

        new_due = (due_d + timedelta(days=RENEW_DAYS)).isoformat()

        if not confirmed:
            conn.close()
            return {
                "status": "needs_confirmation",
                "summary": f"Renew '{book['title']}' for {RENEW_DAYS} additional days until {new_due}?"
            }

        cur.execute(
            "UPDATE loans SET due_on = ?, renewed_count = 1 WHERE id = ?",
            (new_due, loan["id"])
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "new_due_on": new_due,
            "message": f"Successfully renewed '{book['title']}'. New due date is {new_due}."
        }
    except Exception as e:
        return {"error": str(e)}


def reserve_book(member_id: int, book_id: Any = None, confirmed: bool = False, **kwargs) -> Dict[str, Any]:
    """Reserve a book when 0 copies available."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        book = _resolve_book(book_id, cur)
        if not book:
            conn.close()
            return {"error": f"Book '{book_id}' not found."}

        actual_book_id = book["id"]

        if book["available_copies"] > 0:
            conn.close()
            return {
                "error": f"'{book['title']}' currently has {book['available_copies']} copy/copies available. You can issue it directly instead of reserving."
            }

        cur.execute(
            "SELECT id FROM loans WHERE member_id = ? AND book_id = ? AND returned_on IS NULL",
            (member_id, actual_book_id)
        )
        if cur.fetchone():
            conn.close()
            return {"error": f"You currently hold an active loan for '{book['title']}'."}

        cur.execute(
            "SELECT id FROM reservations WHERE member_id = ? AND book_id = ? AND status = 'active'",
            (member_id, actual_book_id)
        )
        if cur.fetchone():
            conn.close()
            return {"error": f"You already have an active reservation for '{book['title']}'."}

        if not confirmed:
            conn.close()
            return {
                "status": "needs_confirmation",
                "summary": f"Place an active reservation for '{book['title']}'? You will have 2 days to pick it up once returned."
            }

        today_iso = date.today().isoformat()
        cur.execute(
            """INSERT INTO reservations (member_id, book_id, reserved_on, status)
               VALUES (?, ?, ?, 'active')""",
            (member_id, actual_book_id, today_iso)
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Reservation confirmed for '{book['title']}'. Held for 2 days once a copy is returned."
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Member Status & Analytics Tools
# ---------------------------------------------------------------------------
def get_my_loans(member_id: int, **kwargs) -> Dict[str, Any]:
    """Active loans with due_on, days_left or days_overdue, and live fine."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT l.id, l.book_id, b.title, b.author, b.subject, l.issued_on, l.due_on, l.renewed_count 
               FROM loans l 
               JOIN books b ON l.book_id = b.id 
               WHERE l.member_id = ? AND l.returned_on IS NULL 
               ORDER BY l.due_on ASC""",
            (member_id,)
        )
        rows = cur.fetchall()
        conn.close()

        today_date = date.today()
        loan_list = []
        total_live_fine = 0.0

        for r in rows:
            due_d = date.fromisoformat(r["due_on"])
            overdue = today_date > due_d
            if overdue:
                days_overdue = (today_date - due_d).days
                days_left = 0
                fine = days_overdue * FINE_PER_DAY
            else:
                days_overdue = 0
                days_left = (due_d - today_date).days
                fine = 0

            total_live_fine += fine
            loan_list.append({
                "loan_id": r["id"],
                "book_id": r["book_id"],
                "title": r["title"],
                "author": r["author"],
                "subject": r["subject"],
                "issued_on": r["issued_on"],
                "due_on": r["due_on"],
                "renewed_count": r["renewed_count"],
                "is_overdue": overdue,
                "days_left": days_left,
                "days_overdue": days_overdue,
                "fine": fine
            })

        return {
            "active_loans": loan_list,
            "total_active_loans": len(loan_list),
            "total_live_fine": total_live_fine
        }
    except Exception as e:
        return {"error": str(e)}


def calculate_fine(member_id: int, **kwargs) -> Dict[str, Any]:
    """Pending total fine plus per-loan breakdown."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        today_date = date.today()
        today_iso = today_date.isoformat()

        cur.execute(
            """SELECT l.id, b.title, l.issued_on, l.returned_on, l.fine_amount 
               FROM loans l 
               JOIN books b ON l.book_id = b.id 
               WHERE l.member_id = ? AND l.returned_on IS NOT NULL AND l.fine_paid = 0 AND l.fine_amount > 0""",
            (member_id,)
        )
        returned_fines = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT l.id, b.title, l.issued_on, l.due_on 
               FROM loans l 
               JOIN books b ON l.book_id = b.id 
               WHERE l.member_id = ? AND l.returned_on IS NULL AND l.due_on < ?""",
            (member_id, today_iso)
        )
        overdue_active = []
        for r in cur.fetchall():
            due_d = date.fromisoformat(r["due_on"])
            days = (today_date - due_d).days
            overdue_active.append({
                "loan_id": r["id"],
                "title": r["title"],
                "issued_on": r["issued_on"],
                "due_on": r["due_on"],
                "days_overdue": days,
                "fine_amount": days * FINE_PER_DAY
            })

        conn.close()

        total = sum(item["fine_amount"] for item in returned_fines) + sum(item["fine_amount"] for item in overdue_active)
        return {
            "total_pending_fine": round(total, 2),
            "returned_unpaid_fines": returned_fines,
            "active_overdue_fines": overdue_active,
            "borrowing_blocked": total > FINE_BLOCK_LIMIT
        }
    except Exception as e:
        return {"error": str(e)}


def recommend_books(member_id: int, preference_text: str = "", **kwargs) -> Dict[str, Any]:
    """Recommend 3 relevant books based on preference and history."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """SELECT DISTINCT l.book_id, b.subject, b.title 
               FROM loans l 
               JOIN books b ON l.book_id = b.id 
               WHERE l.member_id = ?""",
            (member_id,)
        )
        history = cur.fetchall()
        borrowed_ids = {r["book_id"] for r in history}
        borrowed_subjects = list({r["subject"] for r in history})

        combined_query = str(preference_text or "").strip()
        if borrowed_subjects:
            combined_query += f" (Interests: {', '.join(borrowed_subjects[:3])})"

        results = rag.semantic_search_books(combined_query, k=15)

        recommendations = []
        for book_id, score in results:
            if book_id in borrowed_ids:
                continue

            cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            b = cur.fetchone()
            if not b:
                continue

            why_reason = f"Matches your interest in '{b['subject']}': {b['description']}"
            recommendations.append({
                "id": b["id"],
                "title": b["title"],
                "author": b["author"],
                "subject": b["subject"],
                "available_copies": b["available_copies"],
                "why": why_reason
            })

            if len(recommendations) >= 3:
                break

        conn.close()
        return {"recommendations": recommendations}
    except Exception as e:
        return {"error": str(e)}


def search_policies(member_id: int, question: str = "", **kwargs) -> Dict[str, Any]:
    """RAG search across library policy markdown files with source citations."""
    try:
        chunks = rag.search_policies(str(question or ""), k=3)
        return {"policies": chunks}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool Schemas for Groq / OpenAI Tool Calling (WITHOUT member_id)
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": "Search the library catalog by title, author, or topic using semantic and keyword matching.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": ["string", "null"], "description": "The search keywords or description of the book"},
                    "subject": {"type": ["string", "null"], "description": "Optional category filter like DSA, OS, DBMS, AI, ML, Python, etc. Pass null or omit if not filtering by subject."},
                    "available_only": {"type": ["boolean", "null"], "description": "Whether to only return books with available copies"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_book_details",
            "description": "Get complete information about a specific book by its ID or title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": ["integer", "string"], "description": "The unique numerical ID or title of the book"}
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if a book is available by title, and get earliest return date and reservation queue if out of stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": ["string", "null"], "description": "Title or partial title of the book to check"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "issue_book",
            "description": "Issue a book to the student for 14 days. First call with confirmed=false to preview, then confirmed=true when user confirms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": ["integer", "string"], "description": "The numerical ID or title of the book to issue"},
                    "confirmed": {"type": ["boolean", "null"], "description": "true only after the user has explicitly said yes to the confirmation, false otherwise"}
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "return_book",
            "description": "Process return of a currently borrowed book and record fines if overdue. First preview with confirmed=false, then confirmed=true on confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": ["integer", "string"], "description": "The numerical ID or title of the book to return"},
                    "confirmed": {"type": ["boolean", "null"], "description": "true only after the user has explicitly said yes to the confirmation, false otherwise"}
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "renew_book",
            "description": "Renew a borrowed book for 7 extra days. First preview with confirmed=false, then confirmed=true when user approves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": ["integer", "string"], "description": "The numerical ID or title of the book to renew"},
                    "confirmed": {"type": ["boolean", "null"], "description": "true only after the user has explicitly said yes to the confirmation, false otherwise"}
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_book",
            "description": "Reserve a book when copies are 0. First preview with confirmed=false, then confirmed=true when user confirms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {"type": ["integer", "string"], "description": "The numerical ID or title of the book to reserve"},
                    "confirmed": {"type": ["boolean", "null"], "description": "true only after the user has explicitly said yes to the confirmation, false otherwise"}
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_loans",
            "description": "Retrieve the current student's active book loans, due dates, overdue statuses, and live fines.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_fine",
            "description": "Calculate total pending fines for the student with a per-book breakdown and check if borrowing is blocked.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_books",
            "description": "Recommend 3 relevant books based on the student's preference and borrowing history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preference_text": {"type": ["string", "null"], "description": "What kind of books or topics the user wants to read"}
                },
                "required": ["preference_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_policies",
            "description": "Search library policy documents regarding borrowing rules, fines, timings, lost books, digital resources, or conduct.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": ["string", "null"], "description": "The policy question to look up"}
                },
                "required": ["question"]
            }
        }
    }
]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "search_books": search_books,
    "get_book_details": get_book_details,
    "check_availability": check_availability,
    "issue_book": issue_book,
    "return_book": return_book,
    "renew_book": renew_book,
    "reserve_book": reserve_book,
    "get_my_loans": get_my_loans,
    "calculate_fine": calculate_fine,
    "recommend_books": recommend_books,
    "search_policies": search_policies,
}


def dispatch(name: str, args: Dict[str, Any], member_id: int) -> Dict[str, Any]:
    """Run the tool matching `name` with member_id injected first. Never raises."""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return {"error": f"Tool '{name}' is not recognized."}

    # Clean out any member_id the model might have sent
    clean_args = {k: v for k, v in args.items() if k != "member_id"}
    
    # Safe boolean normalization
    if "confirmed" in clean_args:
        clean_args["confirmed"] = bool(clean_args["confirmed"]) if clean_args["confirmed"] is not None else False
    if "available_only" in clean_args:
        clean_args["available_only"] = bool(clean_args["available_only"]) if clean_args["available_only"] is not None else False

    # Safe string normalization
    for str_key in ["query", "title", "question", "preference_text"]:
        if str_key in clean_args and clean_args[str_key] is None:
            clean_args[str_key] = ""

    try:
        return func(member_id, **clean_args)
    except Exception as e:
        return {"error": f"Error running {name}: {str(e)}"}
