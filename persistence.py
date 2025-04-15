#!/usr/bin/env python
"""
PERSISTENCE MODULE
=================

What This Module Does:
--------------------
This module handles the persistence of trade data to JSON files.
It provides functions to save, load, and manage trade history.

How to Use:
----------
1. Save a trade:
   from persistence import save_trade_to_json
   trade = {...}  # Your trade dictionary
   save_trade_to_json(trade)

2. Save a trade to custom location:
   save_trade_to_json(trade, "custom_trades.json")

What This Helps You See:
-----------------------
- Creates a historical record of all trades
- Maintains a consistent JSON format for trade history
- Ensures data persistence across program runs
- Enables later analysis of trade performance
- Stores macroeconomic context with each trade for reinforcement learning
"""

import json
import os
import sys
import datetime
from typing import Dict, Any, List, Optional

# Import data collectors
from macro_data_collector import get_macro_snapshot, get_fred_data
from options_data_collector import get_options_snapshot
from technical_indicator_collector import get_technical_indicators

DEFAULT_TRADES_FILE = "trade_history.json"

def save_trade_to_json(trade: Dict[str, Any], output_path: str = DEFAULT_TRADES_FILE, 
                       include_macro: bool = True, include_options: bool = True,
                       include_technicals: bool = True) -> bool:
    """
    Append a trade to a JSON file with a timestamp, macroeconomic context, and options data.
    
    Trade record structure:
    {
        "headline": "The headline text that triggered the trade",
        "macro_snapshot": {macro economic indicators and their values},
        "options_snapshot": {options market metrics like IV, skew, put/call ratio},
        "technical_indicators": {RSI, MACD, SMA/EMA cross signals},
        "event_tags": {tags indicating market conditions like 'is_fed_week', 'is_cpi_week'},
        "prompt_enhancers": {enhanced prompt context used for LLM reasoning},
        "llm_output": {original LLM classification and recommendation},
        "timestamp": "ISO-formatted timestamp",
        ...other trade details...
    }
    
    Args:
        trade: The trade dictionary to save
        output_path: Path to the JSON file (default: trade_history.json)
        include_macro: Whether to include macroeconomic context (default: True)
        include_options: Whether to include options market data (default: True)
        include_technicals: Whether to include technical indicators (default: True)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a standardized trade record with the required structure
        standardized_trade = {
            # Ensure headline field exists
            "headline": trade.get("headline", trade.get("title", "No headline provided")),
            # Timestamp will be added below
            # Macro snapshot will be added if enabled
            # Options snapshot will be added if enabled
            # Technical indicators will be added if enabled
            # Event tags will be preserved if available
            # Prompt enhancers will be preserved if available
            # Preserve the original LLM output if available
            "llm_output": trade.get("llm_output", trade.get("classification", {})),
        }
        
        # Copy other trade fields that aren't explicitly in our standard structure
        for key, value in trade.items():
            if key not in ["headline", "title", "macro_snapshot", "options_snapshot", "technical_indicators", "event_tags", 
                          "prompt_enhancers", "llm_output", "classification", "timestamp", "saved_timestamp"]:
                standardized_trade[key] = value
        
        # Add timestamp to the trade
        standardized_trade['timestamp'] = datetime.datetime.now().isoformat()
        
        # For backward compatibility
        standardized_trade['saved_timestamp'] = standardized_trade['timestamp']
        
        # Add macroeconomic context if enabled
        if include_macro:
            try:
                # Get current macro snapshot (using cache if available)
                macro_snapshot = get_macro_snapshot(use_cache=True)
                
                # Remove metadata fields with leading underscores for cleaner storage
                clean_snapshot = {k: v for k, v in macro_snapshot.items() if not k.startswith('_')}
                
                # Add to the trade record
                standardized_trade['macro_snapshot'] = clean_snapshot
            except Exception as e:
                print(f"Warning: Failed to include macro context: {str(e)}")
                # Add empty macro snapshot to maintain structure
                standardized_trade['macro_snapshot'] = {}
        else:
            # Ensure macro_snapshot field exists even if not populated
            standardized_trade['macro_snapshot'] = {}
        
        # Add options market data if enabled
        if include_options:
            try:
                # Determine which ticker to use - first look in the trade, then fall back to SPY
                ticker = "SPY"  # Default
                
                # Try to get ticker from trade recommendation
                if "trade" in trade and isinstance(trade["trade"], dict) and "ticker" in trade["trade"]:
                    ticker = trade["trade"]["ticker"]
                elif "ticker" in trade:
                    ticker = trade["ticker"]
                
                # Get options snapshot for the ticker (use cache if available)
                options_snapshot = get_options_snapshot(ticker, use_cache=True)
                
                # Add to the trade record
                standardized_trade['options_snapshot'] = options_snapshot
                
                # Also log the ticker used for options data
                standardized_trade['options_ticker'] = ticker
                
            except Exception as e:
                print(f"Warning: Failed to include options data: {str(e)}")
                # Add empty options snapshot to maintain structure
                standardized_trade['options_snapshot'] = {}
        else:
            # Ensure options_snapshot field exists even if not populated
            standardized_trade['options_snapshot'] = {}
        
        # Add technical indicators if enabled
        if include_technicals:
            try:
                # Determine which ticker to use - first look in the trade, then fall back to SPY
                ticker = "SPY"  # Default
                
                # Try to get ticker from trade recommendation
                if "trade" in trade and isinstance(trade["trade"], dict) and "ticker" in trade["trade"]:
                    ticker = trade["trade"]["ticker"]
                elif "ticker" in trade:
                    ticker = trade["ticker"]
                
                # Get current date for the technical indicators
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                
                # Get technical indicators for the ticker
                tech_indicators = get_technical_indicators(ticker, date)
                
                # Add to the trade record
                standardized_trade['technical_indicators'] = tech_indicators
                
            except Exception as e:
                print(f"Warning: Failed to include technical indicators: {str(e)}")
                # Add empty technical indicators to maintain structure
                standardized_trade['technical_indicators'] = {}
        else:
            # Ensure technical_indicators field exists even if not populated
            standardized_trade['technical_indicators'] = {}
            
        # Preserve event tags if available in the trade
        if "event_tags" in trade and trade["event_tags"]:
            standardized_trade['event_tags'] = trade["event_tags"]
        else:
            # Add empty event tags to maintain structure
            standardized_trade['event_tags'] = {}
            
        # Preserve prompt enhancers if available in the trade
        if "prompt_enhancers" in trade and trade["prompt_enhancers"]:
            standardized_trade['prompt_enhancers'] = trade["prompt_enhancers"]
        else:
            # Add empty prompt enhancers to maintain structure
            standardized_trade['prompt_enhancers'] = {}
        
        # Load existing trades if the file exists
        existing_trades = []
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r') as f:
                    existing_trades = json.load(f)
                    
                    # Ensure the loaded data is a list
                    if not isinstance(existing_trades, list):
                        print(f"Warning: {output_path} contains invalid format. Creating new file.")
                        existing_trades = []
            except json.JSONDecodeError:
                print(f"Warning: {output_path} contains invalid JSON. Creating new file.")
        
        # Append the new trade
        existing_trades.append(standardized_trade)
        
        # Write back to the file
        with open(output_path, 'w') as f:
            json.dump(existing_trades, f, indent=2)
            
        print(f"Trade saved to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error saving trade to {output_path}: {str(e)}")
        return False

def load_trades(input_path: str = DEFAULT_TRADES_FILE) -> List[Dict[str, Any]]:
    """
    Load all trades from a JSON file.
    
    Args:
        input_path: Path to the JSON file (default: trade_history.json)
        
    Returns:
        List of trade dictionaries
    """
    if not os.path.exists(input_path):
        print(f"Trade history file {input_path} not found.")
        return []
        
    try:
        with open(input_path, 'r') as f:
            trades = json.load(f)
            
        if not isinstance(trades, list):
            print(f"Warning: {input_path} contains invalid format (not a list).")
            return []
            
        return trades
    except Exception as e:
        print(f"Error loading trades from {input_path}: {str(e)}")
        return []

def clear_trade_history(file_path: str = DEFAULT_TRADES_FILE) -> bool:
    """
    Clear all trades from the history file.
    
    Args:
        file_path: Path to the JSON file (default: trade_history.json)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, 'w') as f:
            json.dump([], f)
        print(f"Trade history cleared in {file_path}")
        return True
    except Exception as e:
        print(f"Error clearing trade history: {str(e)}")
        return False

