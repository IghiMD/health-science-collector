from utils.scraper_sme_direct import fetch_sme_direct
from pprint import pprint

articles = fetch_sme_direct()
print(f"Načítané články: {len(articles)}")
for i, article in enumerate(articles[:3], 1):
    print(f"\n{i}. {article['title']}")
    print(f"   URL: {article['url']}")
