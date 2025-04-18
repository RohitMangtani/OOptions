import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import math
import random
from pandas.tseries.offsets import BDay
import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

def get_next_friday(from_date=None):
    """Get the next Friday from the given date."""
    if from_date is None:
        from_date = datetime.now()
    
    days_until_friday = (4 - from_date.weekday()) % 7
    if days_until_friday == 0 and from_date.hour >= 16:  # If it's Friday after market close
        days_until_friday = 7
    
    next_friday = from_date + timedelta(days=days_until_friday)
    return next_friday.date()

@lru_cache(maxsize=100)
def fetch_current_price_cached(ticker):
    """
    Cached version of current price fetching to reduce API calls.
    Cache expires after a short period to ensure data freshness.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        price_data = ticker_obj.history(period="1d")
        if not price_data.empty:
            return price_data['Close'].iloc[-1]
    except Exception as e:
        logger.error(f"Error fetching current price for {ticker}: {e}")
    return None

def fetch_current_price(ticker):
    """Fetch the current price of a stock."""
    # Use the cached version but with a short expiration to ensure fresh data
    return fetch_current_price_cached(ticker)

# Cache expiry time-based key function
def _get_cache_key(ticker, days=1):
    """Generate a cache key that includes the date to expire cache daily"""
    today = datetime.now().strftime('%Y-%m-%d')
    return f"{ticker}_{today}_{days}"

@lru_cache(maxsize=50)
def _fetch_ticker_history_cached(cache_key, ticker, days):
    """Internal cached function for fetching historical data"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        ticker_obj = yf.Ticker(ticker)
        history = ticker_obj.history(start=start_date, end=end_date)
        return history
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return pd.DataFrame()

def fetch_ticker_history(ticker, days=30):
    """Fetch historical data for a ticker with caching"""
    cache_key = _get_cache_key(ticker, days)
    return _fetch_ticker_history_cached(cache_key, ticker, days)

@lru_cache(maxsize=30)
def _fetch_option_data_cached(cache_key, ticker):
    """Internal cached function for fetching options data"""
    try:
        ticker_obj = yf.Ticker(ticker)
        expiry_dates = ticker_obj.options
        
        if not expiry_dates:
            logger.warning(f"No options data available for {ticker}")
            return [], {}
            
        # Get options for the first expiry date
        options = ticker_obj.option_chain(expiry_dates[0])
        
        return expiry_dates, {
            'calls': options.calls,
            'puts': options.puts
        }
    except Exception as e:
        logger.error(f"Error fetching options data for {ticker}: {e}")
        return [], {}

def fetch_option_data(ticker):
    """Fetch options data for a ticker with caching"""
    # Create a cache key that expires daily
    cache_key = _get_cache_key(ticker)
    return _fetch_option_data_cached(cache_key, ticker)

def select_expiry_date(expiry_dates, min_days=7, max_days=45):
    """Select an appropriate expiry date for options."""
    if not expiry_dates:
        return get_next_friday()
        
    today = datetime.now().date()
    valid_dates = []
    
    for date_str in expiry_dates:
        expiry = datetime.strptime(date_str, '%Y-%m-%d').date()
        days_to_expiry = (expiry - today).days
        
        if min_days <= days_to_expiry <= max_days:
            valid_dates.append(expiry)
    
    if valid_dates:
        return min(valid_dates)  # Return the closest valid date
    elif expiry_dates:
        # If no date in range, get the closest one to our range
        all_dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in expiry_dates]
        return min(all_dates, key=lambda d: abs((d - today).days - 30))
    else:
        return get_next_friday()

def select_strike_price(current_price, price_history, sentiment, option_type):
    """Calculate an appropriate strike price based on current price and historical price changes."""
    if price_history.empty:
        # Default to 5% OTM if no history available
        multiplier = 1.05 if option_type == 'call' and sentiment == 'bullish' else 0.95
        return round(current_price * multiplier, 1)
    
    # Calculate daily returns and volatility
    price_history['Daily Return'] = price_history['Close'].pct_change()
    daily_volatility = price_history['Daily Return'].std()
    
    # Calculate expected price move based on volatility
    expected_move = current_price * daily_volatility * 2  # 2-sigma move
    
    # Adjust based on sentiment
    if sentiment == 'bullish':
        if option_type == 'call':
            # For bullish sentiment, call slightly OTM
            target_price = current_price * (1 + daily_volatility * 1.5)
        else:
            # For bullish sentiment, put further OTM
            target_price = current_price * (1 - daily_volatility * 2.5)
    else:  # bearish
        if option_type == 'call':
            # For bearish sentiment, call further OTM
            target_price = current_price * (1 + daily_volatility * 2.5)
        else:
            # For bearish sentiment, put slightly OTM
            target_price = current_price * (1 - daily_volatility * 1.5)
    
    # Round to nearest 0.5 or 1.0 depending on price level
    if current_price < 50:
        return round(target_price * 2) / 2  # Round to nearest 0.5
    elif current_price < 100:
        return round(target_price)  # Round to nearest 1.0
    else:
        return round(target_price / 5) * 5  # Round to nearest 5.0

