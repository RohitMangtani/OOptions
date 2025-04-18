#!/usr/bin/env python
"""
View Analysis Utility

This command-line tool allows users to view and manage saved historical analyses.
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
import analysis_persistence as ap
from functools import lru_cache

@lru_cache(maxsize=32)
def _load_analysis_with_cache(file_path: str) -> Optional[Dict]:
    """
    Load an analysis file with caching to avoid redundant disk reads
    
    Args:
        file_path: Path to the analysis file
        
    Returns:
        Dict or None: The analysis data or None if not found/error
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading analysis from {file_path}: {str(e)}")
        return None

def _get_full_path(base_dir: str, file_path: str) -> str:
    """
    Convert a relative path to a full path based on the base directory
    
    Args:
        base_dir: Base directory
        file_path: Relative or absolute file path
        
    Returns:
        str: Full path
    """
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(base_dir, file_path)

def list_analyses(ticker: str = None, days: int = 30, 
                  pattern: str = None, limit: int = 10,
                  detailed: bool = False) -> None:
    """
    List saved analyses matching the criteria
    
    Args:
        ticker: Optional ticker symbol to filter by
        days: Number of recent days to include
        pattern: Optional pattern to filter by
        limit: Maximum number of analyses to show
        detailed: Whether to show detailed information
    """
    persistence = ap.AnalysisPersistence()
    
    # Process analyses in batches to improve memory efficiency
    BATCH_SIZE = 5  # Number of detailed analyses to load at once
    
    # Helper function to display a batch of analyses
    def display_analyses_batch(analyses_batch, start_idx, analysis_type="historical"):
        for i, analysis in enumerate(analyses_batch, start_idx):
            if analysis_type == "historical":
                ticker = analysis.get("ticker", "Unknown")
                event_date = analysis.get("event_date", "Unknown")
                price_change = analysis.get("price_change", 0)
                trend = analysis.get("trend", "Unknown")
                saved_at = analysis.get("saved_at", "Unknown")
                file_path = analysis.get("file_path", "")
                
                print(f"{i}. {ticker} - {event_date} - {price_change}% ({trend})")
            else:  # similar events
                pattern = analysis.get("pattern", "Unknown")
                ticker = analysis.get("dominant_ticker", "Unknown")
                change = analysis.get("avg_price_change", 0)
                consistency = analysis.get("consistency_score", 0)
                saved_at = analysis.get("saved_at", "Unknown")
                file_path = analysis.get("file_path", "")
                
                print(f"{i}. {pattern} - {ticker} - {change}% (Consistency: {consistency}%)")
            
            if detailed:
                print(f"   Saved: {saved_at}")
                print(f"   File: {file_path}")
                
                # Load full analysis for detailed view using cache - handle relative paths
                full_path = _get_full_path(persistence.base_dir, file_path)
                full_analysis = _load_analysis_with_cache(full_path)
                if full_analysis:
                    # Show additional details
                    if analysis_type == "historical":
                        if "max_drawdown_pct" in full_analysis:
                            print(f"   Max Drawdown: {full_analysis.get('max_drawdown_pct')}%")
                        if "volatility_pct" in full_analysis:
                            print(f"   Volatility: {full_analysis.get('volatility_pct')}%")
                        if "days_analyzed" in full_analysis:
                            print(f"   Analysis Period: {full_analysis.get('days_analyzed')} days")
                    else:  # similar events
                        if "avg_max_drawdown" in full_analysis:
                            print(f"   Avg Max Drawdown: {full_analysis.get('avg_max_drawdown')}%")
                        if "bullish_pct" in full_analysis and "bearish_pct" in full_analysis:
                            print(f"   Trend Distribution: {full_analysis.get('bullish_pct')}% Bullish, {full_analysis.get('bearish_pct')}% Bearish")
                        if "similar_events_count" in full_analysis:
                            print(f"   Similar Events Count: {full_analysis.get('similar_events_count')}")
                    
                    # Show query if available
                    metadata = full_analysis.get("_metadata", {})
                    if "query" in metadata:
                        print(f"   Query: \"{metadata.get('query')}\"")
                print()
    
    # Get and display historical event analyses
    if ticker:
        print(f"\nHistorical Event Analyses for {ticker}:")
        print("-" * 60)
        historical_analyses = persistence.find_historical_analysis(ticker=ticker)
    else:
        print("\nRecent Historical Event Analyses:")
        print("-" * 60)
        # Get all analyses and sort by saved_at (newest first)
        historical_analyses = []
        for ticker_analyses in persistence.event_index["events"].values():
            historical_analyses.extend(ticker_analyses)
    
    # Sort by saved_at (most recent first)
    historical_analyses.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    
    # Limit the number of results
    historical_analyses = historical_analyses[:limit]
    
    # Display analyses in batches
    if historical_analyses:
        if detailed:
            # Process in batches to avoid loading too many files at once
            for i in range(0, len(historical_analyses), BATCH_SIZE):
                batch = historical_analyses[i:i+BATCH_SIZE]
                display_analyses_batch(batch, i+1, "historical")
        else:
            # If not detailed, we can display all at once (no file loading needed)
            display_analyses_batch(historical_analyses, 1, "historical")
    else:
        print("No historical event analyses found.")
    
    # Get and display similar events analyses
    if pattern:
        print(f"\nSimilar Events Analyses matching '{pattern}':")
        print("-" * 60)
        similar_analyses = persistence.find_similar_events_analysis(pattern=pattern)
    else:
        print("\nRecent Similar Events Analyses:")
        print("-" * 60)
        # Get all analyses and sort by saved_at (newest first)
        similar_analyses = []
        for pattern_analyses in persistence.event_index["similar_events"].values():
            similar_analyses.extend(pattern_analyses)
    
    # Sort by saved_at (most recent first)
    similar_analyses.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    
    # Limit the number of results
    similar_analyses = similar_analyses[:limit]
    
    # Display analyses in batches
    if similar_analyses:
        if detailed:
            # Process in batches to avoid loading too many files at once
            for i in range(0, len(similar_analyses), BATCH_SIZE):
                batch = similar_analyses[i:i+BATCH_SIZE]
                display_analyses_batch(batch, i+1, "similar")
        else:
            # If not detailed, we can display all at once (no file loading needed)
            display_analyses_batch(similar_analyses, 1, "similar")
    else:
        print("No similar events analyses found.")

