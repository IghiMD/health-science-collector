from utils.scraper_sita_rss import fetch_sita_articles
from utils.logger import logger

articles = fetch_sita_articles()
for i, article in enumerate(articles[:3], 1):
    print(f"{i}. {article['title']}")
    print(f"   URL: {article['url']}")
    print(f"   Obsah: {article['content'][:100]}...\n")
