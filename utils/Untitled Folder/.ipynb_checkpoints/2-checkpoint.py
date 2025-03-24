import json
import os
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.gemini_service import GeminiService
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_sentiment_analysis():
    """Test the sentiment analysis on fake articles with clear sentiment signals"""
    try:
        # Initialize the Gemini service
        gemini_service = GeminiService()
        logger.info("GeminiService initialized successfully")
        
        # Create directory for results
        os.makedirs("data/test_results", exist_ok=True)
        
        # Load test articles
        test_articles_dir = "data/test_articles"
        results = []
        
        if not os.path.exists(test_articles_dir):
            logger.error(f"Test articles directory not found: {test_articles_dir}")
            return
        
        # Process each test article
        for filename in os.listdir(test_articles_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(test_articles_dir, filename)
                
                with open(file_path, "r") as f:
                    article = json.load(f)
                
                title = article.get("title", "No Title")
                content = article.get("content", "")
                
                logger.info(f"Analyzing test article: {title}")
                
                # Analyze the article
                analysis = gemini_service.analyze_article(title, content)
                
                # Store the result
                results.append({
                    "article": article,
                    "analysis": analysis
                })
                
                logger.info(f"Sentiment: {analysis.get('Sentiment', 'Unknown')}, Score: {analysis.get('Sentiment_Score', 'Unknown')}")
        
        # Save all results to a single file
        with open("data/test_results/sentiment_analysis_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Completed analysis of {len(results)} test articles. Results saved to data/test_results/sentiment_analysis_results.json")
        
        # Print summary
        print("\nSentiment Analysis Summary:")
        print("=" * 50)
        for result in results:
            title = result["article"]["title"]
            sentiment = result["analysis"].get("Sentiment", "Unknown")
            score = result["analysis"].get("Sentiment_Score", "Unknown")
            print(f"Title: {title}")
            print(f"Sentiment: {sentiment}")
            print(f"Score: {score}")
            print(f"Indicators: {', '.join(result['analysis'].get('Sentiment_Indicators', []))}")
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"Error in test_sentiment_analysis: {str(e)}")

if __name__ == "__main__":
    test_sentiment_analysis()