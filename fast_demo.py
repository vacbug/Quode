#!/usr/bin/env python3
"""
Fast Demo - Market Intelligence System
Runs without Unicode issues and shows performance metrics
"""

import time
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class TweetData:
    username: str
    timestamp: datetime
    content: str
    likes: int
    retweets: int
    replies: int
    mentions: List[str]
    hashtags: List[str]
    urls: List[str]
    language: str
    quality_score: float

class FastMockTwitterScraper:
    def __init__(self, max_tweets: int = 50):
        self.max_tweets = max_tweets
        self.users = ["trader_pro", "market_analyst", "stock_guru", "finance_expert", "investor_insights"]
        self.hashtags = ["#nifty50", "#sensex", "#banknifty", "#intraday", "#stockmarket"]
        
    def collect_tweets(self, hashtags: List[str]) -> List[TweetData]:
        start_time = time.time()
        tweets = []
        
        for i in range(self.max_tweets):
            user = random.choice(self.users)
            hashtag = random.choice(hashtags)
            content = f"Market analysis: {hashtag} showing strong momentum. Technical indicators suggest bullish trend. #stockmarket"
            
            tweet = TweetData(
                username=user,
                timestamp=datetime.now() - timedelta(hours=random.randint(0, 24)),
                content=content,
                likes=random.randint(10, 200),
                retweets=random.randint(5, 50),
                replies=random.randint(2, 20),
                mentions=[],
                hashtags=[hashtag, "#stockmarket"],
                urls=[],
                language="en",
                quality_score=random.uniform(0.8, 1.0)
            )
            tweets.append(tweet)
        
        collection_time = time.time() - start_time
        print(f"[FAST] Collected {len(tweets)} tweets in {collection_time:.3f}s")
        return tweets

class FastDataValidator:
    def __init__(self):
        self.validation_rules = {
            "min_content_length": 10,
            "max_content_length": 280,
            "min_engagement": 1,
            "max_engagement": 1000
        }
    
    def validate_tweets(self, tweets: List[TweetData]) -> Dict[str, Any]:
        start_time = time.time()
        valid_tweets = []
        invalid_count = 0
        
        for tweet in tweets:
            if self._validate_tweet(tweet):
                valid_tweets.append(tweet)
            else:
                invalid_count += 1
        
        validation_time = time.time() - start_time
        quality_score = len(valid_tweets) / len(tweets) if tweets else 0
        
        print(f"[FAST] Validated {len(tweets)} tweets in {validation_time:.3f}s")
        print(f"[FAST] Quality score: {quality_score:.3f}")
        
        return {
            "total_records": len(tweets),
            "valid_records": len(valid_tweets),
            "invalid_records": invalid_count,
            "quality_score": quality_score,
            "processing_time": validation_time,
            "valid_tweets": valid_tweets
        }
    
    def _validate_tweet(self, tweet: TweetData) -> bool:
        return (
            len(tweet.content) >= self.validation_rules["min_content_length"] and
            len(tweet.content) <= self.validation_rules["max_content_length"] and
            tweet.likes >= self.validation_rules["min_engagement"] and
            tweet.retweets >= 0
        )

class FastAnalyzer:
    def __init__(self):
        self.sentiment_words = {
            "positive": ["bullish", "strong", "up", "gain", "profit", "positive", "good"],
            "negative": ["bearish", "weak", "down", "loss", "negative", "bad", "crash"]
        }
    
    def analyze_tweets(self, tweets: List[TweetData]) -> Dict[str, Any]:
        start_time = time.time()
        
        total_engagement = sum(t.likes + t.retweets + t.replies for t in tweets)
        unique_users = len(set(t.username for t in tweets))
        avg_likes = sum(t.likes for t in tweets) / len(tweets) if tweets else 0
        
        # Hashtag analysis
        hashtag_counts = {}
        for tweet in tweets:
            for hashtag in tweet.hashtags:
                hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
        
        # Sentiment analysis
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        
        for tweet in tweets:
            content_lower = tweet.content.lower()
            positive_words = sum(1 for word in self.sentiment_words["positive"] if word in content_lower)
            negative_words = sum(1 for word in self.sentiment_words["negative"] if word in content_lower)
            
            if positive_words > negative_words:
                bullish_count += 1
            elif negative_words > positive_words:
                bearish_count += 1
            else:
                neutral_count += 1
        
        analysis_time = time.time() - start_time
        print(f"[FAST] Analyzed {len(tweets)} tweets in {analysis_time:.3f}s")
        
        return {
            "total_tweets": len(tweets),
            "unique_users": unique_users,
            "total_engagement": total_engagement,
            "average_likes": round(avg_likes, 1),
            "hashtag_counts": hashtag_counts,
            "sentiment_breakdown": {
                "bullish": bullish_count,
                "bearish": bearish_count,
                "neutral": neutral_count
            },
            "processing_time": analysis_time
        }

