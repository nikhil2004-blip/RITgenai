"""
config.py – Load environment and define all project-wide constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Support environment variables and Streamlit Cloud secrets
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    try:
        import streamlit as st
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass

# Paths
DB_PATH: str = str(BASE_DIR / "library.db")
CHROMA_PATH: str = str(BASE_DIR / "chroma_db")

# LLM / STT models
LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
STT_MODEL: str = os.getenv("STT_MODEL", "whisper-large-v3-turbo")

# Loan rules
LOAN_DAYS: int = 14
RENEW_DAYS: int = 7
MAX_LOANS: int = 3
FINE_PER_DAY: int = 2        # Rs. 2 per book per day
FINE_BLOCK_LIMIT: int = 50   # Borrowing blocked if pending fine > Rs. 50
