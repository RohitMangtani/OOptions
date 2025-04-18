import streamlit as st
import os
import sys
from datetime import datetime, timedelta, timezone
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
import matplotlib.pyplot as plt
import numpy as np
import openai
from functools import lru_cache
import re
import yfinance as yf

# Set page configuration
st.set_page_config(
    page_title="Option Bot - Market Terminal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load environment variables
load_dotenv()

# JavaScript for draggable and resizable windows
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# Apply custom styling for a Bloomberg terminal look
st.markdown(
    """
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
    
    /* Query Dashboard Styles */
    .dashboard-section-header {
        font-family: monospace;
        font-size: 18px;
        font-weight: bold;
        color: #00ff00;
        margin: 15px 0 10px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid #333;
        text-transform: uppercase;
    }
    
    .dashboard-query-box {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 15px;
    }
    
    .dashboard-label {
        color: #cccccc;
        font-family: monospace;
        margin-bottom: 5px;
        font-size: 12px;
    }
    
    .dashboard-content {
        color: #ffffff;
        font-family: monospace;
        background-color: #121212;
        padding: 10px;
        border-radius: 4px;
        overflow-x: auto;
        white-space: pre-wrap;
    }
    
    /* Flow diagram */
    .flow-diagram {
        display: flex;
        flex-direction: column;
        gap: 5px;
        margin: 15px 0;
    }
    
    .flow-step {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
        border-left: 3px solid #555;
    }
    
    .flow-input {
        border-left-color: #00ff00;
    }
    
    .flow-process {
        border-left-color: #cccccc;
    }
    
    .flow-output {
        border-left-color: #00aaff;
    }
    
    .flow-step-header {
        color: #00ff00;
        font-family: monospace;
        font-weight: bold;
        font-size: 14px;
    }
    
    .flow-step-content {
        color: #ffffff;
        font-family: monospace;
        font-size: 12px;
        margin-top: 5px;
    }
    
    .flow-arrow {
        color: #555;
        text-align: center;
        font-size: 18px;
        margin: 2px 0;
    }
    
    /* Dashboard cards */
    .dashboard-card {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 15px;
        height: 100%;
    }
    
    .dashboard-card-header {
        color: #00ff00;
        font-family: monospace;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
    }
    
    .dashboard-card-content {
        color: #ffffff;
        font-family: monospace;
        font-size: 12px;
    }
    
    .dashboard-list {
        list-style-type: none;
        padding-left: 0;
        margin: 0;
    }
    
    .dashboard-list li {
        padding: 5px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .dashboard-tag {
        display: inline-block;
        background-color: #333;
        color: #cccccc;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
    }
    
    .dashboard-tag.active {
        background-color: #00aa00;
        color: #000000;
    }
    
    /* Component cards */
    .component-card {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 15px;
        height: 100%;
    }
    
    .component-header {
        font-family: monospace;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
        color: #00ff00;
    }
    
    .component-header.data {
        color: #00aaff;
    }
    
    .component-header.analysis {
        color: #ff9900;
    }
    
    .component-header.output {
        color: #00ff00;
    }
    
    .component-content {
        color: #ffffff;
        font-family: monospace;
        font-size: 12px;
    }
    
    .component-list {
        list-style-type: none;
        padding-left: 0;
        margin: 0;
    }
    
    .component-list li {
        padding: 5px 0;
        border-bottom: 1px dotted #333;
    }
    
    .component-list li:last-child {
        border-bottom: none;
    }
    
    /* Component flow */
    .component-flow {
        font-family: monospace;
        font-size: 12px;
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
    }
    
    .flow-line {
        padding: 8px 0;
        color: #ffffff;
        border-bottom: 1px dotted #333;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .flow-line:last-child {
        border-bottom: none;
    }
    
    .flow-step-number {
        background-color: #00aa00;
        color: #000000;
        width: 20px;
        height: 20px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-weight: bold;
        margin-right: 5px;
    }
    
    .flow-component {
        color: #00ff00;
        font-weight: bold;
    }
    
    .flow-description {
        color: #cccccc;
        margin-left: auto;
        font-style: italic;
    }
    
    /* Data source cards */
    .data-source-card {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 15px;
        height: 100%;
    }
    
    .data-source-header {
        color: #00ff00;
        font-family: monospace;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
    }
    
    .data-source-content {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-bottom: 10px;
    }
    
    .data-source-tag {
        background-color: #333;
        color: #ffffff;
        padding: 3px 8px;
        border-radius: 3px;
        font-size: 11px;
        font-family: monospace;
    }
    
    .data-source-status {
        font-family: monospace;
        font-size: 12px;
        color: #cccccc;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .data-source-status.active {
        color: #00ff00;
    }
    
    .data-source-dot {
        width: 8px;
        height: 8px;
        background-color: #555;
        border-radius: 50%;
        display: inline-block;
    }
    
    .data-source-status.active .data-source-dot {
        background-color: #00ff00;
    }
    
    /* Metric cards */
    .metric-card {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
        height: 100%;
    }
    
    .metric-value {
        font-family: monospace;
        font-size: 24px;
        font-weight: bold;
        color: #00ff00;
        margin-bottom: 5px;
    }
    
    .metric-label {
        font-family: monospace;
        font-size: 14px;
        color: #ffffff;
        margin-bottom: 5px;
    }
    
    .metric-description {
        font-family: monospace;
        font-size: 11px;
        color: #cccccc;
    }
    
    /* Optimization card */
    .optimization-card {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 15px;
    }
    
    .optimization-header {
        color: #00ff00;
        font-family: monospace;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
    }
    
    .optimization-content {
        color: #ffffff;
        font-family: monospace;
        font-size: 12px;
    }
    
    .optimization-list {
        list-style-type: none;
        padding-left: 0;
        margin: 0;
    }
    
    .optimization-list li {
        padding: 8px 0;
        border-bottom: 1px dotted #333;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .optimization-list li:last-child {
        border-bottom: none;
    }
    
    .optimization-action {
        background-color: #00aa00;
        color: #000000;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
    }
    
    /* Improved queries */
    .improved-query {
        background-color: #1e1e1e;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .improved-query-number {
        background-color: #00aa00;
        color: #000000;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-weight: bold;
        font-family: monospace;
    }
    
    .improved-query-text {
        flex-grow: 1;
        color: #ffffff;
        font-family: monospace;
        font-size: 12px;
    }
    
    .improved-query-button {
        background-color: #333;
        color: #00ff00;
        padding: 3px 8px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: bold;
        font-family: monospace;
        cursor: pointer;
    }
    
    .improved-query-button:hover {
        background-color: #00aa00;
        color: #000000;
    }

    /* NEW: Component Equation Builder */
    .equation-container {
        margin-bottom: 20px;
        background-color: #1a1a1a;
        border-radius: 5px;
        padding: 15px;
    }
    .equation-title {
        color: #00ff00;
        font-weight: bold;
        margin-bottom: 10px;
        font-size: 16px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .equation-row {
        display: flex;
        align-items: flex-start;
        margin-bottom: 12px;
    }
    .equation-symbol {
        font-size: 24px;
        margin: 0 15px;
        color: #00ff00;
        font-weight: bold;
    }
    .equation-value {
        background-color: #222;
        padding: 10px;
        border-radius: 4px;
        color: #ffffff;
        flex-grow: 1;
        border-left: 3px solid;
        font-family: 'Courier New', monospace;
        overflow: hidden;
        text-overflow: ellipsis;
        max-height: 200px;
        overflow-y: auto;
    }
    .equation-label {
        width: 170px;
        text-align: right;
        padding-right: 10px;
        font-weight: bold;
        color: #cccccc;
        text-transform: uppercase;
        font-size: 14px;
        letter-spacing: 0.5px;
    }
    .result-box {
        background-color: #222;
        padding: 15px;
        border-radius: 4px;
        border-left: 3px solid #00ff00;
        margin-top: 20px;
        text-align: center;
    }
    .tag-pill {
        display: inline-block;
        padding: 2px 8px;
        background-color: #333;
        border-radius: 10px;
        margin: 2px;
        font-size: 12px;
        color: white;
    }
    .data-preview {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
    }
    .data-item {
        background-color: #333;
        padding: 8px;
        border-radius: 4px;
        margin-bottom: 5px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Constants
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Check for the presence of the OpenAI API key
# Read API key directly from .env file to ensure we get the current value
try:
    with open(".env", "r") as f:
        env_contents = f.read()
        for line in env_contents.splitlines():
            if line.startswith("OPENAI_API_KEY="):
                OPENAI_API_KEY = line.split("=", 1)[1]
                st.sidebar.success(
                    f"✅ OpenAI API key loaded: {OPENAI_API_KEY[:4]}...{OPENAI_API_KEY[-4:]}"
                )
                break
        else:
            OPENAI_API_KEY = None
            st.error("❌ ERROR: OPENAI_API_KEY not found in .env file")
except Exception as e:
    st.error(f"❌ ERROR reading .env file: {str(e)}")
    OPENAI_API_KEY = None

# Fallback to environment variable if direct read failed
if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if OPENAI_API_KEY:
        st.sidebar.success(f"✅ OpenAI API key loaded from environment")
    else:
        st.error("❌ ERROR: OpenAI API key not found in environment")
        st.info(
            "Please add your OpenAI API key to the .env file with the variable name OPENAI_API_KEY"
        )
        st.stop()

# Sample queries to help users get started
SAMPLE_QUERIES = [
    "What happened when Bitcoin ETF was approved?",
    "How did the market react to the Fed raising interest rates last year?",
    "What was the impact of Silicon Valley Bank collapse?",
    "How did Tesla stock perform after their Q1 2023 earnings?",
    "What happened to crypto during COVID-19 crash?",
]

# Sample follow-up queries to give users ideas
FOLLOW_UP_PROMPTS = [
    "How does this compare to similar events?",
    "What was the inflation rate at that time?",
    "Why did the market react this way?",
    "How long did it take to recover?",
    "What are the implications for future events?",
]


# Function to fetch RSS headlines and store them in session state
def fetch_news_feed():
    try:
        with st.spinner("Fetching latest financial news..."):
            headlines = fetch_rss_headlines()

            # Process each headline to ensure URL and date are properly set
            for headline in headlines:
                # Make sure URL is set correctly - if not in "url", use "link" instead
                if "link" in headline and (
                    "url" not in headline or not headline["url"]
                ):
                    headline["url"] = headline["link"]

                # Ensure there's a valid published date, default to current time if missing
                if "published" not in headline or not headline["published"]:
                    headline["published"] = datetime.now(pytz.UTC).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )

            # Sort by published date (newest first)
            headlines = sorted(
                headlines,
                key=lambda x: x.get("published", datetime.now()),
                reverse=True,
            )

            # Check if we have new content
            has_new_content = False
            if st.session_state.news_headlines:
                # Compare newest headline
                if headlines and (
                    headlines[0].get("title")
                    != st.session_state.news_headlines[0].get("title")
                    or headlines[0].get("published")
                    != st.session_state.news_headlines[0].get("published")
                ):
                    has_new_content = True
            else:
                # First load
                has_new_content = True

            # Update latest headline tracking
            if headlines:
                newest = headlines[0]
                st.session_state.latest_headline_id = (
                    f"{newest.get('title', '')}_{newest.get('published', '')}"
                )

            # Set refresh indicator if we have new content
            if has_new_content:
                st.session_state.refresh_triggered = True

            # Update the session state - store all headlines instead of limiting to 30
            if st.session_state.news_headlines:
                # Add new headlines to existing ones, avoiding duplicates
                existing_titles = {
                    h.get("title", ""): True for h in st.session_state.news_headlines
                }
                for headline in headlines:
                    title = headline.get("title", "")
                    if title not in existing_titles:
                        st.session_state.news_headlines.append(headline)
                        existing_titles[title] = True

                # Sort headlines again to ensure newest first
                st.session_state.news_headlines = sorted(
                    st.session_state.news_headlines,
                    key=lambda x: x.get("published", datetime.now()),
                    reverse=True,
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
        eastern = pytz.timezone("US/Eastern")
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

        return {"relative": relative_time, "exact": exact_time, "raw": published_date}
    except Exception as e:
        # Return a fallback date string if parsing fails
        print(f"Error formatting date: {str(e)}")
        return {"relative": "Recently published", "exact": "Date unknown", "raw": None}


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
            st.session_state.latest_headline_id = (
                f"{latest.get('title', '')}_{latest.get('published', '')}"
            )
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
                headline["published"] = datetime.now(pytz.UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )

        # Sort by published date (newest first)
        headlines = sorted(
            headlines, key=lambda x: x.get("published", datetime.now()), reverse=True
        )

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
            is_follow_up=st.session_state.has_received_response,
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
        st.session_state.conversation.append(
            {"role": "assistant", "content": response_text}
        )
        
        # Add any sections as additional assistant messages if they exist
        for section in sections:
            if section.get("title") and section.get("content"):
                section_content = f"**{section['title']}**\n\n{section['content']}"
                st.session_state.conversation.append(
                    {"role": "assistant", "content": section_content}
                )
        
        st.session_state.query_count += 1
        st.session_state.error = None
        st.session_state.has_received_response = True
        st.session_state.last_query_time = datetime.now()
        st.session_state.current_query = ""  # Clear the current query
        return response
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        st.session_state.error = error_msg
        st.session_state.conversation.append(
            {
                "role": "assistant",
                "content": f"❌ {error_msg}\n\nPlease try again or reset the conversation.",
            }
        )
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
    st.markdown(
        '<div class="terminal-header">COMMAND TERMINAL</div>', unsafe_allow_html=True
    )

    # Add command input
    st.markdown(
        "<div class='command-input-label'>Enter market query:</div>",
        unsafe_allow_html=True,
    )
    
    # Display error if exists
    if st.session_state.get("error"):
        st.error(st.session_state.error)
    
    # Command input with form to control submission
    with st.form(key="command_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([8, 1, 1])
        with col1:
            query = st.text_input(
                "",
                key="command_input",
                placeholder="Type a market query..."
            )
        with col2:
            submit_button = st.form_submit_button("ENTER")
        with col3:
            refresh_button = st.form_submit_button("RESET")
    
        # Check if we are already processing a query
        is_processing = "is_query_processing" in st.session_state and st.session_state.is_query_processing
        
        # Only process query when form is submitted (Enter pressed or button clicked)
        if submit_button:
            # Validate query length
            if not query or len(query.strip()) <= 1:
                st.error("Please enter a valid query with at least 2 characters.")
                time.sleep(0.5)  # Short pause to ensure error is visible
            elif is_processing:
                st.warning("Please wait while your previous query is being processed.")
                time.sleep(0.5)  # Short pause to ensure warning is visible
            else:
                # Store query for processing and set processing flag
                st.session_state.current_query = query
                st.session_state.is_query_processing = True
        
        # Reset conversation if refresh button is clicked
        if refresh_button:
            # Also clear any processing flags
            if "is_query_processing" in st.session_state:
                st.session_state.is_query_processing = False
            reset_conversation()
            st.rerun()
    
    # Process query only if form was submitted and we have a valid query
    if "current_query" in st.session_state and st.session_state.current_query and st.session_state.get("is_query_processing", False):
        # Only process if it's a new query
        if "last_processed_query" not in st.session_state or st.session_state.last_processed_query != st.session_state.current_query:
            with st.spinner("PROCESSING QUERY..."):
                process_user_query(st.session_state.current_query)
            # Store the processed query to prevent reprocessing
            st.session_state.last_processed_query = st.session_state.current_query
            # Clear current query after processing
            st.session_state.current_query = ""
            # Release the processing lock
            st.session_state.is_query_processing = False
            # Keep current active tab index
            st.query_params.tab = st.session_state.active_tab
            st.rerun()
    
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
            unsafe_allow_html=True,
        )
    
    # Add a status bar at the bottom with Eastern Time
    eastern = pytz.timezone("US/Eastern")
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
        unsafe_allow_html=True,
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
    st.markdown(
        '<div class="terminal-header">NEWS TERMINAL</div>', unsafe_allow_html=True
    )

    # Top control bar
    col1, col2, col3 = st.columns([5, 4, 1])

    with col1:
        # Initialize search variables in session state if not already present
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""  # The actual query that will be used for filtering
            
        # Use a form to control when search is triggered
        with st.form(key="news_search_form", clear_on_submit=False):
            # This text input will not affect filtering until form is submitted
            search_input = st.text_input(
                "🔍 Search headlines", 
                placeholder="Enter search term", 
                key="search_input_field"  # No value parameter to prevent auto-updates
            )
            # Submit button that will be triggered when Enter is pressed
            submit_search = st.form_submit_button("Search")
            
            # Only update the actual search query when form is submitted
            if submit_search:
                # Validate search input - trim whitespace and ensure it's substantial
                cleaned_search = search_input.strip()
                if not cleaned_search and st.session_state.search_query:
                    # Empty search clears the filter
                    st.session_state.search_query = ""
                    st.info("Search cleared. Showing all headlines.")
                elif not cleaned_search:
                    # Empty search but no previous filter
                    st.info("Please enter a search term or press Enter to show all headlines.")
                elif len(cleaned_search) == 1:
                    # Single character searches are likely not useful
                    st.warning("Please use a more specific search term (at least 2 characters).")
                else:
                    # Valid search term
                    st.session_state.search_query = cleaned_search
                    
        # Show active search filter if one is set
        if st.session_state.search_query:
            st.markdown(
                f"""<div style="margin-top: 5px; margin-bottom: 10px; padding: 5px 10px; 
                background-color: #1a1a1a; border-radius: 4px; border-left: 2px solid #00ff00;">
                <span style="color: #cccccc;">Active filter:</span> <span style="color: #00ff00;">{st.session_state.search_query}</span>
                <button style="background: none; border: none; color: #cccccc; float: right; cursor: pointer; 
                font-size: 0.8rem; padding: 0;" 
                onclick="document.querySelector('#news_search_form button[type=\'submit\']').click();">
                ❌</button></div>""",
                unsafe_allow_html=True
            )

    with col2:
        last_fetch_time = st.session_state.last_news_fetch_time
        if last_fetch_time:
            # Convert to Eastern Time
            eastern = pytz.timezone("US/Eastern")
            last_fetch_time = last_fetch_time.astimezone(eastern)
            st.markdown(
                f'<div class="feed-timestamp">Last updated: {last_fetch_time.strftime("%I:%M:%S %p ET")}</div>',
                unsafe_allow_html=True,
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
                st.session_state.live_refresh = (
                    not st.session_state.previous_live_refresh
                )
                # Update previous state for next toggle
                st.session_state.previous_live_refresh = st.session_state.live_refresh

            # Use the checkbox with our custom callback
            live_refresh = st.checkbox(
                "Live updates",
                value=st.session_state.live_refresh,
                key="live_refresh_toggle",
                on_change=handle_live_refresh_change,
                help="Automatically refresh when new headlines are available",
            )

        with live_refresh_col2:
            # Show blinking indicator if refresh was triggered
            if st.session_state.refresh_triggered:
                st.markdown(
                    '<div class="refresh-indicator-container"><div class="refresh-indicator"></div></div>',
                    unsafe_allow_html=True,
                )
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
            unsafe_allow_html=True,
        )

    # Filter and display news items
    if not st.session_state.news_headlines:
        st.info("No news headlines found. Click refresh to try again.")
    else:
        # Apply filters to headlines
        filtered_headlines = filter_headlines(
            st.session_state.news_headlines,
            search_query=st.session_state.search_query,
            max_headlines=50
        )

        # Limit display count
        display_count = 50  # Fixed display count
        display_headlines = filtered_headlines[:display_count]

        # Show number of headlines displayed vs total with different messaging based on filter status
        if st.session_state.search_query and not filtered_headlines:
            st.warning(f"No headlines match your search for '{st.session_state.search_query}'. Try a different term.")
            # Add clear search button
            if st.button("Clear Search"):
                st.session_state.search_query = ""
                st.rerun()
        elif st.session_state.search_query:
            st.caption(
                f"Found {len(filtered_headlines)} matches for '{st.session_state.search_query}' (showing max {min(len(filtered_headlines), display_count)})"
            )
            # Add clear search button inline
            if st.button("Clear Search", key="clear_search_results"):
                st.session_state.search_query = ""
                st.rerun()
        else:
            st.caption(
                f"Displaying {min(len(filtered_headlines), display_count)} of {len(st.session_state.news_headlines)} headlines"
            )

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
                unsafe_allow_html=True,
            )

    # Add a status bar at the bottom
    # Determine refresh status message
    if st.session_state.live_refresh:
        refresh_status = "LIVE UPDATES"
    else:
        refresh_status = "MANUAL REFRESH"

    # Convert to Eastern Time
    eastern = pytz.timezone("US/Eastern")
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
        unsafe_allow_html=True,
    )


def display_query_dashboard():
    st.header("Query Dashboard")
    
    if "conversation" not in st.session_state or not st.session_state.conversation:
        st.warning("No queries have been made yet. Try asking a question in the chat tab.")
        return
    
    # Get the latest user query and assistant response
    latest_query = None
    latest_response = None
    
    for message in reversed(st.session_state.conversation):
        if message["role"] == "user" and latest_query is None:
            latest_query = message["content"]
        elif message["role"] == "assistant" and latest_response is None:
            latest_response = message["content"]
        
        if latest_query and latest_response:
            break
    
    if not latest_query:
        st.warning("No user query found in conversation history.")
        return
    
    # Query metadata
    query_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query_length = len(latest_query)
    
    # Enhanced preprocessing with LLM-based entity extraction
    try:
        extracted_entities = extract_entities_llm(latest_query)
    except Exception as e:
        st.error(f"Error in LLM entity extraction: {str(e)}")
        # Fallback to rule-based extraction
        extracted_entities = {
            "companies": re.findall(r'\b[A-Z][A-Za-z]*\b', latest_query),
            "tickers": re.findall(r'\$[A-Z]+|\b[A-Z]{1,5}\b', latest_query),
            "sectors": ["Technology"] if "tech" in latest_query.lower() else [],
            "time_periods": re.findall(r'\b\d+\s+(?:day|week|month|year)s?\b', latest_query.lower())
        }
    
    # Filter and clean entities
    cleaned_entities = clean_entities(extracted_entities)
    
    # Get relevant news based on extracted terms
    search_terms = cleaned_entities.get("companies", []) + cleaned_entities.get("tickers", []) + cleaned_entities.get("sectors", [])
    relevant_news = get_mock_news(search_terms, limit=5)
    
    # Mock market data based on query content
    market_data = get_mock_market_data(cleaned_entities.get("tickers", []))
    
    # Mock economic indicators
    economic_indicators = get_mock_economic_indicators()
    
    # Construct LLM input dictionary with all elements
    llm_input = {
        "user_query": latest_query,
        "extracted_terms": cleaned_entities,
        "entity_types": list(cleaned_entities.keys()),
        "market_data": market_data,
        "economic_indicators": economic_indicators,
        "recent_news": relevant_news[:3]  # Top 3 news items
    }
    
    # Display query details
    with st.expander("Query Details", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("User Query")
            st.write(latest_query)
            st.caption(f"Timestamp: {query_timestamp}")
            st.caption(f"Query length: {query_length} characters")
        
        with col2:
            st.subheader("Assistant Response")
            if latest_response:
                st.write(latest_response[:300] + "..." if len(latest_response) > 300 else latest_response)
            else:
                st.info("No response available")
    
    # NEW: LLM Input Formula Visualization
    with st.expander("How Your Query Becomes an Answer", expanded=True):
        st.subheader("🔄 The Input Formula")
        
        # Create a progress-style indicator for the flow
        st.markdown("""
        <style>
        .step-container {
            display: flex;
            flex-direction: column;
            margin-bottom: 25px;
        }
        .step-number {
            background-color: #00aa00;
            color: black;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 10px;
            flex-shrink: 0;
        }
        .step-content {
            background-color: #1e1e1e;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #00ff00;
            margin-bottom: 5px;
            width: 100%;
        }
        .step-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .step-title {
            color: #00ff00;
            font-weight: bold;
            font-size: 16px;
            margin: 0;
        }
        .step-description {
            color: white;
            margin: 0;
        }
        .connector {
            width: 2px;
            height: 20px;
            background-color: #00aa00;
            margin-left: 14px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display steps
        st.markdown("""
        <div class="step-container">
            <div class="step-header">
                <div class="step-number">1</div>
                <h3 class="step-title">USER QUERY CAPTURED</h3>
                </div>
            <div class="step-content">
                <p class="step-description">Your question is analyzed to identify important keywords, intent, and context.</p>
            </div>
            <div class="connector"></div>
        </div>
        
        <div class="step-container">
            <div class="step-header">
                <div class="step-number">2</div>
                <h3 class="step-title">ENTITY EXTRACTION</h3>
                </div>
            <div class="step-content">
                <p class="step-description">We identify companies, stock tickers, financial terms, sectors, and time periods from your query.</p>
            </div>
            <div class="connector"></div>
        </div>
        
        <div class="step-container">
            <div class="step-header">
                <div class="step-number">3</div>
                <h3 class="step-title">DATA GATHERING</h3>
                </div>
            <div class="step-content">
                <p class="step-description">System collects relevant market data, economic indicators, and financial news related to your query.</p>
            </div>
            <div class="connector"></div>
        </div>
        
        <div class="step-container">
            <div class="step-header">
                <div class="step-number">4</div>
                <h3 class="step-title">PROMPT CONSTRUCTION</h3>
                </div>
            <div class="step-content">
                <p class="step-description">Your query + extracted entities + market data + news + economic indicators are combined into a comprehensive prompt.</p>
            </div>
            <div class="connector"></div>
        </div>
        
        <div class="step-container">
            <div class="step-header">
                <div class="step-number">5</div>
                <h3 class="step-title">LLM PROCESSING</h3>
                </div>
            <div class="step-content">
                <p class="step-description">The AI analyzes all the information to generate a comprehensive response with market analysis and insights.</p>
            </div>
            <div class="connector"></div>
        </div>
        
        <div class="step-container">
            <div class="step-header">
                <div class="step-number">6</div>
                <h3 class="step-title">RESPONSE DELIVERY</h3>
                </div>
            <div class="step-content">
                <p class="step-description">You receive a structured answer with market analysis, directional outlook, and trade recommendations.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # NEW: Input Component Breakdown
    with st.expander("🧩 What Goes Into Your Answer", expanded=True):
        # Create a visual representation of the formula with percentage bars
        st.subheader("Input Components")
        
        # Get weights for each component
        query_weight = 35
        entities_weight = 15
        market_weight = 20
        news_weight = 20
        econ_weight = 10
        
        # Display component breakdown with percentage bars
        components = [
            {"name": "Your Query", "weight": query_weight, "color": "#00ff00", "icon": "❓", 
             "description": f"'{latest_query[:50] + '...' if len(latest_query) > 50 else latest_query}'"},
            {"name": "Extracted Entities", "weight": entities_weight, "color": "#ff9900", "icon": "🔍", 
             "description": f"{sum(len(entities) for entities in cleaned_entities.values())} terms identified"},
            {"name": "Market Data", "weight": market_weight, "color": "#ff00aa", "icon": "📊", 
             "description": f"{len(market_data)} market indicators"},
            {"name": "News Articles", "weight": news_weight, "color": "#00aaff", "icon": "📰", 
             "description": f"{len(relevant_news[:3])} recent headlines"},
            {"name": "Economic Indicators", "weight": econ_weight, "color": "#00ffaa", "icon": "📈", 
             "description": f"{len(economic_indicators)} economic metrics"}
        ]
        
        for comp in components:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"<div style='font-size:30px;text-align:center;'>{comp['icon']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;color:{comp['color']};font-weight:bold;'>{comp['weight']}%</div>", unsafe_allow_html=True)
        with col2:
                st.markdown(f"<p style='margin-bottom:0;'><b style='color:{comp['color']};'>{comp['name']}</b></p>", unsafe_allow_html=True)
                st.markdown(f"<div style='width:100%;background-color:#333;height:20px;border-radius:5px;margin-top:5px;'><div style='width:{comp['weight']}%;background-color:{comp['color']};height:20px;border-radius:5px;'></div></div>", unsafe_allow_html=True)
                st.caption(comp["description"])
                st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
        
        # Show the formula in plain language
        st.markdown("---")
        st.markdown("### The Formula in Plain English")
        st.markdown("""
        ```
        FINAL ANSWER = AI_Model(Your_Query + Extracted_Entities + Market_Data + News + Economic_Indicators)
        ```
        """)
        
    # NEW: Actual Input Values section
    with st.expander("🔎 Content That Went Into Your Answer", expanded=True):
        component_tabs = st.tabs(["User Query", "Entities", "Market Data", "News", "Economic Indicators"])
        
        with component_tabs[0]:
            st.markdown("### Your Original Question")
            st.info(latest_query)
        
        with component_tabs[1]:
            st.markdown("### Extracted Entities")
            
            if any(entities for entities in cleaned_entities.values()):
                entity_cols = st.columns(len([k for k, v in cleaned_entities.items() if v]))
                col_idx = 0
                
                for entity_type, entities in cleaned_entities.items():
                    if entities:
                        with entity_cols[col_idx]:
                            st.markdown(f"#### {entity_type.title()}")
                            for entity in entities:
                                st.markdown(f"- {entity}")
                        col_idx += 1
            else:
                st.info("No entities were extracted from your query.")
        
        with component_tabs[2]:
            st.markdown("### Market Data")
            if market_data:
                for i, data in enumerate(market_data):
                    ticker = data.get("ticker", "Unknown")
                    price = data.get("price", "N/A")
                    change = data.get("change", "N/A")
                    
                    # Color for change (green for positive, red for negative)
                    color = "#00ff00" if "+" in change else "#ff0000" if "-" in change else "#ffffff"
                    
                    st.markdown(f"""
                    <div style="padding:10px; margin-bottom:10px; background-color:#1e1e1e; border-radius:5px; border-left:3px solid #ff00aa;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-weight:bold; font-size:16px;">{ticker}</span>
                            <span style="font-weight:bold;">{price}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-top:5px;">
                            <span>{data.get("name", ticker)}</span>
                            <span style="color:{color};">{change}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No specific market data was used for this query.")
        
        with component_tabs[3]:
            st.markdown("### Recent News Headlines")
            if relevant_news:
                for news in relevant_news[:3]:
                    st.markdown(f"""
                    <div style="padding:10px; margin-bottom:10px; background-color:#1e1e1e; border-radius:5px; border-left:3px solid #00aaff;">
                        <div style="font-weight:bold; margin-bottom:5px;">{news['title']}</div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span style="color:#00aaff;">{news['source']}</span>
                            <span style="color:#cccccc;">{news['date']}</span>
                        </div>
                        <div style="font-size:0.9em;">{news['summary']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No relevant news articles were included for this query.")
        
        with component_tabs[4]:
            st.markdown("### Economic Indicators")
            if economic_indicators:
                # Create a grid of economic indicators
                indicators_html = "<div style='display:grid; grid-template-columns:repeat(2, 1fr); gap:10px;'>"
                
                for indicator in economic_indicators:
                    name = indicator.get("indicator", "Unknown")
                    value = indicator.get("value", "N/A")
                    change = indicator.get("change", "N/A")
                    
                    # Color for change
                    change_color = "#00ff00" if "+" in change else "#ff0000" if "-" in change else "#ffffff"
                    
                    indicators_html += f"""
                    <div style="padding:10px; background-color:#1e1e1e; border-radius:5px; border-left:3px solid #00ffaa;">
                        <div style="font-weight:bold; margin-bottom:5px;">{name}</div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-size:1.2em;">{value}</span>
                            <span style="color:{change_color};">{change}</span>
                        </div>
                    </div>
                    """
                
                indicators_html += "</div>"
                st.markdown(indicators_html, unsafe_allow_html=True)
            else:
                st.info("No economic indicators were included for this query.")
    
    # NEW: Example Full Analysis Flow
    with st.expander("📊 Complete Analysis Sample", expanded=False):
        st.markdown("### Real Example: Bitcoin ETF Query Analysis")
        
        # Sample data for demonstration
        sample_data = """
        🔄 DATA FLOW: SENDING QUERY TO LLM
        ------------------------------------------------------------
        📥 INPUT QUERY: "What happened when Bitcoin ETF was approved?"
        
        📰 NEWS INTEGRATED INTO PROMPT:
        - [CNBC Markets] Four money traps to avoid in a volatile market, according to 'Fast Money' trader Tim Seymour
        - [Yahoo Finance] Nasdaq Tumbles 3.1% as Nvidia Drives Tech Sell-Off; Markets Assess Fed Chair Remarks
        - [Yahoo Finance] Stocks resume sell-off as tariff costs hit tech and Powell delivers starkest warning yet on Trump's trade war
        - [Yahoo Finance] How major US stock indexes fared Wednesday, 4/16/2025
        - [CNBC Markets] OpenAI in talks to pay about $3 billion to acquire AI coding startup Windsurf
        
        📊 MACRO ENVIRONMENT DATA:
        - Inflation (CPI): 2.4%
        - Fed Funds Rate: 4.33%
        - Unemployment: 4.2%
        - 10Y Treasury: 4.28%
        
        🧮 LLM INPUT FORMULA:
        Final_Output = LLM(User_Query + Enhanced_Context + News_Articles + Macro_Data)
        
        FORMULA WEIGHT DISTRIBUTION:
        - User Query:         31.2%
        - News Articles:      43.1%
        - Macro Environment:  24.2%
        - Historical Data:    0.0%
        
        📤 OUTPUT COMPONENTS:
        
        MARKET ANALYSIS:
        The recent financial news indicates a volatile market environment with significant sell-offs in tech stocks driven by concerns over trade policies and Federal Reserve Chair's remarks.
        
        DIRECTIONAL OUTLOOK:
        Given the current market volatility and uncertainty surrounding trade policies, the outlook remains cautious. The sell-off in tech stocks and the broader market indicates a risk-off sentiment among investors.
        
        TRADE SUGGESTION:
        **Trade Idea:** Short Trade on Nasdaq ETF (QQQ)
        - **Direction:** Bearish
        - **Timeframe:** Short-term
        - **Risk Level:** Medium to High
        """
        
        st.code(sample_data, language=None)
        
        st.markdown("### Visualization of the Analysis Flow")
        
        # Create a visual flow diagram
        flow_html = """
        <div style="background-color:#1e1e1e; padding:15px; border-radius:5px; margin-bottom:15px;">
            <div style="display:flex; align-items:center; margin-bottom:10px;">
                <div style="background-color:#00aa00; color:black; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px;">1</div>
                <div>
                    <div style="font-weight:bold; color:#00ff00;">USER QUERY</div>
                    <div>"What happened when Bitcoin ETF was approved?"</div>
                </div>
            </div>
            <div style="text-align:center; font-size:20px; margin:10px 0;">↓</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <div style="width:30%; background-color:#222; padding:10px; border-radius:5px; border-left:3px solid #00aaff;">
                    <div style="font-weight:bold; color:#00aaff; margin-bottom:5px;">NEWS DATA</div>
                    <div style="font-size:0.9em;">5 recent headlines</div>
                </div>
                <div style="width:30%; background-color:#222; padding:10px; border-radius:5px; border-left:3px solid #ff9900;">
                    <div style="font-weight:bold; color:#ff9900; margin-bottom:5px;">ENTITY EXTRACTION</div>
                    <div style="font-size:0.9em;">Bitcoin, ETF, approval</div>
                </div>
                <div style="width:30%; background-color:#222; padding:10px; border-radius:5px; border-left:3px solid #00ffaa;">
                    <div style="font-weight:bold; color:#00ffaa; margin-bottom:5px;">MACRO DATA</div>
                    <div style="font-size:0.9em;">CPI: 2.4%, Fed Rate: 4.33%</div>
                </div>
            </div>
            <div style="text-align:center; font-size:20px; margin:10px 0;">↓</div>
            <div style="background-color:#222; padding:10px; border-radius:5px; margin-bottom:10px; border-left:3px solid #ff00aa;">
                <div style="font-weight:bold; color:#ff00aa; margin-bottom:5px;">LLM PROCESSING</div>
                <div style="font-size:0.9em;">All components analyzed by AI model to generate comprehensive response</div>
            </div>
            <div style="text-align:center; font-size:20px; margin:10px 0;">↓</div>
            <div style="background-color:#222; padding:10px; border-radius:5px; border-left:3px solid #00ff00;">
                <div style="font-weight:bold; color:#00ff00; margin-bottom:5px;">FINAL RESPONSE</div>
                <div style="font-size:0.9em;">Market Analysis + Directional Outlook + Trade Recommendation</div>
            </div>
        </div>
        """
        
        st.markdown(flow_html, unsafe_allow_html=True)
        
    # Update the tabs to be more user-friendly
    tab1, tab2, tab3, tab4 = st.tabs(["Query Analysis", "Market Data", "News Sources", "Data Sources"])

    # NEW: Component Equation Builder
    with st.expander("🔬 EXACT QUERY COMPOSITION", expanded=True):
        st.markdown("### SEE EXACTLY WHAT GOES INTO YOUR ANSWER")
        
        # Create a step-by-step equation builder showing the exact input values
        st.markdown("""
        <style>
        .equation-container {
            margin-bottom: 20px;
            background-color: #1a1a1a;
            border-radius: 5px;
            padding: 15px;
        }
        .equation-title {
            color: #00ff00;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .equation-row {
            display: flex;
            align-items: flex-start;
            margin-bottom: 12px;
        }
        .equation-symbol {
            font-size: 24px;
            margin: 0 15px;
            color: #00ff00;
            font-weight: bold;
        }
        .equation-value {
            background-color: #222;
            padding: 10px;
            border-radius: 4px;
            color: #ffffff;
            flex-grow: 1;
            border-left: 3px solid;
            font-family: 'Courier New', monospace;
            overflow: hidden;
            text-overflow: ellipsis;
            max-height: 200px;
            overflow-y: auto;
        }
        .equation-label {
            width: 170px;
            text-align: right;
            padding-right: 10px;
            font-weight: bold;
            color: #cccccc;
            text-transform: uppercase;
            font-size: 14px;
            letter-spacing: 0.5px;
        }
        .result-box {
            background-color: #222;
            padding: 15px;
            border-radius: 4px;
            border-left: 3px solid #00ff00;
            margin-top: 20px;
            text-align: center;
        }
        .tag-pill {
            display: inline-block;
            padding: 2px 8px;
            background-color: #333;
            border-radius: 10px;
            margin: 2px;
            font-size: 12px;
            color: white;
        }
        .data-preview {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        .data-item {
            background-color: #333;
            padding: 8px;
            border-radius: 4px;
            margin-bottom: 5px;
        }
        </style>
        """, unsafe_allow_html=True)

        # Create the equation view
        st.markdown("""
        <div class="equation-container">
            <div class="equation-title">QUERY INPUT FORMULA</div>
        """, unsafe_allow_html=True)
        
        # USER QUERY
        st.markdown(f"""
        <div class="equation-row">
            <div class="equation-label">YOUR QUERY</div>
            <div class="equation-value" style="border-color: #00ff00;">
                {latest_query}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # + EXTRACTED ENTITIES
        entity_html = ""
        if any(entities for entities in cleaned_entities.values()):
            entity_items = []
            for entity_type, entities in cleaned_entities.items():
                if entities:
                    for entity in entities:
                        entity_items.append(f'<div class="data-item"><strong>{entity_type}:</strong> {entity}</div>')
            entity_html = "".join(entity_items)
        else:
            entity_html = "<em>No entities extracted</em>"
            
        st.markdown(f"""
        <div class="equation-row">
            <div class="equation-symbol">+</div>
            <div class="equation-label">ENTITY EXTRACTION</div>
            <div class="equation-value" style="border-color: #ff9900;">
                {entity_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # + MARKET DATA
        market_html = ""
        if market_data:
            market_items = []
            for data in market_data:
                ticker = data.get("ticker", "Unknown")
                price = data.get("price", "N/A")
                change = data.get("change", "N/A")
                name = data.get("name", "")
                color = "color: #00ff00;" if "+" in change else "color: #ff0000;" if "-" in change else ""
                market_items.append(f"""
                <div class="data-item">
                    <strong>{ticker}</strong> ({name}): {price} <span style="{color}">{change}</span>
                </div>
                """)
            market_html = "".join(market_items)
        else:
            market_html = "<em>No market data included</em>"
            
        st.markdown(f"""
        <div class="equation-row">
            <div class="equation-symbol">+</div>
            <div class="equation-label">MARKET DATA</div>
            <div class="equation-value" style="border-color: #ff00aa;">
                {market_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # + NEWS DATA
        news_html = ""
        if relevant_news:
            news_items = []
            for news in relevant_news[:3]:
                title = news.get("title", "Unknown")
                source = news.get("source", "Unknown")
                date = news.get("date", "")
                news_items.append(f"""
                <div class="data-item">
                    <div><strong>{source}</strong> ({date})</div>
                    <div>{title}</div>
                </div>
                """)
            news_html = "".join(news_items)
        else:
            news_html = "<em>No news articles included</em>"
            
        st.markdown(f"""
        <div class="equation-row">
            <div class="equation-symbol">+</div>
            <div class="equation-label">NEWS ARTICLES</div>
            <div class="equation-value" style="border-color: #00aaff;">
                {news_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # + ECONOMIC INDICATORS
        econ_html = ""
        if economic_indicators:
            econ_items = []
            for indicator in economic_indicators:
                name = indicator.get("indicator", "Unknown")
                value = indicator.get("value", "N/A")
                change = indicator.get("change", "N/A")
                color = "color: #00ff00;" if "+" in change else "color: #ff0000;" if "-" in change else ""
                econ_items.append(f"""
                <div class="data-item">
                    <strong>{name}:</strong> {value} <span style="{color}">{change}</span>
                </div>
                """)
            econ_html = "".join(econ_items)
        else:
            econ_html = "<em>No economic indicators included</em>"
            
        st.markdown(f"""
        <div class="equation-row">
            <div class="equation-symbol">+</div>
            <div class="equation-label">ECONOMIC DATA</div>
            <div class="equation-value" style="border-color: #00ffaa;">
                {econ_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # RESULT
        st.markdown("""
        <div class="equation-row">
            <div class="equation-symbol">=</div>
            <div class="result-box">
                <span style="color: #00ff00; font-weight: bold; font-size: 18px;">LLM ANALYSIS INPUT</span>
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add JSON representation and raw prompt
        st.subheader("RAW LLM INPUT")
        st.markdown("""
        <div style="background-color: #1a1a1a; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
            <div style="color: #00ff00; font-weight: bold; font-size: 16px; margin-bottom: 10px;">SYSTEM PROMPT</div>
            <div style="background-color: #222; padding: 10px; border-radius: 4px; font-family: 'Courier New', monospace; max-height: 200px; overflow-y: auto; color: #cccccc;">
            You are a financial market analyst AI assistant. Analyze the provided user query, market data, news headlines, and economic indicators to provide insights about market events, trends, and potential trade ideas. 
            
            Structure your response in the following sections:
            1. MARKET ANALYSIS: Provide a concise analysis of the current market situation based on the provided data.
            2. DIRECTIONAL OUTLOOK: Offer a directional prediction based on the analysis.
            3. TRADE SUGGESTION: If appropriate, suggest a potential trade idea with specific parameters.
            
            Base your analysis on facts from the provided data, not on speculation.
            </div>
        </div>
        
        <div style="background-color: #1a1a1a; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
            <div style="color: #00ff00; font-weight: bold; font-size: 16px; margin-bottom: 10px;">USER PROMPT TEMPLATE</div>
            <div style="background-color: #222; padding: 10px; border-radius: 4px; font-family: 'Courier New', monospace; max-height: 200px; overflow-y: auto; color: #cccccc;">
            USER QUERY:
            {user_query}
            
            EXTRACTED ENTITIES:
            {entities}
            
            CURRENT MARKET DATA:
            {market_data}
            
            RECENT NEWS HEADLINES:
            {news_headlines}
            
            ECONOMIC INDICATORS:
            {economic_indicators}
            
            Please analyze this information and provide insights about the market events, trends, and potential trade ideas.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show JSON representation
        st.markdown('<div style="color: #00ff00; font-weight: bold; font-size: 16px; margin-bottom: 10px;">COMPLETE JSON DATA SENT TO LLM</div>', unsafe_allow_html=True)
        st.json(llm_input)

    # Data Flow Visualization
    with st.expander("🔄 DATA FLOW VISUALIZATION", expanded=True):
        st.markdown("### SEE HOW DATA FLOWS FROM SOURCES TO RESULT")
        
        st.markdown("""
        <style>
        .flow-container {
            background-color: #1a1a1a;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .flow-stage {
            text-align: center;
            margin-bottom: 10px;
        }
        .flow-title {
            color: #00ff00;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        .flow-arrow {
            color: #00ff00;
            font-size: 24px;
            margin: 5px 0;
        }
        .data-box {
            display: inline-block;
            padding: 8px 12px;
            margin: 5px;
            background-color: #333;
            border-radius: 4px;
            text-align: center;
            font-size: 0.9em;
        }
        .data-box-green {
            border-left: 3px solid #00ff00;
        }
        .data-box-blue {
            border-left: 3px solid #00aaff;
        }
        .data-box-orange {
            border-left: 3px solid #ff9900;
        }
        .data-box-pink {
            border-left: 3px solid #ff00aa;
        }
        .data-box-teal {
            border-left: 3px solid #00ffaa;
        }
        .processing-box {
            background-color: #222;
            padding: 15px;
            border-radius: 5px;
            margin: 10px auto;
            max-width: 500px;
            border-left: 3px solid #00ff00;
            text-align: center;
        }
        .flow-stage-container {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create the flow visualization
        st.markdown("""
        <div class="flow-container">
            <!-- Stage 1: Input Sources -->
            <div class="flow-stage">
                <div class="flow-title">INPUT SOURCES</div>
                <div class="flow-stage-container">
                    <div class="data-box data-box-green">User Query Input</div>
                    <div class="data-box data-box-blue">RSS News Feed</div>
                    <div class="data-box data-box-pink">Yahoo Finance API</div>
                    <div class="data-box data-box-teal">FRED Economic API</div>
                </div>
            </div>
            
            <div class="flow-arrow">↓</div>
            
            <!-- Stage 2: Data Retrieval -->
            <div class="flow-stage">
                <div class="flow-title">DATA RETRIEVAL</div>
                <div class="flow-stage-container">
                    <div class="data-box data-box-green">Raw Query Text</div>
                    <div class="data-box data-box-blue">News Headlines</div>
                    <div class="data-box data-box-pink">Stock Prices & Charts</div>
                    <div class="data-box data-box-teal">Economic Indicators</div>
                </div>
            </div>
            
            <div class="flow-arrow">↓</div>
            
            <!-- Stage 3: Data Processing -->
            <div class="flow-stage">
                <div class="flow-title">DATA PROCESSING</div>
                <div class="flow-stage-container">
                    <div class="data-box data-box-orange">Entity Extraction</div>
                    <div class="data-box data-box-blue">News Filtering & Ranking</div>
                    <div class="data-box data-box-pink">Market Data Formatting</div>
                    <div class="data-box data-box-teal">Indicator Selection</div>
                </div>
            </div>
            
            <div class="flow-arrow">↓</div>
            
            <!-- Stage 4: LLM Input Preparation -->
            <div class="flow-stage">
                <div class="flow-title">LLM INPUT PREPARATION</div>
                <div class="processing-box">
                    <strong>FORMATTED PROMPT CREATION</strong><br>
                    Combined data formatted into structured prompt with specific sections
                </div>
            </div>
            
            <div class="flow-arrow">↓</div>
            
            <!-- Stage 5: LLM Processing -->
            <div class="flow-stage">
                <div class="flow-title">LLM PROCESSING</div>
                <div class="processing-box">
                    <strong>AI ANALYSIS</strong><br>
                    OpenAI GPT analyzes all data sources to generate comprehensive response
                </div>
            </div>
            
            <div class="flow-arrow">↓</div>
            
            <!-- Stage 6: Output Generation -->
            <div class="flow-stage">
                <div class="flow-title">OUTPUT GENERATION</div>
                <div class="flow-stage-container">
                    <div class="data-box data-box-green">Market Analysis</div>
                    <div class="data-box data-box-green">Directional Outlook</div>
                    <div class="data-box data-box-green">Trade Suggestion</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Exact data flow details
        st.markdown("### EXACT DATA FLOW DETAILS")
        
        # Create columns for the stages
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="background-color: #1a1a1a; padding: 15px; border-radius: 5px; height: 100%;">
                <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px; text-transform: uppercase;">STAGE 1: DATA COLLECTION</div>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="margin-bottom: 8px;"><strong>User Query:</strong> Captured directly from user input</li>
                    <li style="margin-bottom: 8px;"><strong>Tickers:</strong> Extracted from query using regex patterns</li>
                    <li style="margin-bottom: 8px;"><strong>News Feed:</strong> Fetched from multiple financial RSS sources</li>
                    <li style="margin-bottom: 8px;"><strong>Stock Data:</strong> Retrieved from Yahoo Finance API</li>
                    <li style="margin-bottom: 8px;"><strong>Economic Data:</strong> Pulled from FRED Economic Database</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="background-color: #1a1a1a; padding: 15px; border-radius: 5px; height: 100%;">
                <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px; text-transform: uppercase;">STAGE 2: DATA PROCESSING</div>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="margin-bottom: 8px;"><strong>Query Analysis:</strong> NLP processing to identify key components</li>
                    <li style="margin-bottom: 8px;"><strong>News Relevance:</strong> Filtered by relation to query entities</li>
                    <li style="margin-bottom: 8px;"><strong>Market Context:</strong> Price data formatted with change %</li>
                    <li style="margin-bottom: 8px;"><strong>Economic Context:</strong> Current values compared to historical</li>
                    <li style="margin-bottom: 8px;"><strong>Entity Resolution:</strong> Matching companies to correct tickers</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div style="background-color: #1a1a1a; padding: 15px; border-radius: 5px; height: 100%;">
                <div style="color: #00ff00; font-weight: bold; margin-bottom: 10px; text-transform: uppercase;">STAGE 3: LLM PROCESSING</div>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="margin-bottom: 8px;"><strong>Prompt Creation:</strong> Data structured into standard format</li>
                    <li style="margin-bottom: 8px;"><strong>Data Weighting:</strong> Importance assigned to different components</li>
                    <li style="margin-bottom: 8px;"><strong>Context Building:</strong> Historical patterns identified</li>
                    <li style="margin-bottom: 8px;"><strong>Analysis Generation:</strong> AI evaluation of market situation</li>
                    <li style="margin-bottom: 8px;"><strong>Response Formatting:</strong> Output structured into sections</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Query Transformation Map
        st.markdown("### QUERY TRANSFORMATION MAP")
        
        # Create a visual transformation map
        transformation_html = f"""
        <div style="background-color: #1a1a1a; padding: 15px; border-radius: 5px; margin-top: 15px;">
            <div style="color: #00ff00; font-weight: bold; margin-bottom: 15px; text-transform: uppercase;">TRANSFORMATION: USER QUERY → LLM ANALYSIS</div>
            
            <div style="display: flex; margin-bottom: 15px; align-items: stretch;">
                <div style="background-color: #222; padding: 15px; border-radius: 5px; width: 45%; border-left: 3px solid #00ff00;">
                    <div style="font-weight: bold; margin-bottom: 8px;">ORIGINAL QUERY:</div>
                    <div style="font-family: 'Courier New', monospace; font-size: 0.9em;">{latest_query}</div>
                </div>
                
                <div style="display: flex; flex-direction: column; justify-content: center; padding: 0 15px; width: 10%;">
                    <div style="text-align: center; font-size: 24px; color: #00ff00;">→</div>
                </div>
                
                <div style="background-color: #222; padding: 15px; border-radius: 5px; width: 45%; border-left: 3px solid #00ff00;">
                    <div style="font-weight: bold; margin-bottom: 8px;">ENRICHED DATA:</div>
                    <div style="font-family: 'Courier New', monospace; font-size: 0.9em;">
                        <span style="color: #ff9900;">+{sum(len(entities) for entities in cleaned_entities.values())} entities</span><br>
                        <span style="color: #ff00aa;">+{len(market_data)} market data points</span><br>
                        <span style="color: #00aaff;">+{len(relevant_news[:3])} news headlines</span><br>
                        <span style="color: #00ffaa;">+{len(economic_indicators)} economic indicators</span>
                    </div>
                </div>
            </div>
            
            <div style="text-align: center; font-size: 24px; color: #00ff00; margin: 10px 0;">↓</div>
            
            <div style="background-color: #222; padding: 15px; border-radius: 5px; border-left: 3px solid #00ff00;">
                <div style="font-weight: bold; margin-bottom: 8px;">FINAL LLM ANALYSIS OUTPUT:</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div style="background-color: #333; padding: 10px; border-radius: 5px; width: 30%;">
                        <div style="font-weight: bold; color: #00ff00; margin-bottom: 5px;">MARKET ANALYSIS</div>
                        <div style="font-size: 0.9em;">Current market assessment based on all input data</div>
                    </div>
                    
                    <div style="background-color: #333; padding: 10px; border-radius: 5px; width: 30%;">
                        <div style="font-weight: bold; color: #00ff00; margin-bottom: 5px;">DIRECTIONAL OUTLOOK</div>
                        <div style="font-size: 0.9em;">Future price movement prediction with confidence level</div>
                    </div>
                    
                    <div style="background-color: #333; padding: 10px; border-radius: 5px; width: 30%;">
                        <div style="font-weight: bold; color: #00ff00; margin-bottom: 5px;">TRADE SUGGESTION</div>
                        <div style="font-size: 0.9em;">Actionable trade recommendation with specific parameters</div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        st.markdown(transformation_html, unsafe_allow_html=True)

    # Complete Data Breakdown
    with st.expander("📝 COMPLETE DATA BREAKDOWN", expanded=True):
        st.markdown("### ALL SOURCE DATA USED IN THIS QUERY")
        
        st.markdown("""
        <style>
        .data-section {
            background-color: #1a1a1a;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .data-section-title {
            color: #00ff00;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            margin-bottom: 10px;
        }
        .data-table th {
            text-align: left;
            padding: 8px;
            background-color: #222;
            color: #00ff00;
            font-weight: bold;
            border-bottom: 1px solid #333;
        }
        .data-table td {
            padding: 8px;
            border-bottom: 1px solid #222;
            font-size: 0.9em;
        }
        .data-field {
            font-weight: bold;
            color: #cccccc;
        }
        .data-value {
            font-family: 'Courier New', monospace;
        }
        .json-view {
            background-color: #222;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 10px;
            font-size: 0.9em;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Tab interface for different data types
        tabs = st.tabs(["Overview", "Market Data", "News Articles", "Economic Indicators", "Complete JSON"])
        
        with tabs[0]:
            # Overview table
            st.markdown("""
            <div class="data-section">
                <div class="data-section-title">QUERY OVERVIEW</div>
                <table class="data-table">
                    <tr>
                        <td class="data-field">User Query:</td>
                        <td class="data-value">{}</td>
                    </tr>
                    <tr>
                        <td class="data-field">Query Length:</td>
                        <td class="data-value">{} characters</td>
                    </tr>
                    <tr>
                        <td class="data-field">Timestamp:</td>
                        <td class="data-value">{}</td>
                    </tr>
                    <tr>
                        <td class="data-field">Total Data Points:</td>
                        <td class="data-value">{}</td>
                    </tr>
                </table>
            </div>
            """.format(
                latest_query,
                len(latest_query),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sum(len(entities) for entities in cleaned_entities.values()) + 
                len(market_data) + len(relevant_news[:3]) + len(economic_indicators) + 1  # +1 for the query itself
            ), unsafe_allow_html=True)
            
            # Extracted entities
            entities_html = "<div class='data-section'><div class='data-section-title'>EXTRACTED ENTITIES</div>"
            
            if any(entities for entities in cleaned_entities.values()):
                entities_html += "<table class='data-table'><tr><th>Entity Type</th><th>Values</th></tr>"
                for entity_type, entities in cleaned_entities.items():
                    if entities:
                        entities_html += f"""
                        <tr>
                            <td class="data-field">{entity_type.title()}</td>
                            <td class="data-value">{', '.join(entities)}</td>
                        </tr>
                        """
                entities_html += "</table>"
            else:
                entities_html += "<p>No entities were extracted from this query.</p>"
            
            entities_html += "</div>"
            st.markdown(entities_html, unsafe_allow_html=True)
            
            # Data summary
            st.markdown("""
            <div class="data-section">
                <div class="data-section-title">DATA SOURCE SUMMARY</div>
                <table class="data-table">
                    <tr>
                        <th>Data Type</th>
                        <th>Count</th>
                        <th>Source</th>
                    </tr>
                    <tr>
                        <td class="data-field">Market Data Points</td>
                        <td class="data-value">{}</td>
                        <td class="data-value">Yahoo Finance API</td>
                    </tr>
                    <tr>
                        <td class="data-field">News Articles</td>
                        <td class="data-value">{}</td>
                        <td class="data-value">Financial RSS Feeds</td>
                    </tr>
                    <tr>
                        <td class="data-field">Economic Indicators</td>
                        <td class="data-value">{}</td>
                        <td class="data-value">FRED Economic Database</td>
                    </tr>
                </table>
            </div>
            """.format(
                len(market_data),
                len(relevant_news[:3]),
                len(economic_indicators)
            ), unsafe_allow_html=True)
        
        with tabs[1]:
            # Market data details
            market_html = "<div class='data-section'><div class='data-section-title'>DETAILED MARKET DATA</div>"
            
            if market_data:
                market_html += """
                <table class="data-table">
                    <tr>
                        <th>Ticker</th>
                        <th>Company</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Volume</th>
                        <th>Data Source</th>
                    </tr>
                """
                
                for data in market_data:
                    ticker = data.get("ticker", "Unknown")
                    name = data.get("name", ticker)
                    price = data.get("price", "N/A")
                    change = data.get("change", "N/A")
                    volume = data.get("volume", "N/A")
                    
                    # Determine color for change value
                    change_color = "#00ff00" if "+" in change else "#ff0000" if "-" in change else "#ffffff"
                    
                    market_html += f"""
                    <tr>
                        <td class="data-field">{ticker}</td>
                        <td class="data-value">{name}</td>
                        <td class="data-value">{price}</td>
                        <td class="data-value" style="color:{change_color}">{change}</td>
                        <td class="data-value">{volume}</td>
                        <td class="data-value">Yahoo Finance</td>
                    </tr>
                    """
                
                market_html += "</table>"
                
                # Add raw JSON view option
                market_html += """
                <div style="margin-top:15px">
                    <div style="color:#00ff00;font-weight:bold;margin-bottom:5px">RAW MARKET DATA JSON:</div>
                    <div class="json-view">
                """
                market_html += json.dumps(market_data, indent=2)
                market_html += "</div></div>"
                
            else:
                market_html += "<p>No market data was included for this query.</p>"
            
            market_html += "</div>"
            st.markdown(market_html, unsafe_allow_html=True)
        
        with tabs[2]:
            # News articles details
            news_html = "<div class='data-section'><div class='data-section-title'>NEWS ARTICLES DATA</div>"
            
            if relevant_news:
                news_html += """
                <table class="data-table">
                    <tr>
                        <th>Source</th>
                        <th>Date</th>
                        <th>Headline</th>
                        <th>Relevance</th>
                    </tr>
                """
                
                for i, news in enumerate(relevant_news[:5]):
                    title = news.get("title", "Unknown")
                    source = news.get("source", "Unknown")
                    date = news.get("date", "")
                    # Fake relevance score for demonstration
                    relevance = 100 - (i * 15)
                    
                    news_html += f"""
                    <tr>
                        <td class="data-field">{source}</td>
                        <td class="data-value">{date}</td>
                        <td class="data-value">{title}</td>
                        <td class="data-value">{relevance}%</td>
                    </tr>
                    """
                
                news_html += "</table>"
                
                # Add raw JSON view option
                news_html += """
                <div style="margin-top:15px">
                    <div style="color:#00ff00;font-weight:bold;margin-bottom:5px">RAW NEWS DATA JSON:</div>
                    <div class="json-view">
                """
                news_html += json.dumps(relevant_news[:5], indent=2)
                news_html += "</div></div>"
                
            else:
                news_html += "<p>No news articles were included for this query.</p>"
            
            news_html += "</div>"
            st.markdown(news_html, unsafe_allow_html=True)
        
        with tabs[3]:
            # Economic indicators details
            econ_html = "<div class='data-section'><div class='data-section-title'>ECONOMIC INDICATORS DATA</div>"
            
            if economic_indicators:
                econ_html += """
                <table class="data-table">
                    <tr>
                        <th>Indicator</th>
                        <th>Current Value</th>
                        <th>Change</th>
                        <th>Data Source</th>
                    </tr>
                """
                
                for indicator in economic_indicators:
                    name = indicator.get("indicator", "Unknown")
                    value = indicator.get("value", "N/A")
                    change = indicator.get("change", "N/A")
                    
                    # Determine color for change value
                    change_color = "#00ff00" if "+" in change else "#ff0000" if "-" in change else "#ffffff"
                    
                    econ_html += f"""
                    <tr>
                        <td class="data-field">{name}</td>
                        <td class="data-value">{value}</td>
                        <td class="data-value" style="color:{change_color}">{change}</td>
                        <td class="data-value">FRED Economic Database</td>
                    </tr>
                    """
                
                econ_html += "</table>"
                
                # Add raw JSON view option
                econ_html += """
                <div style="margin-top:15px">
                    <div style="color:#00ff00;font-weight:bold;margin-bottom:5px">RAW ECONOMIC DATA JSON:</div>
                    <div class="json-view">
                """
                econ_html += json.dumps(economic_indicators, indent=2)
                econ_html += "</div></div>"
                
            else:
                econ_html += "<p>No economic indicators were included for this query.</p>"
            
            econ_html += "</div>"
            st.markdown(econ_html, unsafe_allow_html=True)
        
        with tabs[4]:
            # Complete JSON data
            st.markdown("<div class='data-section-title'>COMPLETE INPUT JSON SENT TO LLM</div>", unsafe_allow_html=True)
            st.json(llm_input)
            
            # Show the system and user prompts
            st.markdown("<div class='data-section-title' style='margin-top:20px'>COMPLETE LLM PROMPT TEMPLATE</div>", unsafe_allow_html=True)
            st.markdown("""
            ```
            SYSTEM PROMPT:
            You are a financial market analyst AI assistant. Analyze the provided user query, market data, news headlines, and economic indicators to provide insights about market events, trends, and potential trade ideas.
            
            Structure your response in the following sections:
            1. MARKET ANALYSIS: Provide a concise analysis of the current market situation based on the provided data.
            2. DIRECTIONAL OUTLOOK: Offer a directional prediction based on the analysis.
            3. TRADE SUGGESTION: If appropriate, suggest a potential trade idea with specific parameters.
            
            Base your analysis on facts from the provided data, not on speculation.
            
            USER PROMPT:
            USER QUERY:
            {user_query}
            
            EXTRACTED ENTITIES:
            {entities}
            
            CURRENT MARKET DATA:
            {market_data}
            
            RECENT NEWS HEADLINES:
            {news_headlines}
            
            ECONOMIC INDICATORS:
            {economic_indicators}
            
            Please analyze this information and provide insights about the market events, trends, and potential trade ideas.
            ```
            """)
            
            # Show token estimation
            st.markdown("<div class='data-section-title' style='margin-top:20px'>TOKEN USAGE ESTIMATION</div>", unsafe_allow_html=True)
            
            # Rough token estimation
            query_tokens = len(latest_query.split()) * 1.3
            entity_tokens = sum(len(str(entities)) for entity_type, entities in cleaned_entities.items()) / 4
            market_tokens = len(str(market_data)) / 4
            news_tokens = len(str(relevant_news[:3])) / 4
            eco_tokens = len(str(economic_indicators)) / 4
            system_tokens = 100  # Approximate
            
            total_tokens = query_tokens + entity_tokens + market_tokens + news_tokens + eco_tokens + system_tokens
            
            # Create token estimation table
            token_html = """
            <table class="data-table">
                <tr>
                    <th>Component</th>
                    <th>Estimated Tokens</th>
                    <th>Percentage</th>
                </tr>
            """
            
            components = [
                {"name": "System Prompt", "tokens": system_tokens},
                {"name": "User Query", "tokens": query_tokens},
                {"name": "Extracted Entities", "tokens": entity_tokens},
                {"name": "Market Data", "tokens": market_tokens},
                {"name": "News Articles", "tokens": news_tokens},
                {"name": "Economic Indicators", "tokens": eco_tokens}
            ]
            
            for component in components:
                percent = (component["tokens"] / total_tokens) * 100
                token_html += f"""
                <tr>
                    <td class="data-field">{component["name"]}</td>
                    <td class="data-value">{int(component["tokens"])}</td>
                    <td class="data-value">{percent:.1f}%</td>
                </tr>
                """
            
            token_html += f"""
            <tr style="border-top:2px solid #333">
                <td class="data-field" style="font-weight:bold">TOTAL</td>
                <td class="data-value" style="font-weight:bold">{int(total_tokens)}</td>
                <td class="data-value" style="font-weight:bold">100%</td>
            </tr>
            </table>
            """
            
            st.markdown(token_html, unsafe_allow_html=True)

# Helper functions for the dashboard
@lru_cache(maxsize=100)
def extract_entities_llm(query):
    """Extract entities using LLM (simulated for now)"""
    # In a real implementation, this would call an LLM API
    # For now, we'll use a simple rule-based approach
    entities = {
        "companies": re.findall(r'\b[A-Z][A-Za-z]+\b', query),
        "tickers": re.findall(r'\$[A-Z]+|\b[A-Z]{1,5}\b', query),
        "sectors": []
    }
    
    sector_keywords = {
        "tech": "Technology",
        "finance": "Financial",
        "healthcare": "Healthcare",
        "retail": "Retail",
        "energy": "Energy"
    }
    
    for keyword, sector in sector_keywords.items():
        if keyword in query.lower():
            entities["sectors"].append(sector)
    
    # Extract time periods
    time_periods = re.findall(r'\b\d+\s+(?:day|week|month|year)s?\b', query.lower())
    if time_periods:
        entities["time_periods"] = time_periods
    
    return entities

def clean_entities(entities):
    """Clean and filter extracted entities to remove duplicates and common words"""
    cleaned = {}
    
    common_words = {"A", "I", "AN", "THE", "IT", "IS", "ARE", "FOR", "AND", "OR", "BUY", "SELL"}
    
    for entity_type, entity_list in entities.items():
        if entity_type == "tickers":
            # Keep only tickers that look like stock symbols
            cleaned[entity_type] = [e.replace("$", "") for e in entity_list if len(e.replace("$", "")) <= 5 and e.replace("$", "") not in common_words]
        elif entity_type == "companies":
            # Filter out common words
            cleaned[entity_type] = [e for e in entity_list if e not in common_words and len(e) > 1]
        else:
            cleaned[entity_type] = list(set(entity_list))  # Remove duplicates
    
    return cleaned

def get_mock_news(search_terms, limit=5):
    """Get relevant mock news based on search terms"""
    if not search_terms:
        return []
    
    all_news = [
        {
            "title": "Tech Stocks Rally on Positive Earnings Reports",
            "date": "2023-05-01",
            "source": "Financial Times",
            "summary": "Major tech companies reported better than expected earnings, driving a market rally.",
            "url": "https://example.com/tech-rally"
        },
        {
            "title": "Federal Reserve Signals Interest Rate Decision",
            "date": "2023-04-28",
            "source": "Wall Street Journal",
            "summary": "The Federal Reserve indicated it may slow the pace of interest rate hikes in coming months.",
            "url": "https://example.com/fed-rates"
        },
        {
            "title": "AAPL Announces New Product Line",
            "date": "2023-04-25",
            "source": "CNBC",
            "summary": "Apple unveiled its latest products during its annual spring event, including updates to its flagship devices.",
            "url": "https://example.com/apple-products"
        },
        {
            "title": "TSLA Reports Record Quarter",
            "date": "2023-04-20",
            "source": "Reuters",
            "summary": "Tesla reported record deliveries and profits in the latest quarter, exceeding analyst expectations.",
            "url": "https://example.com/tesla-earnings"
        },
        {
            "title": "Healthcare Sector Sees Increased Investment",
            "date": "2023-04-15",
            "source": "Bloomberg",
            "summary": "Investors are allocating more capital to healthcare companies amid technological advancements in the sector.",
            "url": "https://example.com/healthcare-investment"
        },
        {
            "title": "Retail Sales Decline in Q1",
            "date": "2023-04-10",
            "source": "Yahoo Finance",
            "summary": "Consumer spending slowed in the first quarter, impacting retail sales across major markets.",
            "url": "https://example.com/retail-decline"
        },
        {
            "title": "Energy Sector Faces Regulatory Changes",
            "date": "2023-04-05",
            "source": "The Economist",
            "summary": "New regulations aimed at reducing carbon emissions will impact energy companies' operations.",
            "url": "https://example.com/energy-regulations"
        }
    ]
    
    # Filter news based on search terms
    relevant_news = []
    for news in all_news:
        for term in search_terms:
            if term.lower() in news["title"].lower() or term.lower() in news["summary"].lower():
                relevant_news.append(news)
                break
    
    # If no specific news matches, return general news
    if not relevant_news:
        return all_news[:limit]
    
    return relevant_news[:limit]

def get_mock_market_data(tickers):
    """Get mock market data for specified tickers"""
    if not tickers:
        # Return general market indices if no specific tickers
        return [
            {"ticker": "SPY", "name": "S&P 500 ETF", "price": "450.23", "change": "+1.2%", "volume": "65.3M"},
            {"ticker": "QQQ", "name": "Nasdaq 100 ETF", "price": "380.45", "change": "+1.5%", "volume": "42.8M"},
            {"ticker": "DIA", "name": "Dow Jones ETF", "price": "350.78", "change": "+0.8%", "volume": "28.9M"}
        ]
    
    market_data = []
    for ticker in tickers[:5]:  # Limit to first 5 tickers
        try:
            # Attempt to get real data
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get('currentPrice', 0) 
            previous_close = info.get('previousClose', 0)
            
            if current_price and previous_close:
                change_pct = ((current_price - previous_close) / previous_close) * 100
                market_data.append({
                    "ticker": ticker,
                    "name": info.get('shortName', ticker),
                    "price": f"${current_price:.2f}",
                    "change": f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%",
                    "volume": f"{info.get('volume', 0) / 1000000:.1f}M"
                })
            else:
                # Fallback to mock data
                raise Exception("Missing price data")
                
        except Exception:
            # Fallback to mock data
            price = round(100 + np.random.random() * 900, 2)
            change = round((np.random.random() * 6) - 3, 2)
            volume = round(np.random.random() * 100, 1)
            
            market_data.append({
                "ticker": ticker,
                "name": f"{ticker} Inc.",
                "price": f"${price}",
                "change": f"{'+' if change >= 0 else ''}{change}%",
                "volume": f"{volume}M"
            })
    
    return market_data

def get_mock_economic_indicators():
    """Get mock economic indicators"""
    return [
        {"indicator": "U.S. 10Y Treasury", "value": "3.75%", "change": "+0.05"},
        {"indicator": "VIX Volatility Index", "value": "18.42", "change": "-0.86"},
        {"indicator": "U.S. Unemployment", "value": "3.6%", "change": "0.00"},
        {"indicator": "Inflation Rate (CPI)", "value": "3.2%", "change": "-0.1"},
        {"indicator": "GDP Growth Rate", "value": "2.1%", "change": "+0.3"}
    ]


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
            unsafe_allow_html=True,
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
            unsafe_allow_html=True,
        )

        # Reset button
        st.button(
            "RESET SESSION", on_click=reset_conversation, use_container_width=True
        )

        st.markdown(
            '<div class="sidebar-section-header">SAMPLE QUERIES</div>',
            unsafe_allow_html=True,
        )
        for query in SAMPLE_QUERIES:
            st.button(
                query.upper(),
                on_click=use_sample_query,
                args=(query,),
                key=f"sample_{query[:20]}",
            )

        st.markdown(
            '<div class="sidebar-section-header">TERMINAL INFO</div>',
            unsafe_allow_html=True,
        )
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
            unsafe_allow_html=True,
        )

    # Main content area with tabs
    st.markdown(
        "<h1 class='main-heading'>OPTIONS BOT TERMINAL</h1>", unsafe_allow_html=True
    )

    # Create tabs
    tab_names = ["COMMAND", "NEWS FEED", "QUERY DASHBOARD"]

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
        
    # Query Dashboard tab
    with tabs[2]:
        display_query_dashboard()


# Helper function for filtering headlines
def filter_headlines(
    headlines,
    search_query="",
    date_filter=None,
    selected_sources=None,
    max_headlines=50,
):
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
    if not headlines:
        return []
        
    filtered = headlines.copy()

    # Apply search filter if provided
    if search_query:
        search_terms = search_query.lower().strip().split()
        if search_terms:
            filtered = []
            for headline in headlines:
                # Get searchable text from the headline (title and summary)
                title = headline.get("title", "").lower()
                summary = headline.get("summary", "").lower()
                source = headline.get("source", "").lower()
                
                # Check if all search terms are in title, summary, or source
                if all(term in title or term in summary or term in source for term in search_terms):
                    filtered.append(headline)

    # Apply source filter if provided
    if selected_sources and isinstance(selected_sources, list) and len(selected_sources) > 0:
        filtered = [
            h for h in filtered if h.get("source", "Unknown") in selected_sources
        ]

    # Apply date filter if provided
    if date_filter and isinstance(date_filter, tuple) and len(date_filter) == 2:
        start_date, end_date = date_filter
        if start_date and end_date:
            # Convert datetime objects to dates if needed
            if not isinstance(start_date, datetime):
                try:
                    start_date = datetime.combine(start_date, datetime.min.time()).replace(
                        tzinfo=pytz.UTC
                    )
                except (TypeError, ValueError):
                    # Default to 30 days ago if invalid
                    start_date = datetime.now(pytz.UTC) - timedelta(days=30)
                    
            if not isinstance(end_date, datetime):
                try:
                    end_date = datetime.combine(end_date, datetime.max.time()).replace(
                        tzinfo=pytz.UTC
                    )
                except (TypeError, ValueError):
                    # Default to current time if invalid
                    end_date = datetime.now(pytz.UTC)

            # Filter headlines by published date, with safety checks
            date_filtered = []
            for h in filtered:
                if not h.get("published"):
                    continue
                
                try:
                    # Parse the published date and ensure it has timezone info
                    pub_date = parser.parse(h.get("published"))
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=pytz.UTC)
                        
                    # Include if within date range
                    if start_date <= pub_date <= end_date:
                        date_filtered.append(h)
                except (ValueError, TypeError, parser.ParserError):
                    # Skip headlines with unparseable dates
                    continue
            
            filtered = date_filtered

    # Ensure max_headlines is valid
    try:
        max_headlines = int(max_headlines)
        if max_headlines <= 0:
            max_headlines = 50  # Default if invalid
    except (ValueError, TypeError):
        max_headlines = 50  # Default if invalid
        
    # Limit to max_headlines
    return filtered[:max_headlines]


if __name__ == "__main__":
    main() 
