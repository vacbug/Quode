"""
Twitter/X scraper for collecting Indian stock market tweets.
Uses Selenium with sophisticated anti-bot measures and rate limiting.
"""

import time
import random
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Generator
from pathlib import Path
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger

from ..utils.config import get_config
from ..utils.logger import get_logger, LogContext
from ..utils.helpers import (
    clean_text, extract_hashtags, extract_mentions, extract_urls,
    parse_timestamp, generate_content_hash, is_within_time_window
)
from .rate_limiter import RateLimiter, RequestSession, AntiBotMeasures


@dataclass
class TweetData:
    """Data structure for tweet information."""
    tweet_id: str
    username: str
    content: str
    timestamp: datetime
    likes: int
    retweets: int
    replies: int
    hashtags: List[str]
    mentions: List[str]
    urls: List[str]
    is_retweet: bool
    is_reply: bool
    language: str
    content_hash: str
    collection_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'tweet_id': self.tweet_id,
            'username': self.username,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'likes': self.likes,
            'retweets': self.retweets,
            'replies': self.replies,
            'hashtags': self.hashtags,
            'mentions': self.mentions,
            'urls': self.urls,
            'is_retweet': self.is_retweet,
            'is_reply': self.is_reply,
            'language': self.language,
            'content_hash': self.content_hash,
            'collection_timestamp': self.collection_timestamp.isoformat()
        }


