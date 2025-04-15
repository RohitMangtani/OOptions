# Ooptions - Financial News and Market Event Analysis Platform

A comprehensive system for analyzing financial news headlines, classifying market events, matching them to historical patterns, generating trading recommendations based on macro data and event analysis, and evaluating trade performance.

## Features

- **Real-time Financial News Feed**: Automatically fetches and displays the latest financial news from multiple sources
- **AI-powered Event Classification**: Uses GPT models to classify market events by type, sentiment, and sector
- **Trade Alerts**: Monitors news for potential trading opportunities and provides automated alerts
- **Historical Event Analysis**: Compares current events with similar historical scenarios to identify patterns
- **Macro Environment Context**: Incorporates current macroeconomic data into analysis
- **Trade Recommendations**: Generates specific trade ideas based on comprehensive analysis
- **Streamlit Interface**: User-friendly web interface with multiple tabs for different functions

## Demo Screenshot

![Ooptions Platform](https://example.com/screenshot.png) *(Replace with actual screenshot URL)*

## Setup Instructions

### Prerequisites
- Python 3.9+
- OpenAI API key
- FRED API key (optional for enhanced macroeconomic data)

### Installation

1. Clone this repository
```bash
git clone https://github.com/RohitMangtani/ooptions.git
cd ooptions
```

2. Create a virtual environment
```bash
python -m venv .venv
```

3. Activate the environment
- Windows: `.venv\Scripts\activate`
- Unix/Mac: `source .venv/bin/activate`

4. Install dependencies
```bash
pip install -r requirements.txt
```

5. Set up environment variables
Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key_here
FRED_API_KEY=your_fred_key_here
```

### Running the Application

Run the Streamlit application:
```bash
streamlit run streamlit_app.py
```

The application will be available at http://localhost:8501

## Project Structure

- `streamlit_app.py`: Main Streamlit application
- `llm_event_query.py`: Core logic for processing market event queries
- `llm_event_classifier.py`: AI model for classifying financial headlines
- `rss_ingestor.py`: Fetches news from various financial sources
- `macro_data_collector.py`: Retrieves and processes macroeconomic indicators
- `historical_matcher.py`: Matches current events with historical patterns
- `trade_picker.py`: Generates trade recommendations
- Additional support modules for persistence, analysis, and evaluation

## Usage Examples

- View real-time financial news in the News Feed tab
- Monitor AI-generated trade alerts in the Trade Alerts tab
- Ask questions like "What happened when Bitcoin ETF was approved?" in the Search tab

## License

MIT

## Acknowledgements

- Built with [Streamlit](https://streamlit.io/)
- Financial data provided by [yfinance](https://pypi.org/project/yfinance/)
- Macroeconomic data from [FRED](https://fred.stlouisfed.org/)
- AI capabilities powered by [OpenAI](https://openai.com/) 