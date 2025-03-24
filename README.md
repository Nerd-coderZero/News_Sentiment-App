# Company News Sentiment Analyzer

A web-based application that extracts news articles about companies, performs sentiment analysis, and generates text-to-speech output in Hindi.

## Features

- **News Extraction**: Scrapes 10 unique news articles related to a specified company using BeautifulSoup.
- **Sentiment Analysis**: Analyzes article sentiment (positive, negative, neutral) using Google's Gemini model.
- **Comparative Analysis**: Compares sentiment and topics across multiple articles.
- **Text-to-Speech**: Converts the summarized content into Hindi speech.
- **Interactive UI**: Provides a Streamlit-based interface for exploring the analysis.
- **API Integration**: Communication between frontend and backend via FastAPI endpoints.
- **Querying System**: Natural language query capabilities for the analysis data.

## Project Structure

```
news-sentiment-app/
├── app.py                  # Main Streamlit application
├── api.py                  # API endpoints with FastAPI
├── cron.py                 # Batch processor for companies
├── data/
│   ├── company_list.csv    # List of companies to analyze
│   └── output/             # Processed data files
├── utils/
│   ├── __init__.py         # Makes utils a package
│   ├── news_scraper.py     # News scraping functionality
│   ├── text_to_speech.py   # TTS and Hindi translation
│   └── gemini_service.py   # LLM for analysis
├── requirements.txt
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Google Gemini API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/news-sentiment-app.git
   cd news-sentiment-app
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. Create the company list:
   Create a CSV file at `data/company_list.csv` with a column named 'company' listing the companies you want to analyze.

### Running the Application

1. Run the batch processor to fetch and analyze news:
   ```
   python cron.py
   ```

2. Start the API server:
   ```
   python api.py
   ```

3. In a new terminal, run the Streamlit UI:
   ```
   streamlit run app.py
   ```

4. Access the application in your browser at `http://localhost:8501`

## API Endpoints

The application provides the following API endpoints:

- `GET /companies`: List all available companies
- `GET /company/{company_name}`: Get analysis data for a specific company
- `GET /company/{company_name}/tts`: Generate Hindi TTS for the company's sentiment analysis
- `POST /company/query`: Query the company data with natural language

## Querying System

The application includes a natural language querying system that allows users to ask questions about the analysis data. Examples:

- "What are the most common positive topics for this company?"
- "Is the overall sentiment more positive or negative?"
- "Which articles mention regulatory challenges?"
- "What are the key differences between the positive and negative articles?"

## Model Details

- **Summarization & Analysis**: Uses Google's Gemini model for summarization, sentiment analysis, topic extraction, and comparative analysis.
- **Text-to-Speech**: Uses Google Text-to-Speech (gTTS) API for generating Hindi audio.
- **Translation**: Uses Google Translate API for English to Hindi translation.

## Deployment

The application can be deployed on Hugging Face Spaces:

1. Create a new Space on Hugging Face Spaces
2. Connect your GitHub repository
3. Set up the necessary secrets (GEMINI_API_KEY)
4. Configure the Space to install dependencies and run the application

## Assumptions & Limitations

- The application assumes that news articles can be accessed and scraped without JavaScript rendering.
- API rate limits may affect the number of companies that can be processed in a short period.
- Translation quality depends on the Google Translate API.
- The application is designed for English news articles that are translated to Hindi for TTS.

## Future Improvements

- Add support for more languages
- Implement caching to reduce API calls
- Add user authentication
- Include historical sentiment tracking
- Support for JavaScript-rendered websites using tools like Selenium