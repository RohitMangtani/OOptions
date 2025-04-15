# Ooptions - Market Event Analysis Streamlit App

This Streamlit application provides a user-friendly interface for the Ooptions Market Event Analysis system. It allows you to analyze historical market events, understand market reactions, and identify patterns across similar events.

## Features

- Interactive chat interface to query about market events
- **Contextual conversation** that maintains the full context of previous exchanges
- Intelligent follow-up suggestions for deeper analysis
- Persistent conversation history
- Reset button to start a new conversation
- Sample queries to help you get started
- Error handling and feedback

## Conversation Context

The app maintains the full context of your conversation, allowing for natural follow-up questions without repeating information:

- Start by asking about a market event ("What happened when Bitcoin ETF was approved?")
- Then ask follow-up questions ("Why did it react that way?" or "How does this compare to similar events?")
- The system remembers previous queries and data, building a connected conversation
- Follow-up questions are automatically identified and processed with context

## Installation Requirements

Make sure you have all the required dependencies installed:

```bash
pip install streamlit pandas openai numpy matplotlib yfinance fredapi requests
```

## Running the App

To run the Streamlit app, use the following command from the root directory of the project:

```bash
streamlit run streamlit_app.py
```

The app will start and automatically open in your default web browser. If it doesn't, you can access it at `http://localhost:8501`.

## Using the App

1. **Ask Initial Question**: Type your query about market events in the chat input at the bottom of the page.

2. **Ask Follow-Up Questions**: After receiving a response, you can ask follow-up questions that build on the previous context. The app will suggest types of follow-up questions you can ask.

3. **Sample Queries**: Click on any of the sample queries in the sidebar to quickly try out the system.

4. **Reset Conversation**: Use the "Reset Conversation" button in the sidebar to start a fresh conversation if needed.

5. **View History**: Your conversation history is displayed in the main area of the app, maintaining the full context.

## Example Conversations

Start with an initial question:
- "What happened when Bitcoin ETF was approved?"

Then continue with follow-ups:
- "How does this compare to similar crypto events?"
- "What was the macro environment at the time?"
- "Why did it have this specific impact?"

Or start with:
- "How did the market react to the Fed raising interest rates last year?"

And follow up with:
- "How long did it take to recover?"
- "What sectors were most affected?"
- "What does this suggest for future rate hikes?"

## Troubleshooting

- If you encounter any errors, check the error message displayed at the top of the page.
- Try resetting the conversation using the "Reset Conversation" button.
- Ensure you have a valid OpenAI API key set in your environment.
- Check your internet connection as the app requires access to external data sources.

## API Keys and Configuration

The app requires the following environment variables to be set:

- `OPENAI_API_KEY`: Your OpenAI API key for processing natural language queries
- `FRED_API_KEY`: FRED API key for accessing macroeconomic data (optional)

You can set these in a `.env` file in the project root directory. 