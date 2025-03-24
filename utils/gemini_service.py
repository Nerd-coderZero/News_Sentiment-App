import json
import time
import logging
import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GeminiService:
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini service for text analysis.
        
        Args:
            api_key: API key for Gemini (optional, will use env var if not provided)
        """
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.rate_limit_retries = 3
        self.rate_limit_backoff = 2  # seconds
        
        # Create a cache directory for storing responses
        os.makedirs("data/cache", exist_ok=True)
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                logging.info("Gemini API initialized successfully")
            except Exception as e:
                logging.error(f"Error initializing Gemini API: {str(e)}")
                raise ValueError("Could not initialize Gemini API. Please check your API key.")
        else:
            raise ValueError("No API key provided or found in environment variables.")
    
    # _call_api_with_retry remains the same...
    def _call_api_with_retry(self, prompt: str) -> str:
        """
        Call the Gemini API with retry logic for rate limiting.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            API response text
        """
        retries = 0
        while retries <= self.rate_limit_retries:
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e) and retries < self.rate_limit_retries:
                    # Rate limited - exponential backoff
                    wait_time = self.rate_limit_backoff * (2 ** retries)
                    logging.warning(f"Rate limited. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    # Other error or max retries reached
                    raise e
        
        raise Exception("Max retries reached for API call")
    
    # Cache methods remain the same...
    def _get_cache_key(self, text: str) -> str:
        """Generate a simple cache key from text."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check if result exists in cache."""
        cache_path = f"data/cache/{cache_key}.json"
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """Save result to cache."""
        cache_path = f"data/cache/{cache_key}.json"
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logging.error(f"Error saving to cache: {str(e)}")
    
    # Add this function to the GeminiService class to replace the existing analyze_article method

    def analyze_article(self, title: str, content: str) -> Dict[str, Any]:
        """
        Analyze an article to extract summary, sentiment, and topics with enhanced sentiment sensitivity.
        
        Args:
            title: The article title
            content: The article content
            
        Returns:
            Dictionary with analysis results
        """
        # Generate cache key from title and truncated content
        cache_key = self._get_cache_key(f"{title}_{content[:1000]}")
        cached_result = self._check_cache(cache_key)
        
        if cached_result:
            logging.info(f"Using cached analysis for article '{title}'")
            return cached_result
        
        try:
            # Modified prompt with stronger emphasis on non-neutral sentiment detection
            prompt = f"""
            Title: {title}
            
            Content: {content[:4000]}... (truncated)
            
            Analyze the above news article about a company and provide the following:
            1. A concise summary of the article (2-3 sentences)
            2. The sentiment of the article on a 5-point scale - CRITICAL INSTRUCTION: DO NOT DEFAULT TO NEUTRAL. Look for sentiment signals and lean toward assigning a non-neutral sentiment unless truly warranted:
               - Very Negative (1): Highly critical, reporting major problems or failures
               - Negative (2): Reporting problems, challenges, or disappointing performance
               - Neutral (3): Balanced reporting of facts with minimal bias
               - Positive (4): Reporting success, growth, or positive developments
               - Very Positive (5): Highly favorable, reporting exceptional performance or achievements
            3. A list of 2-4 main topics or themes mentioned in the article
            4. Key sentiment indicators - IMPORTANT: Identify SPECIFIC words, phrases, or facts that convey sentiment, particularly those that suggest non-neutral attitudes
            
            Format your response as a JSON object with these fields:
            {{
              "Title": "{title}",
              "Summary": "Concise summary here",
              "Sentiment": "Very Negative/Negative/Neutral/Positive/Very Positive",
              "Sentiment_Score": A number from 1-5 where 1=Very Negative, 3=Neutral, 5=Very Positive,
              "Topics": ["Topic1", "Topic2", ...],
              "Sentiment_Indicators": ["Indicator1", "Indicator2", ...]
            }}
            
            IMPORTANT GUIDELINES:
            - Assign sentiment scores of 1, 2, 4, or 5 whenever possible
            - Use 3 (Neutral) ONLY when the article is truly balanced with equal positive and negative elements
            - Look for subtle indicators of sentiment in word choice and emphasis
            - Consider industry context (e.g., "steady growth" is positive; "only grew by 2%" suggests disappointment)
            
            Do not include any explanation or other text outside the JSON object.
            """
            
            response_text = self._call_api_with_retry(prompt)
            
            # Clean up response to extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Ensure all required fields are present
            required_fields = ["Title", "Summary", "Sentiment", "Sentiment_Score", "Topics", "Sentiment_Indicators"]
            for field in required_fields:
                if field not in result:
                    if field in ["Topics", "Sentiment_Indicators"]:
                        result[field] = []
                    elif field == "Sentiment_Score":
                        result[field] = 3  # Default neutral
                    else:
                        result[field] = ""
            
            # Ensure title is preserved from input
            if "Title" not in result or not result["Title"]:
                result["Title"] = title
            
            # Post-processing step: Adjust sentiment labels based on score for consistency
            score = result["Sentiment_Score"]
            if score <= 1.5:
                result["Sentiment"] = "Very Negative"
            elif score <= 2.5:
                result["Sentiment"] = "Negative"
            elif score <= 3.5:
                result["Sentiment"] = "Neutral"
            elif score <= 4.5:
                result["Sentiment"] = "Positive"
            else:
                result["Sentiment"] = "Very Positive"
                
            # Save to cache
            self._save_to_cache(cache_key, result)
            return result
                
        except Exception as e:
            logging.error(f"Error analyzing article '{title}': {str(e)}")
            raise
            
    
    def generate_comparative_analysis(self, company_name: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate enhanced comparative analysis across multiple articles, focusing on
        coverage differences and sentiment variations.
        
        Args:
            company_name: Name of the company
            articles: List of analyzed articles with sentiment data
        
        Returns:
            Dict with comprehensive comparative analysis
        """
        # Generate cache key from company name and article titles
        titles = "_".join([article.get("Title", "")[:20] for article in articles[:3]])
        cache_key = self._get_cache_key(f"comp_{company_name}_{titles}")
        cached_result = self._check_cache(cache_key)
        
        if cached_result:
            logging.info(f"Using cached comparative analysis for {company_name}")
            return cached_result
        
        try:
            # Count detailed sentiments with more focus on variation
            sentiment_dist = {
                "Very Positive": 0, 
                "Positive": 0, 
                "Neutral": 0, 
                "Negative": 0, 
                "Very Negative": 0
            }
            
            # Calculate average sentiment score
            total_score = 0
            titles_with_sentiment = []
            all_topics = []
            all_indicators = []
            
            # Extract key data from articles
            for article in articles:
                sentiment = article.get("Sentiment", "Neutral")
                if sentiment in sentiment_dist:
                    sentiment_dist[sentiment] += 1
                
                # Add sentiment score if available
                total_score += article.get("Sentiment_Score", 3)
                
                # Collect titles and their sentiment for the prompt
                titles_with_sentiment.append({
                    "title": article.get("Title", "Unknown Title"),
                    "sentiment": sentiment,
                    "score": article.get("Sentiment_Score", 3)
                })
                
                # Collect all topics and indicators
                all_topics.extend(article.get("Topics", []))
                all_indicators.extend(article.get("Sentiment_Indicators", []))
            
            avg_sentiment_score = total_score / len(articles) if articles else 3.0
            
            # Create list of article titles, sentiments and indicators for prompt
            article_list = []
            for i, article in enumerate(articles):
                title = article.get("Title", f"Article {i+1}")
                sentiment = article.get("Sentiment", "Neutral")
                score = article.get("Sentiment_Score", 3)
                topics_str = ", ".join(article.get("Topics", []))
                indicators_str = ", ".join(article.get("Sentiment_Indicators", []))
                summary = article.get("Summary", "No summary available")
                
                article_list.append(
                    f"Article {i+1}: {title}\n"
                    f"- Summary: {summary}\n"
                    f"- Sentiment: {sentiment} (Score: {score}/5)\n"
                    f"- Topics: {topics_str}\n"
                    f"- Key Indicators: {indicators_str}"
                )
            
            articles_text = "\n\n".join(article_list)
            
            # Enhanced prompt with more focus on coverage differences
            prompt = f"""
            Company: {company_name}
            
            Articles about {company_name}:
            {articles_text}
            
            TASK: Generate a DETAILED comparative analysis of how news coverage differs across these articles.
            
            Focus on:
            1. How the SAME topics are covered differently (positive in one article, negative in another)
            2. UNIQUE perspectives or angles that appear in only some articles
            3. CONFLICTING information or claims between articles
            4. EMPHASIS differences - what some articles highlight vs. downplay
            5. TIMELINE differences - how reporting has evolved if articles span different dates
            
            DO NOT default to generic analysis. Be SPECIFIC about actual differences found.
            If articles are similar, identify the subtle ways they still differ in perspective.
            
            Format the response as a JSON with these fields:
            {{
              "Sentiment_Distribution": {{
                "Very Positive": {sentiment_dist["Very Positive"]},
                "Positive": {sentiment_dist["Positive"]},
                "Neutral": {sentiment_dist["Neutral"]},
                "Negative": {sentiment_dist["Negative"]},
                "Very Negative": {sentiment_dist["Very Negative"]}
              }},
              "Average_Sentiment_Score": {avg_sentiment_score:.2f},
              "Sentiment_Trend": "Description of overall sentiment pattern across articles",
              "Coverage_Differences": [
                {{
                  "Comparison": "Description of a key difference between articles",
                  "Articles_Involved": ["Article title 1", "Article title 2"],
                  "Impact": "Impact on overall perception"
                }},
                {{
                  "Comparison": "Another key difference between articles",
                  "Articles_Involved": ["Article title 1", "Article title 3"],
                  "Impact": "Impact on overall perception"
                }}
              ],
              "Sentiment_Drivers": {{
                "Positive_Factors": ["Factor1", "Factor2", ...],
                "Negative_Factors": ["Factor1", "Factor2", ...]
              }},
              "Topic_Analysis": {{
                "Common_Topics": ["Topic1", "Topic2", ...],
                "Topic_Sentiment_Map": {{
                  "Topic1": "Positive/Negative/Mixed/Neutral",
                  "Topic2": "Positive/Negative/Mixed/Neutral",
                  ...
                }}
              }}
            }}
            
            IMPORTANT: Provide at least 3-4 specific, detailed coverage differences in the Coverage_Differences array.
            Do not include any explanation or other text outside the JSON object.
            """
            
            response_text = self._call_api_with_retry(prompt)
            
            # Clean up response to extract JSON
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                # Parse JSON response
                result = json.loads(response_text)
                
                # Ensure sentiment distribution matches actual count (but keep any additional analysis)
                result["Sentiment_Distribution"] = sentiment_dist
                result["Average_Sentiment_Score"] = avg_sentiment_score
                
                # Add error check for empty Coverage_Differences
                if "Coverage_Differences" not in result or not result["Coverage_Differences"]:
                    result["Coverage_Differences"] = [
                        {
                            "Comparison": "Differences in reporting emphasis",
                            "Articles_Involved": [article.get("Title", "Unknown") for article in articles[:2]],
                            "Impact": "Creates varied impressions of company priorities"
                        }
                    ]
                
                # Ensure we have all required fields
                if "Sentiment_Drivers" not in result:
                    result["Sentiment_Drivers"] = {
                        "Positive_Factors": [],
                        "Negative_Factors": []
                    }
                
                if "Topic_Analysis" not in result:
                    result["Topic_Analysis"] = {
                        "Common_Topics": list(set(all_topics))[:5],
                        "Topic_Sentiment_Map": {}
                    }
                
                # Save to cache
                self._save_to_cache(cache_key, result)
                return result
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON response: {str(e)}")
                # Return a basic analysis when parsing fails
                basic_result = {
                    "Sentiment_Distribution": sentiment_dist,
                    "Average_Sentiment_Score": avg_sentiment_score,
                    "Sentiment_Trend": "Unable to determine due to processing error",
                    "Coverage_Differences": [
                        {
                            "Comparison": "Analysis encountered an error",
                            "Articles_Involved": [article.get("Title", "Unknown") for article in articles[:2]],
                            "Impact": "Complete comparative analysis not available"
                        }
                    ],
                    "Sentiment_Drivers": {
                        "Positive_Factors": [],
                        "Negative_Factors": []
                    },
                    "Topic_Analysis": {
                        "Common_Topics": list(set(all_topics))[:5],
                        "Topic_Sentiment_Map": {}
                    }
                }
                self._save_to_cache(cache_key, basic_result)
                return basic_result
                    
        except Exception as e:
            logging.error(f"Error generating comparative analysis for {company_name}: {str(e)}")
            raise
    
    def generate_final_sentiment(self, company_name: str, analysis_result: Dict[str, Any]) -> str:
        """
        Generate a final sentiment analysis statement.
        
        Args:
            company_name: Name of the company
            analysis_result: Complete analysis result
            
        Returns:
            String with final sentiment analysis
        """
        # Generate cache key
        cache_key = self._get_cache_key(f"final_{company_name}")
        cached_result = self._check_cache(cache_key)
        
        if cached_result and "sentiment" in cached_result:
            logging.info(f"Using cached final sentiment for {company_name}")
            return cached_result["sentiment"]
        
        try:
            # Extract sentiment distribution
            sentiment_dist = analysis_result.get("Comparative_Sentiment_Score", {}).get("Sentiment_Distribution", {})
            avg_score = analysis_result.get("Comparative_Sentiment_Score", {}).get("Average_Sentiment_Score", 3.0)
            
            # Get sentiment drivers
            sentiment_drivers = analysis_result.get("Comparative_Sentiment_Score", {}).get("Sentiment_Drivers", {})
            positive_factors = sentiment_drivers.get("Positive_Factors", [])
            negative_factors = sentiment_drivers.get("Negative_Factors", [])
            
            # Create a summary of the articles for context
            articles_summary = []
            for i, article in enumerate(analysis_result.get("Articles", [])[:3]):  # Use first 3 for brevity
                title = article.get("Title", f"Article {i+1}")
                sentiment = article.get("Sentiment", "Neutral")
                score = article.get("Sentiment_Score", 3)
                articles_summary.append(f"- {title} (Sentiment: {sentiment}, Score: {score}/5)")
            
            articles_text = "\n".join(articles_summary)
            
            # Create prompt for final sentiment
            prompt = f"""
            Company: {company_name}
            
            The sentiment analysis for {company_name} has been completed.
            Key findings:
            - **Positive Factors**: {", ".join(positive_factors)}
            - **Negative Factors**: {", ".join(negative_factors)}
            - **Overall Sentiment Trend**: {avg_score:.2f}/5 on the sentiment scale.
            
            Summarize the overall sentiment **briefly** in 2-3 sentences. Focus on the **major insights**, avoiding generic statements.

            
            Your analysis should:
            1. Describe the nuanced sentiment (not just positive/negative/neutral)
            2. Explain key factors driving the sentiment
            3. Suggest potential implications for investors or stakeholders
            4. Highlight any discrepancies or notable patterns across articles
            
            Avoid generic language and focus on specific insights from the data.
            """
            
            final_sentiment = self._call_api_with_retry(prompt).strip()
            
            # Save to cache
            self._save_to_cache(cache_key, {"sentiment": final_sentiment})
            return final_sentiment
            
        except Exception as e:
            logging.error(f"Error generating final sentiment for {company_name}: {str(e)}")
            raise
    
    def generate_query_response(self, company_name: str, company_data: Dict[str, Any], query: str) -> str:
        """
        Generate a response to a user query about the company's news sentiment data.
        
        Args:
            company_name: Name of the company
            company_data: Analysis data for the company
            query: User's query
            
        Returns:
            str: Response to the query
        """
        cache_key = self._get_cache_key(f"query_{company_name}_{query}")
        cached_result = self._check_cache(cache_key)
        
        if cached_result and "response" in cached_result:
            return cached_result["response"]
        
        try:
            # Create a prompt for the query with detailed context
            prompt = f"""
            Company: {company_name}
            
            User Query: {query}
            
            Summarize an answer **based only on the sentiment trends and key findings**. Avoid generic statements.


            Be specific and focus on the key insights from the data, particularly the nuanced sentiment analysis.
            
            If the query relates to sentiment, be sure to reference:
            1. The full 5-point sentiment scale (Very Negative to Very Positive)
            2. The specific sentiment indicators found in articles
            3. Any sentiment trends or patterns across articles
            
            Make your response concrete and evidence-based, citing specific elements from the analysis.
            """
            
            # Generate response using the Gemini API
            response = self._call_api_with_retry(prompt)
            
            # Save to cache
            self._save_to_cache(cache_key, {"response": response})
            
            return response.strip()
        
        except Exception as e:
            logging.error(f"Error generating query response: {str(e)}")
            raise