def show_analysis(file_path: str, format: str = "text") -> None:
    """
    Show a specific analysis
    
    Args:
        file_path: Path to the analysis file
        format: Output format (text or json)
    """
    # Convert to full path if necessary
    persistence = ap.AnalysisPersistence()
    if not os.path.isabs(file_path) and not os.path.exists(file_path):
        # Try treating it as a relative path to the base directory
        full_path = _get_full_path(persistence.base_dir, file_path)
    else:
        full_path = file_path
    
    # Use cached loader instead of persistence.load_analysis
    analysis = _load_analysis_with_cache(full_path)
    
    if not analysis:
        print(f"Analysis not found or could not be loaded: {file_path}")
        return
    
    if format == "json":
        # Print the raw JSON
        print(json.dumps(analysis, indent=2))
        return
    
    # Helper function to safely display a section if it exists
    def display_section(section_name, formatter, required_keys=None):
        if section_name in analysis:
            section_data = analysis[section_name]
            
            # Skip if we require certain keys and they're not present
            if required_keys and not all(k in section_data for k in required_keys):
                return
                
            # Apply the formatter function
            formatter(section_data)
    
    # Print formatted text output
    print("\n" + "=" * 80)
    
    # Determine the type of analysis and display the header
    if "price_change_pct" in analysis and "event_date" in analysis:
        print(f"Historical Event Analysis - {analysis.get('ticker', 'Unknown')} on {analysis.get('event_date', 'Unknown')}")
        print("-" * 80)
        
        # Event details
        print(f"Event Date: {analysis.get('event_date', 'Unknown')}")
        print(f"Ticker: {analysis.get('ticker', 'Unknown')}")
        print(f"Price Change: {analysis.get('price_change_pct', 0)}%")
        print(f"Maximum Drawdown: {analysis.get('max_drawdown_pct', 0)}%")
        print(f"Volatility: {analysis.get('volatility_pct', 0)}%")
        print(f"Trend: {analysis.get('trend', 'Unknown')}")
        print(f"Analysis Period: {analysis.get('days_analyzed', 0)} days ({analysis.get('date_range_analyzed', 'Unknown')})")
        
        # Print price details
        if all(k in analysis for k in ["start_price", "end_price", "highest_price", "lowest_price"]):
            print("\nPrice Details:")
            print(f"  Start Price: ${analysis.get('start_price', 0)}")
            print(f"  End Price: ${analysis.get('end_price', 0)}")
            print(f"  Highest Price: ${analysis.get('highest_price', 0)}")
            print(f"  Lowest Price: ${analysis.get('lowest_price', 0)}")
        
        # Print macro data if available - using formatter function
        def format_macro_data(macro):
            print("\nMacroeconomic Environment:")
            for key, value in macro.items():
                if not key.startswith("_"):  # Skip metadata fields
                    print(f"  {key}: {value}")
        
        display_section("macro_data", format_macro_data)
        
        # Print impact explanation if available - using formatter function
        def format_impact_explanation(impact):
            if not impact.get("success", False):
                return
                
            print("\nImpact Explanation:")
            print(f"  Immediate Reaction: {impact.get('immediate_reaction', '')}")
            print(f"  Causal Explanation: {impact.get('causal_explanation', '')}")
            print(f"  Follow-on Effects: {impact.get('follow_on_effects', '')}")
            
            if "macro_context" in impact:
                print(f"\n  Macroeconomic Context: {impact.get('macro_context', '')}")
            
            if "historical_pattern_analysis" in impact:
                print(f"\n  Historical Pattern Comparison: {impact.get('historical_pattern_analysis', '')}")
                
        display_section("impact_explanation", format_impact_explanation)
        
        # Print sentiment analysis if available - using formatter function
        def format_sentiment_analysis(sentiment):
            print("\nSentiment Analysis:")
            print(f"  Price-Based Sentiment: {sentiment['classified_sentiment']['label']} (score: {sentiment['classified_sentiment']['score']})")
            print(f"  Historical Sentiment: {sentiment['historical_sentiment']['label']} (score: {sentiment['historical_sentiment']['score']})")
            print(f"  Agreement: {sentiment['comparison']['agreement_label']} ({sentiment['comparison']['agreement']})")
            
            if "insights" in sentiment:
                print("\n  Sentiment Insights:")
                for insight in sentiment["insights"]:
                    print(f"    • {insight}")
        
        display_section("sentiment_analysis", format_sentiment_analysis, 
                       required_keys=["classified_sentiment", "historical_sentiment", "comparison"])
        
    elif "pattern_summary" in analysis and "similar_events_count" in analysis:
        # Similar events analysis
        print(f"Similar Events Analysis - {analysis.get('pattern_summary', 'Unknown')}")
        print("-" * 80)
        
        # Pattern details
        print(f"Pattern: {analysis.get('pattern_summary', 'Unknown')}")
        print(f"Consistency: {analysis.get('consistency_score', 0)}%")
        print(f"Average Price Change: {analysis.get('avg_price_change', 0)}%")
        print(f"Average Maximum Drawdown: {analysis.get('avg_max_drawdown', 0)}%")
        print(f"Trend Distribution: {analysis.get('bullish_pct', 0)}% Bullish, {analysis.get('bearish_pct', 0)}% Bearish")
        print(f"Similar Events Count: {analysis.get('similar_events_count', 0)}")
        print(f"Most Common Sector: {analysis.get('dominant_sector', 'Unknown')}")
        print(f"Most Common Ticker: {analysis.get('dominant_ticker', 'Unknown')}")
        
        # Print sentiment analysis if available - using formatter function
        def format_sentiment_pattern(sentiment_data):
            print("\nSentiment Pattern Analysis:")
            print(f"  Events with sentiment data: {analysis.get('events_with_sentiment', 0)}")
            print(f"  Sentiment-price alignment: {analysis.get('sentiment_alignment_pct', 0)}%")
            
            # Print performance comparison if available
            if "sentiment_performance" in analysis:
                perf = analysis["sentiment_performance"]
                print(f"\n  Performance when sentiment aligned with price: {perf.get('aligned_sentiment_avg_price_change', 0)}% ({perf.get('aligned_count', 0)} events)")
                print(f"  Performance when sentiment diverged from price: {perf.get('diverged_sentiment_avg_price_change', 0)}% ({perf.get('diverged_count', 0)} events)")
            
            # Print sentiment insights if available
            if "sentiment_insights" in analysis:
                print("\n  Sentiment Pattern Insights:")
                for i, insight in enumerate(analysis["sentiment_insights"], 1):
                    print(f"    {i}. {insight}")
        
        if analysis.get("has_sentiment_analysis", False):
            format_sentiment_pattern({})  # Using empty dict since we're accessing from analysis directly
        
        # Print macro analysis if available - using formatter function
        def format_macro_analysis(macro_data):
            print("\nMacro Correlation Analysis:")
            print(f"  Events with macro data: {analysis.get('events_with_macro', 0)}")
            
            # Print correlations if available
            if "macro_correlations" in analysis:
                for factor, data in analysis["macro_correlations"].items():
                    if data.get("strength") != "None" and data.get("sample_size", 0) >= 3:
                        factor_display = {
                            'cpi': 'Inflation Rate',
                            'fed_rate': 'Fed Funds Rate',
                            'unemployment': 'Unemployment Rate',
                            'yield_curve': 'Yield Curve (10Y-2Y)'
                        }.get(factor, factor.title())
                        
                        print(f"  {factor_display}: {data.get('correlation')} correlation ({data.get('strength')} {data.get('direction')}) - sample size: {data.get('sample_size')}")
            
            # Print macro insights if available
            if "macro_insights" in analysis:
                print("\nMacro Environment Insights:")
                for i, insight in enumerate(analysis["macro_insights"], 1):
                    print(f"  {i}. {insight}")
        
        if analysis.get("has_macro_analysis", False):
            format_macro_analysis({})  # Using empty dict since we're accessing from analysis directly
    
    # Print metadata
    if "_metadata" in analysis:
        metadata = analysis["_metadata"]
        print("\nMetadata:")
        print(f"  Saved At: {metadata.get('saved_at', 'Unknown')}")
        if "query" in metadata:
            print(f"  Query: \"{metadata.get('query')}\"")
        print(f"  File Path: {metadata.get('file_path', 'Unknown')}")
    
    print("=" * 80)

