import feedparser

SOURCES = {
    "ČTK Zdraví": "https://www.ceskenoviny.cz/sluzby/rss/zpravy.php?temata=118",
    "Denník N Vedomosť": "https://dennikn.sk/vedomosti/feed/",
    "UK Bratislava": "https://uniba.sk/veda/aktuality/feed/"
}

def test_rss_feed(url, source_name):
    try:
        print(f"\n🔎 Testujem {source_name}...")
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"❌ {source_name}: Žiadne články v RSS!")
            return False
        
        print(f"✅ {source_name}: Načítané {len(feed.entries)} článkov")
        print(f"   Ukážka: '{feed.entries[0].title[:50]}...'")
        print(f"   URL: {feed.entries[0].link}")
        return True
        
    except Exception as e:
        print(f"🔴 {source_name} CHYBA: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🔥 TEST ZDROJOV V3 (LEN OVERENÉ) 🔥".center(60))
    print("="*60)
    
    for name, url in SOURCES.items():
        test_rss_feed(url, name)