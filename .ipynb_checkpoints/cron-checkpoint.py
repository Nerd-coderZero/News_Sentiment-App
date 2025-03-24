import os
import time
import json
import pandas as pd
import pickle
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv

# Import local utilities
from utils.news_scraper import NewsScraper
from utils.gemini_service import GeminiService
from utils.text_to_speech import TextToSpeechService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, api_url: str = "http://localhost:8000"):
        """Initialize the batch processor with configuration."""
        self.api_url = api_url
        self.news_scraper = NewsScraper()
        
        # Load API key from environment variable
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables. Some functionality may be limited.")
            self.gemini_service = None
        else:
            self.gemini_service = GeminiService(api_key=gemini_api_key)
        
        # Initialize TTS service with Gemini as the primary translator
        self.tts_service = TextToSpeechService(gemini_service=self.gemini_service)
        
        # Create necessary directories
        os.makedirs(os.path.join("data", "output", "audio"), exist_ok=True)
        os.makedirs(os.path.join("data", "output", "text"), exist_ok=True)
        
        logger.info("Batch processor initialized")

    def load_company_list(self) -> List[str]:
        """Load the list of companies to process."""
        company_list_path = os.path.join("data", "company_list.csv")
        
        if os.path.exists(company_list_path):
            try:
                df = pd.read_csv(company_list_path)
                return df["company"].tolist()
            except Exception as e:
                logger.error(f"Error loading company list: {str(e)}")
                # Fallback to default companies
                return self.get_default_companies()
        else:
            logger.warning(f"Company list file not found at {company_list_path}. Using default companies.")
            return self.get_default_companies()

    def get_default_companies(self) -> List[str]:
        """Get the default list of companies."""
        default_companies = os.getenv("DEFAULT_COMPANIES", "Tesla,Apple,Microsoft,Google,Amazon")
        return [company.strip() for company in default_companies.split(",")]

    def process_company(self, company_name: str) -> Dict[str, Any]:
        """Process a single company with title extraction from content."""
        logger.info(f"Processing company: {company_name}")
        
        try:
            # Step 1: Scrape news articles
            articles = self.news_scraper.search_company_news(company_name, max_results=10)
            
            if not articles:
                logger.warning(f"No articles found for {company_name}")
                return None
            
            # Step 2: Process and analyze articles
            analysis_result = {
                "Company": company_name,
                "Articles": []
            }
            
            successful_analyses = 0
            
            for article in articles:
                # Extract content
                content = article.get("content", "")
                
                # Check if title exists in the article data
                if "title" in article and article["title"] and article["title"] != "No Title":
                    title = article["title"]
                else:
                    # Extract title from the content
                    title, content = extract_title_from_article(content)
                
                try:
                    # Analyze sentiment and extract topics
                    article_analysis = self.gemini_service.analyze_article(title, content)
    
                    # Verify we have a valid analysis
                    if article_analysis and "Sentiment_Score" in article_analysis:
                        # Use a more nuanced sentiment classification
                        sentiment_score = article_analysis["Sentiment_Score"]
                        
                        # Adjust thresholds to create more diversity
                        if sentiment_score >= 3.7:  # Lowered from 4.0
                            article_analysis["Sentiment"] = "Positive"
                        elif sentiment_score <= 2.7:  # Raised from 2.5
                            article_analysis["Sentiment"] = "Negative"
                        else:
                            article_analysis["Sentiment"] = "Neutral"
                        
                        # Make sure title is preserved
                        article_analysis["Title"] = title
                        
                        # Store original content length and truncated content for reference
                        article_analysis["Content_Length"] = len(content)
                        article_analysis["Content_Preview"] = content[:200] + "..." if len(content) > 200 else content
                        
                        analysis_result["Articles"].append(article_analysis)
                        successful_analyses += 1
                    else:
                        logger.warning(f"Invalid analysis for article: {title}")
                except Exception as e:
                    logger.error(f"Error analyzing article {title}: {str(e)}")
            
            # Only proceed if we have enough successful analyses
            if successful_analyses >= 3:
                # Step 3: Generate comparative analysis without overriding
                comparative_analysis = self.gemini_service.generate_comparative_analysis(company_name, analysis_result["Articles"])
                
                # Don't completely override the sentiment trend, maybe enhance it
                if "Sentiment_Trend" in comparative_analysis:
                    original_trend = comparative_analysis["Sentiment_Trend"]
                    comparative_analysis["Sentiment_Trend"] = original_trend
                
                analysis_result["Comparative_Sentiment_Score"] = comparative_analysis
                
                # Step 4: Generate final sentiment statement
                final_sentiment = self.gemini_service.generate_final_sentiment(company_name, analysis_result)
                
                # Don't append, replace
                analysis_result["Final_Sentiment_Analysis"] = final_sentiment
                
                # Step 5: Generate TTS in Hindi
                self.generate_tts_and_text(company_name, final_sentiment)
                
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing {company_name}: {str(e)}")
            return None

    def generate_tts_and_text(self, company_name: str, final_sentiment_analysis: str):
        """
        Generate TTS audio and save Hindi text for the final sentiment analysis.
        
        Args:
            company_name: Name of the company
            final_sentiment_analysis: Final sentiment analysis text
        """
        try:
            if not final_sentiment_analysis:
                logger.warning(f"No final sentiment analysis available for {company_name}")
                return
            
            # Create consistent file paths
            company_slug = company_name.lower().replace(' ', '_')
            audio_dir = os.path.join("data", "output", "audio")
            text_dir = os.path.join("data", "output", "text")
            
            # Ensure directories exist
            os.makedirs(audio_dir, exist_ok=True)
            os.makedirs(text_dir, exist_ok=True)
            
            # Define file paths
            audio_path = os.path.join(audio_dir, f"{company_slug}.mp3")
            text_path = os.path.join(text_dir, f"{company_slug}_hindi.txt")
            
            # Generate Hindi speech and save both audio and text
            audio_file, hindi_text = self.tts_service.generate_hindi_speech_from_english(
                final_sentiment_analysis,
                audio_path
            )
            
            # Save Hindi text to file for later reference
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(hindi_text)
            
            logger.info(f"Generated audio and text for {company_name}: {audio_path}, {text_path}")
            
        except Exception as e:
            logger.error(f"Error generating TTS and text for {company_name}: {str(e)}")

    def save_result(self, company_name: str, analysis_result: Dict[str, Any]) -> bool:
        """Save the analysis result to disk."""
        try:
            if not analysis_result:
                return False
                
            file_name = company_name.lower().replace(" ", "_")
            file_path = os.path.join("data", "output", f"{file_name}.pkl")
            
            with open(file_path, "wb") as f:
                pickle.dump(analysis_result, f)
                
            logger.info(f"Saved analysis for {company_name} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving analysis for {company_name}: {str(e)}")
            return False
            
    def process_all_companies(self):
        """Process all companies in the list."""
        companies = self.load_company_list()
        logger.info(f"Starting batch processing for {len(companies)} companies")
        
        results = {
            "total": len(companies),
            "success": 0,
            "failed": 0,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        for company in companies:
            logger.info(f"Processing {company} ({companies.index(company) + 1}/{len(companies)})")
            
            try:
                # Process company
                analysis_result = self.process_company(company)
                
                # Save result
                if analysis_result and self.save_result(company, analysis_result):
                    results["success"] += 1
                else:
                    results["failed"] += 1
                
                # Add delay between processing to avoid rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {company}: {str(e)}")
                results["failed"] += 1
        
        results["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Batch processing completed. Succeeded: {results['success']}, Failed: {results['failed']}")
        
        # Save results summary
        with open(os.path.join("data", "output", "batch_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        
        return results

    def process_via_api(self, company_name: str):
        """Process a company by calling the API endpoint."""
        try:
            response = requests.post(
                f"{self.api_url}/analyze",
                json={"company_name": company_name}  # Use json instead of data
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully processed {company_name} via API")
                return response.json()
            else:
                logger.error(f"API error for {company_name}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling API for {company_name}: {str(e)}")
            return None

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="News Sentiment Analysis Batch Processor")
    parser.add_argument("--api", action="store_true", help="Use API for processing instead of direct processing")
    parser.add_argument("--company", type=str, help="Process a specific company")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    
    # Initialize batch processor
    processor = BatchProcessor(api_url=args.api_url)
    
    if args.company:
        # Process a single company
        logger.info(f"Processing single company: {args.company}")
        
        if args.api:
            result = processor.process_via_api(args.company)
        else:
            result = processor.process_company(args.company)
            if result:
                processor.save_result(args.company, result)
                
        if result:
            logger.info(f"Successfully processed {args.company}")
        else:
            logger.error(f"Failed to process {args.company}")
    else:
        # Process all companies
        logger.info("Processing all companies")
        processor.process_all_companies()

if __name__ == "__main__":
    main()