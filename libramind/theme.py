"""
theme.py – Aesthetic, high-contrast warm editorial library theme for LibraMind.
"""
import streamlit as st


def apply_theme():
    """Inject polished, high-contrast warm library CSS with protected icon fonts."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Lora:ital,wght@0,500;0,600;1,400&display=swap');

    /* Global Body Typography */
    body, .stApp {
        background-color: #FAF7F2 !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1C1917;
    }

    /* Headings in refined literary serif */
    h1, h2, h3, h4 {
        font-family: 'Lora', Georgia, serif !important;
        font-weight: 600 !important;
        color: #1C1917 !important;
        letter-spacing: -0.01em !important;
    }

    /* High-contrast text for paragraphs and markdown */
    .stMarkdown p, .stMarkdown div, .stMarkdown li {
        color: #1C1917 !important;
    }

    /* =========================================================================
       CRITICAL FIX: Expander Layout & Text Overlap Elimination
       ========================================================================= */
    [data-testid="stExpander"] {
        border: 1px solid #E7DDD0 !important;
        border-radius: 10px !important;
        background-color: #FAF7F2 !important;
        margin-top: 8px !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] details {
        border: none !important;
    }

    [data-testid="stExpander"] details summary {
        display: flex !important;
        align-items: center !important;
        padding: 10px 14px !important;
        cursor: pointer !important;
        background-color: #F7EFE6 !important;
        border-radius: 8px !important;
        list-style: none !important;
    }

    [data-testid="stExpander"] details summary::-webkit-details-marker {
        display: none !important;
    }

    /* Target the summary flex wrapper: ensure full width & comfortable gap */
    [data-testid="stExpander"] details summary > span {
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        max-width: 100% !important;
        gap: 10px !important;
    }

    /* Summary child 1 (icon container): strictly lock width and clip overflow */
    [data-testid="stExpander"] details summary > span > div:first-child {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 18px !important;
        min-width: 18px !important;
        max-width: 18px !important;
        height: 18px !important;
        overflow: hidden !important;
        flex-shrink: 0 !important;
    }

    /* Summary child 2 (label container): allow flex growth with no overlap */
    [data-testid="stExpander"] details summary > span > div:nth-child(2) {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }

    /* Completely silence any overflowing ligature text (e.g. keyboard_arrow_right) */
    [data-testid="stExpander"] details summary [data-testid="stIconMaterial"],
    [data-testid="stExpander"] details summary [class*="stIcon"] {
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
        width: 18px !important;
        min-width: 18px !important;
        max-width: 18px !important;
        height: 18px !important;
        overflow: hidden !important;
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        user-select: none !important;
    }

    /* Pure CSS Arrow Indicator: always crisp, never overlaps, zero font dependency */
    [data-testid="stExpander"] details summary [data-testid="stIconMaterial"]::before,
    [data-testid="stExpander"] details summary [class*="stIcon"]::before,
    [data-testid="stExpander"] details summary > span > div:first-child::before {
        content: '▶' !important;
        font-size: 10px !important;
        color: #78350F !important;
        display: inline-block !important;
        transform: rotate(0deg) !important;
        transition: transform 0.2s ease !important;
    }

    [data-testid="stExpander"] details[open] summary [data-testid="stIconMaterial"]::before,
    [data-testid="stExpander"] details[open] summary [class*="stIcon"]::before,
    [data-testid="stExpander"] details[open] summary > span > div:first-child::before {
        transform: rotate(90deg) !important;
    }

    /* Expander title label */
    [data-testid="stExpander"] details summary [data-testid="stMarkdownContainer"] p,
    [data-testid="stExpander"] details summary p {
        margin: 0 !important;
        color: #4A3E31 !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        white-space: normal !important;
        display: inline-block !important;
    }

    /* General icon preservation */
    [data-testid="stIconMaterial"], 
    [data-testid="stIcon"], 
    .material-symbols-rounded, 
    .material-icons, 
    svg {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        font-style: normal !important;
        letter-spacing: normal !important;
        text-transform: none !important;
    }

    /* Sidebar Navigation & Text Contrast */
    [data-testid="stSidebar"] {
        background-color: #F4ECE1 !important;
        border-right: 1px solid #E6DCD0 !important;
    }

    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span {
        color: #1C1917 !important;
    }

    /* Sidebar Navigation Links */
    [data-testid="stSidebarNav"] a span {
        color: #292524 !important;
        font-weight: 500 !important;
    }

    [data-testid="stSidebarNav"] a:hover {
        background-color: #EAE0D3 !important;
        border-radius: 8px !important;
    }

    /* Primary Buttons */
    .stButton > button {
        background-color: #78350F !important;
        color: #FFFFFF !important;
        border: 1px solid #632B0C !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        transition: all 0.15s ease !important;
    }
    
    .stButton > button p, .stButton > button span {
        color: #FFFFFF !important;
    }

    .stButton > button:hover {
        background-color: #5C2709 !important;
        border-color: #481E07 !important;
        box-shadow: 0 4px 12px rgba(120, 53, 15, 0.2) !important;
    }

    /* Metric KPI Cards */
    [data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #E7DDD0 !important;
        padding: 16px 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(40, 30, 20, 0.04) !important;
    }

    [data-testid="stMetricLabel"] p {
        color: #786C5E !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }

    [data-testid="stMetricValue"] div {
        color: #1C1917 !important;
        font-family: 'Lora', serif !important;
        font-weight: 600 !important;
        font-size: 1.8rem !important;
    }

    /* Chat Messages - High Contrast & Clean */
    [data-testid="stChatMessage"] {
        background: #FFFFFF !important;
        border: 1px solid #E7DDD0 !important;
        border-radius: 12px !important;
        padding: 18px 22px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 2px 8px rgba(40, 30, 20, 0.03) !important;
    }

    [data-testid="stChatMessage"] p {
        color: #1C1917 !important;
        line-height: 1.6 !important;
    }

    /* Chat Input Bar */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #D8CBBF !important;
        border-radius: 12px !important;
        color: #1C1917 !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #78350F !important;
        box-shadow: 0 0 0 2px rgba(120, 53, 15, 0.15) !important;
    }

    /* Audio Input Widget */
    [data-testid="stAudioInput"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E7DDD0 !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
    }

    /* Selectboxes */
    .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D8CBBF !important;
        border-radius: 8px !important;
    }

    .stSelectbox span, .stSelectbox p {
        color: #1C1917 !important;
    }

    /* Dividers */
    hr {
        border-color: #E8DDD2 !important;
        margin: 1.5rem 0 !important;
    }

    /* Dataframe Tables */
    [data-testid="stDataFrame"] {
        background: #FFFFFF !important;
        border: 1px solid #E7DDD0 !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)