class FastSignalGenerator:
    def __init__(self):
        self.weights = {
            "sentiment": 0.4,
            "engagement": 0.3,
            "momentum": 0.2,
            "temporal": 0.1
        }
    
    def generate_signals(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        total_tweets = analysis["total_tweets"]
        sentiment_data = analysis["sentiment_breakdown"]
        
        # Calculate signal components
        sentiment_score = (sentiment_data["bullish"] - sentiment_data["bearish"]) / total_tweets
        engagement_score = min(analysis["total_engagement"] / (total_tweets * 100), 1.0)
        momentum_score = sentiment_data["bullish"] / total_tweets
        temporal_score = 0.5  # Mock temporal factor
        
        # Composite signal
        signal_strength = (
            self.weights["sentiment"] * sentiment_score +
            self.weights["engagement"] * engagement_score +
            self.weights["momentum"] * momentum_score +
            self.weights["temporal"] * temporal_score
        )
        
        # Confidence interval (mock)
        confidence_lower = signal_strength - 0.1
        confidence_upper = signal_strength + 0.1
        
        signal_time = time.time() - start_time
        print(f"[FAST] Generated signals in {signal_time:.3f}s")
        
        return {
            "total_signals": total_tweets,
            "bullish_signals": sentiment_data["bullish"],
            "bearish_signals": sentiment_data["bearish"],
            "neutral_signals": sentiment_data["neutral"],
            "signal_strength": round(signal_strength, 3),
            "confidence_interval": [round(confidence_lower, 3), round(confidence_upper, 3)],
            "processing_time": signal_time
        }

def main():
    print("=" * 60)
    print("FAST MARKET INTELLIGENCE SYSTEM DEMO")
    print("=" * 60)
    
    total_start_time = time.time()
    
    # 1. Data Collection
    print("\n1. DATA COLLECTION")
    print("-" * 30)
    scraper = FastMockTwitterScraper(max_tweets=50)
    tweets = scraper.collect_tweets(["#nifty50", "#sensex", "#banknifty", "#intraday"])
    
    # 2. Data Validation
    print("\n2. DATA VALIDATION")
    print("-" * 30)
    validator = FastDataValidator()
    validation_result = validator.validate_tweets(tweets)
    
    # 3. Data Analysis
    print("\n3. DATA ANALYSIS")
    print("-" * 30)
    analyzer = FastAnalyzer()
    analysis_result = analyzer.analyze_tweets(validation_result["valid_tweets"])
    
    # 4. Signal Generation
    print("\n4. SIGNAL GENERATION")
    print("-" * 30)
    signal_generator = FastSignalGenerator()
    signals = signal_generator.generate_signals(analysis_result)
    
    # 5. Save Results
    print("\n5. SAVING RESULTS")
    print("-" * 30)
    results = {
        "collection": {"tweets_count": len(tweets)},
        "validation": validation_result,
        "analysis": analysis_result,
        "signals": signals,
        "performance": {
            "total_time": time.time() - total_start_time
        }
    }
    
    # Save to file
    with open("data/demo_output/fast_demo_results.json", "w") as f:
        json.dump(results, f, default=str, indent=2)
    
    print(f"[FAST] Results saved to: data/demo_output/fast_demo_results.json")
    
    # Summary
    print("\n" + "=" * 60)
    print("FAST DEMO SUMMARY")
    print("=" * 60)
    print(f"Total execution time: {time.time() - total_start_time:.3f}s")
    print(f"Tweets processed: {len(tweets)}")
    print(f"Quality score: {validation_result['quality_score']:.3f}")
    print(f"Signal strength: {signals['signal_strength']}")
    print(f"Bullish sentiment: {signals['bullish_signals']} ({signals['bullish_signals']/signals['total_signals']*100:.1f}%)")
    print("\n[FAST] Demo completed successfully!")

if __name__ == "__main__":
    main()

