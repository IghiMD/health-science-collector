from utils.news_scraper import scrape_all
from utils.logger import logger
import asyncio

async def main():
    try:
        logger.info("\n🟢 ZAČÍNAM SCRAPOVANIE...")
        articles = scrape_all()
        
        # Štatistiky
        sources = {art['source'] for art in articles}
        logger.info("\n" + "="*60)
        logger.info("📝 SÚHRN ZDROJOV".center(60))
        logger.info("="*60)
        for source in sorted(sources):
            count = sum(1 for art in articles if art['source'] == source)
            logger.info(f"   • {source.upper():<15}: {count:>3} článkov")
        
        logger.info("\n" + "="*60)
        logger.info(f"🟢 SCRAPOVANIE DOKONČENÉ | Celkom {len(articles)} článkov".center(60))
        logger.info("="*60)

    except Exception as e:
        logger.error(f"\n🔴 KRITICKÁ CHYBA: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
