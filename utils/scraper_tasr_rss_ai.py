import feedparser
from utils.logger import logger

DEFAULT_RSS_URL = "https://www.teraz.sk/rss/zdravie.rss"

def fetch_tasr_articles(rss_url=DEFAULT_RSS_URL):
    try:
        feed = feedparser.parse(rss_url)
        articles = []
        
        for entry in feed.entries:
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "content": entry.get("summary", "")
            })
        
        logger.info(f"Načítané {len(articles)} článkov z TASR")
        return articles
        
    except Exception as e:
        logger.error(f"Chyba pri načítaní TASR RSS: {e}")
        return []
