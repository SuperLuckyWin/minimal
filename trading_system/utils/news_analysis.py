import feedparser
from datetime import datetime
import time

class NewsAnalyzer:
    def __init__(self, news_source, interval=60, keywords=[]):
      self.news_source = news_source
      self.interval = interval
      self.keywords = keywords
      self.last_update = None

    def fetch_news(self):
      """获取最新新闻"""
      try:
        feed = feedparser.parse(self.news_source)
        return feed.entries
      except Exception as e:
        print(f'Error fetching news: {e}')
        return []

    def analyze_news(self, entries):
      """分析新闻情绪"""
      signals = []
      for entry in entries:
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()

        if any(keyword in title or keyword in summary for keyword in self.keywords):
           sentiment = self.get_sentiment(title + ' ' + summary) #简化，使用关键词匹配代替情绪分析
           if sentiment == 'positive':
              signals.append('BUY')
           elif sentiment == 'negative':
              signals.append('SELL')
      return signals

    def get_sentiment(self, text):
      """使用关键词判断情绪"""
      positive_keywords = ["bullish", "positive", "surge", "increase", "uptrend", "buy"]
      negative_keywords = ["bearish", "negative", "drop", "decrease", "downtrend", "sell"]

      if any(keyword in text for keyword in positive_keywords):
         return 'positive'
      if any(keyword in text for keyword in negative_keywords):
           return 'negative'
      return 'neutral'

    def generate_signal(self):
      """生成交易信号"""
      current_time = datetime.now()
      if not self.last_update or (current_time - self.last_update).total_seconds() >= self.interval:
        news_entries = self.fetch_news()
        signals = self.analyze_news(news_entries)
        self.last_update = current_time
        if signals:
          return signals[0] # 只取第一个信号
      return None
