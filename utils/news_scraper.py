import feedparser
import requests
from datetime import datetime
from utils.logger import logger

SOURCES = {
    "TASR Zdravie": "https://www.teraz.sk/rss/zdravie.rss", 
    "Aktuality Zdravie": "https://www.aktuality.sk/rss/sekcia/zdravotnictvo/",
    "iDNES Zdraví": "https://www.idnes.cz/rss/zdravi"
}

def fetch_feed(url, source_name):
    try:
        logger.info(f"\n🔎 Načítavam: {source_name.upper()}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        feed = feedparser.parse(response.content)
        
        if not feed.entries:
            logger.warning(f"⚠️ Žiadne články v {source_name}")
            return []

        logger.info(f"📡 Zdroj: {url}")
        logger.info(f"📊 Počet článkov: {len(feed.entries)}")
        
        articles = []
        for idx, entry in enumerate(feed.entries, 1):
            article = {
                'title': entry.get('title', 'Bez názvu').strip(),
                'url': entry.get('link', '').strip(),
                'content': entry.get('description', '').strip(),
                'source': source_name,
                'published': entry.get('published', 'neuvedený')
            }
            articles.append(article)
            
            # Detailný výpis každého článku
            logger.info(f"\n📌 Článok {idx}:")
            logger.info(f"   🏷️ Titulok: {article['title']}")
            logger.info(f"   🔗 URL: {article['url']}")
            logger.info(f"   📅 Dátum: {article['published']}")
            logger.info(f"   📝 Obsah: {article['content'][:150]}...")
            logger.info(f"   📏 Dĺžka: {len(article['content'])} znakov")

        logger.info(f"\n✅ {source_name}: Načítané {len(articles)} článkov")
        return articles

    except Exception as e:
        logger.error(f"❌ Chyba v {source_name}: {str(e)}", exc_info=True)
        return []

def scrape_all():
    logger.info("\n" + "="*60)
    logger.info("🌐 SPÚŠŤAM SCRAPOVANIE ZDROJOV".center(60))
    logger.info("="*60)
    
    all_articles = []
    for name, url in SOURCES.items():
        all_articles.extend(fetch_feed(url, name))
    
    logger.info("\n" + "="*60)
    logger.info(f"📊 CELKOM: {len(all_articles)} článkov z {len(SOURCES)} zdrojov".center(60))
    logger.info("="*60)
    return all_articles
