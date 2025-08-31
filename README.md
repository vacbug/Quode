# Market Intelligence Data Collection & Analysis System

A comprehensive real-time market intelligence system that scrapes Twitter/X for Indian stock market discussions and converts textual data into quantitative trading signals.

## 🚀 Features

- **Real-time Data Collection**: Scrapes Twitter/X for Indian market hashtags (#nifty50, #sensex, #intraday, #banknifty)
- **Advanced Data Processing**: Text cleaning, normalization, and deduplication
- **Signal Generation**: Converts tweet content into quantitative trading signals using TF-IDF and sentiment analysis
- **Efficient Storage**: Parquet format with optimized schema
- **Memory-Efficient Visualization**: Streaming plots and data sampling techniques
- **Scalable Architecture**: Concurrent processing with rate limiting and anti-bot measures

## 📁 Project Structure

```
market_intelligence/
├── src/
│   ├── data_collection/
│   │   ├── twitter_scraper.py      # Twitter/X scraping engine
│   │   ├── rate_limiter.py         # Rate limiting and anti-bot measures
│   │   └── data_validator.py       # Data validation and cleaning
│   ├── data_processing/
│   │   ├── text_processor.py       # Text cleaning and normalization
│   │   ├── feature_engineering.py  # TF-IDF and feature extraction
│   │   └── deduplication.py        # Data deduplication mechanisms
│   ├── analysis/
│   │   ├── sentiment_analyzer.py   # Sentiment analysis engine
│   │   ├── signal_generator.py     # Trading signal generation
│   │   └── signal_aggregator.py    # Composite signal creation
│   ├── storage/
│   │   ├── parquet_handler.py      # Parquet storage operations
│   │   └── data_manager.py         # Data management utilities
│   ├── visualization/
│   │   ├── streaming_plots.py      # Memory-efficient plotting
│   │   └── dashboard.py            # Real-time dashboard
│   └── utils/
│       ├── config.py               # Configuration management
│       ├── logger.py               # Logging utilities
│       └── helpers.py              # Helper functions
├── data/
│   ├── raw/                        # Raw scraped data
│   ├── processed/                  # Processed data
│   └── signals/                    # Generated signals
├── notebooks/
│   └── analysis_demo.ipynb         # Analysis demonstration
├── tests/
│   └── test_*.py                   # Unit tests
├── requirements.txt                # Python dependencies
├── config.yaml                     # Configuration file
└── main.py                         # Main execution script
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd market_intelligence
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the system**
   ```bash
   # Copy and edit configuration
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```

5. **Run the system**
   ```bash
   python main.py
   ```

##  Usage

### Data Collection
```python
from src.data_collection.twitter_scraper import TwitterScraper

scraper = TwitterScraper()
tweets = scraper.collect_tweets(target_hashtags=['#nifty50', '#sensex'])
```

### Signal Generation
```python
from src.analysis.signal_generator import SignalGenerator

generator = SignalGenerator()
signals = generator.generate_signals(tweets)
```

### Visualization
```python
from src.visualization.dashboard import Dashboard

dashboard = Dashboard()
dashboard.show_real_time_signals()
```

## 🔧 Technical Approach

### Data Collection Strategy
- **Web Scraping**: Uses Selenium with rotating user agents and proxy support
- **Rate Limiting**: Implements exponential backoff and request queuing
- **Anti-Bot Measures**: Random delays, user agent rotation, and session management

### Data Processing Pipeline
1. **Text Cleaning**: Remove special characters, normalize Unicode, handle Indian languages
2. **Feature Engineering**: TF-IDF vectorization, sentiment scoring, hashtag extraction
3. **Deduplication**: Content-based hashing with fuzzy matching

### Signal Generation
- **Sentiment Analysis**: VADER sentiment scoring with domain-specific lexicon
- **Volume Analysis**: Engagement metrics normalization
- **Composite Signals**: Weighted combination of multiple features
- **Confidence Intervals**: Statistical significance testing

### Performance Optimizations
- **Concurrent Processing**: Async/await for I/O operations
- **Memory Management**: Streaming data processing and chunked operations
- **Storage Optimization**: Parquet compression and partitioning

## 📈 Sample Output

The system generates:
- **Raw Tweets**: 2000+ tweets with metadata
- **Processed Data**: Cleaned and normalized text data
- **Trading Signals**: Quantitative signals with confidence intervals
- **Visualizations**: Real-time charts and dashboards

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 📝 Configuration

Edit `config.yaml` to customize:
- Target hashtags and keywords
- Rate limiting parameters
- Storage settings
- Analysis parameters

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This system is for educational and research purposes only. Trading decisions should not be based solely on social media sentiment analysis. Always consult with financial advisors before making investment decisions.