def show_query_history(limit: int = 10, search: str = None, export_file: str = None) -> None:
    """
    Show query history
    
    Args:
        limit: Maximum number of queries to show
        search: Optional search term to filter by
        export_file: Optional file path to export the query history to
    """
    persistence = ap.AnalysisPersistence()
    queries = persistence.search_query_history(query_term=search, limit=limit)
    
    if not queries:
        print("No queries found.")
        return
    
    # No need to sort again as search_query_history already returns sorted results
    queries_to_display = queries[:limit]
    
    # Export to file if requested
    if export_file:
        try:
            export_data = {
                "query_history": queries_to_display,
                "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "filter": {"search": search, "limit": limit}
            }
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"Exported {len(queries_to_display)} queries to {export_file}")
        except Exception as e:
            print(f"Error exporting query history to {export_file}: {str(e)}")
    
    print("\nQuery History:")
    print("-" * 80)
    
    for i, query in enumerate(queries_to_display, 1):
        q = query.get("query", "Unknown")
        timestamp = query.get("timestamp", "Unknown")
        result_type = query.get("result_type", "Unknown")
        file_path = query.get("file_path", "Unknown")
        
        print(f"{i}. \"{q}\" ({timestamp})")
        print(f"   Type: {result_type}")
        
        # Add additional details based on result type
        if result_type == "historical_event":
            ticker = query.get("ticker", "Unknown")
            event_date = query.get("event_date", "Unknown")
            print(f"   Analysis: {ticker} on {event_date}")
        elif result_type == "similar_events":
            pattern = query.get("pattern", "Unknown")
            ticker = query.get("dominant_ticker", "Unknown")
            print(f"   Analysis: {pattern} - {ticker}")
        
        # Check if file still exists
        if os.path.exists(file_path):
            print(f"   File: {file_path}")
        else:
            print(f"   File: {file_path} (not found)")
        print()

