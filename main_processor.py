#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hlavný koordinačný skript pre zber, spracovanie a ukladanie zdravotníckych a vedeckých správ.
"""

import os
import sys
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
# Načítanie premenných z .env súboru
from dotenv import load_dotenv
load_dotenv()  # toto načíta premenné z .env súboru do prostredia
import schedule
import newspaper
import re
import argparse

# Import vlastných modulov
from utils.source_relevance import SourceRelevanceTester, DEFAULT_SOURCES
from utils.article_processor import ArticleProcessor
from utils.file_manager import FileManager
from utils.email_processor import EmailProcessor

# Konfigurácia loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/main_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main_processor")

# Konfigurácia
MAX_SUMMARY_ARTICLES = 5  # Maximálny počet článkov v súhrnnom dokumente
CYCLE_START_HOUR = 8  # Hodina, kedy sa začína denný cyklus (8:00)
EMAIL_PROCESSING_DAYS = 1  # Počet dní do minulosti, z ktorých sa majú spracovať e-maily

class NewsProcessor:
    """Hlavná trieda pre spracovanie správ."""
    
    def __init__(self):
        """Inicializácia procesora správ."""
        self.source_tester = SourceRelevanceTester()
        self.article_processor = ArticleProcessor()
        self.file_manager = FileManager()
        self.email_processor = EmailProcessor()
        self.daily_summary_articles = []  # Zoznam článkov pre denný súhrn
        self.current_date = datetime.now().date()
        
        # Vytvorenie priečinkov logs a output, ak neexistujú
        os.makedirs("logs", exist_ok=True)
        os.makedirs("output", exist_ok=True)
    
    def _is_new_day_cycle(self) -> bool:
        """
        Kontroluje, či začal nový denný cyklus (po 8:00).
        
        Returns:
            True ak začal nový denný cyklus, inak False.
        """
        now = datetime.now()
        return (now.date() > self.current_date or 
                (now.date() == self.current_date and now.hour >= CYCLE_START_HOUR and 
                 self.current_date < now.date()))
    
    def _get_links_from_source(self, source: Dict) -> List[str]:
        """
        Získa zoznam odkazov na články z daného zdroja.
        
        Args:
            source: Dictionary s informáciami o zdroji.
            
        Returns:
            Zoznam URL adries článkov.
        """
        try:
            # Stiahnutie článkov pomocou newspaper3k
            news_source = newspaper.build(source['url'], memoize_articles=False)
            
            # Získanie odkazov na články
            article_urls = []
            for article in news_source.articles:
                article_urls.append(article.url)
            
            logger.info(f"Získaných {len(article_urls)} odkazov zo zdroja {source['name']}")
            return article_urls
        
        except Exception as e:
            logger.error(f"Chyba pri získavaní odkazov zo zdroja {source['name']}: {str(e)}")
            return []
    
    def _filter_relevant_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Filtruje a zoraďuje články podľa relevancie.
        
        Args:
            articles: Zoznam článkov na filtrovanie.
            
        Returns:
            Filtrovaný a zoradený zoznam článkov.
        """
        # Ak je menej článkov ako MAX_SUMMARY_ARTICLES, vrátime všetky
        if len(articles) <= MAX_SUMMARY_ARTICLES:
            return articles
        
        # Ohodnotenie relevancie pre každý článok
        for article in articles:
            # Ak článok už má skóre relevancie, preskočíme ho
            if 'relevance_score' in article:
                continue
                
            # Kontrola relevancie článku
            is_relevant, relevance_score, reason = self.source_tester.check_article_relevance(article)
            
            # Uloženie skóre a dôvodu
            article['relevance_score'] = relevance_score
            article['relevance_reason'] = reason
            article['is_relevant'] = is_relevant
        
        # Filter len na relevantné články
        relevant_articles = [article for article in articles if article.get('is_relevant', False)]
        
        # Ak máme menej relevantných článkov ako MAX_SUMMARY_ARTICLES, vrátime všetky relevantné
        if len(relevant_articles) <= MAX_SUMMARY_ARTICLES:
            # Zoradenie podľa skóre relevancie (od najvyššieho)
            return sorted(relevant_articles, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Inak vrátime MAX_SUMMARY_ARTICLES najrelevantnejších článkov
        sorted_articles = sorted(relevant_articles, key=lambda x: x.get('relevance_score', 0), reverse=True)
        return sorted_articles[:MAX_SUMMARY_ARTICLES]
    
    def process_email_sources(self) -> List[Dict]:
        """
        Spracuje zdravotnícke a vedecké zdroje z e-mailovej schránky.
        
        Returns:
            Zoznam spracovaných článkov z e-mailov.
        """
        logger.info("Začínam spracovanie e-mailových zdrojov...")
        
        # Získanie URL adries z e-mailov
        urls = self.email_processor.get_urls_from_emails(days=EMAIL_PROCESSING_DAYS)
        logger.info(f"Získaných {len(urls)} URL adries z e-mailov.")
        
        # Spracovanie URL adries
        processed_articles = []
        
        for url in urls:
            try:
                # Spracovanie článku z URL
                article_data = self.article_processor.process_article(url)
                
                if article_data:
                    # Kontrola relevancie článku
                    is_relevant, relevance_score, reason = self.source_tester.check_article_relevance(article_data)
                    
                    # Uloženie skóre a dôvodu
                    article_data['relevance_score'] = relevance_score
                    article_data['relevance_reason'] = reason
                    article_data['is_relevant'] = is_relevant
                    
                    if is_relevant:
                        processed_articles.append(article_data)
                        logger.info(f"URL z e-mailu úspešne spracovaná: {url}")
                    else:
                        logger.info(f"URL z e-mailu nie je relevantná: {url} - {reason}")
            
            except Exception as e:
                logger.error(f"Chyba pri spracovaní URL z e-mailu {url}: {str(e)}")
        
        logger.info(f"Spracovaných {len(processed_articles)} relevantných článkov z e-mailov.")
        return processed_articles
    
    def process_hourly_news(self):
        """Spracuje aktuálne správy pre danú hodinu."""
        logger.info("=== Začínam hodinové spracovanie správ ===")
        current_time = datetime.now()
        logger.info(f"Aktuálny čas: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Kontrola, či začal nový denný cyklus
        if self._is_new_day_cycle():
            logger.info("Začínam nový denný cyklus...")
            self.current_date = datetime.now().date()
            self.daily_summary_articles = []  # Reset zoznamu článkov
        
        # Aktuálny čas
        now = datetime.now()
        
        # Spracovanie webových zdrojov
        web_articles = self.process_web_sources()
        logger.info(f"Získaných {len(web_articles)} článkov z webových zdrojov.")
        
        # Spracovanie e-mailových zdrojov
        email_articles = self.process_email_sources()
        logger.info(f"Získaných {len(email_articles)} článkov z e-mailových zdrojov.")
        
        # Spojenie článkov z oboch zdrojov
        all_articles = web_articles + email_articles
        logger.info(f"Celkovo získaných {len(all_articles)} článkov.")
        
        # Vytvorenie hodinových súborov
        if all_articles:
            # Vytvorenie hodinových DOCX a HTML súborov
            docx_file, html_file = self.file_manager.create_hourly_files(all_articles, now)
            logger.info(f"Vytvorené hodinové súbory: {docx_file}, {html_file}")
            
            # Upload súborov na FTP
            self.file_manager.upload_multiple_to_ftp([docx_file, html_file])
            
            # Aktualizácia zoznamu článkov pre denný súhrn
            self.daily_summary_articles.extend(all_articles)
            
            # Filtrovanie a zoradenie článkov pre súhrn
            summary_articles = self._filter_relevant_articles(self.daily_summary_articles)
            logger.info(f"Vybraných {len(summary_articles)} článkov pre denný súhrn.")
            
            # Vytvorenie súhrnných súborov
            summary_docx, summary_html = self.file_manager.create_or_update_summary_files(summary_articles, now)
            logger.info(f"Aktualizované súhrnné súbory: {summary_docx}, {summary_html}")
            
            # Upload súhrnných súborov na FTP
            self.file_manager.upload_multiple_to_ftp([summary_docx, summary_html])
        else:
            logger.warning("Neboli nájdené žiadne relevantné články v tejto hodine.")
        
        logger.info("=== Hodinové spracovanie správ ukončené ===")
    
    def process_web_sources(self) -> List[Dict]:
        """
        Spracuje webové zdroje a vráti relevantné články.
        
        Returns:
            Zoznam spracovaných článkov z webových zdrojov.
        """
        logger.info("Začínam spracovanie webových zdrojov...")
        
        # Testovanie relevancie zdrojov
        relevant_sources = []
        for source in DEFAULT_SOURCES:
            result = self.source_tester.test_source(source['name'], source['url'])
            if result['is_relevant']:
                relevant_sources.append(source)
        
        logger.info(f"Identifikovaných {len(relevant_sources)} relevantných zdrojov z {len(DEFAULT_SOURCES)} testovaných.")
        
        # Získanie odkazov na články
        all_article_urls = []
        for source in relevant_sources:
            article_urls = self._get_links_from_source(source)
            all_article_urls.extend(article_urls)
        
        logger.info(f"Celkovo získaných {len(all_article_urls)} odkazov na články.")
        
        # Spracovanie článkov (kvôli výkonu obmedzíme počet)
        max_articles_to_process = 20
        processed_articles = []
        
        for url in all_article_urls[:max_articles_to_process]:
            try:
                article_data = self.article_processor.process_article(url)
                
                if article_data:
                    # Kontrola relevancie článku
                    is_relevant, relevance_score, reason = self.source_tester.check_article_relevance(article_data)
                    
                    # Uloženie skóre a dôvodu
                    article_data['relevance_score'] = relevance_score
                    article_data['relevance_reason'] = reason
                    article_data['is_relevant'] = is_relevant
                    
                    if is_relevant:
                        processed_articles.append(article_data)
                        logger.info(f"Článok úspešne spracovaný a relevantný: {article_data['title']}")
                    else:
                        logger.info(f"Článok nie je relevantný: {article_data['title']} - {reason}")
            
            except Exception as e:
                logger.error(f"Chyba pri spracovaní článku {url}: {str(e)}")
        
        logger.info(f"Spracovaných {len(processed_articles)} relevantných článkov z webových zdrojov.")
        return processed_articles
    
    def start_scheduler(self):
        """Spustí plánovač pre pravidelné spracovanie správ."""
        # Nastavenie hodinového spracovania
        schedule.every().hour.at(":00").do(self.process_hourly_news)
        
        logger.info("Plánovač spustený. Čakám na najbližšiu plánovanú úlohu...")
        logger.info("Stlačte Ctrl+C pre ukončenie.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Kontrola každú minútu
        except KeyboardInterrupt:
            logger.info("Plánovač ukončený užívateľom.")

def main():
    """Hlavná funkcia programu."""
    parser = argparse.ArgumentParser(description='Spracovanie zdravotníckych a vedeckých správ')
    parser.add_argument('--run-once', action='store_true', help='Spustí spracovanie jedenkrát a skončí')
    parser.add_argument('--web-only', action='store_true', help='Spracuje len webové zdroje')
    parser.add_argument('--email-only', action='store_true', help='Spracuje len e-mailové zdroje')
    args = parser.parse_args()
    
    processor = NewsProcessor()
    
    if args.web_only:
        # Spracovanie len webových zdrojov
        web_articles = processor.process_web_sources()
        logger.info(f"Získaných {len(web_articles)} článkov z webových zdrojov.")
        
        if web_articles:
            # Vytvorenie súborov
            docx_file, html_file = processor.file_manager.create_hourly_files(web_articles)
            logger.info(f"Vytvorené súbory: {docx_file}, {html_file}")
            
            # Upload súborov na FTP
            processor.file_manager.upload_multiple_to_ftp([docx_file, html_file])
    
    elif args.email_only:
        # Spracovanie len e-mailových zdrojov
        email_articles = processor.process_email_sources()
        logger.info(f"Získaných {len(email_articles)} článkov z e-mailových zdrojov.")
        
        if email_articles:
            # Vytvorenie súborov
            docx_file, html_file = processor.file_manager.create_hourly_files(email_articles)
            logger.info(f"Vytvorené súbory: {docx_file}, {html_file}")
            
            # Upload súborov na FTP
            processor.file_manager.upload_multiple_to_ftp([docx_file, html_file])
    
    elif args.run_once:
        # Jednorazové spustenie kompletného spracovania
        processor.process_hourly_news()
    
    else:
        # Spustenie plánovača
        processor.start_scheduler()

if __name__ == "__main__":
    main()