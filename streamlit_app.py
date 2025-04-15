import streamlit as st
import os
import sys
from datetime import datetime
import traceback
import json
import time
import pandas as pd
import threading
from llm_event_query import process_query, create_new_session, get_session
from rss_ingestor import fetch_rss_headlines, FINANCIAL_FEEDS
from llm_event_classifier import classify_macro_event

# Load API keys from Streamlit secrets
if 'OPENAI_API_KEY' in st.secrets:
    os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
    print("Loaded OpenAI API key from Streamlit secrets")

if 'FRED_API_KEY' in st.secrets:
    os.environ['FRED_API_KEY'] = st.secrets['FRED_API_KEY']
    print("Loaded FRED API key from Streamlit secrets")

if 'CLOUD_STORAGE_API_KEY' in st.secrets:
    os.environ['CLOUD_STORAGE_API_KEY'] = st.secrets['CLOUD_STORAGE_API_KEY']
    print("Loaded Cloud Storage API key from Streamlit secrets")

# Set page configuration
st.set_page_config(
    page_title="Ooptions - Market Event Analysis",
    page_icon="📈",
    layout="wide"
)

# Custom CSS to fix font colors and improve visibility
st.markdown("""
<style>
    /* Main app styling */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* Improve button contrast */
    .stButton button {
        background-color: #1e293b;
        color: white;
        border: 1px solid #334155;
    }
    
    /* Improve chat message visibility */
    .user-message {
        background-color: #1e293b;
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    .assistant-message {
        background-color: #152238;
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    /* Fix sidebar text color */
    .css-1d391kg {
        color: white;
    }
    
    /* Fix sidebar headers */
    .sidebar .stMarkdown h1, .sidebar .stMarkdown h2, .sidebar .stMarkdown h3 {
        color: white;
    }
    
    /* Fix captions */
    .stMarkdown p {
        color: #e2e8f0;
    }
    
    /* Fix info box */
    .stAlert {
        background-color: #1e293b;
        color: white;
    }
    
    /* Improve context hint visibility */
    .context-hint {
        color: #93c5fd;
        font-size: 0.9em;
        margin-bottom: 10px;
    }
    
    /* News feed styles */
    .news-card {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    
    .news-source {
        color: #93c5fd;
        font-size: 0.8em;
    }
    
    .news-time {
        color: #64748b;
        font-size: 0.8em;
    }
    
    .news-title {
        font-size: 1.1em;
        font-weight: bold;
        margin: 5px 0;
    }
    
    /* Alert card styling */
    .alert-high {
        border-left: 4px solid #ef4444;
        background-color: rgba(239, 68, 68, 0.1);
    }
    
    .alert-medium {
        border-left: 4px solid #f59e0b;
        background-color: rgba(245, 158, 11, 0.1);
    }
    
    .alert-low {
        border-left: 4px solid #10b981;
        background-color: rgba(16, 185, 129, 0.1);
    }
</style>
""", unsafe_allow_html=True)

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
    "Can you recommend a trade based on this analysis?",
    "What specific asset would you invest in based on this?",
    "What trading strategy would work best in this scenario?",
    "How would this affect other cryptocurrencies?",
    "What would be a good hedging strategy here?"
]

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
        st.session_state.cached_data = {}  # Store retrieved data for reuse
        st.session_state.analysis_context = {
            "tickers": [],
            "dates": [],
            "macro_data": {},
            "market_data": {},
            "events": []
        }  # Track analyzed items
        
    # News feed session state
    if "news_feed" not in st.session_state:
        st.session_state.news_feed = []
        st.session_state.last_news_fetch = None
        st.session_state.important_headlines = []
        st.session_state.interpreted_headlines = []
        st.session_state.auto_refresh = True
        st.session_state.news_lock = threading.Lock()
    
    # Trade alerts session state
    if "trade_alerts" not in st.session_state:
        st.session_state.trade_alerts = []
        st.session_state.last_alert_check = None
        
    # Load saved data if it exists
    load_data()

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
        st.session_state.cached_data = {}
        st.session_state.analysis_context = {
            "tickers": [],
            "dates": [],
            "macro_data": {},
            "market_data": {},
            "events": []
        }
        st.success("Conversation reset. New session started.")
    except Exception as e:
        st.error(f"Error resetting conversation: {str(e)}")