@lru_cache(maxsize=1)
def _get_cached_statistics():
    """Get cached analysis statistics to avoid recalculation"""
    persistence = ap.AnalysisPersistence()
    return persistence.get_statistics()

def clear_statistics_cache():
    """Clear the statistics cache to force recalculation"""
    _get_cached_statistics.cache_clear()
    
def show_statistics() -> None:
    """Show statistics about saved analyses"""
    # Use cached statistics to avoid recalculation
    stats = _get_cached_statistics()
    
    print("\nAnalysis Storage Statistics:")
    print("-" * 80)
    print(f"Total Historical Event Analyses: {stats.get('total_historical_events', 0)}")
    print(f"Total Similar Events Analyses: {stats.get('total_similar_events', 0)}")
    print(f"Total Queries: {stats.get('total_queries', 0)}")
    
    if stats.get("tickers_analyzed"):
        # Use join for better performance with large lists
        tickers = stats.get("tickers_analyzed", [])
        # Limit display to first 20 tickers if there are many
        if len(tickers) > 20:
            displayed_tickers = tickers[:20]
            print(f"Tickers Analyzed: {', '.join(displayed_tickers)} (and {len(tickers) - 20} more)")
        else:
            print(f"Tickers Analyzed: {', '.join(tickers)}")
    
    if stats.get("most_analyzed_ticker"):
        print(f"Most Analyzed Ticker: {stats.get('most_analyzed_ticker')}")
    
    if stats.get("most_common_pattern"):
        print(f"Most Common Pattern: {stats.get('most_common_pattern')}")
    
    if stats.get("most_recent_query"):
        print(f"Most Recent Query: \"{stats.get('most_recent_query')}\"")