def analyze_macro_context(trades: List[Dict[str, Any]], success_key: str = 'success', threshold: float = 0.0) -> Dict[str, Any]:
    """
    Analyze the macroeconomic context data stored with trades to find patterns.
    
    This function analyzes the relationship between macroeconomic conditions and trade outcomes.
    It can be used for:
    1. Identifying which macro indicators correlate with successful trades
    2. Finding optimal ranges for each indicator where trade success is highest
    3. Analyzing how different option types (CALL/PUT) perform in various macro environments
    4. Generating trade environment summaries for reinforcement learning
    
    Args:
        trades: List of trades with macro_snapshot data
        success_key: Dictionary key that indicates if a trade was successful (default: 'success')
        threshold: Value threshold to consider a trade successful for numeric outcomes (default: 0.0)
        
    Returns:
        Dictionary with analysis results including:
        - Basic statistics (count, sum, min, max, avg) for each macro indicator
        - Success rate correlation for each indicator (above/below median analysis)
        - Option type performance in different macro environments
    """
    # Initialize counters
    total_trades = len(trades)
    trades_with_macro = 0
    macro_indicators = {}
    
    # Success tracking
    successful_trades = 0
    successful_with_macro = 0
    
    # Track by option type if available
    call_trades = 0
    put_trades = 0
    call_success = 0
    put_success = 0
    
    # Collect all values for each indicator to calculate median later
    indicator_values = {}
    indicator_success_mapping = {}
    
    # Analyze trades
    for trade in trades:
        # Check if this trade has macro data
        has_macro = 'macro_snapshot' in trade and trade['macro_snapshot']
        
        # Check if this trade was successful
        is_successful = False
        if success_key in trade:
            if isinstance(trade[success_key], bool):
                is_successful = trade[success_key]
            elif isinstance(trade[success_key], (int, float)):
                is_successful = trade[success_key] > threshold
            elif isinstance(trade[success_key], str):
                is_successful = trade[success_key].lower() in ('true', 'yes', 'success', '1')
        
        # Track success overall
        if is_successful:
            successful_trades += 1
            
        # Track option type performance if available
        option_type = trade.get('option_type', '').upper()
        if option_type in ('CALL', 'PUT'):
            if option_type == 'CALL':
                call_trades += 1
                if is_successful:
                    call_success += 1
            else:
                put_trades += 1
                if is_successful:
                    put_success += 1
        
        # Skip if no macro data
        if not has_macro:
            continue
            
        trades_with_macro += 1
        if is_successful:
            successful_with_macro += 1
            
        # Process each macro indicator
        for key, value in trade['macro_snapshot'].items():
            # Initialize if first time seeing this indicator
            if key not in macro_indicators:
                macro_indicators[key] = {
                    'count': 0,
                    'sum': 0,
                    'min': float('inf'),
                    'max': float('-inf')
                }
                indicator_values[key] = []
                indicator_success_mapping[key] = []
            
            # Update statistics for numeric values
            try:
                value_float = float(value)
                macro_indicators[key]['count'] += 1
                macro_indicators[key]['sum'] += value_float
                macro_indicators[key]['min'] = min(macro_indicators[key]['min'], value_float)
                macro_indicators[key]['max'] = max(macro_indicators[key]['max'], value_float)
                
                # Store value and success for correlation analysis
                indicator_values[key].append(value_float)
                indicator_success_mapping[key].append(is_successful)
            except (ValueError, TypeError):
                # Skip non-numeric values
                pass
    
    # Calculate averages
    for key in macro_indicators:
        if macro_indicators[key]['count'] > 0:
            macro_indicators[key]['avg'] = macro_indicators[key]['sum'] / macro_indicators[key]['count']
    
    # Calculate correlation between macro indicators and success rate
    correlation_analysis = {}
    for key in indicator_values:
        if len(indicator_values[key]) >= 5:  # Need sufficient data points
            # Calculate median
            median = sorted(indicator_values[key])[len(indicator_values[key]) // 2]
            
            # Count trades and success above/below median
            above_median_count = 0
            above_median_success = 0
            below_median_count = 0
            below_median_success = 0
            
            for value, success in zip(indicator_values[key], indicator_success_mapping[key]):
                if value >= median:
                    above_median_count += 1
                    if success:
                        above_median_success += 1
                else:
                    below_median_count += 1
                    if success:
                        below_median_success += 1
            
            # Calculate success rates
            above_success_rate = above_median_success / above_median_count if above_median_count > 0 else 0
            below_success_rate = below_median_success / below_median_count if below_median_count > 0 else 0
            
            correlation_analysis[key] = {
                'median': median,
                'above_median': {
                    'count': above_median_count,
                    'success_count': above_median_success,
                    'success_rate': above_success_rate
                },
                'below_median': {
                    'count': below_median_count,
                    'success_count': below_median_success,
                    'success_rate': below_success_rate
                },
                'correlation_strength': abs(above_success_rate - below_success_rate),
                'favors_higher': above_success_rate > below_success_rate
            }
    
    # Calculate overall success rate
    overall_success_rate = successful_trades / total_trades if total_trades > 0 else 0
    macro_success_rate = successful_with_macro / trades_with_macro if trades_with_macro > 0 else 0
    
    return {
        'total_trades': total_trades,
        'successful_trades': successful_trades,
        'overall_success_rate': overall_success_rate,
        'trades_with_macro': trades_with_macro,
        'successful_with_macro': successful_with_macro,
        'macro_success_rate': macro_success_rate,
        'option_type_performance': {
            'CALL': {
                'count': call_trades,
                'success_count': call_success,
                'success_rate': call_success / call_trades if call_trades > 0 else 0
            },
            'PUT': {
                'count': put_trades,
                'success_count': put_success,
                'success_rate': put_success / put_trades if put_trades > 0 else 0
            }
        },
        'macro_indicators': macro_indicators,
        'correlation_analysis': correlation_analysis
    }

def analyze_options_context(trades: List[Dict[str, Any]], success_key: str = 'success', threshold: float = 0.0) -> Dict[str, Any]:
    """
    Analyze the options market data stored with trades to find patterns.
    
    This function analyzes the relationship between options metrics and trade outcomes.
    It can be used for:
    1. Identifying which options metrics correlate with successful trades
    2. Finding optimal ranges for each metric where trade success is highest
    3. Analyzing how different option types (CALL/PUT) perform in different IV environments
    4. Generating options environment summaries for reinforcement learning
    
    Args:
        trades: List of trades with options_snapshot data
        success_key: Dictionary key that indicates if a trade was successful (default: 'success')
        threshold: Value threshold to consider a trade successful for numeric outcomes (default: 0.0)
        
    Returns:
        Dictionary with analysis results including:
        - Basic statistics for each options metric
        - Success rate correlation for each metric
        - Option type performance in different IV environments
    """
    # Initialize counters
    total_trades = len(trades)
    trades_with_options = 0
    options_metrics = {}
    
    # Success tracking
    successful_trades = 0
    successful_with_options = 0
    
    # Track by option type if available
    call_trades = 0
    put_trades = 0
    call_success = 0
    put_success = 0
    
    # Track by IV environment
    high_iv_trades = 0
    low_iv_trades = 0
    high_iv_success = 0
    low_iv_success = 0
    
    # High skew vs low skew
    high_skew_trades = 0
    low_skew_trades = 0
    high_skew_success = 0
    low_skew_success = 0
    
    # Collect all values for each metric to calculate median later
    metric_values = {}
    metric_success_mapping = {}
    
    # Analyze trades
    for trade in trades:
        # Check if this trade has options data
        has_options = 'options_snapshot' in trade and trade['options_snapshot']
        
        # Check if this trade was successful
        is_successful = False
        if success_key in trade:
            if isinstance(trade[success_key], bool):
                is_successful = trade[success_key]
            elif isinstance(trade[success_key], (int, float)):
                is_successful = trade[success_key] > threshold
            elif isinstance(trade[success_key], str):
                is_successful = trade[success_key].lower() in ('true', 'yes', 'success', '1')
        
        # Track success overall
        if is_successful:
            successful_trades += 1
            
        # Track option type performance if available
        option_type = trade.get('option_type', '').upper()
        if option_type in ('CALL', 'PUT'):
            if option_type == 'CALL':
                call_trades += 1
                if is_successful:
                    call_success += 1
            else:
                put_trades += 1
                if is_successful:
                    put_success += 1
        
        # Skip if no options data
        if not has_options:
            continue
            
        trades_with_options += 1
        if is_successful:
            successful_with_options += 1
            
        # Get options data
        options_data = trade['options_snapshot']
        
        # Track IV environment
        atm_iv = options_data.get('IV_atm')
        if atm_iv is not None:
            if atm_iv > 0.3:  # 30% IV threshold for "high" IV
                high_iv_trades += 1
                if is_successful:
                    high_iv_success += 1
            else:
                low_iv_trades += 1
                if is_successful:
                    low_iv_success += 1
        
        # Track skew environment
        iv_skew = options_data.get('IV_skew')
        if iv_skew is not None:
            if iv_skew > 0.03:  # 3% skew threshold for "high" skew
                high_skew_trades += 1
                if is_successful:
                    high_skew_success += 1
            else:
                low_skew_trades += 1
                if is_successful:
                    low_skew_success += 1
                
        # Process each options metric
        for key, value in options_data.items():
            # Initialize if first time seeing this metric
            if key not in options_metrics:
                options_metrics[key] = {
                    'count': 0,
                    'sum': 0,
                    'min': float('inf'),
                    'max': float('-inf')
                }
                metric_values[key] = []
                metric_success_mapping[key] = []
            
            # Update statistics for numeric values
            try:
                if value is not None:
                    value_float = float(value)
                    options_metrics[key]['count'] += 1
                    options_metrics[key]['sum'] += value_float
                    options_metrics[key]['min'] = min(options_metrics[key]['min'], value_float)
                    options_metrics[key]['max'] = max(options_metrics[key]['max'], value_float)
                    
                    # Store value and success for correlation analysis
                    metric_values[key].append(value_float)
                    metric_success_mapping[key].append(is_successful)
            except (ValueError, TypeError):
                # Skip non-numeric values
                pass
    
    # Calculate averages
    for key in options_metrics:
        if options_metrics[key]['count'] > 0:
            options_metrics[key]['avg'] = options_metrics[key]['sum'] / options_metrics[key]['count']
    
    # Calculate correlation between options metrics and success rate
    correlation_analysis = {}
    for key in metric_values:
        if len(metric_values[key]) >= 5:  # Need sufficient data points
            # Calculate median
            median = sorted(metric_values[key])[len(metric_values[key]) // 2]
            
            # Count trades and success above/below median
            above_median_count = 0
            above_median_success = 0
            below_median_count = 0
            below_median_success = 0
            
            for value, success in zip(metric_values[key], metric_success_mapping[key]):
                if value >= median:
                    above_median_count += 1
                    if success:
                        above_median_success += 1
                else:
                    below_median_count += 1
                    if success:
                        below_median_success += 1
            
            # Calculate success rates
            above_success_rate = above_median_success / above_median_count if above_median_count > 0 else 0
            below_success_rate = below_median_success / below_median_count if below_median_count > 0 else 0
            
            correlation_analysis[key] = {
                'median': median,
                'above_median': {
                    'count': above_median_count,
                    'success_count': above_median_success,
                    'success_rate': above_success_rate
                },
                'below_median': {
                    'count': below_median_count,
                    'success_count': below_median_success,
                    'success_rate': below_success_rate
                },
                'correlation_strength': abs(above_success_rate - below_success_rate),
                'favors_higher': above_success_rate > below_success_rate
            }
    
    # Calculate overall success rate
    overall_success_rate = successful_trades / total_trades if total_trades > 0 else 0
    options_success_rate = successful_with_options / trades_with_options if trades_with_options > 0 else 0
    
    # Calculate success rates for different environments
    high_iv_success_rate = high_iv_success / high_iv_trades if high_iv_trades > 0 else 0
    low_iv_success_rate = low_iv_success / low_iv_trades if low_iv_trades > 0 else 0
    high_skew_success_rate = high_skew_success / high_skew_trades if high_skew_trades > 0 else 0
    low_skew_success_rate = low_skew_success / low_skew_trades if low_skew_trades > 0 else 0
    
    return {
        'total_trades': total_trades,
        'successful_trades': successful_trades,
        'overall_success_rate': overall_success_rate,
        'trades_with_options': trades_with_options,
        'successful_with_options': successful_with_options,
        'options_success_rate': options_success_rate,
        'option_type_performance': {
            'CALL': {
                'count': call_trades,
                'success_count': call_success,
                'success_rate': call_success / call_trades if call_trades > 0 else 0
            },
            'PUT': {
                'count': put_trades,
                'success_count': put_success,
                'success_rate': put_success / put_trades if put_trades > 0 else 0
            }
        },
        'environment_performance': {
            'high_iv': {
                'count': high_iv_trades,
                'success_count': high_iv_success,
                'success_rate': high_iv_success_rate
            },
            'low_iv': {
                'count': low_iv_trades,
                'success_count': low_iv_success,
                'success_rate': low_iv_success_rate
            },
            'high_skew': {
                'count': high_skew_trades,
                'success_count': high_skew_success,
                'success_rate': high_skew_success_rate
            },
            'low_skew': {
                'count': low_skew_trades,
                'success_count': low_skew_success,
                'success_rate': low_skew_success_rate
            }
        },
        'options_metrics': options_metrics,
        'correlation_analysis': correlation_analysis
    }

def analyze_technical_indicators(trades, success_key='success', success_threshold=0.05):
    """
    Analyze technical indicators in relation to trade success.
    
    Args:
        trades (list): List of trade dictionaries
        success_key (str): Key in trade dict that indicates success
        success_threshold (float): Threshold for considering a trade successful
    
    Returns:
        dict: Analysis results of technical indicators
    """
    # Initialize counters and collections
    total_trades = len(trades)
    trades_with_technical_data = 0
    successful_trades = 0
    successful_with_technical_data = 0
    
    # RSI environments
    rsi_environments = {
        'overbought': {'total': 0, 'success': 0},
        'neutral': {'total': 0, 'success': 0},
        'oversold': {'total': 0, 'success': 0},
    }
    
    # Trend environments
    trend_environments = {
        'bullish': {'total': 0, 'success': 0},
        'bearish': {'total': 0, 'success': 0},
        'neutral': {'total': 0, 'success': 0},
    }
    
    # MACD signals
    macd_signals = {
        'bullish_cross': {'total': 0, 'success': 0},
        'bearish_cross': {'total': 0, 'success': 0},
        'neutral': {'total': 0, 'success': 0},
    }
    
    # Moving average crossovers
    ma_crossovers = {
        'golden_cross': {'total': 0, 'success': 0},
        'death_cross': {'total': 0, 'success': 0},
        'no_cross': {'total': 0, 'success': 0},
    }
    
    # Collect metrics for correlation analysis
    metric_values = {}
    success_values = []
    
    for trade in trades:
        # Check if trade has technical indicators
        if 'technical_indicators' not in trade:
            continue
            
        trades_with_technical_data += 1
        tech_data = trade['technical_indicators']
        
        # Determine if trade was successful
        is_successful = False
        if success_key in trade:
            if isinstance(trade[success_key], bool):
                is_successful = trade[success_key]
            elif isinstance(trade[success_key], (int, float)):
                is_successful = trade[success_key] >= success_threshold
                
        if is_successful:
            successful_trades += 1
            successful_with_technical_data += 1
            
        # Process success value for correlation
        success_values.append(1 if is_successful else 0)
        
        # Process RSI
        if 'rsi' in tech_data:
            rsi = tech_data['rsi']
            
            # Store metric for correlation analysis
            if 'rsi' not in metric_values:
                metric_values['rsi'] = []
            metric_values['rsi'].append(rsi)
            
            # Categorize RSI environment
            if rsi >= 70:
                rsi_environments['overbought']['total'] += 1
                if is_successful:
                    rsi_environments['overbought']['success'] += 1
            elif rsi <= 30:
                rsi_environments['oversold']['total'] += 1
                if is_successful:
                    rsi_environments['oversold']['success'] += 1
            else:
                rsi_environments['neutral']['total'] += 1
                if is_successful:
                    rsi_environments['neutral']['success'] += 1
        
        # Process trend
        if 'trend' in tech_data:
            trend = tech_data['trend']
            
            # Store metric for correlation analysis
            if 'trend' not in metric_values:
                metric_values['trend'] = []
            # Convert trend to numeric value for correlation
            trend_value = 1 if trend == 'bullish' else (-1 if trend == 'bearish' else 0)
            metric_values['trend'].append(trend_value)
            
            # Categorize trend environment
            if trend == 'bullish':
                trend_environments['bullish']['total'] += 1
                if is_successful:
                    trend_environments['bullish']['success'] += 1
            elif trend == 'bearish':
                trend_environments['bearish']['total'] += 1
                if is_successful:
                    trend_environments['bearish']['success'] += 1
            else:
                trend_environments['neutral']['total'] += 1
                if is_successful:
                    trend_environments['neutral']['success'] += 1
        
        # Process MACD
        if 'macd_signal' in tech_data:
            macd_signal = tech_data['macd_signal']
            
            # Store metric for correlation analysis
            if 'macd_signal' not in metric_values:
                metric_values['macd_signal'] = []
            # Convert MACD signal to numeric value for correlation
            macd_value = 1 if macd_signal == 'bullish_cross' else (-1 if macd_signal == 'bearish_cross' else 0)
            metric_values['macd_signal'].append(macd_value)
            
            # Categorize MACD signal
            if macd_signal == 'bullish_cross':
                macd_signals['bullish_cross']['total'] += 1
                if is_successful:
                    macd_signals['bullish_cross']['success'] += 1
            elif macd_signal == 'bearish_cross':
                macd_signals['bearish_cross']['total'] += 1
                if is_successful:
                    macd_signals['bearish_cross']['success'] += 1
            else:
                macd_signals['neutral']['total'] += 1
                if is_successful:
                    macd_signals['neutral']['success'] += 1
        
        # Process moving average crossovers
        if 'ma_crossover' in tech_data:
            ma_crossover = tech_data['ma_crossover']
            
            # Store metric for correlation analysis
            if 'ma_crossover' not in metric_values:
                metric_values['ma_crossover'] = []
            # Convert MA crossover to numeric value for correlation
            ma_value = 1 if ma_crossover == 'golden_cross' else (-1 if ma_crossover == 'death_cross' else 0)
            metric_values['ma_crossover'].append(ma_value)
            
            # Categorize MA crossover
            if ma_crossover == 'golden_cross':
                ma_crossovers['golden_cross']['total'] += 1
                if is_successful:
                    ma_crossovers['golden_cross']['success'] += 1
            elif ma_crossover == 'death_cross':
                ma_crossovers['death_cross']['total'] += 1
                if is_successful:
                    ma_crossovers['death_cross']['success'] += 1
            else:
                ma_crossovers['no_cross']['total'] += 1
                if is_successful:
                    ma_crossovers['no_cross']['success'] += 1
        
        # Process other numeric indicators for correlation analysis
        for key, value in tech_data.items():
            if key in ['rsi', 'trend', 'macd_signal', 'ma_crossover']:
                # Already processed above
                continue
                
            if isinstance(value, (int, float)):
                if key not in metric_values:
                    metric_values[key] = []
                metric_values[key].append(value)
    
    # Calculate correlations for numeric metrics
    correlations = {}
    for metric, values in metric_values.items():
        if len(values) == len(success_values) and len(values) > 1:
            # Check that we have sufficient data points
            try:
                from scipy.stats import pearsonr
                corr, _ = pearsonr(values, success_values)
                correlations[metric] = corr
            except:
                # Fall back to simple correlation if scipy not available
                try:
                    import numpy as np
                    corr = np.corrcoef(values, success_values)[0, 1]
                    correlations[metric] = corr
                except:
                    # Skip correlation if numpy not available
                    pass
    
    # Calculate above/below median success rates for top correlations
    median_metrics = {}
    for metric in correlations:
        if len(metric_values[metric]) <= 1:
            continue
            
        values = metric_values[metric]
        import numpy as np
        median = np.median(values)
        
        above_median = {'total': 0, 'success': 0}
        below_median = {'total': 0, 'success': 0}
        
        for i, value in enumerate(values):
            if value >= median:
                above_median['total'] += 1
                if success_values[i] == 1:
                    above_median['success'] += 1
            else:
                below_median['total'] += 1
                if success_values[i] == 1:
                    below_median['success'] += 1
        
        median_metrics[metric] = {
            'median': median,
            'above_median': above_median,
            'below_median': below_median
        }
    
    # Prepare results
    results = {
        'total_trades': total_trades,
        'trades_with_technical_data': trades_with_technical_data,
        'successful_trades': successful_trades,
        'successful_with_technical_data': successful_with_technical_data,
        'rsi_environments': rsi_environments,
        'trend_environments': trend_environments,
        'macd_signals': macd_signals,
        'ma_crossovers': ma_crossovers,
        'correlations': correlations,
        'median_metrics': median_metrics
    }
    
    return results

def create_trade_from_classification(classification: Dict[str, Any], headline: str, 
                                macro_context: Optional[Dict[str, float]] = None,
                                options_context: Optional[Dict[str, Any]] = None,
                                technical_context: Optional[Dict[str, Any]] = None,
                                event_tags: Optional[Dict[str, bool]] = None,
                                prompt_enhancers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create a standardized trade record from LLM event classifier output.
    
    Args:
        classification: The LLM classification output
        headline: The headline text that triggered the classification
        macro_context: Optional macroeconomic data to include
        options_context: Optional options market data to include
        technical_context: Optional technical indicators to include
        event_tags: Optional event-level context tags to include
        prompt_enhancers: Optional enhanced prompt context used for LLM reasoning
        
    Returns:
        A standardized trade record
    """
    # Create trade dictionary with required standard fields
    trade = {
        "headline": headline,
        "llm_output": classification,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Extract event type and sentiment if available
    if "event_type" in classification:
        trade["event_type"] = classification["event_type"]
    if "sentiment" in classification:
        trade["sentiment"] = classification["sentiment"]
    if "sector" in classification:
        trade["sector"] = classification["sector"]
    
    # If trade recommendation is available, extract it
    if "trade" in classification and isinstance(classification["trade"], dict):
        trade_rec = classification["trade"]
        
        # Extract key trade details
        if "ticker" in trade_rec:
            trade["ticker"] = trade_rec["ticker"]
        if "option_type" in trade_rec:
            trade["option_type"] = trade_rec["option_type"]
        if "strike" in trade_rec:
            trade["strike"] = trade_rec["strike"]
        if "expiry" in trade_rec:
            trade["expiry"] = trade_rec["expiry"]
        if "rationale" in trade_rec:
            trade["rationale"] = trade_rec["rationale"]
        
        # Extract trade_type (option/equity) if available, default to 'option' if not
        if "trade_type" in trade_rec:
            trade["trade_type"] = trade_rec["trade_type"]
        else:
            # Default to 'option' if option_type is present, otherwise use 'equity'
            trade["trade_type"] = "option" if "option_type" in trade_rec else "equity"
            
        # Extract direction (BUY/SELL) if available, default to 'BUY' if not
        if "direction" in trade_rec:
            trade["direction"] = trade_rec["direction"]
        else:
            # Default to BUY for both options and equity unless sentiment is bearish
            if "sentiment" in classification and classification["sentiment"].lower() == "bearish":
                # For bearish sentiment: default to SELL for equity, BUY for PUT options
                if trade["trade_type"] == "equity":
                    trade["direction"] = "SELL"
                else:
                    # For options, we're buying a PUT instead of selling the stock
                    trade["direction"] = "BUY"
            else:
                trade["direction"] = "BUY"
    else:
        # Set default values for trade_type and direction if trade recommendation is not available
        trade["trade_type"] = "option"  # Default to option
        trade["direction"] = "BUY"      # Default to BUY direction
    
    # Add macro context if provided
    if macro_context:
        trade["macro_snapshot"] = macro_context
    
    # Add options context if provided
    if options_context:
        trade["options_snapshot"] = options_context
        
    # Add technical indicators if provided
    if technical_context:
        trade["technical_indicators"] = technical_context
        
    # Add event tags if provided
    if event_tags:
        trade["event_tags"] = event_tags
        
    # Add prompt enhancers if provided
    if prompt_enhancers:
        trade["prompt_enhancers"] = prompt_enhancers
    
    return trade

def save_classification(classification: Dict[str, Any], headline: str, output_path: str = DEFAULT_TRADES_FILE,
                       macro_context: Optional[Dict[str, float]] = None,
                       options_context: Optional[Dict[str, Any]] = None,
                       technical_context: Optional[Dict[str, Any]] = None,
                       event_tags: Optional[Dict[str, bool]] = None,
                       prompt_enhancers: Optional[Dict[str, str]] = None) -> bool:
    """
    Convert LLM classification to a trade record and save it to JSON.
    
    This function streamlines the process of:
    1. Converting LLM output to a standardized trade record
    2. Saving it to the trade history JSON
    
    Args:
        classification: The LLM classification output
        headline: The headline text that triggered the classification
        output_path: Path to save the trade (default: trade_history.json)
        macro_context: Optional pre-fetched macroeconomic data
        options_context: Optional pre-fetched options market data
        technical_context: Optional pre-fetched technical indicators
        event_tags: Optional pre-generated event context tags
        prompt_enhancers: Optional enhanced prompt context used for LLM reasoning
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Create the trade record
    trade = create_trade_from_classification(
        classification=classification,
        headline=headline,
        macro_context=macro_context,
        options_context=options_context,
        technical_context=technical_context,
        event_tags=event_tags,
        prompt_enhancers=prompt_enhancers
    )
    
    # Save the trade to JSON
    # Only fetch new data if not already provided
    return save_trade_to_json(
        trade=trade,
        output_path=output_path,
        include_macro=macro_context is None,      # Only fetch if not provided
        include_options=options_context is None,  # Only fetch if not provided
        include_technicals=technical_context is None  # Only fetch if not provided
    )

def print_trade_summary(trade: Dict[str, Any], show_macro: bool = True, show_options: bool = True, 
                        show_tags: bool = True, show_technicals: bool = True,
                        show_prompt_enhancers: bool = False) -> None:
    """
    Print a formatted summary of a trade record with macro and options context.
    
    Args:
        trade: Trade record to print
        show_macro: Whether to show macroeconomic context (default: True)
        show_options: Whether to show options market data (default: True)
        show_tags: Whether to show event tags (default: True)
        show_technicals: Whether to show technical indicators (default: True)
        show_prompt_enhancers: Whether to show prompt enhancers (default: False)
    """
    if not trade:
        print("No trade data available")
        return
    
    # Print basic trade information
    print(f"Headline: {trade.get('headline', 'N/A')}")
    
    # Print timestamp in a more readable format
    timestamp_str = trade.get('timestamp', 'N/A')
    if timestamp_str != 'N/A':
        try:
            # Parse ISO format timestamp
            timestamp = datetime.datetime.fromisoformat(timestamp_str)
            # Format as human-readable
            print(f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        except (ValueError, TypeError):
            print(f"Date: {timestamp_str}")
    else:
        print("Date: N/A")
    
    # Print classification details
    print(f"Event Type: {trade.get('event_type', 'N/A')}")
    print(f"Sentiment: {trade.get('sentiment', 'N/A')}")
    print(f"Sector: {trade.get('sector', 'N/A')}")
    
    # Print trade details
    print("\nTrade Details:")
    print(f"  Ticker: {trade.get('ticker', 'N/A')}")
    print(f"  Trade Type: {trade.get('trade_type', 'option')}")  # Default to 'option' if not specified
    print(f"  Direction: {trade.get('direction', 'BUY')}")      # Default to 'BUY' if not specified
    
    # Only print option-specific details if the trade type is 'option'
    if trade.get('trade_type', 'option') == 'option':
        print(f"  Option Type: {trade.get('option_type', 'N/A')}")
        print(f"  Strike: {trade.get('strike', 'N/A')}")
        print(f"  Expiry: {trade.get('expiry', 'N/A')}")
    
    # Print rationale if available
    if 'rationale' in trade and trade['rationale']:
        print(f"\nRationale: {trade['rationale']}")
    
    # Print technical indicators if available and requested
    if show_technicals and 'technical_indicators' in trade and trade['technical_indicators']:
        print("\nTechnical Indicators:")
        tech_data = trade['technical_indicators']
        
        # Print RSI with interpretation
        if 'rsi' in tech_data and tech_data['rsi'] is not None:
            rsi = tech_data['rsi']
            if rsi > 70:
                rsi_interp = "OVERBOUGHT"
            elif rsi < 30:
                rsi_interp = "OVERSOLD"
            else:
                rsi_interp = "NEUTRAL"
            print(f"  RSI (14): {rsi:.2f} - {rsi_interp}")
            
        # Print MACD crossover
        if 'macd_cross' in tech_data:
            macd_cross = tech_data['macd_cross']
            if macd_cross == 'bullish':
                signal = "BUY SIGNAL"
            elif macd_cross == 'bearish':
                signal = "SELL SIGNAL"
            else:
                signal = "NO SIGNAL"
            print(f"  MACD Cross: {macd_cross.upper()} - {signal}")
            
        # Print moving averages
        if 'sma_50' in tech_data and 'sma_200' in tech_data and tech_data['sma_50'] is not None and tech_data['sma_200'] is not None:
            sma_50 = tech_data['sma_50']
            sma_200 = tech_data['sma_200']
            print(f"  50-day SMA: {sma_50:.2f}")
            print(f"  200-day SMA: {sma_200:.2f}")
            
            # Print MA relation
            relation = "ABOVE" if sma_50 > sma_200 else "BELOW"
            print(f"  50-day SMA is {relation} 200-day SMA - {relation == 'ABOVE' and 'BULLISH' or 'BEARISH'}")
            
        # Print overall trend
        if 'trend' in tech_data:
            trend = tech_data['trend'].upper()
            print(f"  Overall Trend: {trend}")
            
        # Print crossover event if it just happened
        if 'trend_cross' in tech_data and tech_data['trend_cross'] != 'none' and tech_data['trend_cross'] != 'unknown':
            cross_type = tech_data['trend_cross']
            cross_signal = "BULLISH" if cross_type == "golden_cross" else "BEARISH"
            print(f"  RECENT CROSSOVER: {cross_type.upper()} - {cross_signal}")
            
        # Print last close
        if 'last_close' in tech_data and tech_data['last_close'] is not None:
            print(f"  Last Close: ${tech_data['last_close']:.2f}")
    
    # Print event tags if available and requested
    if show_tags and 'event_tags' in trade and trade['event_tags']:
        print("\nEvent Tags:")
        tags = trade['event_tags']
        for tag, value in tags.items():
            print(f"  {tag}: {value}")
            
    # Print prompt enhancers if available and requested
    if show_prompt_enhancers and 'prompt_enhancers' in trade and trade['prompt_enhancers']:
        print("\nPrompt Context Used:")
        enhancers = trade['prompt_enhancers']
        if 'time_aware_text' in enhancers:
            print(f"  🕒 Time Awareness:\n    {enhancers['time_aware_text']}")
        if 'delta_description' in enhancers:
            print(f"  📊 Economic Surprise:\n    {enhancers['delta_description']}")
        if 'relevance_weights' in enhancers:
            print(f"  ⚖️ Relevance Signals:\n    {enhancers['relevance_weights']}")
    
    # Print options data if available and requested
    if show_options and 'options_snapshot' in trade and trade['options_snapshot']:
        print("\nOptions Market Data:")
        options_data = trade['options_snapshot']
        
        # Print IV metrics as percentages
        if 'IV_atm' in options_data:
            iv_atm = options_data['IV_atm'] * 100 if isinstance(options_data['IV_atm'], (int, float)) else options_data['IV_atm']
            print(f"  ATM Implied Volatility: {iv_atm}%")
        
        if 'IV_call_otm' in options_data:
            iv_call = options_data['IV_call_otm'] * 100 if isinstance(options_data['IV_call_otm'], (int, float)) else options_data['IV_call_otm']
            print(f"  OTM Call IV: {iv_call}%")
            
        if 'IV_put_otm' in options_data:
            iv_put = options_data['IV_put_otm'] * 100 if isinstance(options_data['IV_put_otm'], (int, float)) else options_data['IV_put_otm']
            print(f"  OTM Put IV: {iv_put}%")
        
        # Print IV skew
        if 'IV_skew' in options_data:
            skew = options_data['IV_skew']
            skew_interp = "Bearish (puts more expensive)" if skew > 0 else "Bullish (calls more expensive)"
            print(f"  IV Skew: {skew} ({skew_interp})")
            
        # Print put/call ratio
        if 'put_call_ratio' in options_data:
            pc_ratio = options_data['put_call_ratio']
            pc_interp = "Bearish" if pc_ratio > 1.0 else "Bullish" if pc_ratio < 1.0 else "Neutral"
            print(f"  Put/Call Ratio: {pc_ratio} ({pc_interp})")
            
        # Print open interest data
        if 'open_interest' in options_data:
            oi = options_data['open_interest']
            print("\n  Open Interest:")
            for key, value in oi.items():
                print(f"    {key}: {value}")
    
    # Print macro data if available and requested
    if show_macro and 'macro_snapshot' in trade and trade['macro_snapshot']:
        print("\nMacroeconomic Context:")
        
        # Group indicators for better readability
        macro_data = trade['macro_snapshot']
        
        # Define groups
        inflation_indicators = ['CPI_YoY', 'CoreCPI', 'PPI', 'PCE', 'CorePCE']
        rates_indicators = ['FedFundsRate', 'Treasury2Y', 'Treasury10Y', 'Treasury30Y', 'LIBOR']
        employment_indicators = ['Unemployment', 'NonFarmPayrolls', 'JobsAdded', 'InitialJoblessClaims']
        market_indicators = ['VIX', 'SP500_PE', 'SP500_Change1D', 'SP500_Change1M']
        growth_indicators = ['GDP_QoQ', 'GDP_YoY', 'RetailSales', 'ISM_Manufacturing', 'ISM_Services']
        
        # Print grouped indicators
        grouped_indicators = {
            'Inflation': [ind for ind in inflation_indicators if ind in macro_data],
            'Interest Rates': [ind for ind in rates_indicators if ind in macro_data],
            'Employment': [ind for ind in employment_indicators if ind in macro_data],
            'Market Indicators': [ind for ind in market_indicators if ind in macro_data],
            'Economic Growth': [ind for ind in growth_indicators if ind in macro_data]
        }
        
        # Track which indicators have been printed
        printed_indicators = set()
        
        # Print each group
        for group_name, indicators in grouped_indicators.items():
            if indicators:
                print(f"\n  {group_name}:")
                for ind in indicators:
                    value = macro_data[ind]
                    # Format percentages
                    if any(x in ind for x in ['YoY', 'QoQ', 'Change', 'CPI', 'PCE', 'Inflation', 'PPI']):
                        # Ensure it's a number before formatting as percentage
                        try:
                            value = float(value)
                            print(f"    {ind}: {value:.2f}%")
                        except (ValueError, TypeError):
                            print(f"    {ind}: {value}")
                    else:
                        print(f"    {ind}: {value}")
                    
                    printed_indicators.add(ind)
        
        # Print any remaining indicators not in groups
        remaining = [ind for ind in macro_data if ind not in printed_indicators]
        if remaining:
            print("\n  Other Indicators:")
            for ind in remaining:
                print(f"    {ind}: {macro_data[ind]}")

def get_latest_trade(file_path: str = DEFAULT_TRADES_FILE) -> Optional[Dict[str, Any]]:
    """
    Get the most recent trade from the trade history file.
    
    Args:
        file_path: Path to the JSON file (default: trade_history.json)
        
    Returns:
        The most recent trade or None if no trades exist
    """
    trades = load_trades(file_path)
    if not trades:
        return None
    
    return trades[-1]  # Last trade in the list is most recent

def print_technical_analysis_summary(analysis: Dict[str, Any]) -> None:
    """
    Print a formatted summary of technical indicator analysis.
    
    Args:
        analysis: Dictionary with analysis results from analyze_technical_indicators
    """
    print("\n=== TECHNICAL INDICATOR ANALYSIS ===")
    
    # Print overall stats
    print(f"Total trades analyzed: {analysis['total_trades']}")
    print(f"Trades with technical data: {analysis['trades_with_technical_data']} ({analysis['trades_with_technical_data']/analysis['total_trades']:.1%} of total)")
    print(f"Overall success rate: {analysis['overall_success_rate']:.1%}")
    print(f"Success rate with technicals: {analysis['successful_with_technical_data']/analysis['trades_with_technical_data']:.1%}")
    
    # Print RSI environment performance
    print("\n--- RSI ENVIRONMENT PERFORMANCE ---")
    rsi_env = analysis['rsi_environments']
    if rsi_env['overbought']['total'] > 0:
        print(f"Overbought (RSI > 70): {rsi_env['overbought']['success']}/{rsi_env['overbought']['total']} trades")
    if rsi_env['neutral']['total'] > 0:
        print(f"Neutral (30 < RSI < 70): {rsi_env['neutral']['success']}/{rsi_env['neutral']['total']} trades")
    if rsi_env['oversold']['total'] > 0:
        print(f"Oversold (RSI < 30): {rsi_env['oversold']['success']}/{rsi_env['oversold']['total']} trades")
    
    # Print trend environment performance
    print("\n--- TREND ENVIRONMENT PERFORMANCE ---")
    trend_env = analysis['trend_environments']
    if trend_env['bullish']['total'] > 0:
        print(f"Bullish trend (50-day SMA > 200-day SMA): {trend_env['bullish']['success']}/{trend_env['bullish']['total']} trades")
    if trend_env['bearish']['total'] > 0:
        print(f"Bearish trend (50-day SMA < 200-day SMA): {trend_env['bearish']['success']}/{trend_env['bearish']['total']} trades")
    
    # Print MACD signal performance
    print("\n--- MACD SIGNAL PERFORMANCE ---")
    macd_perf = analysis['macd_signals']
    if macd_perf['bullish_cross']['total'] > 0:
        print(f"Bullish MACD cross: {macd_perf['bullish_cross']['success']}/{macd_perf['bullish_cross']['total']} trades")
    if macd_perf['bearish_cross']['total'] > 0:
        print(f"Bearish MACD cross: {macd_perf['bearish_cross']['success']}/{macd_perf['bearish_cross']['total']} trades")
    if macd_perf['neutral']['total'] > 0:
        print(f"No recent MACD cross: {macd_perf['neutral']['success']}/{macd_perf['neutral']['total']} trades")
    
    # Print MA crossover performance
    print("\n--- MOVING AVERAGE CROSSOVER PERFORMANCE ---")
    cross_perf = analysis['ma_crossovers']
    if cross_perf['golden_cross']['total'] > 0:
        print(f"Golden cross (50-day crosses above 200-day): {cross_perf['golden_cross']['success']}/{cross_perf['golden_cross']['total']} trades")
    if cross_perf['death_cross']['total'] > 0:
        print(f"Death cross (50-day crosses below 200-day): {cross_perf['death_cross']['success']}/{cross_perf['death_cross']['total']} trades")
    if cross_perf['no_cross']['total'] > 0:
        print(f"No recent crossover: {cross_perf['no_cross']['success']}/{cross_perf['no_cross']['total']} trades")
    
    # Print correlation analysis for numeric metrics
    print("\n--- CORRELATION ANALYSIS ---")
    print("Metrics most predictive of trade success:")
    
    # Sort metrics by correlation strength
    corr_metrics = []
    for metric, corr in analysis['correlations'].items():
        if corr > 0.05:  # Only show meaningful correlations
            corr_metrics.append((metric, corr))
    
    # Display top correlations
    corr_metrics.sort(key=lambda x: x[1], reverse=True)
    for i, (metric, corr) in enumerate(corr_metrics[:5], 1):  # Show top 5
        print(f"{i}. {metric}: {corr:.2f}")
    
    if not corr_metrics or corr_metrics[0][1] <= 0.05:
        print("No strong correlations found with available data")

def analyze_event_tags(trades: List[Dict[str, Any]], success_key: str = 'success', threshold: float = 0.0) -> Dict[str, Any]:
    """
    Analyze the event tags associated with trades to find success patterns.
    
    This function analyzes the relationship between event tags and trade outcomes.
    It can be used for:
    1. Identifying which event characteristics correlate with successful trades
    2. Finding optimal trading strategies for specific event types
    3. Generating event context summaries for reinforcement learning
    
    Args:
        trades: List of trades with event_tags data
        success_key: Dictionary key that indicates if a trade was successful (default: 'success')
        threshold: Value threshold to consider a trade successful for numeric outcomes (default: 0.0)
        
    Returns:
        Dictionary with analysis results including:
        - Basic statistics for each event tag
        - Success rate for each tag value (True/False)
        - Overall tag influence on success rates
    """
    # Initialize counters
    total_trades = len(trades)
    trades_with_tags = 0
    successful_trades = 0
    successful_with_tags = 0
    
    # Track all possible tags
    all_tags = set()
    for trade in trades:
        if 'event_tags' in trade and trade['event_tags']:
            all_tags.update(trade['event_tags'].keys())
    
    # Statistics for each tag
    tag_stats = {}
    for tag in all_tags:
        tag_stats[tag] = {
            'true': {'total': 0, 'success': 0},
            'false': {'total': 0, 'success': 0},
            'missing': {'total': 0, 'success': 0}
        }
    
    # Process each trade
    for trade in trades:
        # Check if this trade was successful
        is_successful = False
        if success_key in trade:
            if isinstance(trade[success_key], bool):
                is_successful = trade[success_key]
            elif isinstance(trade[success_key], (int, float)):
                is_successful = trade[success_key] > threshold
            elif isinstance(trade[success_key], str):
                is_successful = trade[success_key].lower() in ('true', 'yes', 'success', '1')
        
        # Track overall success
        if is_successful:
            successful_trades += 1
        
        # Check if trade has event tags
        has_tags = 'event_tags' in trade and trade['event_tags']
        
        if has_tags:
            trades_with_tags += 1
            if is_successful:
                successful_with_tags += 1
            
            # Process each possible tag
            for tag in all_tags:
                if tag in trade['event_tags']:
                    # Determine tag value (true/false)
                    tag_value = trade['event_tags'][tag]
                    value_key = 'true' if tag_value else 'false'
                    
                    # Update statistics
                    tag_stats[tag][value_key]['total'] += 1
                    if is_successful:
                        tag_stats[tag][value_key]['success'] += 1
                else:
                    # Tag is missing for this trade
                    tag_stats[tag]['missing']['total'] += 1
                    if is_successful:
                        tag_stats[tag]['missing']['success'] += 1
        else:
            # No tags for this trade, update missing counts for all tags
            for tag in all_tags:
                tag_stats[tag]['missing']['total'] += 1
                if is_successful:
                    tag_stats[tag]['missing']['success'] += 1
    
    # Calculate success rates and differentials
    tag_influence = {}
    for tag, stats in tag_stats.items():
        # Calculate success rates
        true_success_rate = stats['true']['success'] / stats['true']['total'] if stats['true']['total'] > 0 else 0
        false_success_rate = stats['false']['success'] / stats['false']['total'] if stats['false']['total'] > 0 else 0
        missing_success_rate = stats['missing']['success'] / stats['missing']['total'] if stats['missing']['total'] > 0 else 0
        
        # Add success rates to statistics
        stats['true']['success_rate'] = true_success_rate
        stats['false']['success_rate'] = false_success_rate
        stats['missing']['success_rate'] = missing_success_rate
        
        # Calculate influence (how much this tag affects success rate)
        if stats['true']['total'] > 0 and stats['false']['total'] > 0:
            # Measure difference between true and false success rates
            differential = true_success_rate - false_success_rate
            tag_influence[tag] = {
                'differential': differential,
                'significance': abs(differential),
                'favors_true': differential > 0
            }
    
    # Calculate overall success rate
    overall_success_rate = successful_trades / total_trades if total_trades > 0 else 0
    tags_success_rate = successful_with_tags / trades_with_tags if trades_with_tags > 0 else 0
    
    return {
        'total_trades': total_trades,
        'successful_trades': successful_trades,
        'overall_success_rate': overall_success_rate,
        'trades_with_tags': trades_with_tags,
        'successful_with_tags': successful_with_tags,
        'tags_success_rate': tags_success_rate,
        'tag_stats': tag_stats,
        'tag_influence': tag_influence
    }

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Trade History Manager')
    parser.add_argument('--analyze', action='store_true', help='Analyze trade history and show stats')
    parser.add_argument('--clear', action='store_true', help='Clear trade history')
    parser.add_argument('--example', action='store_true', help='Save an example trade')
    parser.add_argument('--file', type=str, default='trades.json', help='Trade history file name')
    parser.add_argument('--latest', action='store_true', help='Show latest trade')
    parser.add_argument('--no-macro', action='store_true', help='Skip macro data in example or latest trade')
    parser.add_argument('--no-options', action='store_true', help='Skip options data in example or latest trade')
    parser.add_argument('--no-technicals', action='store_true', help='Skip technical analysis in trade analysis')
    
    args = parser.parse_args()
    
    if args.clear:
        # Clear the trade history file
        with open(args.file, 'w') as f:
            json.dump([], f)
        print(f"Cleared trade history in {args.file}")
    
    elif args.example:
        # Create an example trade
        from datetime import datetime
        
        # Fetch macro and options data based on flags
        macro_context = None
        options_context = None
        
        if not args.no_macro:
            try:
                from macro_data_collector import get_macro_snapshot
                macro_context = get_macro_snapshot()
            except Exception as e:
                print(f"Warning: Could not fetch macro data: {e}")
        
        if not args.no_options:
            try:
                from options_data_collector import get_options_snapshot
                options_context = get_options_snapshot("AAPL")
            except Exception as e:
                print(f"Warning: Could not fetch options data: {e}")
                
        # Create an example trade
        example_classification = {
            "headline": "Apple announces new iPhone with improved AI capabilities",
            "event_type": "product_launch",
            "sentiment": "bullish",
            "sector": "technology",
            "ticker": "AAPL",
            "option_type": "CALL",
            "strike": 190.0,
            "expiry": "2023-12-15",
            "trade_type": "option",
            "direction": "BUY",
            "confidence": 0.85,
            "rationale": "The new iPhone features are likely to drive significant consumer upgrade cycles, positively impacting Apple's revenue for the upcoming quarters."
        }
        
        # Get event tags if possible
        event_tags = None
        try:
            from event_tagger import generate_event_tags
            event_date = datetime.now()
            event_tags = generate_event_tags(
                example_classification["headline"],
                macro_context,
                event_date,
                example_classification["ticker"]
            )
        except Exception as e:
            print(f"Warning: Could not generate event tags: {e}")
        
        # Get technical indicators if possible
        technical_indicators = None
        if not args.no_technicals:
            try:
                from technical_analyzer import get_technical_indicators
                technical_indicators = get_technical_indicators(example_classification["ticker"])
            except Exception as e:
                print(f"Warning: Could not fetch technical indicators: {e}")
        
        # Save the example classification to create a trade
        save_classification(
            example_classification,
            args.file,
            macro_context=macro_context,
            options_context=options_context,
            event_tags=event_tags,
            technical_indicators=technical_indicators
        )
        
        print(f"Saved example trade to {args.file}")
        
        # Show the saved trade
        trades = load_trades(args.file)
        if trades:
            print("\nExample Trade Summary:")
            print_trade_summary(
                trades[-1], 
                show_macro=not args.no_macro, 
                show_options=not args.no_options
            )
    
    elif args.latest:
        # Show the latest trade
        trades = load_trades(args.file)
        if trades:
            print("Latest Trade Summary:")
            print_trade_summary(
                trades[-1], 
                show_macro=not args.no_macro, 
                show_options=not args.no_options
            )
        else:
            print("No trades found in history.")
    
    elif args.analyze:
        # Analyze trade history
        trades = load_trades(args.file)
        if not trades:
            print("No trades found to analyze.")
            exit(0)
            
        print(f"Analyzing {len(trades)} trades from {args.file}")
        
        # Basic statistics
        total_trades = len(trades)
        bullish_trades = sum(1 for t in trades if t.get('sentiment') == 'bullish')
        bearish_trades = sum(1 for t in trades if t.get('sentiment') == 'bearish')
        neutral_trades = total_trades - bullish_trades - bearish_trades
        
        option_trades = sum(1 for t in trades if t.get('trade_type') == 'option')
        equity_trades = sum(1 for t in trades if t.get('trade_type') == 'equity')
        other_trades = total_trades - option_trades - equity_trades
        
        buy_trades = sum(1 for t in trades if t.get('direction') == 'BUY')
        sell_trades = sum(1 for t in trades if t.get('direction') == 'SELL')
        other_direction = total_trades - buy_trades - sell_trades
        
        print("\n=== Basic Trade Statistics ===")
        print(f"Total Trades: {total_trades}")
        print(f"Sentiment Distribution: {bullish_trades} bullish ({bullish_trades/total_trades:.1%}), " 
              f"{bearish_trades} bearish ({bearish_trades/total_trades:.1%}), "
              f"{neutral_trades} neutral ({neutral_trades/total_trades:.1%})")
        print(f"Trade Type Distribution: {option_trades} options ({option_trades/total_trades:.1%}), "
              f"{equity_trades} equity ({equity_trades/total_trades:.1%}), "
              f"{other_trades} other ({other_trades/total_trades:.1%})")
        print(f"Direction Distribution: {buy_trades} buy ({buy_trades/total_trades:.1%}), "
              f"{sell_trades} sell ({sell_trades/total_trades:.1%}), "
              f"{other_direction} other ({other_direction/total_trades:.1%})")
              
        # Event type analysis
        event_types = {}
        for trade in trades:
            event_type = trade.get('event_type', 'unknown')
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        print("\n=== Event Type Analysis ===")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            print(f"{event_type}: {count} trades ({count/total_trades:.1%})")
            
        # Analyze macro data if available and not skipped
        macro_trades = sum(1 for t in trades if 'macro_snapshot' in t)
        if macro_trades > 0 and not args.no_macro:
            print("\n=== Macroeconomic Analysis ===")
            print(f"Trades with macro data: {macro_trades} ({macro_trades/total_trades:.1%})")
            
            try:
                macro_analysis = analyze_macro_context(trades)
                
                # Print success rates in different macro environments
                print("\nPerformance in Different Macro Environments:")
                for env_name, env_data in macro_analysis['macro_environments'].items():
                    if env_data['total'] > 0:
                        success_rate = env_data['success'] / env_data['total'] if env_data['total'] > 0 else 0
                        print(f"  {env_name}: {env_data['success']}/{env_data['total']} successful ({success_rate:.1%})")
                
                # Print top correlations
                print("\nTop Macro Indicator Correlations:")
                sorted_correlations = sorted(
                    macro_analysis['correlations'].items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )
                for indicator, correlation in sorted_correlations[:5]:  # Show top 5
                    if abs(correlation) >= 0.1:  # Only show meaningful correlations
                        sign = "+" if correlation > 0 else ""
                        print(f"  {indicator}: {sign}{correlation:.2f}")
                
                # Print median analysis for top indicators
                print("\nPerformance Above/Below Median for Key Indicators:")
                for metric, data in list(macro_analysis['median_metrics'].items())[:3]:  # Show top 3
                    above_success_rate = data['above_median']['success'] / data['above_median']['total'] if data['above_median']['total'] > 0 else 0
                    below_success_rate = data['below_median']['success'] / data['below_median']['total'] if data['below_median']['total'] > 0 else 0
                    print(f"  {metric} (median: {data['median']:.2f}):")
                    print(f"    Above median: {above_success_rate:.1%} success rate ({data['above_median']['success']}/{data['above_median']['total']})")
                    print(f"    Below median: {below_success_rate:.1%} success rate ({data['below_median']['success']}/{data['below_median']['total']})")
            
            except Exception as e:
                print(f"Error analyzing macro data: {e}")
        
        # Analyze options data if available and not skipped
        options_trades = sum(1 for t in trades if 'options_snapshot' in t)
        if options_trades > 0 and not args.no_options:
            print("\n=== Options Market Analysis ===")
            print(f"Trades with options data: {options_trades} ({options_trades/total_trades:.1%})")
            
            try:
                options_analysis = analyze_options_context(trades)
                
                # Print performance by option type
                call_success_rate = options_analysis['option_types']['CALL']['success'] / options_analysis['option_types']['CALL']['total'] if options_analysis['option_types']['CALL']['total'] > 0 else 0
                put_success_rate = options_analysis['option_types']['PUT']['success'] / options_analysis['option_types']['PUT']['total'] if options_analysis['option_types']['PUT']['total'] > 0 else 0
                
                print("\nPerformance by Option Type:")
                print(f"  CALL options: {call_success_rate:.1%} success rate ({options_analysis['option_types']['CALL']['success']}/{options_analysis['option_types']['CALL']['total']})")
                print(f"  PUT options: {put_success_rate:.1%} success rate ({options_analysis['option_types']['PUT']['success']}/{options_analysis['option_types']['PUT']['total']})")
                
                # Print performance in different IV environments
                print("\nPerformance in Different IV Environments:")
                for env_name, env_data in options_analysis['iv_environments'].items():
                    if env_data['total'] > 0:
                        success_rate = env_data['success'] / env_data['total']
                        print(f"  {env_name}: {success_rate:.1%} success rate ({env_data['success']}/{env_data['total']})")
                
                # Print top correlations
                print("\nTop Options Metric Correlations:")
                sorted_correlations = sorted(
                    options_analysis['correlations'].items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )
                for metric, correlation in sorted_correlations[:5]:  # Show top 5
                    if abs(correlation) >= 0.1:  # Only show meaningful correlations
                        sign = "+" if correlation > 0 else ""
                        print(f"  {metric}: {sign}{correlation:.2f}")
            
            except Exception as e:
                print(f"Error analyzing options data: {e}")
                
        # Analyze technical data if available and not skipped
        technical_trades = sum(1 for t in trades if 'technical_indicators' in t)
        if technical_trades > 0 and not args.no_technicals:
            print("\n=== Technical Analysis ===")
            print(f"Trades with technical data: {technical_trades} ({technical_trades/total_trades:.1%})")
            
            try:
                technical_analysis = analyze_technical_indicators(trades)
                
                # Print RSI environment performance
                print("\nPerformance in Different RSI Environments:")
                for env_name, env_data in technical_analysis['rsi_environments'].items():
                    if env_data['total'] > 0:
                        success_rate = env_data['success'] / env_data['total']
                        print(f"  {env_name}: {success_rate:.1%} success rate ({env_data['success']}/{env_data['total']})")
                
                # Print trend environment performance
                print("\nPerformance in Different Trend Environments:")
                for env_name, env_data in technical_analysis['trend_environments'].items():
                    if env_data['total'] > 0:
                        success_rate = env_data['success'] / env_data['total']
                        print(f"  {env_name}: {success_rate:.1%} success rate ({env_data['success']}/{env_data['total']})")
                
                # Print MACD signal performance
                print("\nPerformance by MACD Signal:")
                for signal_name, signal_data in technical_analysis['macd_signals'].items():
                    if signal_data['total'] > 0:
                        success_rate = signal_data['success'] / signal_data['total']
                        print(f"  {signal_name}: {success_rate:.1%} success rate ({signal_data['success']}/{signal_data['total']})")
                
                # Print MA crossover performance
                print("\nPerformance by Moving Average Crossover:")
                for crossover_name, crossover_data in technical_analysis['ma_crossovers'].items():
                    if crossover_data['total'] > 0:
                        success_rate = crossover_data['success'] / crossover_data['total']
                        print(f"  {crossover_name}: {success_rate:.1%} success rate ({crossover_data['success']}/{crossover_data['total']})")
                
                # Print top correlations
                print("\nTop Technical Indicator Correlations:")
                sorted_correlations = sorted(
                    technical_analysis['correlations'].items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )
                for indicator, correlation in sorted_correlations[:5]:  # Show top 5
                    if abs(correlation) >= 0.1:  # Only show meaningful correlations
                        sign = "+" if correlation > 0 else ""
                        print(f"  {indicator}: {sign}{correlation:.2f}")
            
            except Exception as e:
                print(f"Error analyzing technical data: {e}")
                
        # Analyze event tags if available
        event_tag_trades = sum(1 for t in trades if 'event_tags' in t)
        if event_tag_trades > 0:
            print("\n=== Event Tag Analysis ===")
            print(f"Trades with event tags: {event_tag_trades} ({event_tag_trades/total_trades:.1%})")
            
            try:
                event_tags_analysis = analyze_event_tags(trades)
                
                # Print tag influence (most significant tags first)
                print("\nEvent Tag Influence on Trade Success:")
                sorted_tags = sorted(
                    event_tags_analysis['tag_influence'].items(),
                    key=lambda x: abs(x[1]['significance']),
                    reverse=True
                )
                
                for tag, influence in sorted_tags:
                    tag_stats = event_tags_analysis['tag_stats'][tag]
                    diff = influence['differential']
                    sign = "+" if diff > 0 else ""
                    direction = "when True" if influence['favors_true'] else "when False"
                    
                    print(f"  {tag}: {sign}{diff:.2f} (better {direction})")
                    print(f"    True: {tag_stats['true']['success_rate']:.1%} success ({tag_stats['true']['success']}/{tag_stats['true']['total']})")
                    print(f"    False: {tag_stats['false']['success_rate']:.1%} success ({tag_stats['false']['success']}/{tag_stats['false']['total']})")
                
            except Exception as e:
                print(f"Error analyzing event tags: {e}")
    
    else:
        # Show usage if no flag is provided
        parser.print_help()

    sys.exit(0) 