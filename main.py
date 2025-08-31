#!/usr/bin/env python3
"""
Main execution script for the Market Intelligence System.
Orchestrates the complete data collection and analysis pipeline.
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.config import get_config
from src.utils.logger import get_logger, LogContext, log_data_collection_start
from src.data_collection.twitter_scraper import TwitterScraper, MockTwitterScraper
from src.data_collection.data_validator import DataValidator


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Market Intelligence Data Collection System")
    
    parser.add_argument(
        "--mode",
        choices=["collect", "validate", "analyze", "full"],
        default="full",
        help="Operation mode (default: full)"
    )
    
    parser.add_argument(
        "--hashtags",
        nargs="+",
        help="Specific hashtags to collect (overrides config)"
    )
    
    parser.add_argument(
        "--max-tweets",
        type=int,
        help="Maximum tweets to collect per hashtag"
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data for testing"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Output directory for data files"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    return parser.parse_args()


def setup_environment():
    """Set up the environment and create necessary directories."""
    log = get_logger("main")
    
    # Create output directories
    output_dirs = ["data/raw", "data/processed", "data/signals", "logs"]
    for dir_path in output_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    log.info("Environment setup completed")


def collect_data(hashtags: List[str] = None, max_tweets: int = None, 
                mock: bool = False, headless: bool = True) -> List[Dict[str, Any]]:
    """
    Collect tweet data from Twitter/X.
    
    Args:
        hashtags: List of hashtags to collect
        max_tweets: Maximum tweets per hashtag
        mock: Whether to use mock data
        headless: Whether to run browser headless
    
    Returns:
        List of tweet dictionaries
    """
    log = get_logger("main")
    
    with LogContext("data_collection", "main"):
        # Initialize scraper
        if mock:
            scraper = MockTwitterScraper()
            log.info("Using mock scraper for testing")
        else:
            scraper = TwitterScraper(headless=headless)
            log.info("Using real Twitter scraper")
        
        try:
            # Collect tweets
            tweets = scraper.collect_tweets(hashtags=hashtags, max_tweets_per_hashtag=max_tweets)
            
            # Convert to dictionaries for storage
            tweet_dicts = [tweet.to_dict() for tweet in tweets]
            
            log.info(f"Successfully collected {len(tweet_dicts)} tweets")
            
            return tweet_dicts
            
        finally:
            scraper.close()


def validate_data(tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate collected tweet data.
    
    Args:
        tweets: List of tweet dictionaries
    
    Returns:
        Validation report
    """
    log = get_logger("main")
    
    with LogContext("data_validation", "main"):
        validator = DataValidator()
        
        # Convert back to TweetData objects for validation
        from src.data_collection.twitter_scraper import TweetData
        from datetime import datetime
        
        tweet_objects = []
        for tweet_dict in tweets:
            # Convert timestamp string back to datetime
            tweet_dict['timestamp'] = datetime.fromisoformat(tweet_dict['timestamp'])
            tweet_dict['collection_timestamp'] = datetime.fromisoformat(tweet_dict['collection_timestamp'])
            
            tweet_objects.append(TweetData(**tweet_dict))
        
        # Validate tweets
        metrics = validator.validate_tweet_batch(tweet_objects)
        report = validator.generate_validation_report(metrics)
        
        log.info(f"Validation completed - Quality score: {metrics.quality_score:.3f}")
        
        return report


def save_data(tweets: List[Dict[str, Any]], output_dir: str = "data"):
    """
    Save collected data to files.
    
    Args:
        tweets: List of tweet dictionaries
        output_dir: Output directory
    """
    log = get_logger("main")
    
    with LogContext("data_saving", "main"):
        import json
        from datetime import datetime
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw data
        raw_file = Path(output_dir) / "raw" / f"tweets_{timestamp}.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
        
        log.info(f"Saved {len(tweets)} tweets to {raw_file}")
        
        # Save summary
        summary = {
            "collection_timestamp": datetime.now().isoformat(),
            "total_tweets": len(tweets),
            "hashtags": list(set([tag for tweet in tweets for tag in tweet.get('hashtags', [])])),
            "languages": list(set([tweet.get('language', 'en') for tweet in tweets])),
            "date_range": {
                "earliest": min([tweet['timestamp'] for tweet in tweets]),
                "latest": max([tweet['timestamp'] for tweet in tweets])
            }
        }
        
        summary_file = Path(output_dir) / "raw" / f"summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        log.info(f"Saved summary to {summary_file}")