# Function to extract and store context from response
def extract_context_from_response(response):
    # Skip if response isn't a dictionary or doesn't have the expected fields
    if not isinstance(response, dict):
        return
    
    # Extract and store tickers
    if "ticker" in response:
        ticker = response.get("ticker")
        if ticker and ticker not in st.session_state.analysis_context["tickers"]:
            st.session_state.analysis_context["tickers"].append(ticker)
    
    # Extract and store dates
    if "event_date" in response:
        date = response.get("event_date")
        if date and date not in st.session_state.analysis_context["dates"]:
            st.session_state.analysis_context["dates"].append(date)
    
    # Store macro data if available
    if "macro_data" in response and isinstance(response["macro_data"], dict):
        st.session_state.analysis_context["macro_data"].update(response["macro_data"])
    
    # Store market data if available
    if "price_change_pct" in response or "volatility_pct" in response:
        ticker = response.get("ticker", "unknown")
        market_data = {
            "price_change": response.get("price_change_pct"),
            "volatility": response.get("volatility_pct"),
            "max_drawdown": response.get("max_drawdown_pct")
        }
        st.session_state.analysis_context["market_data"][ticker] = market_data
    
    # Store event information
    if "event_date" in response and "ticker" in response:
        event = {
            "date": response.get("event_date"),
            "ticker": response.get("ticker"),
            "description": response.get("event_description", "")
        }
        st.session_state.analysis_context["events"].append(event)
    
    # Cache the whole response for potential reuse
    response_id = f"response_{st.session_state.query_count}"
    st.session_state.cached_data[response_id] = response

# Function to process user query
def process_user_query(user_query):
    # Add to conversation history immediately for better UX
    st.session_state.conversation.append({"role": "user", "content": user_query})
    
    try:
        is_follow_up = st.session_state.has_received_response
        
        # Process the query
        response, new_session_id = process_query(
            user_query, 
            st.session_state.session_id,
            # If we've already had a conversation, treat this as a follow-up
            is_follow_up=is_follow_up
        )
        
        # Update session ID if changed
        if new_session_id:
            st.session_state.session_id = new_session_id
        
        # Extract response content
        if isinstance(response, dict) and "response" in response:
            response_text = response["response"]
            sections = response.get("sections", [])
            
            # Extract and store context if this is not a follow-up or has new data
            if not is_follow_up or "success" in response and response.get("success"):
                extract_context_from_response(response)
                
        elif isinstance(response, tuple) and len(response) > 0:
            response_text = response[0]
            sections = []
        else:
            response_text = str(response)
            sections = []
        
        # For follow-up queries, augment response with context about data reuse
        if is_follow_up and st.session_state.cached_data:
            # Only add this context note for certain types of follow-ups
            if any(keyword in user_query.lower() for keyword in ["trade", "invest", "buy", "sell", "strategy", "recommendation"]):
                context_items = []
                
                if st.session_state.analysis_context["tickers"]:
                    tickers_str = ", ".join(st.session_state.analysis_context["tickers"])
                    context_items.append(f"using market data for {tickers_str}")
                
                if st.session_state.analysis_context["dates"]:
                    recent_date = st.session_state.analysis_context["dates"][-1]
                    context_items.append(f"based on the event date {recent_date}")
                
                if context_items:
                    context_note = " and ".join(context_items)
                    response_text = f"{response_text}\n\n_Note: This recommendation is {context_note} from our previous analysis._"
        
        # Add main response to conversation
        st.session_state.conversation.append({"role": "assistant", "content": response_text})
        
        # Add any sections as additional assistant messages if they exist
        for section in sections:
            if section and isinstance(section, dict) and "title" in section and "content" in section:
                section_text = f"**{section['title']}**\n\n{section['content']}"
                st.session_state.conversation.append({"role": "assistant", "content": section_text})
        
        # Update session state
        st.session_state.has_received_response = True
        st.session_state.query_count += 1
        st.session_state.last_query_time = datetime.now()
        st.session_state.current_query = ""  # Clear the current query
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        if not isinstance(e, (ValueError, TypeError)):
            error_msg += "\n\n" + traceback.format_exc()
        
        st.session_state.error = error_msg
        st.session_state.conversation.append({"role": "assistant", "content": f"Error: {str(e)}"})