def generate_trade_idea(headline_data, market_data=None):
    """
    Generate a trade idea based on a classified headline and historical market data.
    
    Args:
        headline_data (dict): Contains information about the headline including:
            - ticker: Stock symbol
            - sentiment: bullish or bearish
            - headline: The original headline text
        market_data (dict, optional): Additional market context if available
    
    Returns:
        dict: A trade idea with specific trade parameters
    """
    ticker = headline_data.get('ticker')
    sentiment = headline_data.get('sentiment', '').lower()
    
    if not ticker or not re.match(r'^[A-Z]{1,5}$', ticker):
        return {"error": "Invalid ticker symbol"}
    
    if sentiment not in ['bullish', 'bearish', 'neutral']:
        return {"error": "Invalid sentiment. Must be 'bullish', 'bearish', or 'neutral'"}
    
    # Skip neutral sentiment for trade ideas
    if sentiment == 'neutral':
        return {"message": "Neutral sentiment - no trade idea generated"}
    
    # Get current price
    current_price = fetch_current_price(ticker)
    if not current_price:
        return {"error": f"Could not fetch current price for {ticker}"}
    
    # Get historical price data for volatility calculation
    price_history = fetch_ticker_history(ticker, days=30)
    
    # Fetch available options
    expiry_dates, options_data = fetch_option_data(ticker)
    
    # Select option type based on sentiment
    option_type = 'call' if sentiment == 'bullish' else 'put'
    
    # Select expiry date
    expiry_date = select_expiry_date(expiry_dates)
    
    # Select strike price
    strike_price = select_strike_price(current_price, price_history, sentiment, option_type)
    
    # Generate trade idea
    trade_idea = {
        'ticker': ticker,
        'sentiment': sentiment,
        'current_price': round(current_price, 2),
        'trade_type': f"{option_type.upper()} option",
        'option_expiry': expiry_date.strftime('%Y-%m-%d'),
        'strike_price': strike_price,
        'recommendation': f"{'Buy' if option_type == 'call' else 'Sell'} {ticker} based on news: {headline_data.get('headline', '')}"
    }
    
    return trade_idea

def process_headlines_for_trades(classified_headlines: List[Dict[str, Any]], historical_matches_by_headline: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Process multiple headlines and their historical matches to generate trade ideas.
    
    Args:
        classified_headlines: List of classified headlines
        historical_matches_by_headline: List of historical matches for each headline
        
    Returns:
        List[Dict[str, Any]]: List of trade ideas
    """
    trade_ideas = []
    
    for headline, matches in zip(classified_headlines, historical_matches_by_headline):
        trade_idea = generate_trade_idea(headline, matches)
        
        # Only add valid trade ideas (for option trades, need strike price)
        if (trade_idea.get('trade_type') == 'equity' or 
            (trade_idea.get('trade_type') == 'option' and trade_idea.get('strike') is not None)):
            trade_ideas.append(trade_idea)
    
    # Sort trade ideas by priority (could implement custom logic here)
    return trade_ideas

if __name__ == "__main__":
    # Example usage with a sample headline and matches
    test_headline = {
        "title": "Fed signals potential rate cut on cooling inflation",
        "event_type": "Monetary Policy",
        "sentiment": "Bullish",
        "sector": "Financials",
        "event_tags": {
            "is_fed_week": True,
            "is_cpi_week": False,
            "surprise_positive": True
        }
    }
    
    test_matches = [
        {
            "event_summary": "Fed signals pause in rate hikes after continuous increases",
            "match_score": 0.8,
            "affected_ticker": "SPY",
            "drop_pct": 4.5,  # This is actually a gain since Fed pausing is bullish
            "max_drawdown_pct": -1.5,  # Max drawdown during the period
            "event_date": "2023-09-20"
        },
        {
            "event_summary": "Fed announces emergency rate cut during COVID-19",
            "match_score": 0.7,
            "affected_ticker": "SPY",
            "drop_pct": -2.8,  # Negative value means market dropped
            "max_drawdown_pct": -5.2,  # Max drawdown during the period
            "event_date": "2020-03-03"
        }
    ]
    
    trade_idea = generate_trade_idea(test_headline)
    
    print("RECOMMENDED TRADE:")
    print(f"Ticker: {trade_idea['ticker']}")
    print(f"Trade Type: {trade_idea['trade_type']}")
    print(f"Direction: {trade_idea['direction']}")
    if trade_idea['trade_type'] == 'option':
        print(f"Option Type: {trade_idea['option_type']}")
        print(f"Strike: {trade_idea['strike']}")
        print(f"Expiry: {trade_idea['expiry']}")
    print(f"Rationale: {trade_idea['rationale']}") 