def export_analyses(output_file: str, ticker: str = None, pattern: str = None) -> None:
    """
    Export analyses to a file
    
    Args:
        output_file: Path to the output file
        ticker: Optional ticker to filter by
        pattern: Optional pattern to filter by
    """
    persistence = ap.AnalysisPersistence()
    
    # Get analyses to export
    export_data = {
        "historical_events": [],
        "similar_events": [],
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filter": {"ticker": ticker, "pattern": pattern}
    }
    
    # Constants for batch processing
    BATCH_SIZE = 10  # Process 10 files at a time to limit memory usage
    
    # Helper function to load and process analyses in batches with caching
    @lru_cache(maxsize=50)  # Cache for the batch processor to avoid redundant file reads
    def process_analysis_file_for_export(file_path):
        """Process a single analysis file with caching for export"""
        if file_path and os.path.exists(file_path):
            # Use the existing file cache if possible
            return _load_analysis_with_cache(file_path)
        return None
    
    def process_analyses_batch(analyses, target_list):
        """Process a batch of analyses and add them to the target list"""
        batch_count = 0
        
        for analysis_info in analyses:
            file_path = analysis_info.get("file_path", "")
            # Convert to full path if needed
            if not os.path.isabs(file_path) and not os.path.exists(file_path):
                file_path = _get_full_path(persistence.base_dir, file_path)
            
            # Use the cached function to load the analysis
            full_analysis = process_analysis_file_for_export(file_path)
            if full_analysis:
                target_list.append(full_analysis)
                batch_count += 1
                
                # Give progress updates for large exports
                if len(target_list) % 25 == 0:
                    print(f"Processed {len(target_list)} analyses...")
        
        return batch_count
    
    # Get historical event analyses
    print("Finding historical event analyses...")
    if ticker:
        historical_analyses = persistence.find_historical_analysis(ticker=ticker)
    else:
        historical_analyses = []
        for ticker_analyses in persistence.event_index["events"].values():
            historical_analyses.extend(ticker_analyses)
    
    # Process historical analyses in batches
    total_historical = 0
    if historical_analyses:
        print(f"Processing {len(historical_analyses)} historical analyses in batches...")
        for i in range(0, len(historical_analyses), BATCH_SIZE):
            batch = historical_analyses[i:i+BATCH_SIZE]
            total_historical += process_analyses_batch(batch, export_data["historical_events"])
    
    # Get similar events analyses
    print("Finding similar events analyses...")
    if pattern:
        similar_analyses = persistence.find_similar_events_analysis(pattern=pattern)
    else:
        similar_analyses = []
        for pattern_analyses in persistence.event_index["similar_events"].values():
            similar_analyses.extend(pattern_analyses)
    
    # Process similar events analyses in batches
    total_similar = 0
    if similar_analyses:
        print(f"Processing {len(similar_analyses)} similar events analyses in batches...")
        for i in range(0, len(similar_analyses), BATCH_SIZE):
            batch = similar_analyses[i:i+BATCH_SIZE]
            total_similar += process_analyses_batch(batch, export_data["similar_events"])
    
    # Save to output file
    try:
        print(f"Writing {total_historical + total_similar} analyses to {output_file}...")
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"Exported {len(export_data['historical_events'])} historical event analyses and {len(export_data['similar_events'])} similar events analyses to {output_file}")
    except Exception as e:
        print(f"Error exporting analyses to {output_file}: {str(e)}")

