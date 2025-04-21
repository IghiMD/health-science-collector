import feedparser
from pprint import pprint

def test_sme_feed():
    print("Testujem SME Zdravie RSS feed...")
    feed_url = "https://zdravie.sme.sk/rss"
    feed = feedparser.parse(feed_url)
    
    print(f"\nStav: {feed.status}")
    print(f"Počet článkov: {len(feed.entries)}")
    
    if feed.entries:
        print("\nPrvý článok:")
        pprint({
            'title': feed.entries[0].title,
            'link': feed.entries[0].link,
            'description': feed.entries[0].description[:100] + '...'
        })

test_sme_feed()
