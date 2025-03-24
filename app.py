import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from typing import Dict, Any
from datetime import datetime
from gtts import gTTS
import logging
from utils.news_scraper import NewsScraper
from utils.gemini_service import GeminiService
from dotenv import load_dotenv
from utils.text_to_speech import TextToSpeechService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API base URL - change this when deploying to Hugging Face Spaces
API_BASE_URL = "http://localhost:8000"  # Local development
# API_BASE_URL = "https://yourusername-news-sentiment-app.hf.space/api"  # HF Spaces

# Set page configuration
st.set_page_config(
    page_title="Company News Sentiment Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
    }
    .sentiment-positive {
        color: #198754;
        font-weight: 600;
    }
    .sentiment-negative {
        color: #dc3545;
        font-weight: 600;
    }
    .sentiment-neutral {
        color: #6c757d;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Ensure temp/audio directory exists
os.makedirs(os.path.join("temp", "audio"), exist_ok=True)

def fetch_companies():
    """Fetch list of available companies from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/companies")
        if response.status_code == 200:
            return response.json().get("companies", [])
        else:
            st.error(f"Error fetching companies: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []

def fetch_company_analysis(company_name):
    """Fetch analysis data for a specific company."""
    try:
        response = requests.get(f"{API_BASE_URL}/company/{company_name}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching analysis: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return None

def generate_tts_audio_locally(company_name: str, company_data: Dict[str, Any], tts_service: TextToSpeechService) -> Dict[str, Any]:
    """
    Fetch pre-generated TTS audio and Hindi text from the output/audio folder.
    
    Args:
        company_name: Name of the company
        company_data: Analysis data for the company
        tts_service: Instance of TextToSpeechService (not used here, but kept for compatibility)
        
    Returns:
        Dictionary with audio_path and hindi_text
    """
    try:
        # Define file paths
        company_slug = company_name.lower().replace(' ', '_')
        audio_path = os.path.join("data", "output", "audio", f"{company_slug}.mp3")
        text_path = os.path.join("data", "output", "text", f"{company_slug}_hindi.txt")

        # Check if audio file exists
        if not os.path.exists(audio_path):
            st.error(f"Audio file not found for {company_name}.")
            return None

        # Read Hindi text
        hindi_text = ""
        if os.path.exists(text_path):
            with open(text_path, 'r', encoding='utf-8') as f:
                hindi_text = f.read()

        return {
            "audio_path": audio_path,
            "hindi_text": hindi_text
        }
    except Exception as e:
        st.error(f"Error fetching TTS audio: {str(e)}")
        return None

def display_coverage_differences(coverage_diffs):
    """Display coverage differences in a more structured way."""
    if not coverage_diffs:
        st.info("No comparative analysis available.")
        return
    
    for i, diff in enumerate(coverage_diffs):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"#### Comparison {i+1}")
        with col2:
            st.markdown(f"**Key Difference:** {diff.get('Comparison', '')}")
            st.markdown(f"**Market Impact:** {diff.get('Impact', '')}")
        st.markdown("---")
        
def query_data(company_name, query):
    """Send a natural language query about the company data."""
    try:
        # Fetch the analysis data
        company_data = fetch_company_analysis(company_name)
        if not company_data:
            return "No analysis data available for this company."
        
        # Initialize GeminiService with API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        gemini_service = GeminiService(api_key=api_key)
        
        # Call the generate_query_response method
        response = gemini_service.generate_query_response(company_name, company_data, query)
        return response
    except Exception as e:
        st.error(f"Error processing query: {str(e)}")
        return f"Failed to process query. Error: {str(e)}"

def render_sentiment_distribution(sentiment_dist):
    """Render a pie chart of sentiment distribution."""
    if not sentiment_dist:
        return
    
    labels = list(sentiment_dist.keys())
    values = list(sentiment_dist.values())
    
    colors = {'Positive': '#198754', 'Negative': '#dc3545', 'Neutral': '#6c757d'}
    
    fig = px.pie(
        names=labels,
        values=values,
        color=labels,
        color_discrete_map=colors,
        title="Sentiment Distribution"
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)

def render_topic_heatmap(articles):
    """Render an improved heatmap of topics across articles."""
    if not articles:
        return
    
    # Extract all topics from all articles
    all_topics = set()
    for article in articles:
        if "Topics" in article and article["Topics"]:
            all_topics.update(article["Topics"])
    
    all_topics = sorted(list(all_topics))  # Sort for consistency
    
    if not all_topics:
        st.write("No topics found in articles.")
        return
    
    # Create matrix of topic presence with better visual cues
    data = []
    for i, article in enumerate(articles):
        article_topics = article.get("Topics", [])
        row = {"Article": f"Article {i+1}"}
        
        # Use article title as hover text
        title = article.get('Title', 'No Title')
        row["Title"] = title[:50] + "..." if len(title) > 50 else title
        
        # Add sentiment for color coding
        row["Sentiment"] = article.get("Sentiment", "Neutral")
        
        # Track topic presence
        for topic in all_topics:
            row[topic] = 1 if topic in article_topics else 0
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Create a better visualization using a grouped bar chart instead of heatmap
    topic_counts = {topic: sum(df[topic]) for topic in all_topics}
    sorted_topics = sorted(all_topics, key=lambda x: topic_counts[x], reverse=True)
    
    # Create a simplified bar chart of topic frequency
    topic_df = pd.DataFrame([{"Topic": t, "Count": topic_counts[t]} for t in sorted_topics])
    
    fig = px.bar(
        topic_df, 
        x="Topic", 
        y="Count",
        title="Topic Frequency Across Articles",
        color="Count",
        color_continuous_scale=px.colors.sequential.Blues
    )
    
    fig.update_layout(
        xaxis_title="Topic",
        yaxis_title="Number of Articles",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Also show the relationship between topics and articles
    st.markdown("### Topic Distribution by Article")
    
    # Create a more readable version of the topic matrix
    matrix_data = []
    for i, article in enumerate(articles):
        article_topics = article.get("Topics", [])
        sentiment = article.get("Sentiment", "Neutral")
        
        # Create a cleaner display format
        matrix_data.append({
            "Article": f"Article {i+1}",
            "Title": article.get('Title', 'No Title')[:40] + "..." if len(article.get('Title', 'No Title')) > 40 else article.get('Title', 'No Title'),
            "Sentiment": sentiment,
            "Topics": ", ".join(article_topics) if article_topics else "None"
        })
    
    # Display as a formatted table
    topic_matrix_df = pd.DataFrame(matrix_data)
    
    # Apply conditional formatting based on sentiment
    def highlight_sentiment(val):
        color_map = {
            'Positive': 'background-color: rgba(25, 135, 84, 0.2)',
            'Negative': 'background-color: rgba(220, 53, 69, 0.2)',
            'Neutral': 'background-color: rgba(108, 117, 125, 0.2)'
        }
        return color_map.get(val, '')
    
    styled_df = topic_matrix_df.style.map(
        highlight_sentiment, 
        subset=['Sentiment']
    )
    
    st.dataframe(styled_df, use_container_width=True)

def display_articles(articles, company_name=None):
    """Display article summaries and details."""
    for i, article in enumerate(articles):
        title = article.get('Title', 'No Title')
        # Replace the placeholder if it exists in the title
        if company_name:
            title = title.replace("{Company}", company_name)
        
        # Use the modified title in the expander header
        with st.expander(f"Article {i+1}: {title}"):
            sentiment = article.get("Sentiment", "Unknown")
            sentiment_class = f"sentiment-{sentiment.lower()}" if sentiment in ["Positive", "Negative", "Neutral"] else ""
            
            st.markdown(f"**Sentiment:** <span class='{sentiment_class}'>{sentiment}</span>", unsafe_allow_html=True)
            st.markdown(f"**Summary:**\n{article.get('Summary', 'No summary available')}")
            
            if "Topics" in article and article["Topics"]:
                st.markdown("**Topics:**")
                st.write(", ".join(article["Topics"]))

def display_detailed_analysis_report(company_data):
    """Display a detailed analysis report for cookie points."""
    st.markdown("## 📊 Detailed Analysis Report")
    
    # Get articles and extract data
    articles = company_data.get("Articles", [])
    if not articles:
        st.warning("No article data available for detailed analysis.")
        return
    
    # Prepare data
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    topics_by_sentiment = {}
    topic_counts = {}
    
    for article in articles:
        sentiment = article.get("Sentiment", "Neutral")
        sentiment_counts[sentiment] += 1
        
        for topic in article.get("Topics", []):
            if topic not in topics_by_sentiment:
                topics_by_sentiment[topic] = {"Positive": 0, "Negative": 0, "Neutral": 0}
                topic_counts[topic] = 0
            
            topics_by_sentiment[topic][sentiment] += 1
            topic_counts[topic] += 1
    
    # Create two columns for visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Simple sentiment overview
        st.markdown("### 📊 Sentiment Distribution")
        data = [{"Sentiment": k, "Count": v} for k, v in sentiment_counts.items() if v > 0]
        if data:
            chart_df = pd.DataFrame(data)
            
            colors = {"Positive": "#198754", "Negative": "#dc3545", "Neutral": "#6c757d"}
            fig = px.bar(
                chart_df,
                x="Sentiment",
                y="Count",
                color="Sentiment",
                color_discrete_map=colors,
                title="Article Sentiment Counts"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top topics
        st.markdown("### 🔝 Top Topics")
        
        if topic_counts:
            # Sort by frequency
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            top5_topics = sorted_topics[:5]
            
            topic_data = [{"Topic": k, "Count": v} for k, v in top5_topics]
            topic_df = pd.DataFrame(topic_data)
            
            fig = px.bar(
                topic_df,
                x="Topic",
                y="Count",
                title="Most Frequent Topics",
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Topic-Sentiment relationship
    st.markdown("### 🔍 Topic-Sentiment Relationship")
    
    if topics_by_sentiment:
        # Prepare data for visualization
        topic_sentiment_data = []
        
        for topic, sentiments in topics_by_sentiment.items():
            total = sum(sentiments.values())
            if total > 0:  # Avoid division by zero
                topic_sentiment_data.append({
                    "Topic": topic,
                    "Positive Ratio": (sentiments["Positive"] / total) * 100,
                    "Negative Ratio": (sentiments["Negative"] / total) * 100,
                    "Neutral Ratio": (sentiments["Neutral"] / total) * 100,
                    "Total Articles": total
                })
        
        # Sort by total articles
        topic_sentiment_data.sort(key=lambda x: x["Total Articles"], reverse=True)
        
        # Take top 8 topics for readability
        top_topics = topic_sentiment_data[:8]
        
        if top_topics:
            # Create a stacked bar chart
            df = pd.DataFrame(top_topics)
            
            fig = px.bar(
                df,
                x="Topic",
                y=["Positive Ratio", "Neutral Ratio", "Negative Ratio"],
                title="Sentiment Distribution by Top Topics",
                labels={"value": "Percentage", "variable": "Sentiment"},
                color_discrete_map={
                    "Positive Ratio": "#198754", 
                    "Negative Ratio": "#dc3545", 
                    "Neutral Ratio": "#6c757d"
                }
            )
            
            fig.update_layout(legend_title_text="Sentiment")
            st.plotly_chart(fig, use_container_width=True)
            
            # Create a simple summary
            st.markdown("### Key Insights")
            
            # Find the most positive and negative topics
            most_positive = max(topic_sentiment_data, key=lambda x: x["Positive Ratio"])
            most_negative = max(topic_sentiment_data, key=lambda x: x["Negative Ratio"])
            
            st.markdown(f"""
            - Most positive coverage is about **{most_positive['Topic']}** ({most_positive['Positive Ratio']:.1f}% positive)
            - Most negative coverage is about **{most_negative['Topic']}** ({most_negative['Negative Ratio']:.1f}% negative)
            - Top trending topic is **{top_topics[0]['Topic']}** (mentioned in {top_topics[0]['Total Articles']} articles)
            """)

def main():
    # Header with clean styling
    st.markdown("<div class='main-header'>📊 Company News Sentiment Analyzer</div>", unsafe_allow_html=True)
    st.markdown("Analyze sentiment and topics from recent news articles about companies")

    # Sidebar for controls
    st.sidebar.header("Settings")
    
    # Add API key input with info about .env usage
    api_key = st.sidebar.text_input(
        "Gemini API Key", 
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password", 
        help="Enter your Gemini API key (or set GEMINI_API_KEY in .env file)"
    )
    
    # If API key is provided in the UI, use it temporarily
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    # Initialize GeminiService if API key is available
    gemini_service = None
    if os.getenv("GEMINI_API_KEY"):
        gemini_service = GeminiService(api_key=os.getenv("GEMINI_API_KEY"))
    else:
        st.error("Gemini API key is missing. Please provide a valid API key.")
        return
    
    # Initialize TextToSpeechService with Gemini as the primary translator
    if gemini_service:
        tts_service = TextToSpeechService(gemini_service=gemini_service)
    else:
        st.error("Gemini API key is missing. Please provide a valid API key.")
        return
    
    # Fetch companies
    companies = fetch_companies()
    
    if not companies:
        st.warning("No company data available. Please run the batch processor first.")
        
        if st.sidebar.button("Simulate Demo Data"):
            st.info("Creating simulated data... This would prepare test data in a real implementation.")
    else:
        # Company selection
        selected_company = st.sidebar.selectbox("Select Company", companies)
        
        # Refresh option
        if st.sidebar.button("Refresh Data"):
            st.sidebar.info("Triggering data refresh...")
        
        # Main content area
        if selected_company:
            # Fetch company data
            company_data = fetch_company_analysis(selected_company)
            
            if company_data:
                # Display company name and last updated
                st.markdown(f"## Analysis for {selected_company}")
                
                try:
                    file_path = os.path.join("data", "output", f"{selected_company.lower().replace(' ', '_')}.pkl")
                    last_updated = datetime.fromtimestamp(os.path.getmtime(file_path))
                    st.caption(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M')}")
                except:
                    pass
                
                # Final sentiment in a card
                final_sentiment = company_data.get("Final_Sentiment_Analysis", "No analysis available")
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("### Overall Sentiment Analysis")
                st.write(final_sentiment)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # TTS Audio section
                st.markdown("### 🔊 Hindi Audio Summary")
                tts_data = generate_tts_audio_locally(selected_company, company_data, tts_service)
                if tts_data and "audio_path" in tts_data:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.audio(tts_data["audio_path"])
                    with col2:
                        if "hindi_text" in tts_data:
                            st.caption("Hindi Text:")
                            st.write(tts_data["hindi_text"])
                
                # Create three columns for key metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Count of articles
                    articles = company_data.get("Articles", [])
                    st.metric("Articles Analyzed", len(articles))
                
                with col2:
                    # Sentiment distribution
                    sentiment_dist = company_data.get("Comparative_Sentiment_Score", {}).get("Sentiment Distribution", {})
                    pos_count = sentiment_dist.get("Positive", 0)
                    neg_count = sentiment_dist.get("Negative", 0)
                    
                    sentiment_ratio = f"{pos_count}:{neg_count}"
                    st.metric("Positive:Negative Ratio", sentiment_ratio)
                
                with col3:
                    # Topic count
                    topics = set()
                    for article in articles:
                        topics.update(article.get("Topics", []))
                    
                    st.metric("Unique Topics", len(topics))
                
                # Sentiment tab and topic tab
                tab1, tab2, tab3 = st.tabs(["📊 Sentiment Analysis", "🔍 Topic Analysis", "📑 Article Details"])
                
                with tab1:
                    # Sentiment visualization
                    if sentiment_dist:
                        render_sentiment_distribution(sentiment_dist)
                    
                    # Coverage differences
                    st.markdown("### Coverage Differences")
                    coverage_diffs = company_data.get("Comparative_Sentiment_Score", {}).get("Coverage_Differences", [])
                    display_coverage_differences(coverage_diffs)
                                    
                with tab2:
                    # Topic visualizations
                    render_topic_heatmap(articles)
                
                with tab3:
                    # Article details in an organized format
                    st.markdown("### Article Summaries")
                    display_articles(articles, selected_company)
                
                # Query system in an expander
                with st.expander("🔎 Ask Questions About This Data", expanded=False):
                    enhanced_query_system(selected_company, gemini_service)
                
                # Detailed analysis at the bottom
                display_detailed_analysis_report(company_data)

def enhanced_query_system(company_name, gemini_service):
    """An enhanced querying system for the bonus cookie points."""
    st.markdown("Ask detailed questions about the news sentiment data:")
    
    # Example queries
    example_queries = [
        "What are the most common positive topics?",
        "Which article has the most negative sentiment?",
        "Are there any contradictory reports about the company?",
        "What recommendations can be made based on the sentiment analysis?"
    ]
    
    # Let user select or write query
    query_type = st.radio("Query Type", ["Choose from examples", "Write your own"], horizontal=True)
    
    if query_type == "Choose from examples":
        query = st.selectbox("Select a question", example_queries)
    else:
        query = st.text_area("Your question", height=100,
                            placeholder="Example: What is the relationship between topics and sentiment?")
    
    # Process query when button is clicked
    if query and st.button("Submit Query"):
        with st.spinner("Processing your query..."):
            # Fetch the analysis data
            company_data = fetch_company_analysis(company_name)
            
            if not company_data:
                st.error("No data available for this company.")
                return
            
            # Generate response
            if gemini_service:
                response = gemini_service.generate_query_response(company_name, company_data, query)
            else:
                st.warning("Using fallback mode. For better analysis, please provide a valid Gemini API key.")
                response = "I can't perform detailed analysis in fallback mode. Please provide a valid Gemini API key."
            
            st.markdown("### Analysis")
            st.markdown(response)

if __name__ == "__main__":
    main()