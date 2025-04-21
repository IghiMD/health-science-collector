import feedparser
import requests
from bs4 import BeautifulSoup

SOURCES = {
    # Overené funkčné zdroje
    "ČTK Zdraví": "https://www.ceskenoviny.cz/sluzby/rss/zpravy.php?temata=118",
    "ČT24 Věda": "https://ct24.ceskatelevize.cz/veda/rss",
    # Alternatívy pre nefunkčné RSS
    "SME Vedatech (HTML)": "https://vedatech.sme.sk",
    "SAV Aktuality (HTML)": "https://www.sav.sk/aktuality"
}

def test_rss_feed(url, source_name):
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

def test_html_scraping(url, source_name, title_selector, link_selector="a"):
    try:
        print(f"\n🔎 Testujem {source_name} (HTML)...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        titles = soup.select(title_selector)
        links = soup.select(link_selector) if link_selector else []
        
        if not titles:
            print(f"❌ {source_name}: Žiadne články na stránke!")
            return False
            
        print(f"✅ {source_name}: Nájdených ~{len(titles)} článkov")
        print(f"   Ukážka: '{titles[0].get_text(strip=True)}'")
        print(f"   URL: {links[0]['href'] if links else 'Neuvedené'}")
        return True
        
    except Exception as e:
        print(f"🔴 {source_name} CHYBA: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🔥 TEST ZDROJOV V2 (S FILTROVANÍM) 🔥".center(60))
    print("="*60)
    
    # Test RSS
    test_rss_feed(SOURCES["ČTK Zdraví"], "ČTK Zdraví")
    test_rss_feed(SOURCES["ČT24 Věda"], "ČT24 Věda")
    
    # Test HTML scrapingu
    test_html_scraping(
        SOURCES["SME Vedatech (HTML)"],
        "SME Vedatech",
        title_selector="h3.article-title",
        link_selector="h3.article-title a"
    )
    
    test_html_scraping(
        SOURCES["SAV Aktuality (HTML)"],
        "SAV Aktuality",
        title_selector="div.news-item h2"
    )