def use_sample_query(query):
    # Set the query in session state to be processed
    st.session_state.current_query = query

def get_follow_up_suggestion():
    # If we have analyzed tickers, suggest trade-related follow-ups more often
    if st.session_state.analysis_context["tickers"]:
        # Bias towards trade recommendations for tickers we've analyzed
        trade_prompts = [p for p in FOLLOW_UP_PROMPTS if any(keyword in p.lower() for keyword in ["trade", "invest", "strategy"])]
        if trade_prompts:
            return trade_prompts[hash(datetime.now().minute) % len(trade_prompts)]
    
    # Otherwise return a generic follow-up prompt
    return FOLLOW_UP_PROMPTS[hash(datetime.now().minute) % len(FOLLOW_UP_PROMPTS)]

def show_context_information():
    """Show analysis context information in the sidebar."""
    
    # Show tickers
    if st.session_state.analysis_context["tickers"]:
        st.sidebar.markdown(f"**Tickers:** {', '.join(st.session_state.analysis_context['tickers'])}")
    
    # Show dates
    if st.session_state.analysis_context["dates"]:
        st.sidebar.markdown(f"**Event dates:** {', '.join(st.session_state.analysis_context['dates'])}")
    
    # Show macro data snapshot if available
    if st.session_state.analysis_context["macro_data"]:
        with st.sidebar.expander("Macro Data"):
            for key, value in st.session_state.analysis_context["macro_data"].items():
                if not key.startswith("_") and isinstance(value, (int, float)):
                    st.markdown(f"**{key}:** {value}")

