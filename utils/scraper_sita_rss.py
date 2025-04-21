import feedparser
import requests
from bs4 import BeautifulSoup
from utils.logger import logger

def fetch_sita_articles():
    try:
        # Alternatívny RSS feed
        feed = feedparser.parse("https://www.webnoviny.sk/tag/sita-zdravie/feed/")
        articles = []
        
        for entry in feed.entries:
            # Načítanie plného textu z URL
            full_text = ""
            try:
                response = requests.get(entry.link, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                article_body = soup.find('div', class_='article-content')
                full_text = article_body.get_text() if article_body else entry.description
            except Exception as e:
                logger.warning(f"Nepodarilo sa načítať článok {entry.link}: {e}")
                full_text = entry.description
            
            articles.append({
                "title": entry.title,
                "url": entry.link,
                "content": full_text
            })
        
        logger.info(f"Načítané {len(articles)} článkov z SITA")
        return articles
        
    except Exception as e:
        logger.error(f"Chyba pri SITA: {str(e)}")
        return []
