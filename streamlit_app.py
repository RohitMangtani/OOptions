import streamlit as st
import os
import sys
from datetime import datetime, timedelta
import traceback
import time
import uuid
import json
from dotenv import load_dotenv
from llm_event_query import process_query, create_new_session, get_session
from rss_ingestor import fetch_rss_headlines
from dateutil import parser
import pytz
import pandas as pd
import base64
import io

# Set page configuration
st.set_page_config(
    page_title="Option Bot - Market Terminal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load environment variables
load_dotenv()

# JavaScript for draggable and resizable windows
st.markdown("""
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://code.jquery.com/ui/1.13.2/jquery-ui.min.js"></script>
<script>
$(document).ready(function() {
    // Make widgets draggable and resizable
    $('.widget-container').draggable({
        handle: '.widget-header',
        containment: 'parent',
        snap: true,
        grid: [10, 10]
    }).resizable({
        minHeight: 200,
        minWidth: 300,
        handles: 'all',
        containment: 'parent'
    });
    
    // Close widget functionality
    $('.widget-close').on('click', function() {
        $(this).closest('.widget-container').remove();
    });
    
    // Minimize widget functionality
    $('.widget-minimize').on('click', function() {
        const content = $(this).closest('.widget-container').find('.widget-content');
        content.toggle();
    });
});
</script>
""", unsafe_allow_html=True)

# Apply custom styling for a Bloomberg terminal look
st.markdown("""
<style>
    /* Main app background - dark with subtle texture */
    .stApp {
        background-color: #121212;
        color: #ffffff;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Courier New', monospace;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.3px;
    }
    
    /* Welcome screen */
    .welcome-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #121212;
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    .welcome-text {
        font-family: 'Courier New', monospace;
        font-size: 4.5rem;
        font-weight: 800;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    /* Main heading */
    .main-heading {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 6px;
        padding-bottom: 3px;
        border-bottom: 1px solid #333333;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Logo style */
    .logo-text {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-family: 'Courier New', monospace;
    }
    
    .logo-subtitle {
        font-size: 0.8rem;
        color: #00ff00;
        margin-top: -5px;
        margin-bottom: 12px;
        font-family: 'Courier New', monospace;
        font-weight: 600;
    }
    
    /* Message bubbles */
    .user-message {
        background-color: #1a1a1a;
        padding: 10px 12px;
        border-radius: 4px;
        margin-bottom: 6px;
        color: #ffffff;
        border-left: 2px solid #00ff00;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    
    .assistant-message {
        background-color: #1a1a1a;
        padding: 10px 12px;
        border-radius: 4px;
        margin-bottom: 6px;
        color: #00ff00;
        border-left: 2px solid #00ff00;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    
    /* Sidebar styling */
    [data-testid=stSidebar] {
        background-color: #1a1a1a;
        border-right: 1px solid #333333;
        padding: 0.8rem;
    }
    
    [data-testid=stSidebar] span {
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-weight: 500;
    }
    
    /* All standard text */
    p, li, span, div, a {
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    
    /* Buttons */
    [data-testid=stButton] > button {
        background-color: #1a1a1a;
        color: #ffffff;
        border-radius: 4px;
        border: 1px solid #333333;
        padding: 0.3rem 0.6rem;
        font-weight: 600;
        transition: all 0.2s ease;
        font-family: 'Courier New', monospace;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
    }
    
    [data-testid=stButton] > button:hover {
        background-color: #333333;
        color: #00ff00;
    }
    
    /* Info box */
    .info-box {
        background-color: #1a1a1a;
        border-left: 2px solid #00ff00;
        padding: 10px;
        margin-bottom: 10px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 500;
        border-radius: 4px;
        letter-spacing: 0.2px;
    }
    
    /* Input fields */
    [data-testid=stTextInput] > div > div > input {
        background-color: #1a1a1a;
        color: #ffffff;
        border-radius: 4px;
        border: 1px solid #333333;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
        padding: 8px 10px;
    }
    
    /* Chat input container */
    [data-testid="stChatInput"] > div {
        border-radius: 4px;
        border: 1px solid #333333;
    }
    
    [data-testid="stChatInput"] textarea {
        background-color: #1a1a1a;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
        padding: 8px 10px;
    }
    
    /* News feed styling */
    .news-card {
        background-color: #1a1a1a;
        padding: 10px 12px;
        margin-bottom: 6px;
        color: #ffffff;
        border-left: 2px solid #00ff00;
        font-family: 'Courier New', monospace;
        display: flex;
        flex-direction: column;
        border-radius: 4px;
    }
    
    .news-header {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #333333;
        padding-bottom: 5px;
        margin-bottom: 6px;
    }
    
    .news-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 4px;
        flex-grow: 1;
        font-family: 'Courier New', monospace;
        letter-spacing: 0.2px;
    }
    
    .news-source {
        font-size: 0.8rem;
        font-weight: 700;
        color: #00ff00;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 6px;
        min-width: 80px;
        text-align: right;
        font-family: 'Courier New', monospace;
    }
    
    .news-date {
        font-size: 0.8rem;
        color: #cccccc;
        margin-bottom: 3px;
        font-family: 'Courier New', monospace;
        font-weight: 500;
    }
    
    .news-summary {
        font-size: 0.9rem;
        color: #ffffff;
        margin-bottom: 4px;
        line-height: 1.4;
        font-family: 'Courier New', monospace;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    
    /* Feed header styling */
    .feed-title {
        font-size: 1.1rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 3px;
        text-transform: uppercase;
        font-family: 'Courier New', monospace;
        letter-spacing: 0.5px;
    }
    
    .feed-refresh-text {
        font-size: 0.8rem;
        color: #cccccc;
        font-family: 'Courier New', monospace;
        font-weight: 500;
    }
    
    /* Make tabs consistent with the greener look */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: #1a1a1a;
        border-bottom: 1px solid #333333;
        padding: 0;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab"], 
    .stTabs [data-baseweb="tab-highlight"], 
    .stTabs [data-baseweb="tab-border"] {
        height: 32px;
        white-space: pre-wrap;
        background-color: #1a1a1a;
        border-radius: 4px 4px 0 0;
        gap: 0;
        padding: 4px 12px;
        color: #cccccc !important;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        border-color: #00ff00 !important;
        letter-spacing: 0.5px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #333333;
        color: #ffffff !important;
        font-weight: 800;
        border-top: 2px solid #00ff00;
        border-left: 1px solid #333333;
        border-right: 1px solid #333333;
        border-bottom: none;
    }
    
    /* Checkboxes and radio buttons */
    .stCheckbox > label, .stRadio > label {
        color: #ffffff !important;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    
    /* Expanders */
    .stExpander > details > summary {
        color: #ffffff !important;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 600;
    }
    
    /* Select boxes */
    .stSelectbox > label {
        color: #ffffff !important;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    /* Captions */
    .stCaption {
        color: #cccccc !important;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Alert messages */
    .stAlert > div {
        color: #ffffff !important;
        background-color: #1a1a1a;
        border-radius: 4px;
        border-left: 2px solid #00ff00;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
    }

    /* Status bar (session info) styling */
    .status-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1a1a1a;
        border-top: 1px solid #333333;
        display: flex;
        justify-content: space-between;
        padding: 4px 10px;
        color: #cccccc;
        font-size: 0.8rem;
        font-weight: 600;
        z-index: 1000;
        font-family: 'Courier New', monospace;
        letter-spacing: 0.3px;
    }
    
    .status-item {
        margin-right: 10px;
    }
    
    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #333333;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555555;
    }

    /* News feed styling - Terminal style */
    .terminal-header {
        background-color: #1a1a1a;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-size: 1.2rem;
        font-weight: 800;
        text-align: center;
        padding: 6px 0;
        margin-bottom: 4px;
        border-bottom: 1px solid #333333;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        border-radius: 4px 4px 0 0;
    }
    
    .feed-controls {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .feed-timestamp {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 500;
        color: #cccccc;
        text-align: right;
    }
    
    /* News header row */
    .news-header-row {
        display: grid;
        grid-template-columns: 6fr 1fr 1fr 1fr;
        gap: 5px;
        background-color: #1a1a1a;
        padding: 6px 10px;
        margin-bottom: 3px;
        border-bottom: 1px solid #333333;
        font-family: 'Courier New', monospace;
        color: #ffffff;
        border-radius: 4px 4px 0 0;
    }
    
    .news-header-headline, .news-header-date, .news-header-time, .news-header-source {
        font-size: 0.85rem;
        font-weight: 800;
        text-transform: uppercase;
        color: #ffffff;
        letter-spacing: 0.5px;
    }
    
    /* News rows */
    .news-row {
        display: grid;
        grid-template-columns: 6fr 1fr 1fr 1fr;
        gap: 5px;
        background-color: #1a1a1a;
        padding: 6px 10px;
        margin-bottom: 2px;
        font-family: 'Courier New', monospace;
        text-decoration: none;
        color: #ffffff;
        border-left: 2px solid transparent;
        transition: background-color 0.2s, border-left-color 0.2s;
        border-radius: 4px;
    }
    
    .news-row:hover {
        background-color: #2a2a2a;
        border-left-color: #00ff00;
    }
    
    /* Remove underlines and ensure all text is white */
    a, a:hover, a:visited, a:active {
        text-decoration: none !important;
        color: #ffffff !important;
    }
    
    a:hover {
        color: #00ff00 !important;
    }
    
    .news-row-headline, .news-row-date, .news-row-time, .news-row-source {
        padding: 0 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    
    .news-row-headline {
        white-space: normal;
        line-height: 1.4;
    }
    
    /* Ensure all hover states use green */
    button:hover, 
    .stButton>button:hover,
    .stExpander:hover,
    .stRadio>div:hover {
        border-color: #00ff00 !important;
        color: #00ff00 !important;
    }
    
    /* Streamlit specific element corrections to ensure consistency */
    .streamlit-expanderHeader:hover,
    .streamlit-expanderContent:hover {
        border-color: #00ff00 !important;
    }
    
    /* Fix the conversation history container indentation issue */
    .conversation_container {
        width: 100%;
    }
    
    /* Special color for positive percent changes */
    .pos-change {
        color: #00ff00 !important;
        font-weight: 600;
    }
    
    /* Special color for negative percent changes */
    .neg-change {
        color: #00aa00 !important;
        font-weight: 600;
    }
    
    .news-row-date, .news-row-time {
        color: #cccccc;
        text-align: right;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .news-row-source {
        color: #00ff00;
        text-transform: uppercase;
        font-size: 0.8rem;
        font-weight: 700;
        text-align: right;
        letter-spacing: 0.3px;
    }
    
    /* Additional terminal styling */
    .terminal-cmd-info {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        color: #cccccc;
        margin-bottom: 8px;
        padding: 3px 0;
        border-bottom: 1px solid #333333;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* Command list styling */
    .command-list {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-bottom: 15px;
    }
    
    .command-item {
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        font-weight: 500;
        color: #ffffff;
        display: flex;
        align-items: center;
        padding: 3px 0;
        letter-spacing: 0.2px;
    }
    
    .command-code {
        background-color: #333333;
        padding: 3px 8px;
        margin-right: 8px;
        min-width: 30px;
        text-align: center;
        font-weight: 800;
        color: #00ff00;
        border-radius: 3px;
    }
    
    .command-input-label {
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 5px;
        letter-spacing: 0.3px;
    }
    
    .enter-button {
        background-color: #333333;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 6px 8px;
        text-align: center;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 24px;
        border-radius: 4px;
        letter-spacing: 0.3px;
    }
    
    .filter-label {
        text-align: right;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        color: #ffffff;
        padding: 3px 0;
        letter-spacing: 0.2px;
    }
    
    /* Refresh indicator */
    @keyframes blink {
        0% { opacity: 0; }
        50% { opacity: 1; }
        100% { opacity: 0; }
    }
    
    .refresh-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #00ff00;
        margin-left: 5px;
        animation: blink 0.5s ease-in-out;
        animation-iteration-count: 2;
    }
    
    .refresh-indicator-container {
        display: inline-flex;
        align-items: center;
        margin-left: 5px;
    }
    
    /* Message prefix */
    .message-prefix {
        color: #00ff00;
        font-weight: 800;
        margin-right: 8px;
        letter-spacing: 0.5px;
    }
    
    .terminal-welcome {
        background-color: #1a1a1a;
        padding: 12px;
        font-family: 'Courier New', monospace;
        color: #ffffff;
        border-left: 2px solid #00ff00;
        margin-bottom: 10px;
        line-height: 1.5;
        font-size: 0.95rem;
        font-weight: 500;
        border-radius: 4px;
        letter-spacing: 0.2px;
    }
    
    .logo-container {
        text-align: center;
        margin-bottom: 15px;
        padding-bottom: 12px;
        border-bottom: 1px solid #333333;
    }
    
    .sidebar-section-header {
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 800;
        color: #ffffff;
        text-transform: uppercase;
        margin: 15px 0 8px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #333333;
        letter-spacing: 0.5px;
    }
    
    .sidebar-info {
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 500;
        color: #ffffff;
        line-height: 1.4;
        letter-spacing: 0.2px;
    }
    
    .sidebar-info ul {
        padding-left: 15px;
    }
    
    .sidebar-info li {
        margin-bottom: 6px;
    }
    
    /* Streamlit default components tweaking */
    div.stButton > button:first-child {
        font-family: 'Courier New', monospace;
        text-transform: uppercase;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Table-like styling for quote data */
    .quote-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #333333;
        font-family: 'Courier New', monospace;
        margin-bottom: 10px;
        border-radius: 4px;
        overflow: hidden;
    }
    
    .quote-table th {
        background-color: #1a1a1a;
        color: #ffffff;
        font-size: 0.85rem;
        font-weight: 700;
        padding: 6px 8px;
        text-align: left;
        border-bottom: 1px solid #333333;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .quote-table td {
        padding: 5px 8px;
        border-bottom: 1px solid #333333;
        font-size: 0.9rem;
        font-weight: 500;
        color: #ffffff;
    }
    
    .quote-row:hover {
        background-color: #2a2a2a;
    }
    
    .quote-ticker {
        color: #ffffff;
        font-weight: 700;
    }
    
    .quote-value {
        text-align: right;
        font-weight: 600;
    }
    
    .quote-volume {
        text-align: right;
        color: #cccccc;
    }
    
    .quote-input {
        background-color: #121212;
        border: 1px solid #333333;
        color: #ffffff;
        padding: 6px 8px;
        width: 100%;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 500;
        border-radius: 4px;
    }
    
    /* Filter dropdown menu similar to images */
    .filter-dropdown {
        background-color: #1a1a1a;
        color: #ffffff;
        border: 1px solid #333333;
        padding: 6px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        font-weight: 500;
        border-radius: 4px;
    }

    /* Ticker suggestions dropdown */
    .ticker-suggestions {
        background-color: #1a1a1a;
        border: 1px solid #333333;
        max-height: 300px;
        overflow-y: auto;
        margin-top: 4px;
        z-index: 1000;
        border-radius: 4px;
    }
    
    .ticker-suggestion-item {
        display: flex;
        justify-content: space-between;
        padding: 6px 10px;
        cursor: pointer;
        border-bottom: 1px solid #222222;
    }
    
    .ticker-suggestion-item:hover {
        background-color: #2a2a2a;
    }
    
    .ticker-symbol {
        font-weight: 700;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        letter-spacing: 0.2px;
    }
    
    .ticker-name {
        color: #cccccc;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 500;
        text-overflow: ellipsis;
        overflow: hidden;
        letter-spacing: 0.2px;
    }
</style>
""", unsafe_allow_html=True)

# Check for the presence of the OpenAI API key
# Read API key directly from .env file to ensure we get the current value
try:
    with open('.env', 'r') as f:
        env_contents = f.read()
        for line in env_contents.splitlines():
            if line.startswith('OPENAI_API_KEY='):
                OPENAI_API_KEY = line.split('=', 1)[1]
                st.sidebar.success(f"✅ OpenAI API key loaded: {OPENAI_API_KEY[:4]}...{OPENAI_API_KEY[-4:]}")
                break
        else:
            OPENAI_API_KEY = None
            st.error("❌ ERROR: OPENAI_API_KEY not found in .env file")
except Exception as e:
    st.error(f"❌ ERROR reading .env file: {str(e)}")
    OPENAI_API_KEY = None

# Fallback to environment variable if direct read failed
if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if OPENAI_API_KEY:
        st.sidebar.success(f"✅ OpenAI API key loaded from environment")
    else:
        st.error("❌ ERROR: OpenAI API key not found in environment")
        st.info("Please add your OpenAI API key to the .env file with the variable name OPENAI_API_KEY")
        st.stop()

# Sample queries to help users get started
SAMPLE_QUERIES = [
    "What happened when Bitcoin ETF was approved?",
    "How did the market react to the Fed raising interest rates last year?",
    "What was the impact of Silicon Valley Bank collapse?",
    "How did Tesla stock perform after their Q1 2023 earnings?",
    "What happened to crypto during COVID-19 crash?"
]

# Sample follow-up queries to give users ideas
FOLLOW_UP_PROMPTS = [
    "How does this compare to similar events?",
    "What was the inflation rate at that time?",
    "Why did the market react this way?",
    "How long did it take to recover?",
    "What are the implications for future events?"
]

# Function to fetch RSS headlines and store them in session state
def fetch_news_feed():
    try:
        with st.spinner("Fetching latest financial news..."):
            headlines = fetch_rss_headlines()
            
            # Process each headline to ensure URL and date are properly set
            for headline in headlines:
                # Make sure URL is set correctly - if not in "url", use "link" instead
                if "link" in headline and ("url" not in headline or not headline["url"]):
                    headline["url"] = headline["link"]
                
                # Ensure there's a valid published date, default to current time if missing
                if "published" not in headline or not headline["published"]:
                    headline["published"] = datetime.now(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Sort by published date (newest first)
            headlines = sorted(headlines, key=lambda x: x.get("published", datetime.now()), reverse=True)
            
            # Check if we have new content
            has_new_content = False
            if st.session_state.news_headlines:
                # Compare newest headline
                if headlines and (
                    headlines[0].get("title") != st.session_state.news_headlines[0].get("title") or
                    headlines[0].get("published") != st.session_state.news_headlines[0].get("published")
                ):
                    has_new_content = True
            else:
                # First load
                has_new_content = True
            
            # Update latest headline tracking
            if headlines:
                newest = headlines[0]
                st.session_state.latest_headline_id = f"{newest.get('title', '')}_{newest.get('published', '')}"
            
            # Set refresh indicator if we have new content
            if has_new_content:
                st.session_state.refresh_triggered = True
            
            # Update the session state - store all headlines instead of limiting to 30
            if st.session_state.news_headlines:
                # Add new headlines to existing ones, avoiding duplicates
                existing_titles = {h.get("title", ""): True for h in st.session_state.news_headlines}
                for headline in headlines:
                    title = headline.get("title", "")
                    if title not in existing_titles:
                        st.session_state.news_headlines.append(headline)
                        existing_titles[title] = True
                
                # Sort headlines again to ensure newest first
                st.session_state.news_headlines = sorted(
                    st.session_state.news_headlines, 
                    key=lambda x: x.get("published", datetime.now()), 
                    reverse=True
                )
            else:
                st.session_state.news_headlines = headlines
                
            st.session_state.last_news_fetch_time = datetime.now()
            
            return headlines
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []

# Function to format the headline date
def format_headline_date(published_date):
    """Format the published date of a headline into both human-readable and exact formats."""
    try:
        # If published_date is a string, parse it to a datetime object
        if isinstance(published_date, str):
            published_date = parser.parse(published_date)
        
        # Ensure datetime has timezone info
        if published_date.tzinfo is None:
            published_date = pytz.UTC.localize(published_date)
            
        # Convert to Eastern Time
        eastern = pytz.timezone('US/Eastern')
        published_date = published_date.astimezone(eastern)
            
        # Get current time with timezone (Eastern)
        now = datetime.now(eastern)
        
        # Calculate time difference
        diff = now - published_date
        
        # Format based on time difference for relative time
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                relative_time = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                relative_time = f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days == 1:
            relative_time = "Yesterday"
        elif diff.days < 7:
            relative_time = f"{diff.days} days ago"
        else:
            relative_time = published_date.strftime("%B %d, %Y")
        
        # Format for exact timestamp (using AM/PM format)
        exact_time = published_date.strftime("%B %d, %Y at %I:%M %p ET")
            
        return {
            "relative": relative_time,
            "exact": exact_time,
            "raw": published_date
        }
    except Exception as e:
        # Return a fallback date string if parsing fails
        print(f"Error formatting date: {str(e)}")
        return {
            "relative": "Recently published",
            "exact": "Date unknown",
            "raw": None
        }

# Function to initialize session state
def initialize_session_state():
    if "session_id" not in st.session_state:
        # Create a new conversation session
        try:
            session = create_new_session()
            st.session_state.session_id = session.session_id
        except Exception as e:
            st.error(f"Error creating session: {str(e)}")
            st.session_state.session_id = "error-session"
            
        st.session_state.conversation = []
        st.session_state.query_count = 0
        st.session_state.error = None
        st.session_state.has_received_response = False
        st.session_state.last_query_time = None
        st.session_state.current_query = ""
        
    # Initialize news feed if not already present
    if "news_headlines" not in st.session_state:
        st.session_state.news_headlines = []
        st.session_state.last_news_fetch_time = None
        # Get initial headlines
        fetch_news_feed()
    
    # Flag for real-time auto refresh
    if "live_refresh" not in st.session_state:
        st.session_state.live_refresh = True  # Enable by default
        
    if "refresh_triggered" not in st.session_state:
        st.session_state.refresh_triggered = False
    
    # For keeping track of the latest headline
    if "latest_headline_id" not in st.session_state:
        if st.session_state.news_headlines:
            # Use title and date as a unique ID
            latest = st.session_state.news_headlines[0]
            st.session_state.latest_headline_id = f"{latest.get('title', '')}_{latest.get('published', '')}"
        else:
            st.session_state.latest_headline_id = ""
            
    # Track active tab
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0  # Default to first tab (Command)
        
    # Welcome screen display control
    if "welcome_shown" not in st.session_state:
        st.session_state.welcome_shown = False
        st.session_state.welcome_time = time.time()

# Function to reset conversation
def reset_conversation():
    # Create a new conversation session
    try:
        session = create_new_session()
        st.session_state.session_id = session.session_id
        st.session_state.conversation = []
        st.session_state.query_count = 0
        st.session_state.error = None
        st.session_state.has_received_response = False
        st.session_state.last_query_time = None
        st.session_state.current_query = ""
        st.success("Conversation reset. New session started.")
    except Exception as e:
        st.error(f"Error resetting conversation: {str(e)}")

# Function to check for new RSS feed items
def check_for_new_headlines():
    """Check if there are any new headlines available without updating the session state."""
    try:
        # Quick fetch to check for new items
        headlines = fetch_rss_headlines()
        
        # Process to make comparable
        for headline in headlines:
            if "link" in headline and ("url" not in headline or not headline["url"]):
                headline["url"] = headline["link"]
            
            if "published" not in headline or not headline["published"]:
                headline["published"] = datetime.now(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Sort by published date (newest first)
        headlines = sorted(headlines, key=lambda x: x.get("published", datetime.now()), reverse=True)
        
        # If we have headlines to compare
        if headlines and st.session_state.news_headlines:
            # Get the newest headline from current fetch
            newest = headlines[0]
            newest_id = f"{newest.get('title', '')}_{newest.get('published', '')}"
            
            # Compare with our stored latest headline ID
            if newest_id != st.session_state.latest_headline_id:
                return True  # New headlines available
        
        return False  # No new headlines
    except Exception as e:
        print(f"Error checking for new headlines: {str(e)}")
        return False

# Function to process user query
def process_user_query(user_query):
    # Add to conversation history immediately for better UX
    st.session_state.conversation.append({"role": "user", "content": user_query})
    
    try:
        # Process the query
        response, new_session_id = process_query(
            user_query, 
            st.session_state.session_id,
            # If we've already had a conversation, treat this as a follow-up
            is_follow_up=st.session_state.has_received_response
        )
        
        # Update session ID if changed
        if new_session_id:
            st.session_state.session_id = new_session_id
        
        # Extract response content
        if isinstance(response, dict) and "response" in response:
            response_text = response["response"]
            sections = response.get("sections", [])
        elif isinstance(response, tuple) and len(response) > 0:
            response_text = response[0]
            sections = []
        else:
            response_text = str(response)
            sections = []
        
        # Add main response to conversation
        st.session_state.conversation.append({"role": "assistant", "content": response_text})
        
        # Add any sections as additional assistant messages if they exist
        for section in sections:
            if section.get("title") and section.get("content"):
                section_content = f"**{section['title']}**\n\n{section['content']}"
                st.session_state.conversation.append({"role": "assistant", "content": section_content})
        
        st.session_state.query_count += 1
        st.session_state.error = None
        st.session_state.has_received_response = True
        st.session_state.last_query_time = datetime.now()
        st.session_state.current_query = ""  # Clear the current query
        return response
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        st.session_state.error = error_msg
        st.session_state.conversation.append({"role": "assistant", "content": f"❌ {error_msg}\n\nPlease try again or reset the conversation."})
        traceback.print_exc()
        st.session_state.current_query = ""  # Clear the current query
        return None

# Function to use sample query
def use_sample_query(query):
    # Set the query in session state to be processed
    st.session_state.current_query = query
    
# Function to suggest a random follow-up prompt
def get_follow_up_suggestion():
    import random
    return random.choice(FOLLOW_UP_PROMPTS)
    
# Function to toggle live refresh
def toggle_live_refresh():
    st.session_state.live_refresh = not st.session_state.live_refresh
    
    # Make sure we keep the active tab as news (index 1) when toggling from the news feed
    # Only modify if we're already on the news tab
    if st.session_state.active_tab == 1:
        st.query_params.tab = 1

# Function to set active tab index
def set_active_tab(tab_index):
    st.session_state.active_tab = tab_index

# Function to display chat interface
def display_chat_interface():
    """Display the chat interface with Bloomberg terminal styling."""
    # Terminal header
    st.markdown('<div class="terminal-header">COMMAND TERMINAL</div>', unsafe_allow_html=True)
    
    # Add command input 
    st.markdown("<div class='command-input-label'>Enter market query:</div>", unsafe_allow_html=True)
    
    # Display error if exists
    if st.session_state.get("error"):
        st.error(st.session_state.error)
    
    # Command input
    col1, col2 = st.columns([9, 1])
    with col1:
        query = st.text_input("", value=st.session_state.current_query, key="command_input", 
                             placeholder="Type a market query...")
    with col2:
        st.markdown("<div class='enter-button'>ENTER →</div>", unsafe_allow_html=True)
    
    # Display conversation history
    conversation_container = st.container()
    with conversation_container:
        for message in st.session_state.conversation:
            if message["role"] == "user":
                st.markdown(
                    f"<div class='user-message'>"
                    f"<span class='message-prefix'>QUERY ></span> {message['content']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='assistant-message'>"
                    f"<span class='message-prefix'>OPT_BOT ></span> {message['content']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
    
    # First-time welcome message
    if not st.session_state.conversation:
        st.markdown(
        """
        <div class="terminal-welcome">
<span class="message-prefix">SYSTEM ></span> OPTION BOT INITIALIZED

WELCOME TO OPTION BOT TERMINAL v1.0

ENTER A MARKET QUERY TO ANALYZE:
- "What happened when Bitcoin ETF was approved?"
- "How did the market react to the Fed raising rates?"
- "What was the impact of Silicon Valley Bank collapse?"
- "How did Tesla stock perform after Q1 earnings?"
        </div>
        """, 
            unsafe_allow_html=True
        )
    
    # Process query if entered by user or if a sample query was selected
    if query or st.session_state.current_query:
        user_query = query if query else st.session_state.current_query
        if user_query:
            with st.spinner("PROCESSING QUERY..."):
                process_user_query(user_query)
            # Keep current active tab index
            st.query_params.tab = st.session_state.active_tab
            st.rerun()
    
    # Add a status bar at the bottom with Eastern Time
    eastern = pytz.timezone('US/Eastern')
    current_time = datetime.now(eastern).strftime("%I:%M:%S %p ET")
    st.markdown(
        f"""
        <div class="status-bar">
            <div class="status-item">SESSION: {st.session_state.session_id[:8]}...</div>
            <div class="status-item">QUERIES: {st.session_state.query_count}</div>
            <div class="status-item">TIME: {current_time}</div>
            <div class="status-item">OPTIONS BOT v1.0</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Function to display the news feed tab
def display_news_feed():
    """Display the news feed tab with the latest financial news headlines in Bloomberg terminal style."""
    # Check for new headlines if live refresh is enabled
    if st.session_state.live_refresh and check_for_new_headlines():
        fetch_news_feed()
        # Ensure we keep the news tab active (index 1)
        st.session_state.active_tab = 1
        st.query_params.tab = 1
        st.rerun()
    
    # NEWS FEED HEADER
    st.markdown('<div class="terminal-header">NEWS TERMINAL</div>', unsafe_allow_html=True)
    
    # Top control bar
    col1, col2, col3 = st.columns([5, 4, 1])
    
    with col1:
        search_query = st.text_input("🔍 Search headlines", placeholder="Enter search term", key="news_search")
    
    with col2:
        last_fetch_time = st.session_state.last_news_fetch_time
        if last_fetch_time:
            # Convert to Eastern Time
            eastern = pytz.timezone('US/Eastern')
            last_fetch_time = last_fetch_time.astimezone(eastern)
            st.markdown(
                f'<div class="feed-timestamp">Last updated: {last_fetch_time.strftime("%I:%M:%S %p ET")}</div>',
                unsafe_allow_html=True
            )
    
    with col3:
        if st.button("🔄"):
            # Force refresh now and explicitly set the flag
            fetch_news_feed()
            # Keep news tab active
            st.session_state.active_tab = 1
            st.query_params.tab = 1
            st.rerun()
    
    # Refresh settings and indicator
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Live refresh toggle with indicator
        live_refresh_col1, live_refresh_col2 = st.columns([3, 1])
        with live_refresh_col1:
            # Create a key for the previous live refresh state
            if "previous_live_refresh" not in st.session_state:
                st.session_state.previous_live_refresh = st.session_state.live_refresh
            
            # Custom callback to set active tab before toggle_live_refresh is called
            def handle_live_refresh_change():
                # Set active tab to news feed (1) to maintain tab after rerun
                st.session_state.active_tab = 1
                st.query_params.tab = 1
                # Now toggle the actual live refresh state
                st.session_state.live_refresh = not st.session_state.previous_live_refresh
                # Update previous state for next toggle
                st.session_state.previous_live_refresh = st.session_state.live_refresh
            
            # Use the checkbox with our custom callback
            live_refresh = st.checkbox(
                "Live updates", 
                value=st.session_state.live_refresh,
                key="live_refresh_toggle",
                on_change=handle_live_refresh_change,
                help="Automatically refresh when new headlines are available"
            )
        
        with live_refresh_col2:
            # Show blinking indicator if refresh was triggered
            if st.session_state.refresh_triggered:
                st.markdown('<div class="refresh-indicator-container"><div class="refresh-indicator"></div></div>', unsafe_allow_html=True)
                # Reset the flag after displaying 
                st.session_state.refresh_triggered = False
            else:
                st.empty()  # Empty placeholder when not refreshing
    
    with col2:
        # Show info about live refresh
        if st.session_state.live_refresh:
            st.info("Auto-updating as new headlines appear ⚡")
        else:
            st.caption("Refresh manually or enable live updates")
    
    # Display column headers
        st.markdown(
            """
        <div class="news-header-row">
            <div class="news-header-headline">Headline</div>
            <div class="news-header-date">Date</div>
            <div class="news-header-time">Time</div>
            <div class="news-header-source">Source</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Filter and display news items
    if not st.session_state.news_headlines:
        st.info("No news headlines found. Click refresh to try again.")
    else:
        # Apply filters to headlines
        filtered_headlines = st.session_state.news_headlines.copy()
        
        # Apply search filter
        if search_query:
            filtered_headlines = [
                h for h in filtered_headlines 
                if search_query.lower() in h.get("title", "").lower() or 
                   search_query.lower() in h.get("summary", "").lower()
            ]
        
        # Limit display count
        display_count = 50  # Fixed display count since we removed the advanced options
        display_headlines = filtered_headlines[:display_count]
        
        # Show number of headlines displayed vs total
        st.caption(f"Displaying {len(display_headlines)} of {len(filtered_headlines)} headlines (Total: {len(st.session_state.news_headlines)})")
        
        # Display headlines
        for headline in display_headlines:
            title = headline.get("title", "No title")
            source = headline.get("source", "Unknown source")
            published = headline.get("published")
            url = headline.get("link" if "link" in headline else "url", "#")
            
            # Format date/time in terminal style
            try:
                date_info = format_headline_date(published)
                date_obj = date_info["raw"]
                
                if date_obj:
                    date_str = date_obj.strftime("%m/%d/%y")
                    time_str = date_obj.strftime("%I:%M %p")
                else:
                    date_str = "—"
                    time_str = "—"
            except Exception as e:
                date_str = "—"
                time_str = "—"
                print(f"Error formatting date: {str(e)}")
            
            # Create news row
            st.markdown(
                f"""
                <a href="{url}" target="_blank" class="news-row">
                    <div class="news-row-headline">{title}</div>
                    <div class="news-row-date">{date_str}</div>
                    <div class="news-row-time">{time_str}</div>
                    <div class="news-row-source">{source}</div>
                </a>
                """,
                unsafe_allow_html=True
            )
    
    # Add a status bar at the bottom
    # Determine refresh status message
    if st.session_state.live_refresh:
        refresh_status = "LIVE UPDATES"
    else:
        refresh_status = "MANUAL REFRESH"
        
    # Convert to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    current_time = datetime.now(eastern).strftime("%I:%M:%S %p ET")
    
    st.markdown(
        f"""
        <div class="status-bar">
            <div class="status-item">NEWS</div>
            <div class="status-item">{refresh_status}</div>
            <div class="status-item">HEADLINES: {len(st.session_state.news_headlines)}</div>
            <div class="status-item">TIME: {current_time}</div>
            <div class="status-item">OPTIONS BOT v1.0</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

# Main app layout
def main():
    # Initialize session state
    initialize_session_state()
    
    # Check if welcome screen should be shown
    if not st.session_state.welcome_shown:
        # Display welcome screen
        st.markdown(
            """
            <div class="welcome-screen">
                <div class="welcome-text">WELCOME.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Check if we've displayed the welcome screen for 0.5 second
        if time.time() - st.session_state.welcome_time >= 0.5:
            # Set welcome as shown
            st.session_state.welcome_shown = True
            st.rerun()
        else:
            # Wait remaining time to complete 0.5 second
            time.sleep(max(0, 0.5 - (time.time() - st.session_state.welcome_time)))
            st.session_state.welcome_shown = True
            st.rerun()
        return
    
    # Sidebar with Bloomberg terminal style
    with st.sidebar:
        st.markdown(
            """
            <div class="logo-container">
                <div class="logo-text">OPTION BOT</div>
                <div class="logo-subtitle">MARKET INTELLIGENCE TERMINAL</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Reset button
        st.button("RESET SESSION", on_click=reset_conversation, use_container_width=True)
        
        st.markdown('<div class="sidebar-section-header">SAMPLE QUERIES</div>', unsafe_allow_html=True)
        for query in SAMPLE_QUERIES:
            st.button(query.upper(), on_click=use_sample_query, args=(query,), key=f"sample_{query[:20]}")
            
        st.markdown('<div class="sidebar-section-header">TERMINAL INFO</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="sidebar-info">
            <p>OPTION BOT ANALYZES MARKET EVENTS AND PROVIDES INSIGHTS BASED ON HISTORICAL PATTERNS
            AND MACROECONOMIC DATA.</p>
            
            <ul>
              <li>ANALYZE HISTORICAL MARKET EVENTS</li>
              <li>IDENTIFY MARKET REACTION PATTERNS</li>
              <li>EXPLORE SIMILAR EVENT COMPARISONS</li>
              <li>UNDERSTAND MACROECONOMIC INFLUENCES</li>
              <li>GET ACTIONABLE TRADE IDEAS</li>
            </ul>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Main content area with tabs
    st.markdown("<h1 class='main-heading'>OPTIONS BOT TERMINAL</h1>", unsafe_allow_html=True)
    
    # Create tabs
    tab_names = ["COMMAND", "NEWS FEED"]
    
    # Get tab index from query params if available
    if "tab" in st.query_params:
        try:
            tab_index = int(st.query_params.tab)
            if 0 <= tab_index < len(tab_names):
                st.session_state.active_tab = tab_index
        except ValueError:
            pass
    
    # Create tab objects
    tabs = st.tabs(tab_names)
    
    # Add JavaScript to maintain active tab on page reruns
    active_tab_index = st.session_state.active_tab
    js_code = f"""
    <script>
    // Wait for document to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {{
        // Function to set the active tab
        function setActiveTab(index) {{
            setTimeout(function() {{
                try {{
                    // Get all tab buttons
                    const tabButtons = document.querySelectorAll('button[role="tab"]');
                    if (tabButtons.length > index) {{
                        // Click the correct tab
                        tabButtons[index].click();
                    }}
                }} catch (error) {{
                    console.error('Error setting active tab:', error);
                }}
            }}, 100);
        }}
        
        // Add click listeners to all tab buttons to update query params
        const tabButtons = document.querySelectorAll('button[role="tab"]');
        for (let i = 0; i < tabButtons.length; i++) {{
            tabButtons[i].addEventListener('click', function() {{
                // Update URL when tab is clicked
                const newUrl = new URL(window.location.href);
                newUrl.searchParams.set('tab', i);
                window.history.replaceState(null, '', newUrl.toString());
            }});
        }}
        
        // Set initial active tab
        setActiveTab({active_tab_index});
    }});
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
    
    # Chat tab
    with tabs[0]:
        display_chat_interface()
        
    # News Feed tab
    with tabs[1]:
        display_news_feed()

def get_table_download_link(df, filename="data.csv", link_text="Download CSV"):
    """
    Generates a link to download the provided dataframe as a CSV file
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # B64 encoding
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">⬇️ {link_text}</a>'
    return href

def filter_headlines(headlines, search_query="", date_filter=None, selected_sources=None, max_headlines=50):
    """
    Filter headlines based on search query, date range, and sources
    
    Parameters:
    - headlines: List of headline dictionaries
    - search_query: Text to search in headlines
    - date_filter: Tuple of (start_date, end_date) as datetime objects
    - selected_sources: List of sources to include
    - max_headlines: Maximum number of headlines to display
    
    Returns:
    - Filtered list of headlines
    """
    filtered = headlines.copy()
    
    # Apply search filter if provided
    if search_query:
        filtered = [
            h for h in filtered 
            if search_query.lower() in h.get("title", "").lower() or 
               search_query.lower() in h.get("summary", "").lower()
        ]
    
    # Apply source filter if provided
    if selected_sources:
        filtered = [h for h in filtered if h.get("source", "Unknown") in selected_sources]
    
    # Apply date filter if provided
    if date_filter and isinstance(date_filter, tuple) and len(date_filter) == 2:
        start_date, end_date = date_filter
        if start_date and end_date:
            # Convert datetime objects to dates if needed
            if not isinstance(start_date, datetime):
                start_date = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=pytz.UTC)
            if not isinstance(end_date, datetime):
                end_date = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=pytz.UTC)
            
            filtered = [
                h for h in filtered 
                if h.get("published") and start_date <= parser.parse(h.get("published")).replace(tzinfo=pytz.UTC) <= end_date
            ]
    
    # Limit to max_headlines
    return filtered[:max_headlines]

if __name__ == "__main__":
    main() 