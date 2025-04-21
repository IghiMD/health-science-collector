import feedparser
import requests
from bs4 import BeautifulSoup
from utils.logger import logger

def test_source(url, source_name):
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            logger.warning(f"{source_name}: Žiadne články v RSS feede")
            return False
        
        test_url = feed.entries[0].link
        response = requests.get(test_url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"{source_name}: Články nedostupné (HTTP {response.status_code})")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"{source_name} chyba: {str(e)}")
        return False

# Test rôznych zdrojov
sources = [
    ("https://www.teraz.sk/rss/zdravie.rss", "TASR"),
    ("https://www.sita.sk/rss/zdravie", "SITA"),
    ("https://www.webnoviny.sk/tag/sita-zdravie/feed/", "Webnoviny"),
    ("https://www.topky.sk/rss/krajina", "Topky")
]

for url, name in sources:
    print(f"\nTestujem {name} ({url}):")
    if test_source(url, name):
        print("✅ Funkčné")
    else:
        print("❌ Problém")