def delete_analysis(file_path: str, skip_confirmation: bool = False) -> bool:
    """
    Delete a specific analysis
    
    Args:
        file_path: Path to the analysis file
        skip_confirmation: Whether to skip user confirmation (useful for scripts)
    """
    persistence = ap.AnalysisPersistence()
    
    if not os.path.exists(file_path):
        print(f"Analysis file not found: {file_path}")
        return False
    
    # Load the analysis first to find its metadata
    analysis = _load_analysis_with_cache(file_path)
    if not analysis:
        print(f"Error: Could not load analysis from {file_path}")
        return False
        
    # Extract important info for index updating
    analysis_type = ""
    key_identifier = ""
    
    if "ticker" in analysis and "event_date" in analysis:
        analysis_type = "events"
        key_identifier = analysis.get("ticker", "unknown")
        subkey = analysis.get("event_date", "unknown")
    elif "pattern_summary" in analysis:
        analysis_type = "similar_events"
        key_identifier = analysis.get("pattern_summary", "unknown_pattern")
        subkey = analysis.get("dominant_ticker", "unknown")
    else:
        print("Warning: Unknown analysis type - index may be out of sync after deletion.")
    
    # Confirm deletion if not skipped
    if not skip_confirmation:
        prompt = f"Are you sure you want to delete {os.path.basename(file_path)}"
        if analysis_type and key_identifier:
            prompt += f" ({analysis_type}: {key_identifier})"
        prompt += "? (y/n): "
        
        confirm = input(prompt)
        if confirm.lower() != 'y':
            print("Deletion cancelled.")
            return False
    
    try:
        # Delete the file
        os.remove(file_path)
        print(f"Deleted {file_path}")
        
        # Clear the cache entry 
        try:
            _load_analysis_with_cache.cache_clear()
            clear_statistics_cache()  # Clear statistics cache too
        except:
            pass
            
        # Offer to update the index automatically if not in script mode
        if analysis_type and key_identifier and not skip_confirmation:
            update_prompt = "Would you like to update the index now? (y/n): "
            if input(update_prompt).lower() == 'y':
                reindex()
            else:
                print("NOTE: The index may be out of sync. Run 'reindex' command to update the index.")
        else:
            print("NOTE: The index may be out of sync. Run 'reindex' command to update the index.")
            
        return True  # Return success status
    except Exception as e:
        print(f"Error deleting analysis: {str(e)}")
        return False  # Return failure status

