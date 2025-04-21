import feedparser

# Zdroj + kľúčové slová pre filter
SOURCE = {
    "name": "ČTK Zdraví",
    "url": "https://www.ceskenoviny.cz/sluzby/rss/zpravy.php?temata=118",
    "keywords": ["zdraví", "lékař", "studie", "věda", "výzkum", "nemoc", "léčba", "pacient"]
}

def is_relevant(article, keywords):
    """Overí, či článok obsahuje kľúčové slová."""
    text = f"{article.title} {article.get('description', '')}".lower()
    return any(keyword in text for keyword in keywords)

def test_source(source):
    print(f"\n🔎 Testujem {source['name']}...")
    feed = feedparser.parse(source['url'])
    
    if not feed.entries:
        print(f"❌ {source['name']}: Žiadne články!")
        return
    
    relevant_count = 0
    print(f"✅ {source['name']}: Načítané {len(feed.entries)} článkov")
    
    for idx, entry in enumerate(feed.entries[:5], 1):  # Ukážka prvých 5
        relevance = "RELEVANTNÝ" if is_relevant(entry, source['keywords']) else "MIMO TÉMU"
        print(f"\n📌 Článok {idx}: {relevance}")
        print(f"   Titulok: {entry.title}")
        print(f"   URL: {entry.link}")
        print(f"   Popis: {entry.get('description', '')[:100]}...")
        
        if "RELEVANTNÝ" in relevance:
            relevant_count += 1
    
    print(f"\n📊 Záver: {relevant_count}/{min(5, len(feed.entries))} relevantných článkov")

if __name__ == "__main__":
    print("="*60)
    print("🔥 TEST RELEVANCIA ČLÁNKOV 🔥".center(60))
    print("="*60)
    test_source(SOURCE)