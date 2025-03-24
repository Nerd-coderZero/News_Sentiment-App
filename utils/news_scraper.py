import requests
import logging
from bs4 import BeautifulSoup
import time
import random
from typing import List, Dict, Any

class NewsScraper:
    def __init__(self, user_agent=None, request_delay=1.0):
        """
        Initialize the news scraper.
        
        Args:
            user_agent: Custom user agent string (default: Chrome on Windows)
            request_delay: Delay between requests in seconds to avoid rate limiting
        """
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        
        logging.info("News scraper initialized")
    
    def search_company_news(self, company_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for news articles about a company.
        
        Args:
            company_name: Name of the company to search for
            max_results: Maximum number of articles to return
            
        Returns:
            List of dictionaries with article data
        """
        logging.info(f"Searching for news about: {company_name}")
        
        try:
            # Create a list to store the articles
            articles = []
            
            # Try multiple search approaches
            search_results = self._search_news_api(company_name, max_results)
            
            if not search_results or len(search_results) < max_results // 2:
                # Fallback to web search
                search_results += self._search_web(company_name, max_results - len(search_results))
            
            # Process search results
            for result in search_results[:max_results]:
                # Extract content from each URL
                article_data = self._extract_article_content(result.get("url"))
                
                if article_data:
                    # Combine with search result data
                    full_article = {**result, **article_data}
                    articles.append(full_article)
                    
                    # Add delay between requests
                    time.sleep(self.request_delay)
            
            logging.info(f"Found {len(articles)} articles for {company_name}")
            return articles
            
        except Exception as e:
            logging.error(f"Error searching for news about {company_name}: {str(e)}")
            return []
    
    def _search_news_api(self, company_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for news using a news API (or fallback to simulated data for demo)."""
        try:
            # Note: In a real implementation, you would integrate with NewsAPI, Bing News API, or similar
            # For demo purposes, we'll simulate results
            
            # Simulate a response with better titles
            simulated_results = []
            for i in range(min(10, max_results)):  # Simulate up to 10 results
                # Generate simulated content with a proper title
                simulated_content = self._generate_simulated_content()
                title = simulated_content["title"].replace("{Company}", company_name)
                
                simulated_results.append({
                    "title": title,
                    "url": f"https://example.com/news/{company_name.lower().replace(' ', '-')}/{i+1}",
                    "source": "Simulated News Source",
                    "published_at": "2023-01-01"
                })
            
            return simulated_results
            
        except Exception as e:
            logging.error(f"Error using news API for {company_name}: {str(e)}")
            return []
    
    def _search_web(self, company_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for news using general web search."""
        try:
            # Format search query
            query = f"{company_name} news"
            encoded_query = "+".join(query.split())
            
            # Search URLs to try
            search_urls = [
                f"https://www.google.com/search?q={encoded_query}&tbm=nws",
                f"https://news.search.yahoo.com/search?p={encoded_query}"
            ]
            
            results = []
            
            for search_url in search_urls:
                if len(results) >= max_results:
                    break
                    
                # Send request
                response = self.session.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    # Parse results based on source
                    if "google.com" in search_url:
                        new_results = self._parse_google_news(response.text)
                    elif "yahoo.com" in search_url:
                        new_results = self._parse_yahoo_news(response.text)
                    else:
                        new_results = []
                    
                    # Add results
                    results.extend(new_results)
                    
                    # Add delay between requests
                    time.sleep(self.request_delay)
            
            # Return limited results
            return results[:max_results]
            
        except Exception as e:
            logging.error(f"Error searching web for {company_name}: {str(e)}")
            return []
    
    def _parse_google_news(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse Google News search results."""
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Google news article divs often have a class 'SoaBEf'
            # This might change as Google updates their website
            news_divs = soup.find_all('div', class_='SoaBEf')
            
            for div in news_divs:
                try:
                    # Find the title and link
                    title_element = div.find('div', role='heading')
                    link_element = div.find('a')
                    source_element = div.find('div', class_='CEMjEf')
                    
                    if title_element and link_element:
                        title = title_element.get_text(strip=True)
                        url = link_element.get('href')
                        
                        # Clean the URL (Google prepends their URL to the actual article URL)
                        if url.startswith('/url?'):
                            url = url.split('url=')[1].split('&')[0]
                        
                        # Get source name and date if available
                        source = ""
                        date = ""
                        if source_element:
                            source_text = source_element.get_text(strip=True)
                            if " · " in source_text:
                                source, date = source_text.split(" · ", 1)
                            else:
                                source = source_text
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "source": source,
                            "published_at": date
                        })
                except Exception as e:
                    logging.warning(f"Error parsing a Google News result: {str(e)}")
            
        except Exception as e:
            logging.error(f"Error parsing Google News results: {str(e)}")
        
        return results
    
    def _parse_yahoo_news(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse Yahoo News search results."""
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Yahoo news articles are typically in divs with class 'NewsArticle'
            news_divs = soup.find_all('div', class_='NewsArticle')
            
            for div in news_divs:
                try:
                    # Find the title and link
                    title_element = div.find('h4')
                    link_element = div.find('a')
                    source_element = div.find('span', class_='s-source')
                    date_element = div.find('span', class_='s-time')
                    
                    if title_element and link_element:
                        title = title_element.get_text(strip=True)
                        url = link_element.get('href')
                        
                        # Get source and date if available
                        source = source_element.get_text(strip=True) if source_element else ""
                        date = date_element.get_text(strip=True) if date_element else ""
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "source": source,
                            "published_at": date
                        })
                except Exception as e:
                    logging.warning(f"Error parsing a Yahoo News result: {str(e)}")
            
        except Exception as e:
            logging.error(f"Error parsing Yahoo News results: {str(e)}")
        
        return results
    
    def _extract_article_content(self, url: str) -> Dict[str, Any]:
        """Extract title and content from an article URL."""
        if not url or url.startswith("https://example.com"):
            return self._generate_simulated_content()
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
    
                # Try to extract a better title
                # First try Open Graph title (often more accurate for articles)
                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    title = og_title["content"]
                else:
                    # Try article headlines (common in news sites)
                    headline = soup.find(["h1", "h2"], class_=lambda c: c and any(x in str(c).lower() for x in ['headline', 'title', 'heading']))
                    if headline:
                        title = headline.get_text(strip=True)
                    else:
                        # Fallback to regular h1
                        h1 = soup.find("h1")
                        if h1:
                            title = h1.get_text(strip=True)
                        else:
                            # Last resort: use page title but clean it
                            page_title = soup.find("title")
                            if page_title:
                                title = page_title.get_text(strip=True)
                                # Try to remove site name often at the end after a separator
                                for separator in [' - ', ' | ', ' — ', ' – ', ' :: ', ' // ']:
                                    if separator in title:
                                        title = title.split(separator)[0].strip()
                            else:
                                title = "No Title"
    
                # Extract text content
                paragraphs = soup.find_all('p')
                content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40])
    
                date = self._extract_date(soup)
    
                return {
                    "title": title,
                    "content": content,
                    "word_count": len(content.split()),
                    "published_at": date or "Unknown"
                }
            else:
                logging.warning(f"Failed to fetch {url}: Status code {response.status_code}")
                return {}
    
        except Exception as e:
            logging.error(f"Error extracting content from {url}: {str(e)}")
            return {}

    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date from article HTML."""
        # Try common date metadata
        meta_dates = [
            soup.find('meta', property='article:published_time'),
            soup.find('meta', property='og:article:published_time'),
            soup.find('meta', itemprop='datePublished'),
            soup.find('time')
        ]
        
        for meta in meta_dates:
            if meta:
                if meta.get('content'):
                    return meta['content']
                elif meta.get('datetime'):
                    return meta['datetime']
                elif meta.string:
                    return meta.string
        
        return ""
    
    def _generate_simulated_content(self) -> Dict[str, Any]:
        """Generate simulated article content for demo purposes."""
        # Better simulated titles
        title_templates = [
            "Quarterly Results: {Company} Exceeds Expectations with Strong Performance",
            "{Company} Announces New Strategic Initiatives to Accelerate Growth",
            "Market Analysis: What's Next for {Company} After Recent Developments",
            "{Company} Expands into New Markets: What Investors Need to Know",
            "Inside {Company}'s Latest Product Launch: Industry Experts Weigh In",
            "{Company} Faces Regulatory Challenges, Stock Price Affected",
            "CEO of {Company} Reveals Future Vision in Recent Interview",
            "Analyst Report: {Company} Shows Promising Growth Potential",
            "{Company}'s Competitive Edge: How They're Staying Ahead in the Market",
            "Investment Insights: Is {Company} a Buy Right Now?"
        ]
        
        # Generate a title with a placeholder for company name
        title = random.choice(title_templates)
        
        # List of phrases to randomly combine
        phrases = [
            "The company reported strong quarterly results, exceeding analyst expectations.",
            "Investors remain cautious about the company's growth prospects.",
            "The CEO announced new strategic initiatives to boost revenue.",
            "Market analysts have mixed opinions on the company's recent performance.",
            "New product launches are expected to drive future growth.",
            "Regulatory challenges could impact the company's operations.",
            "The company is expanding into new markets to diversify revenue streams.",
            "Competition in the sector remains intense, putting pressure on margins.",
            "Innovation continues to be a key focus area for the company.",
            "Recent acquisitions are expected to strengthen the company's market position."
        ]
        
        # Randomly select and combine phrases
        num_paragraphs = random.randint(3, 7)
        content_paragraphs = []
        
        for _ in range(num_paragraphs):
            # Create a paragraph with 2-4 sentences
            num_sentences = random.randint(2, 4)
            selected_phrases = random.sample(phrases, num_sentences)
            paragraph = " ".join(selected_phrases)
            content_paragraphs.append(paragraph)
        
        content = "\n\n".join(content_paragraphs)
        
        return {
            "title": title,  # Title with company placeholder, will be filled by the caller
            "content": content,
            "word_count": len(content.split()),
            "published_at": "2023-01-01"  # Simulated date
        }