def reindex() -> None:
    """Rebuild the analysis index from scratch by scanning the directory"""
    # Create a new persistence instance with a temporary index file
    temp_index_file = "temp_index.json"
    persistence = ap.AnalysisPersistence(index_file=temp_index_file)
    
    # Constants for batch processing
    BATCH_SIZE = 20  # Process 20 files at a time
    
    # Initialize empty index
    persistence.event_index = {
        "events": {},
        "similar_events": {},
        "last_updated": persistence._get_formatted_timestamp(),
        "query_history": []
    }
    
    # Base directory for path optimization
    base_dir = persistence.base_dir
    
    # Helper function to safely load and process a JSON file
    def process_analysis_file(file_path, analysis_type):
        try:
            # Use cached file loader instead of opening file directly
            analysis = _load_analysis_with_cache(file_path)
            if not analysis:
                return None
            
            # Validate the analysis based on type
            if analysis_type == "events":
                if not (analysis.get("success", False) and "ticker" in analysis and "event_date" in analysis):
                    return None
            elif analysis_type == "similar_events":
                if not (analysis.get("success", False) and "pattern_summary" in analysis):
                    return None
            
            # Add metadata if missing
            if "_metadata" not in analysis:
                analysis["_metadata"] = {
                    "saved_at": persistence._get_formatted_timestamp(),
                    "query": None,
                    "file_path": _get_optimized_path(base_dir, file_path)
                }
                
                # Save it back to ensure metadata is present
                with open(file_path, 'w') as f:
                    json.dump(analysis, f, indent=2)
            
            return analysis
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return None
    
    # Helper function to process a batch of files
    def process_file_batch(file_paths, analysis_type):
        """Process a batch of files and return successful analyses"""
        results = []
        for file_path in file_paths:
            analysis = process_analysis_file(file_path, analysis_type)
            if analysis:
                results.append((file_path, analysis))
        return results
    
    # Get directory paths
    events_dir = os.path.join(persistence.base_dir, "events")
    similar_dir = os.path.join(persistence.base_dir, "similar_events")
    
    print("Building analysis index...")
    total_processed = 0
    total_successful = 0
    
    # Collect all event files first
    print("Scanning events directory...")
    event_files = []
    if os.path.exists(events_dir):
        for filename in os.listdir(events_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(events_dir, filename)
                event_files.append(file_path)
    
    # Process events in batches
    if event_files:
        print(f"Processing {len(event_files)} historical event files in batches...")
        for i in range(0, len(event_files), BATCH_SIZE):
            batch = event_files[i:i+BATCH_SIZE]
            processed_files = process_file_batch(batch, "events")
            
            # Update index with processed analyses
            for file_path, analysis in processed_files:
                # Add to index
                ticker = analysis.get("ticker", "unknown")
                event_date = analysis.get("event_date", "unknown")
                
                if ticker not in persistence.event_index["events"]:
                    persistence.event_index["events"][ticker] = []
                
                # Store optimized path to reduce memory usage
                optimized_path = _get_optimized_path(base_dir, file_path)
                
                persistence.event_index["events"][ticker].append({
                    "event_date": event_date,
                    "price_change": analysis.get("price_change_pct", 0),
                    "trend": analysis.get("trend", "Unknown"),
                    "file_path": optimized_path,
                    "saved_at": analysis["_metadata"]["saved_at"]
                })
                
                # Add to query history if query is available
                if analysis["_metadata"].get("query"):
                    query_entry = {
                        "query": analysis["_metadata"]["query"],
                        "timestamp": analysis["_metadata"]["saved_at"],
                        "result_type": "historical_event",
                        "ticker": ticker,
                        "event_date": event_date,
                        "file_path": optimized_path
                    }
                    persistence.event_index["query_history"].append(query_entry)
            
            total_processed += len(batch)
            total_successful += len(processed_files)
            print(f"Progress: {total_processed}/{len(event_files)} files processed, {total_successful} successful")
    
    # Collect all similar event files
    print("\nScanning similar events directory...")
    similar_files = []
    if os.path.exists(similar_dir):
        for filename in os.listdir(similar_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(similar_dir, filename)
                similar_files.append(file_path)
    
    # Process similar events in batches
    similar_successful = 0
    if similar_files:
        print(f"Processing {len(similar_files)} similar event files in batches...")
        for i in range(0, len(similar_files), BATCH_SIZE):
            batch = similar_files[i:i+BATCH_SIZE]
            processed_files = process_file_batch(batch, "similar_events")
            
            # Update index with processed analyses
            for file_path, analysis in processed_files:
                # Add to index
                pattern = analysis.get("pattern_summary", "unknown_pattern")
                ticker = analysis.get("dominant_ticker", "unknown")
                
                if pattern not in persistence.event_index["similar_events"]:
                    persistence.event_index["similar_events"][pattern] = []
                
                # Store optimized path to reduce memory usage
                optimized_path = _get_optimized_path(base_dir, file_path)
                
                persistence.event_index["similar_events"][pattern].append({
                    "dominant_ticker": ticker,
                    "avg_price_change": analysis.get("avg_price_change", 0),
                    "consistency_score": analysis.get("consistency_score", 0),
                    "file_path": optimized_path,
                    "saved_at": analysis["_metadata"]["saved_at"]
                })
                
                # Add to query history if query is available
                if analysis["_metadata"].get("query"):
                    query_entry = {
                        "query": analysis["_metadata"]["query"],
                        "timestamp": analysis["_metadata"]["saved_at"],
                        "result_type": "similar_events",
                        "pattern": pattern,
                        "dominant_ticker": ticker,
                        "file_path": optimized_path
                    }
                    persistence.event_index["query_history"].append(query_entry)
            
            total_processed += len(batch)
            similar_successful += len(processed_files)
            print(f"Progress: {total_processed}/{len(event_files) + len(similar_files)} files processed, {similar_successful} successful")
    
    # Sort query history by timestamp (only once at the end)
    print("Sorting query history...")
    persistence.event_index["query_history"].sort(key=lambda x: x.get("timestamp", ""))
    
    # Save the index
    print("Saving index...")
    persistence._save_index()
    
    # Replace the real index file with the temporary one
    real_index_path = os.path.join(persistence.base_dir, ap.DEFAULT_INDEX_FILE)
    temp_index_path = os.path.join(persistence.base_dir, temp_index_file)
    
    if os.path.exists(real_index_path):
        os.replace(temp_index_path, real_index_path)
        print(f"Replaced existing index file: {real_index_path}")
    else:
        os.rename(temp_index_path, real_index_path)
        print(f"Created new index file: {real_index_path}")
    
    # Clear caches to ensure fresh data
    try:
        _load_analysis_with_cache.cache_clear()
        clear_statistics_cache()  # Clear the statistics cache too
        print("Cache cleared")
    except:
        pass
    
    # Print statistics
    stats = persistence.get_statistics()
    print(f"\nReindexing completed successfully!")
    print(f"Processed files: {total_processed}, Successfully indexed: {total_successful + similar_successful}")
    print(f"Reindexed {stats.get('total_historical_events', 0)} historical event analyses and {stats.get('total_similar_events', 0)} similar events analyses.")
    print(f"Total queries in history: {stats.get('total_queries', 0)}")

def _get_optimized_path(base_dir, file_path):
    """
    Convert absolute file paths to relative paths where possible to reduce memory usage
    
    Args:
        base_dir: Base directory path
        file_path: Full file path
        
    Returns:
        str: Optimized path (relative if possible, otherwise unchanged)
    """
    try:
        # If the path starts with the base dir, make it relative
        if file_path.startswith(base_dir):
            return os.path.relpath(file_path, base_dir)
        return file_path
    except:
        # In case of any issues, return the original path
        return file_path
        
def cleanup_temp_files(verbose: bool = False) -> None:
    """
    Clean up temporary files that might be left over from incomplete operations
    
    Args:
        verbose: Whether to print detailed information about cleaned files
    """
    persistence = ap.AnalysisPersistence()
    base_dir = persistence.base_dir
    
    # List of temporary file patterns to look for
    temp_patterns = [
        "temp_index.json",
        "temp_*.json",
        "*.tmp"
    ]
    
    cleaned_files = 0
    
    # Helper function to clean files matching a pattern in a directory
    def clean_matching_files(directory):
        nonlocal cleaned_files
        for pattern in temp_patterns:
            pattern_path = os.path.join(directory, pattern)
            for temp_file in glob.glob(pattern_path):
                if os.path.isfile(temp_file):
                    try:
                        os.remove(temp_file)
                        cleaned_files += 1
                        if verbose:
                            print(f"Removed temporary file: {temp_file}")
                    except Exception as e:
                        if verbose:
                            print(f"Error removing {temp_file}: {str(e)}")
    
    # Clean main directory
    clean_matching_files(base_dir)
    
    # Clean subdirectories
    for subdir in ["events", "similar_events", "queries"]:
        subdir_path = os.path.join(base_dir, subdir)
        if os.path.exists(subdir_path) and os.path.isdir(subdir_path):
            clean_matching_files(subdir_path)
    
    # Print summary
    if cleaned_files > 0:
        print(f"Cleaned up {cleaned_files} temporary files")
    elif verbose:
        print("No temporary files found to clean up")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="View and manage saved analyses")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List saved analyses")
    list_parser.add_argument("--ticker", "-t", help="Filter by ticker symbol")
    list_parser.add_argument("--pattern", "-p", help="Filter by pattern")
    list_parser.add_argument("--days", "-d", type=int, default=30, help="Number of recent days to include")
    list_parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum number of analyses to show")
    list_parser.add_argument("--detailed", action="store_true", help="Show detailed information")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show a specific analysis")
    show_parser.add_argument("file_path", help="Path to the analysis file")
    show_parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show query history")
    history_parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum number of queries to show")
    history_parser.add_argument("--search", "-s", help="Search term to filter by")
    history_parser.add_argument("--export", "-e", help="Export query history to a file")
    
    # Stats command
    subparsers.add_parser("stats", help="Show statistics about saved analyses")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export analyses to a file")
    export_parser.add_argument("output_file", help="Path to the output file")
    export_parser.add_argument("--ticker", "-t", help="Filter by ticker symbol")
    export_parser.add_argument("--pattern", "-p", help="Filter by pattern")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a specific analysis")
    delete_parser.add_argument("file_path", help="Path to the analysis file")
    delete_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation (useful for scripts)")
    
    # Reindex command
    subparsers.add_parser("reindex", help="Rebuild the analysis index")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up temporary files")
    cleanup_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information about cleanup")
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    # Execute the appropriate command
    if args.command == "list":
        list_analyses(ticker=args.ticker, days=args.days, pattern=args.pattern, 
                     limit=args.limit, detailed=args.detailed)
    elif args.command == "show":
        show_analysis(file_path=args.file_path, format=args.format)
    elif args.command == "history":
        show_query_history(limit=args.limit, search=args.search, export_file=args.export)
    elif args.command == "stats":
        show_statistics()
    elif args.command == "export":
        export_analyses(output_file=args.output_file, ticker=args.ticker, pattern=args.pattern)
    elif args.command == "delete":
        delete_analysis(file_path=args.file_path, skip_confirmation=args.force)
    elif args.command == "reindex":
        reindex()
    elif args.command == "cleanup":
        cleanup_temp_files(verbose=args.verbose)
    else:
        # No command or unrecognized command
        print("Please specify a command. Use --help for more information.")
        sys.exit(1)

if __name__ == "__main__":
    main() 