def run_full_pipeline(args):
    """Run the complete data collection and analysis pipeline."""
    log = get_logger("main")
    
    with LogContext("full_pipeline", "main"):
        log.info("Starting full pipeline execution")
        
        # Get configuration
        config = get_config()
        
        # Determine hashtags to collect
        hashtags = args.hashtags or config.data_collection.target_hashtags
        max_tweets = args.max_tweets or config.collection_settings.get("min_tweets", 2000) // len(hashtags)
        
        log_data_collection_start(hashtags, max_tweets * len(hashtags))
        
        # Step 1: Collect data
        log.info("Step 1: Collecting data...")
        tweets = collect_data(
            hashtags=hashtags,
            max_tweets=max_tweets,
            mock=args.mock,
            headless=args.headless
        )
        
        if not tweets:
            log.warning("No tweets collected, stopping pipeline")
            return
        
        # Step 2: Save raw data
        log.info("Step 2: Saving raw data...")
        save_data(tweets, args.output_dir)
        
        # Step 3: Validate data
        log.info("Step 3: Validating data...")
        validation_report = validate_data(tweets)
        
        # Step 4: Save validation report
        import json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        validation_file = Path(args.output_dir) / "processed" / f"validation_report_{timestamp}.json"
        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, ensure_ascii=False, indent=2)
        
        log.info(f"Validation report saved to {validation_file}")
        
        # Step 5: Generate summary
        log.info("Step 4: Generating summary...")
        summary = {
            "pipeline_execution": {
                "timestamp": datetime.now().isoformat(),
                "mode": args.mode,
                "hashtags": hashtags,
                "max_tweets_per_hashtag": max_tweets,
                "mock_mode": args.mock
            },
            "collection_results": {
                "total_tweets": len(tweets),
                "unique_hashtags": len(set([tag for tweet in tweets for tag in tweet.get('hashtags', [])])),
                "languages": list(set([tweet.get('language', 'en') for tweet in tweets]))
            },
            "validation_results": validation_report
        }
        
        summary_file = Path(args.output_dir) / "processed" / f"pipeline_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        log.info(f"Pipeline summary saved to {summary_file}")
        log.info("Full pipeline completed successfully")


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Setup environment
    setup_environment()
    
    # Initialize logging
    log = get_logger("main")
    log.info("Market Intelligence System starting...")
    
    try:
        if args.mode == "collect":
            # Data collection only
            config = get_config()
            hashtags = args.hashtags or config.data_collection.target_hashtags
            max_tweets = args.max_tweets or config.collection_settings.get("min_tweets", 2000) // len(hashtags)
            
            tweets = collect_data(
                hashtags=hashtags,
                max_tweets=max_tweets,
                mock=args.mock,
                headless=args.headless
            )
            save_data(tweets, args.output_dir)
            
        elif args.mode == "validate":
            # Validation only (requires existing data)
            log.error("Validation mode requires existing data files")
            return 1
            
        elif args.mode == "analyze":
            # Analysis only (requires processed data)
            log.error("Analysis mode requires processed data files")
            return 1
            
        elif args.mode == "full":
            # Full pipeline
            run_full_pipeline(args)
        
        log.info("Market Intelligence System completed successfully")
        return 0
        
    except KeyboardInterrupt:
        log.info("Pipeline interrupted by user")
        return 1
    except Exception as e:
        log.error(f"Pipeline failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
