import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Definícia zdrojov + debug funkcie
SOURCES = {
    # Slovensko
    "TASR Veda": "https://www.teraz.sk/rss/veda-technika.rss",
    "SME Vedatech": "https://vedatech.sme.sk/rss",
    "SAV": "https://www.sav.sk/?feed=rss2",
    "ČTK Zdraví": "https://www.ceskenoviny.cz/sluzby/rss/zpravy.php?temata=118",
    "Akademie věd ČR": "https://www.avcr.cz/rss/aktuality/",
    # Česko
    "iDNES Zdraví": "https://www.idnes.cz/rss/zdravi",
    "ČT24 Věda": "https://ct24.ceskatelevize.cz/veda/rss"
}

def test_rss_feed(url, source_name):
    """Test RSS feedu a vypíše počet článkov a ukážku."""
    try:
        print(f"\n🔎 Testujem {source_name}...")
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"❌ {source_name}: Žiadne články v RSS!")
            return False
        
        print(f"✅ {source_name}: Načítané {len(feed.entries)} článkov")
        print(f"   Ukážka: '{feed.entries[0].title}'")
        print(f"   URL: {feed.entries[0].link}")
        return True
        
    except Exception as e:
        print(f"🔴 {source_name} CHYBA: {str(e)}")
        return False

def test_direct_scraping(url, source_name, selector):
    """Test priameho scrapovania HTML."""
    try:
        print(f"\n🔎 Testujem {source_name} (priamo z HTML)...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select(selector)
        
        if not articles:
            print(f"❌ {source_name}: Žiadne články na stránke!")
            return False
            
        print(f"✅ {source_name}: Nájdených {len(articles)} článkov")
        print(f"   Ukážka: '{articles[0].get_text(strip=True)[:100]}...'")
        return True
        
    except Exception as e:
        print(f"🔴 {source_name} CHYBA: {str(e)}")
        return False

# Spustenie testov
if __name__ == "__main__":
    print("="*60)
    print("🔥 TEST NOVÝCH ZDROJOV 🔥".center(60))
    print("="*60)
    
    # Test RSS feedov
    for name, url in SOURCES.items():
        test_rss_feed(url, name)
    
    # Test priameho scrapovania (príklad pre SAV, ak nemá RSS)
    # test_direct_scraping("https://www.sav.sk/aktuality", "SAV Aktuality", "div.news-item")