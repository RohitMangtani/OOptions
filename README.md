# Ooptions - Financial News and Market Event Analysis System

A comprehensive financial analysis platform that combines natural language processing, real-time market data, and economic indicators to generate actionable trading insights.

## Features

- **News Analysis**: Automatically ingest and classify financial headlines from multiple sources
- **Event Classification**: Identify event types, sentiment, and market impact using NLP
- **Historical Pattern Matching**: Compare current events to similar historical scenarios
- **Macro Context Integration**: Incorporate economic indicators into analysis
- **Trade Recommendation**: Generate option trade ideas based on comprehensive analysis
- **Performance Tracking**: Monitor and evaluate trade performance

## Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- FRED API key (for economic data)
- Internet connection for real-time data

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/Ooptions.git
   cd Ooptions
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up API keys:
   - Create a `.env` file with your API keys:
     ```
     OPENAI_API_KEY=your_openai_key_here
     FRED_API_KEY=your_fred_key_here
     ```
   - For Streamlit Cloud deployment, add these to your Streamlit secrets

4. Run the application:
   ```
   streamlit run streamlit_app.py
   ```

## Usage

### Web Interface

The Streamlit app provides a user-friendly interface with:

- **Command Interface**: Submit natural language queries about market events
- **News Terminal**: Browse real-time financial headlines
- **Analysis History**: Review previous analyses and recommendations
- **Trade Tracker**: Monitor performance of recommended trades

### Command Line Interface

For advanced users, the command line interface offers:

```
python llm_event_query.py "query text"  # Process a specific query
python view_trades.py view              # View saved trade recommendations
python view_analysis.py list            # List saved analyses
```

## Architecture

The system consists of several integrated components:

1. **Data Collection**:
   - RSS feed ingestion for financial news
   - Economic data collection via FRED API
   - Market data via Yahoo Finance

2. **Analysis Engine**:
   - LLM-based event classification
   - Historical pattern matching
   - Sentiment analysis
   - Macro data integration

3. **Recommendation Engine**:
   - Option trade generation based on analysis
   - Risk assessment and position sizing

4. **Persistence Layer**:
   - Trade history tracking
   - Analysis storage and retrieval
   - Performance evaluation

## Deployment

This application is designed for both local use and Streamlit Cloud deployment:

1. **Local Development**:
   - Run `streamlit run streamlit_app.py` after setting up the environment

2. **Streamlit Cloud**:
   - Connect your GitHub repository to Streamlit Cloud
   - Add your API keys to Streamlit secrets
   - Deploy directly from the repository

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with OpenAI's GPT models for natural language processing
- Economic data provided by Federal Reserve Economic Data (FRED)
- Market data courtesy of Yahoo Finance API 