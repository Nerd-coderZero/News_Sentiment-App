import json
import sys
import os
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

def test_comparative_analysis():
    """Test the comparative analysis functionality with the test articles"""
    try:
        # Initialize the Gemini service
        gemini_service = GeminiService()
        logger.info("GeminiService initialized successfully")
        
        # Create directory for results
        os.makedirs("data/test_results", exist_ok=True)
        
        # Load test articles
        test_articles_dir = "data/test_articles"
        
        if not os.path.exists(test_articles_dir):
            logger.error(f"Test articles directory not found: {test_articles_dir}")
            return
        
        # Load and analyze all test articles
        articles = []
        company_name = "Test Company"
        
        for filename in os.listdir(test_articles_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(test_articles_dir, filename)
                
                with open(file_path, "r") as f:
                    article_data = json.load(f)
                
                title = article_data.get("title", "No Title")
                content = article_data.get("content", "")
                
                logger.info(f"Analyzing article for comparative analysis: {title}")
                
                # Analyze the article - use the improved version if available
                if hasattr(gemini_service, "analyze_article_improved"):
                    analysis = gemini_service.analyze_article_improved(title, content)
                else:
                    analysis = gemini_service.analyze_article(title, content)
                
                articles.append(analysis)
        
        # Extract company name from the first article title if possible
        if articles and "Title" in articles[0]:
            title_parts = articles[0]["Title"].split()
            if title_parts:
                company_name = title_parts[0]  # Use first word as company name
        
        logger.info(f"Generating comparative analysis for {company_name} with {len(articles)} articles")
        
        # Generate comparative analysis - use the improved version if available
        if hasattr(gemini_service, "generate_comparative_analysis_improved"):
            comparative_analysis = gemini_service.generate_comparative_analysis_improved(company_name, articles)
        else:
            comparative_analysis = gemini_service.generate_comparative_analysis(company_name, articles)
        
        # Save the result
        with open("data/test_results/comparative_analysis_result.json", "w") as f:
            json.dump(comparative_analysis, f, indent=2)
        
        logger.info("Comparative analysis completed and saved to data/test_results/comparative_analysis_result.json")
        
        # Print summary of coverage differences
        print("\nComparative Analysis - Coverage Differences:")
        print("=" * 70)
        
        if "Coverage_Differences" in comparative_analysis and comparative_analysis["Coverage_Differences"]:
            for i, diff in enumerate(comparative_analysis["Coverage_Differences"]):
                print(f"{i+1}. {diff.get('Comparison', 'No comparison available')}")
                
                if "Articles_Involved" in diff:
                    print(f"   Articles: {', '.join(diff['Articles_Involved'])}")
                    
                if "Impact" in diff:
                    print(f"   Impact: {diff['Impact']}")
                    
                print()
        else:
            print("No coverage differences found or available")
        
    except Exception as e:
        logger.error(f"Error in test_comparative_analysis: {str(e)}")

if __name__ == "__main__":
    test_comparative_analysis()