def display_search_interface():
    """Display the search tab interface (original functionality)"""
    st.header("🔍 Market Event Analysis")
    
    # Display error if exists
    if st.session_state.get("error"):
        st.error(st.session_state.error)
    
    # Display conversation history with improved styling
    for message in st.session_state.conversation:
        if message["role"] == "user":
            st.markdown(
                f"<div class='user-message'>"
                f"<b>You:</b> {message['content']}"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='assistant-message'>"
                f"<b>Assistant:</b> {message['content']}"
                f"</div>",
                unsafe_allow_html=True
            )
    
    # Input area with context-aware prompt
    if st.session_state.has_received_response:
        st.markdown("<h3 style='color: white;'>Follow up question</h3>", unsafe_allow_html=True)
        placeholder_text = get_follow_up_suggestion()
        query_prompt = f"Ask a follow-up question about this analysis..."
        
        # Add a hint about context retention with improved visibility
        if st.session_state.query_count > 0:
            st.markdown(
                f"<div class='context-hint'>"
                f"💡 Try asking something like '{placeholder_text}' - I'll use the data I've already gathered"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<h3 style='color: white;'>Ask a question</h3>", unsafe_allow_html=True)
        query_prompt = "Ask about a market event..."
    
    # Query input - no value parameter
    query = st.chat_input(query_prompt)
    
    # Process query if entered by user or if a sample query was selected
    if query or st.session_state.current_query:
        # If query came from chat input, use that; otherwise use the sample query
        user_query = query if query else st.session_state.current_query
        if user_query:  # Make sure we have a query to process
            with st.spinner("Analyzing market data..."):
                process_user_query(user_query)
            st.rerun()
    
    # First-time welcome message with improved styling
    if not st.session_state.conversation:
        st.markdown(
            """
            <div style="background-color: #1e293b; padding: 20px; border-radius: 10px; color: white;">
            <h3 style="color: #93c5fd;">👋 Welcome to the Market Event Analysis tool!</h3>
            <p>
            Ask me about historical market events, and I'll provide analysis based on 
            historical data and patterns. Try clicking one of the sample queries in the sidebar
            to get started, or type your own question.
            </p>
            <p>
            The conversation maintains context, so you can ask follow-up questions that build on 
            previous responses without repeating information. For example, after asking about an event,
            you can ask for specific trade recommendations based on that analysis.
            </p>
            </div>
            """, 
            unsafe_allow_html=True
        )

# Functions for NEWS FEED tab
def format_time_ago(timestamp_str: str) -> str:
    """Convert ISO timestamp to a human-readable 'X minutes ago' format."""
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.now()
        
        delta = now - timestamp
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"
    except Exception:
        return "unknown time"

def fetch_news():
    """Fetch fresh news for the news feed tab"""
    try:
        headlines = fetch_rss_headlines()
        if headlines:
            # Sort by published date, newest first
            headlines.sort(key=lambda x: x.get('published', ''), reverse=True)
            st.session_state.news_feed = headlines
            st.session_state.last_news_fetch = datetime.now()
            
            # Check for important headlines for alerts
            check_important_headlines(headlines[:10])  # Check top 10 headlines
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")

def check_important_headlines(headlines):
    """Identify important headlines and add them to alerts if necessary"""
    # Check for potential market-moving keywords
    important_keywords = ['crash', 'rally', 'surge', 'plunge', 'collapse', 'soar', 
                         'bankrupt', 'recession', 'fed', 'rate', 'inflation', 'war', 
                         'attack', 'emergency', 'surprise', 'unexpected', 'breach',
                         'hack', 'scandal', 'investigation', 'SEC', 'record high',
                         'record low', 'breaks', 'beats', 'misses', 'earnings', 'IPO']
    
    try:
        for headline in headlines:
            # Skip already processed headlines
            headline_id = f"{headline.get('title', '')}_{headline.get('source', '')}"
            if any(h.get('id') == headline_id for h in st.session_state.important_headlines):
                continue
                
            # Check if headline contains important keywords
            title = headline.get('title', '').lower()
            if any(keyword.lower() in title for keyword in important_keywords):
                # Mark as important and add to queue for processing
                headline['id'] = headline_id
                headline['importance'] = 'high' if any(k in title for k in ['crash', 'collapse', 'emergency', 'attack', 'war']) else 'medium'
                headline['processed'] = False
                st.session_state.important_headlines.append(headline)
                
    except Exception as e:
        st.error(f"Error checking important headlines: {str(e)}")

def display_news_feed():
    """Display the news feed tab content"""
    st.header("📰 Financial News Feed")
    
    # Top controls row
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔄 Refresh News", use_container_width=True):
            with st.spinner("Fetching latest headlines..."):
                fetch_news()
                save_data()  # Save updated data
    with col2:
        # Toggle for auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (every 5 min)", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
    with col3:
        # Filter for news sources
        sources = ["All Sources"] + [feed["source"] for feed in FINANCIAL_FEEDS]
        selected_source = st.selectbox("Filter by source:", sources)
    
    # Search input
    search_term = st.text_input("🔍 Search headlines:", placeholder="Enter keywords to search...")
    
    # Display last fetched time
    if st.session_state.last_news_fetch:
        st.caption(f"Last updated: {st.session_state.last_news_fetch.strftime('%H:%M:%S')}")
    
    # Create scrollable container for news
    news_container = st.container()
    
    with news_container:
        if not st.session_state.news_feed:
            st.info("No news headlines loaded. Click 'Refresh News' to fetch latest headlines.")
        else:
            # Filter by selected source if needed
            filtered_news = st.session_state.news_feed
            if selected_source != "All Sources":
                filtered_news = [h for h in st.session_state.news_feed if h.get('source') == selected_source]
            
            # Apply search filter if provided
            if search_term:
                search_words = search_term.lower().split()
                filtered_news = [
                    h for h in filtered_news 
                    if any(word in h.get('title', '').lower() for word in search_words)
                ]
                
                # Show search result count
                st.caption(f"Found {len(filtered_news)} headlines matching '{search_term}'")
            
            # Always sort by newest first
            filtered_news.sort(key=lambda x: x.get('published', ''), reverse=True)
            
            # Display news count
            st.write(f"Showing {len(filtered_news)} headlines")
            
            # Check if we have no results after filtering
            if not filtered_news:
                st.warning("No headlines match the current filters. Try adjusting your search terms or filters.")
            
            # Display news cards
            for headline in filtered_news:
                time_ago = format_time_ago(headline.get('published', ''))
                
                # Check if this headline is marked as important
                is_important = any(
                    h.get('id') == f"{headline.get('title', '')}_{headline.get('source', '')}" 
                    for h in st.session_state.important_headlines
                )
                
                importance_marker = "🔴" if is_important else ""
                
                # Create a news card with HTML styling
                st.markdown(f"""
                <div class="news-card {' alert-high' if is_important else ''}">
                    <div class="news-source">{importance_marker} {headline.get('source', 'Unknown')} • <span class="news-time">{time_ago}</span></div>
                    <div class="news-title">{headline.get('title', 'No Title')}</div>
                    <a href="{headline.get('link', '#')}" target="_blank">Read more</a>
                </div>
                """, unsafe_allow_html=True)
    
    # Auto-refresh logic - make more robust by checking elapsed time
    if st.session_state.auto_refresh:
        # Calculate seconds since last refresh
        last_refresh_seconds = 300  # Default to trigger refresh if no previous fetch
        if st.session_state.last_news_fetch:
            last_refresh_seconds = (datetime.now() - st.session_state.last_news_fetch).seconds
        
        # Refresh if 5 minutes (300 seconds) have passed
        if last_refresh_seconds >= 300:
            st.session_state.last_auto_refresh = datetime.now()
            fetch_news()
            time.sleep(0.1)  # Small delay to avoid aggressive refreshing
            st.experimental_rerun()

# Functions for TRADE ALERTS tab
def process_important_headlines():
    """Process important headlines to generate trade alerts"""
    try:
        # Find unprocessed important headlines
        unprocessed = [h for h in st.session_state.important_headlines if not h.get('processed', False)]
        
        if not unprocessed:
            return
            
        # Process up to 3 headlines at a time to avoid overloading
        for headline in unprocessed[:3]:
            # Mark as processed to avoid reprocessing
            headline['processed'] = True
            
            # Use classify_macro_event to get market insights
            try:
                classification = classify_macro_event(headline)
                
                # Create a trade alert from the classification
                if classification and 'sentiment' in classification:
                    alert = {
                        'headline': headline.get('title', 'Unknown headline'),
                        'source': headline.get('source', 'Unknown source'),
                        'time': headline.get('published', ''),
                        'link': headline.get('link', '#'),
                        'importance': headline.get('importance', 'medium'),
                        'event_type': classification.get('event_type', 'Unknown'),
                        'sentiment': classification.get('sentiment', 'Neutral'),
                        'sector': classification.get('sector', 'General Market'),
                        'timestamp': datetime.now().isoformat(),
                        'id': headline.get('id')
                    }
                    
                    # Add to trade alerts
                    st.session_state.trade_alerts.append(alert)
            except Exception as e:
                st.error(f"Error classifying headline: {str(e)}")
                continue
    
    except Exception as e:
        st.error(f"Error processing important headlines: {str(e)}")

def display_trade_alerts():
    """Display the trade alerts tab content"""
    st.header("🚨 Automated Trade Alerts")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔄 Refresh Alerts", use_container_width=True):
            # Refresh alerts by processing any important headlines
            with st.spinner("Scanning for trading opportunities..."):
                process_important_headlines()
                save_data()  # Save updated data
    with col2:
        # Allow filtering by importance
        importance_filter = st.selectbox("Filter by importance:", ["All Alerts", "High", "Medium", "Low"])
    with col3:
        # Sentiment filter
        sentiment_filter = st.selectbox("Filter by sentiment:", ["All", "Bullish", "Bearish", "Neutral"])
    
    # Metrics row for statistics
    st.markdown("### Alert Statistics")
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    
    with metrics_col1:
        total_alerts = len(st.session_state.trade_alerts)
        st.metric("Total Alerts", total_alerts)
    
    with metrics_col2:
        high_priority = len([a for a in st.session_state.trade_alerts if a.get('importance') == 'high'])
        st.metric("High Priority", high_priority)
    
    with metrics_col3:
        bullish_count = len([a for a in st.session_state.trade_alerts if a.get('sentiment') == 'Bullish'])
        st.metric("Bullish Alerts", bullish_count)
    
    with metrics_col4:
        bearish_count = len([a for a in st.session_state.trade_alerts if a.get('sentiment') == 'Bearish'])
        st.metric("Bearish Alerts", bearish_count)
    
    # Display alerts in a scrollable container
    alerts_container = st.container()
    
    with alerts_container:
        if not st.session_state.trade_alerts:
            st.info("No trade alerts generated yet. Market events that may present trading opportunities will appear here.")
        else:
            # Sort alerts by importance and timestamp (newest first)
            sorted_alerts = sorted(
                st.session_state.trade_alerts,
                key=lambda a: (
                    0 if a.get('importance') == 'high' else 1 if a.get('importance') == 'medium' else 2,
                    a.get('timestamp', ''),
                ),
                reverse=True
            )
            
            # Apply filters if needed
            if importance_filter != "All Alerts":
                sorted_alerts = [a for a in sorted_alerts if a.get('importance', '').lower() == importance_filter.lower()]
            
            if sentiment_filter != "All":
                sorted_alerts = [a for a in sorted_alerts if a.get('sentiment', '') == sentiment_filter]
            
            # Display each alert
            for alert in sorted_alerts:
                importance = alert.get('importance', 'medium')
                sentiment = alert.get('sentiment', 'Neutral')
                sentiment_color = 'green' if sentiment == 'Bullish' else 'red' if sentiment == 'Bearish' else 'gray'
                time_ago = format_time_ago(alert.get('time', ''))
                
                # Create alert box with appropriate styling
                with st.container():
                    st.markdown(f"""
                    <div class="news-card alert-{importance}">
                        <div class="news-source">
                            <span style="color: {'red' if importance == 'high' else 'orange' if importance == 'medium' else 'green'}">
                                {'🔴' if importance == 'high' else '🟠' if importance == 'medium' else '🟢'} 
                                {importance.upper()} PRIORITY
                            </span> • 
                            <span class="news-time">{time_ago} • {alert.get('source', 'Unknown')}</span>
                        </div>
                        <div class="news-title">{alert.get('headline', 'No Title')}</div>
                        <p><b>Analysis:</b> <span>{alert.get('event_type', 'Unknown')}</span> | 
                           <span style="color: {sentiment_color}">{sentiment}</span> | 
                           <span>{alert.get('sector', 'Unknown')}</span></p>
                        <a href="{alert.get('link', '#')}" target="_blank">Read original story</a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add button to generate trade idea based on this alert
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button(f"Generate Trade Idea", key=f"trade_{alert.get('id', '')}"):
                            # Set this headline as the search query
                            st.session_state.current_query = alert.get('headline', '')
                            # Switch to search tab
                            st.session_state.active_tab = "Search"
                            st.rerun()

def start_background_processing():
    """Set up background processing for headlines if not already running"""
    if "background_processing" not in st.session_state:
        st.session_state.background_processing = True
        
        # Start a background thread that processes headlines
        def background_worker():
            while True:
                # Process any important headlines that haven't been processed yet
                unprocessed = [h for h in st.session_state.important_headlines if not h.get('processed', False)]
                if unprocessed:
                    with st.session_state.news_lock:
                        # Process one headline at a time to avoid API rate limits
                        headline = unprocessed[0]
                        headline['processed'] = True
                        
                        try:
                            # Use classify_macro_event to get market insights
                            classification = classify_macro_event(headline)
                            
                            # Create a trade alert from the classification
                            if classification and 'sentiment' in classification:
                                alert = {
                                    'headline': headline.get('title', 'Unknown headline'),
                                    'source': headline.get('source', 'Unknown source'),
                                    'time': headline.get('published', ''),
                                    'link': headline.get('link', '#'),
                                    'importance': headline.get('importance', 'medium'),
                                    'event_type': classification.get('event_type', 'Unknown'),
                                    'sentiment': classification.get('sentiment', 'Neutral'),
                                    'sector': classification.get('sector', 'General Market'),
                                    'timestamp': datetime.now().isoformat(),
                                    'id': headline.get('id')
                                }
                                
                                # Add to trade alerts
                                st.session_state.trade_alerts.append(alert)
                        except Exception as e:
                            # Just log the error and continue
                            print(f"Error classifying headline: {str(e)}")
                
                # Sleep to avoid excessive CPU usage
                time.sleep(10)
        
        # Start the background thread
        processing_thread = threading.Thread(target=background_worker)
        processing_thread.daemon = True
        processing_thread.start()
        
def save_data():
    """Save news, important headlines, and alerts to files"""
    try:
        # Save trade alerts
        if st.session_state.trade_alerts:
            with open('trade_alerts.json', 'w') as f:
                json.dump(st.session_state.trade_alerts, f)
        
        # Save important headlines
        if st.session_state.important_headlines:
            with open('important_headlines.json', 'w') as f:
                json.dump(st.session_state.important_headlines, f)
        
        # Save news feed (last 20 items only)
        if st.session_state.news_feed:
            with open('news_feed.json', 'w') as f:
                json.dump(st.session_state.news_feed[:20], f)
    except Exception as e:
        print(f"Error saving data: {str(e)}")

def load_data():
    """Load saved news, important headlines, and alerts from files"""
    try:
        # Load trade alerts
        if os.path.exists('trade_alerts.json'):
            with open('trade_alerts.json', 'r') as f:
                st.session_state.trade_alerts = json.load(f)
        
        # Load important headlines
        if os.path.exists('important_headlines.json'):
            with open('important_headlines.json', 'r') as f:
                st.session_state.important_headlines = json.load(f)
        
        # Load news feed
        if os.path.exists('news_feed.json'):
            with open('news_feed.json', 'r') as f:
                st.session_state.news_feed = json.load(f)
                st.session_state.last_news_fetch = datetime.now()
    except Exception as e:
        print(f"Error loading data: {str(e)}")

# Main app layout
def main():
    # Initialize session state
    initialize_session_state()
    
    # Start background processing for trade alerts
    start_background_processing()
    
    # Register on_session_end to save data
    if 'on_exit_setup' not in st.session_state:
        st.session_state.on_exit_setup = True
        # This is a workaround - we'll save periodically
        def save_data_periodically():
            while True:
                time.sleep(300)  # Save every 5 minutes
                save_data()
                
        save_thread = threading.Thread(target=save_data_periodically)
        save_thread.daemon = True
        save_thread.start()
    
    # Main title with help tooltip
    st.title("Ooptions Market Analysis Platform")
    
    # Help expander
    with st.expander("ℹ️ How to use this application"):
        st.markdown("""
        ### Welcome to the Ooptions Market Analysis Platform
        
        This application has three main tabs:
        
        **📰 News Feed**
        - View the latest financial news from multiple sources
        - Search and filter news by keywords or source
        - Mark important headlines for trade alerts
        - Auto-refreshes every 5 minutes to get the latest headlines
        
        **🚨 Trade Alerts**
        - Automatically monitors news for potential trading opportunities
        - Analyzes headlines with AI to determine market sentiment and impact
        - Alerts are prioritized by importance (high, medium, low)
        - Click "Generate Trade Idea" to analyze any alert further
        
        **🔍 Search**
        - Ask questions about market events or historical data
        - Analyze specific events and get detailed market impact information
        - Maintain context across follow-up questions
        - Get trade recommendations based on historical patterns
        
        Use the sidebar for sample queries and to reset the conversation as needed.
        """)
    
    # Sidebar
    with st.sidebar:
        st.title("📈 Ooptions")
        st.subheader("Market Event Analysis")
        
        # Reset button
        st.button("Reset Conversation", on_click=reset_conversation, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Sample Queries")
        for query in SAMPLE_QUERIES:
            st.button(query, on_click=use_sample_query, args=(query,), key=f"sample_{query[:20]}")
            
        # Show context information in sidebar when available
        show_context_information()
            
        st.markdown("---")
        st.markdown(
            """
            ## About
            
            This tool analyzes market events and provides insights based on historical patterns 
            and macroeconomic data.
            
            - Monitor financial news in real time
            - Get automated trade alerts when important events occur
            - Search and analyze historical market events
            - Explore similar patterns across events
            - Understand macro correlations
            """
        )
        
        # Session info
        st.markdown("---")
        st.caption(f"Session ID: {st.session_state.session_id}")
        st.caption(f"Queries: {st.session_state.query_count}")
        if st.session_state.last_query_time:
            st.caption(f"Last query: {st.session_state.last_query_time.strftime('%H:%M:%S')}")
        if st.session_state.last_news_fetch:
            st.caption(f"Last news update: {st.session_state.last_news_fetch.strftime('%H:%M:%S')}")
    
    # Initialize active tab if not set
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Search"
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📰 News Feed", "🚨 Trade Alerts", "🔍 Search"])
    
    # Handle content for each tab
    with tab1:
        display_news_feed()
    
    with tab2:
        display_trade_alerts()
    
    with tab3:
        display_search_interface()
    
    # Fetch initial news data if needed
    if st.session_state.news_feed == [] and st.session_state.last_news_fetch is None:
        fetch_news()

if __name__ == "__main__":
    main() 