class TwitterScraper:
    """Advanced Twitter/X scraper with anti-bot measures."""
    
    def __init__(self, headless: bool = True, use_proxy: bool = False):
        """
        Initialize the Twitter scraper.
        
        Args:
            headless: Whether to run browser in headless mode
            use_proxy: Whether to use proxy rotation
        """
        self.config = get_config().data_collection
        self.log = get_logger("twitter_scraper")
        self.rate_limiter = RateLimiter()
        self.anti_bot = AntiBotMeasures()
        self.headless = headless
        self.use_proxy = use_proxy
        self.driver = None
        self.wait = None
        
        # Initialize WebDriver
        self._setup_driver()
        
        self.log.info("Twitter scraper initialized successfully")
    
    def _setup_driver(self) -> None:
        """Set up the Chrome WebDriver with anti-bot measures."""
        try:
            chrome_options = Options()
            
            # Basic options
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Anti-bot measures
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Random user agent
            user_agent = self.rate_limiter.get_user_agent()
            chrome_options.add_argument(f"--user-agent={user_agent}")
            
            # Additional stealth options
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")
            
            # Set up the driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute stealth script
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set up wait
            self.wait = WebDriverWait(self.driver, 10)
            
            self.log.info("WebDriver setup completed")
            
        except Exception as e:
            self.log.error(f"Failed to setup WebDriver: {e}")
            raise
    
    def _search_twitter(self, query: str) -> None:
        """
        Navigate to Twitter search page.
        
        Args:
            query: Search query (hashtag or keyword)
        """
        try:
            # Construct search URL
            search_url = f"https://twitter.com/search?q={query}&src=typed_query&f=live"
            
            self.log.info(f"Navigating to search: {query}")
            self.driver.get(search_url)
            
            # Wait for page to load
            time.sleep(random.uniform(2, 4))
            
            # Check if we need to handle login popup
            self._handle_login_popup()
            
            # Wait for tweets to load
            self._wait_for_tweets()
            
        except Exception as e:
            self.log.error(f"Error navigating to search: {e}")
            raise
    
    def _handle_login_popup(self) -> None:
        """Handle login popup if it appears."""
        try:
            # Look for login popup and close it
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="app-bar-close"]')
            if close_buttons:
                close_buttons[0].click()
                time.sleep(1)
                self.log.debug("Closed login popup")
        except Exception as e:
            self.log.debug(f"Error handling login popup: {e}")
    
    def _wait_for_tweets(self) -> None:
        """Wait for tweets to load on the page."""
        try:
            # Wait for tweet containers to appear
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
            )
            time.sleep(random.uniform(1, 2))
        except TimeoutException:
            self.log.warning("Timeout waiting for tweets to load")
    
    def _scroll_page(self, scroll_count: int = 3) -> None:
        """
        Scroll the page to load more tweets.
        
        Args:
            scroll_count: Number of scrolls to perform
        """
        for i in range(scroll_count):
            try:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for content to load
                time.sleep(random.uniform(2, 4))
                
                # Random pause to mimic human behavior
                if random.random() > 0.7:
                    time.sleep(random.uniform(1, 3))
                
                self.log.debug(f"Scroll {i+1}/{scroll_count} completed")
                
            except Exception as e:
                self.log.warning(f"Error during scroll {i+1}: {e}")
    
    def _extract_tweet_data(self, tweet_element) -> Optional[TweetData]:
        """
        Extract data from a tweet element.
        
        Args:
            tweet_element: Selenium WebElement representing a tweet
        
        Returns:
            TweetData object or None if extraction fails
        """
        try:
            # Extract tweet ID
            tweet_id = tweet_element.get_attribute("data-tweet-id") or self._generate_tweet_id()
            
            # Extract username
            username_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
            username = username_element.text.strip().replace('@', '')
            
            # Extract content
            content_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            content = content_element.text.strip()
            
            # Skip if content is empty
            if not content:
                return None
            
            # Extract timestamp
            timestamp_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
            timestamp_str = timestamp_element.get_attribute("datetime")
            timestamp = parse_timestamp(timestamp_str) or datetime.now()
            
            # Check if tweet is within time window
            if not is_within_time_window(timestamp, self.config.collection_settings.get("time_window_hours", 24)):
                return None
            
            # Extract engagement metrics
            likes = self._extract_metric(tweet_element, '[data-testid="like"]')
            retweets = self._extract_metric(tweet_element, '[data-testid="retweet"]')
            replies = self._extract_metric(tweet_element, '[data-testid="reply"]')
            
            # Extract hashtags, mentions, and URLs
            hashtags = extract_hashtags(content)
            mentions = extract_mentions(content)
            urls = extract_urls(content)
            
            # Determine tweet type
            is_retweet = "RT @" in content or tweet_element.find_elements(By.CSS_SELECTOR, '[data-testid="socialContext"]')
            is_reply = tweet_element.find_elements(By.CSS_SELECTOR, '[data-testid="reply"]')
            
            # Detect language
            language = self._detect_language(content)
            
            # Generate content hash
            content_hash = generate_content_hash(content)
            
            return TweetData(
                tweet_id=tweet_id,
                username=username,
                content=content,
                timestamp=timestamp,
                likes=likes,
                retweets=retweets,
                replies=replies,
                hashtags=hashtags,
                mentions=mentions,
                urls=urls,
                is_retweet=bool(is_retweet),
                is_reply=bool(is_reply),
                language=language,
                content_hash=content_hash,
                collection_timestamp=datetime.now()
            )
            
        except Exception as e:
            self.log.debug(f"Error extracting tweet data: {e}")
            return None
    
    def _extract_metric(self, tweet_element, selector: str) -> int:
        """Extract engagement metric from tweet element."""
        try:
            element = tweet_element.find_element(By.CSS_SELECTOR, selector)
            text = element.text.strip()
            
            # Handle different formats (e.g., "1.2K", "500", "1M")
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(text) if text.isdigit() else 0
        except (NoSuchElementException, ValueError):
            return 0
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the tweet."""
        try:
            from langdetect import detect
            return detect(text)
        except:
            return "en"
    
    def _generate_tweet_id(self) -> str:
        """Generate a unique tweet ID if not found."""
        return f"generated_{int(time.time() * 1000)}"
    
    def collect_tweets(self, hashtags: List[str] = None, max_tweets_per_hashtag: int = None) -> List[TweetData]:
        """
        Collect tweets for specified hashtags.
        
        Args:
            hashtags: List of hashtags to search for
            max_tweets_per_hashtag: Maximum tweets to collect per hashtag
        
        Returns:
            List of TweetData objects
        """
        if hashtags is None:
            hashtags = self.config.target_hashtags
        
        if max_tweets_per_hashtag is None:
            max_tweets_per_hashtag = self.config.collection_settings.get("min_tweets", 2000) // len(hashtags)
        
        all_tweets = []
        seen_hashes = set()
        
        with LogContext("tweet_collection", "twitter_scraper"):
            for hashtag in hashtags:
                self.log.info(f"Collecting tweets for hashtag: {hashtag}")
                
                try:
                    hashtag_tweets = self._collect_tweets_for_hashtag(hashtag, max_tweets_per_hashtag, seen_hashes)
                    all_tweets.extend(hashtag_tweets)
                    
                    self.log.info(f"Collected {len(hashtag_tweets)} tweets for {hashtag}")
                    
                    # Rate limiting between hashtags
                    time.sleep(random.uniform(3, 6))
                    
                except Exception as e:
                    self.log.error(f"Error collecting tweets for {hashtag}: {e}")
                    continue
        
        # Remove duplicates based on content hash
        unique_tweets = []
        for tweet in all_tweets:
            if tweet.content_hash not in seen_hashes:
                seen_hashes.add(tweet.content_hash)
                unique_tweets.append(tweet)
        
        self.log.info(f"Total unique tweets collected: {len(unique_tweets)}")
        return unique_tweets
    
    def _collect_tweets_for_hashtag(self, hashtag: str, max_tweets: int, seen_hashes: set) -> List[TweetData]:
        """
        Collect tweets for a specific hashtag.
        
        Args:
            hashtag: Hashtag to search for
            max_tweets: Maximum number of tweets to collect
            seen_hashes: Set of already seen content hashes
        
        Returns:
            List of TweetData objects
        """
        tweets = []
        scroll_count = 0
        max_scrolls = 10
        
        try:
            # Navigate to search page
            self._search_twitter(hashtag)
            
            while len(tweets) < max_tweets and scroll_count < max_scrolls:
                # Extract tweets from current page
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')
                
                for element in tweet_elements:
                    if len(tweets) >= max_tweets:
                        break
                    
                    tweet_data = self._extract_tweet_data(element)
                    if tweet_data and tweet_data.content_hash not in seen_hashes:
                        tweets.append(tweet_data)
                        seen_hashes.add(tweet_data.content_hash)
                
                # Scroll to load more tweets
                if len(tweets) < max_tweets:
                    self._scroll_page(1)
                    scroll_count += 1
                    
                    # Random delay between scrolls
                    time.sleep(random.uniform(2, 4))
        
        except Exception as e:
            self.log.error(f"Error collecting tweets for {hashtag}: {e}")
        
        return tweets
    
    def collect_tweets_streaming(self, hashtags: List[str] = None, duration_minutes: int = 60) -> Generator[TweetData, None, None]:
        """
        Collect tweets in streaming mode for a specified duration.
        
        Args:
            hashtags: List of hashtags to monitor
            duration_minutes: Duration to collect tweets in minutes
        
        Yields:
            TweetData objects as they are found
        """
        if hashtags is None:
            hashtags = self.config.target_hashtags
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        seen_hashes = set()
        
        with LogContext("streaming_collection", "twitter_scraper"):
            self.log.info(f"Starting streaming collection for {duration_minutes} minutes")
            
            while datetime.now() < end_time:
                for hashtag in hashtags:
                    try:
                        # Collect a small batch of tweets
                        batch_tweets = self._collect_tweets_for_hashtag(hashtag, 10, seen_hashes)
                        
                        for tweet in batch_tweets:
                            yield tweet
                        
                        # Wait before next batch
                        time.sleep(random.uniform(30, 60))
                        
                    except Exception as e:
                        self.log.error(f"Error in streaming collection for {hashtag}: {e}")
                        time.sleep(60)  # Wait longer on error
                
                # Check if we should continue
                if datetime.now() >= end_time:
                    break
    
    def save_tweets_to_json(self, tweets: List[TweetData], filepath: str) -> None:
        """
        Save tweets to JSON file.
        
        Args:
            tweets: List of TweetData objects
            filepath: Path to save the JSON file
        """
        try:
            # Convert tweets to dictionaries
            tweet_dicts = [tweet.to_dict() for tweet in tweets]
            
            # Save to JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tweet_dicts, f, ensure_ascii=False, indent=2)
            
            self.log.info(f"Saved {len(tweets)} tweets to {filepath}")
            
        except Exception as e:
            self.log.error(f"Error saving tweets to JSON: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection session."""
        return {
            "rate_limiter_stats": self.rate_limiter.get_request_stats(),
            "user_agent": self.rate_limiter.get_user_agent(),
            "headless_mode": self.headless,
            "proxy_enabled": self.use_proxy
        }
    
    def close(self) -> None:
        """Close the WebDriver and clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                self.log.info("WebDriver closed successfully")
            except Exception as e:
                self.log.error(f"Error closing WebDriver: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockTwitterScraper(TwitterScraper):
    """Mock Twitter scraper for testing and development."""
    
    def __init__(self):
        """Initialize mock scraper."""
        self.log = get_logger("mock_twitter_scraper")
        self.config = get_config().data_collection
    
    def _setup_driver(self) -> None:
        """Mock driver setup."""
        self.log.info("Mock WebDriver setup - no actual browser needed")
    
    def collect_tweets(self, hashtags: List[str] = None, max_tweets_per_hashtag: int = 50) -> List[TweetData]:
        """Generate mock tweets for testing."""
        if hashtags is None:
            hashtags = self.config.target_hashtags
        
        mock_tweets = []
        
        for hashtag in hashtags:
            for i in range(max_tweets_per_hashtag):
                tweet_data = TweetData(
                    tweet_id=f"mock_{hashtag}_{i}",
                    username=f"user_{i}",
                    content=f"This is a mock tweet about {hashtag} #{hashtag} #stockmarket",
                    timestamp=datetime.now() - timedelta(hours=random.randint(0, 24)),
                    likes=random.randint(0, 100),
                    retweets=random.randint(0, 50),
                    replies=random.randint(0, 20),
                    hashtags=[hashtag, "#stockmarket"],
                    mentions=[],
                    urls=[],
                    is_retweet=False,
                    is_reply=False,
                    language="en",
                    content_hash=f"mock_hash_{i}",
                    collection_timestamp=datetime.now()
                )
                mock_tweets.append(tweet_data)
        
        self.log.info(f"Generated {len(mock_tweets)} mock tweets")
        return mock_tweets
    
    def close(self) -> None:
        """Mock close method."""
        self.log.info("Mock scraper closed")
