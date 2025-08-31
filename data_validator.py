"""
Data validation module for ensuring data quality and integrity.
Validates tweet data and provides data quality metrics.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.helpers import validate_url, safe_int, safe_float
from .twitter_scraper import TweetData


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float


@dataclass
class DataQualityMetrics:
    """Metrics for data quality assessment."""
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_fields: Dict[str, int]
    quality_score: float
    validation_errors: Dict[str, int]
    processing_time: float


class DataValidator:
    """Validates tweet data for quality and integrity."""
    
    def __init__(self):
        """Initialize the data validator."""
        self.config = get_config().data_collection
        self.log = get_logger("data_validator")
        self.validation_rules = self._setup_validation_rules()
    
    def _setup_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Set up validation rules for different fields."""
        return {
            'tweet_id': {
                'required': True,
                'pattern': r'^[a-zA-Z0-9_]+$',
                'min_length': 1,
                'max_length': 50
            },
            'username': {
                'required': True,
                'pattern': r'^[a-zA-Z0-9_]+$',
                'min_length': 1,
                'max_length': 15
            },
            'content': {
                'required': True,
                'min_length': 1,
                'max_length': 280,
                'forbidden_patterns': [
                    r'^\s*$',  # Empty or whitespace only
                    r'^RT\s*$',  # Just RT
                    r'^@\w+\s*$'  # Just a mention
                ]
            },
            'timestamp': {
                'required': True,
                'min_date': datetime.now() - timedelta(days=7),
                'max_date': datetime.now() + timedelta(hours=1)
            },
            'likes': {
                'required': False,
                'min_value': 0,
                'max_value': 1000000
            },
            'retweets': {
                'required': False,
                'min_value': 0,
                'max_value': 1000000
            },
            'replies': {
                'required': False,
                'min_value': 0,
                'max_value': 1000000
            },
            'hashtags': {
                'required': False,
                'max_count': 30,
                'pattern': r'^#[a-zA-Z0-9_]+$'
            },
            'mentions': {
                'required': False,
                'max_count': 50,
                'pattern': r'^@[a-zA-Z0-9_]+$'
            },
            'urls': {
                'required': False,
                'max_count': 10,
                'validate_urls': True
            },
            'language': {
                'required': False,
                'allowed_values': ['en', 'hi', 'ta', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa']
            }
        }
    
    def validate_tweet(self, tweet: TweetData) -> ValidationResult:
        """
        Validate a single tweet.
        
        Args:
            tweet: TweetData object to validate
        
        Returns:
            ValidationResult object
        """
        errors = []
        warnings = []
        
        # Validate each field
        for field_name, rules in self.validation_rules.items():
            field_value = getattr(tweet, field_name, None)
            field_errors, field_warnings = self._validate_field(field_name, field_value, rules)
            errors.extend(field_errors)
            warnings.extend(field_warnings)
        
        # Additional business logic validations
        business_errors, business_warnings = self._validate_business_logic(tweet)
        errors.extend(business_errors)
        warnings.extend(business_warnings)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(tweet, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score
        )
    
    def _validate_field(self, field_name: str, field_value: Any, rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Validate a single field according to rules.
        
        Args:
            field_name: Name of the field
            field_value: Value to validate
            rules: Validation rules for the field
        
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check if required
        if rules.get('required', False) and field_value is None:
            errors.append(f"{field_name}: Field is required but missing")
            return errors, warnings
        
        if field_value is None:
            return errors, warnings
        
        # Type-specific validations
        if isinstance(field_value, str):
            str_errors, str_warnings = self._validate_string_field(field_name, field_value, rules)
            errors.extend(str_errors)
            warnings.extend(str_warnings)
        elif isinstance(field_value, int):
            int_errors, int_warnings = self._validate_integer_field(field_name, field_value, rules)
            errors.extend(int_errors)
            warnings.extend(int_warnings)
        elif isinstance(field_value, datetime):
            date_errors, date_warnings = self._validate_datetime_field(field_name, field_value, rules)
            errors.extend(date_errors)
            warnings.extend(date_warnings)
        elif isinstance(field_value, list):
            list_errors, list_warnings = self._validate_list_field(field_name, field_value, rules)
            errors.extend(list_errors)
            warnings.extend(list_warnings)
        
        return errors, warnings
    
    def _validate_string_field(self, field_name: str, value: str, rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate string field."""
        errors = []
        warnings = []
        
        # Length validation
        if 'min_length' in rules and len(value) < rules['min_length']:
            errors.append(f"{field_name}: Length {len(value)} is below minimum {rules['min_length']}")
        
        if 'max_length' in rules and len(value) > rules['max_length']:
            errors.append(f"{field_name}: Length {len(value)} exceeds maximum {rules['max_length']}")
        
        # Pattern validation
        if 'pattern' in rules:
            if not re.match(rules['pattern'], value):
                errors.append(f"{field_name}: Value '{value}' does not match pattern {rules['pattern']}")
        
        # Forbidden patterns
        if 'forbidden_patterns' in rules:
            for pattern in rules['forbidden_patterns']:
                if re.match(pattern, value):
                    errors.append(f"{field_name}: Value '{value}' matches forbidden pattern {pattern}")
        
        return errors, warnings
    
    def _validate_integer_field(self, field_name: str, value: int, rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate integer field."""
        errors = []
        warnings = []
        
        # Range validation
        if 'min_value' in rules and value < rules['min_value']:
            errors.append(f"{field_name}: Value {value} is below minimum {rules['min_value']}")
        
        if 'max_value' in rules and value > rules['max_value']:
            errors.append(f"{field_name}: Value {value} exceeds maximum {rules['max_value']}")
        
        return errors, warnings
    
    def _validate_datetime_field(self, field_name: str, value: datetime, rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate datetime field."""
        errors = []
        warnings = []
        
        # Date range validation
        if 'min_date' in rules and value < rules['min_date']:
            errors.append(f"{field_name}: Date {value} is before minimum {rules['min_date']}")
        
        if 'max_date' in rules and value > rules['max_date']:
            errors.append(f"{field_name}: Date {value} is after maximum {rules['max_date']}")
        
        return errors, warnings
    
    def _validate_list_field(self, field_name: str, value: List, rules: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate list field."""
        errors = []
        warnings = []
        
        # Count validation
        if 'max_count' in rules and len(value) > rules['max_count']:
            errors.append(f"{field_name}: Count {len(value)} exceeds maximum {rules['max_count']}")
        
        # Pattern validation for list items
        if 'pattern' in rules:
            for item in value:
                if not re.match(rules['pattern'], str(item)):
                    errors.append(f"{field_name}: Item '{item}' does not match pattern {rules['pattern']}")
        
        # URL validation for URL lists
        if field_name == 'urls' and rules.get('validate_urls', False):
            for url in value:
                if not validate_url(url):
                    errors.append(f"{field_name}: Invalid URL '{url}'")
        
        return errors, warnings
    
    def _validate_business_logic(self, tweet: TweetData) -> Tuple[List[str], List[str]]:
        """Validate business logic rules."""
        errors = []
        warnings = []
        
        # Check for suspicious engagement patterns
        total_engagement = tweet.likes + tweet.retweets + tweet.replies
        
        if total_engagement > 10000 and tweet.likes > 0:
            engagement_ratio = tweet.likes / total_engagement
            if engagement_ratio > 0.95:
                warnings.append("Suspicious engagement pattern: very high likes ratio")
        
        # Check for spam indicators
        if len(tweet.hashtags) > 20:
            warnings.append("High number of hashtags may indicate spam")
        
        if len(tweet.mentions) > 30:
            warnings.append("High number of mentions may indicate spam")
        
        # Check for duplicate content indicators
        if len(tweet.content) < 10:
            warnings.append("Very short content may be low quality")
        
        # Check for language consistency
        if tweet.language not in ['en', 'hi'] and len(tweet.content) > 50:
            warnings.append(f"Content in language '{tweet.language}' may need special processing")
        
        return errors, warnings
    
    def _calculate_quality_score(self, tweet: TweetData, errors: List[str], warnings: List[str]) -> float:
        """
        Calculate quality score for a tweet.
        
        Args:
            tweet: TweetData object
            errors: List of validation errors
            warnings: List of validation warnings
        
        Returns:
            Quality score between 0 and 1
        """
        base_score = 1.0
        
        # Deduct for errors
        error_penalty = len(errors) * 0.2
        base_score -= error_penalty
        
        # Deduct for warnings
        warning_penalty = len(warnings) * 0.05
        base_score -= warning_penalty
        
        # Bonus for good engagement
        if tweet.likes + tweet.retweets + tweet.replies > 100:
            base_score += 0.1
        
        # Bonus for good content length
        if 50 <= len(tweet.content) <= 200:
            base_score += 0.05
        
        # Bonus for relevant hashtags
        relevant_hashtags = ['#nifty50', '#sensex', '#banknifty', '#intraday', '#stockmarket']
        if any(tag.lower() in relevant_hashtags for tag in tweet.hashtags):
            base_score += 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def validate_tweet_batch(self, tweets: List[TweetData]) -> DataQualityMetrics:
        """
        Validate a batch of tweets and return quality metrics.
        
        Args:
            tweets: List of TweetData objects
        
        Returns:
            DataQualityMetrics object
        """
        import time
        
        start_time = time.time()
        
        total_records = len(tweets)
        valid_records = 0
        invalid_records = 0
        duplicate_records = 0
        missing_fields = {}
        validation_errors = {}
        content_hashes = set()
        
        for tweet in tweets:
            # Check for duplicates
            if tweet.content_hash in content_hashes:
                duplicate_records += 1
                continue
            content_hashes.add(tweet.content_hash)
            
            # Validate tweet
            validation_result = self.validate_tweet(tweet)
            
            if validation_result.is_valid:
                valid_records += 1
            else:
                invalid_records += 1
            
            # Track errors
            for error in validation_result.errors:
                error_type = error.split(':')[0] if ':' in error else 'unknown'
                validation_errors[error_type] = validation_errors.get(error_type, 0) + 1
        
        # Calculate overall quality score
        quality_score = valid_records / total_records if total_records > 0 else 0.0
        
        processing_time = time.time() - start_time
        
        return DataQualityMetrics(
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            duplicate_records=duplicate_records,
            missing_fields=missing_fields,
            quality_score=quality_score,
            validation_errors=validation_errors,
            processing_time=processing_time
        )
    
    def filter_valid_tweets(self, tweets: List[TweetData], min_quality_score: float = 0.5) -> List[TweetData]:
        """
        Filter tweets based on validation results.
        
        Args:
            tweets: List of TweetData objects
            min_quality_score: Minimum quality score to include
        
        Returns:
            List of valid TweetData objects
        """
        valid_tweets = []
        
        for tweet in tweets:
            validation_result = self.validate_tweet(tweet)
            
            if validation_result.is_valid and validation_result.quality_score >= min_quality_score:
                valid_tweets.append(tweet)
        
        self.log.info(f"Filtered {len(valid_tweets)} valid tweets from {len(tweets)} total tweets")
        return valid_tweets
    
    def generate_validation_report(self, metrics: DataQualityMetrics) -> Dict[str, Any]:
        """
        Generate a comprehensive validation report.
        
        Args:
            metrics: DataQualityMetrics object
        
        Returns:
            Dictionary containing validation report
        """
        report = {
            'summary': {
                'total_records': metrics.total_records,
                'valid_records': metrics.valid_records,
                'invalid_records': metrics.invalid_records,
                'duplicate_records': metrics.duplicate_records,
                'quality_score': metrics.quality_score,
                'processing_time': metrics.processing_time
            },
            'quality_metrics': {
                'validity_rate': metrics.valid_records / metrics.total_records if metrics.total_records > 0 else 0.0,
                'duplicate_rate': metrics.duplicate_records / metrics.total_records if metrics.total_records > 0 else 0.0,
                'error_rate': metrics.invalid_records / metrics.total_records if metrics.total_records > 0 else 0.0
            },
            'validation_errors': metrics.validation_errors,
            'recommendations': self._generate_recommendations(metrics)
        }
        
        return report
    
    def _generate_recommendations(self, metrics: DataQualityMetrics) -> List[str]:
        """Generate recommendations based on validation metrics."""
        recommendations = []
        
        if metrics.quality_score < 0.8:
            recommendations.append("Consider improving data collection to increase quality score")
        
        if metrics.duplicate_records > metrics.total_records * 0.1:
            recommendations.append("Implement better deduplication mechanisms")
        
        if metrics.invalid_records > metrics.total_records * 0.2:
            recommendations.append("Review data collection process to reduce invalid records")
        
        if not recommendations:
            recommendations.append("Data quality is good, no immediate actions required")
        
        return recommendations
