#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Testovací skript pre jednotlivé komponenty projektu health-science-collector.
Slúži na overenie funkčnosti jednotlivých modulov a ich integrácie.
"""

import os
import sys
import logging
import argparse
# Načítanie premenných z .env súboru
from dotenv import load_dotenv
load_dotenv()  # toto načíta premenné z .env súboru do prostredia
from datetime import datetime

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
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_components")

def test_source_relevance():
    """Test modulu pre kontrolu relevancie zdrojov."""
    logger.info("=== Test modulu source_relevance ===")
    tester = SourceRelevanceTester()
    
    # Test prvých 3 zdrojov
    for source in DEFAULT_SOURCES[:3]:
        result = tester.test_source(source['name'], source['url'])
        logger.info(f"Zdroj: {source['name']}")
        logger.info(f"Relevantný: {result['is_relevant']}")
        logger.info(f"Nájdené kľúčové slová: {', '.join(result['found_keywords'])}")
        logger.info(f"AI relevancia: {result['ai_relevance']}")
        logger.info(f"AI dôvod: {result['ai_reason']}")
        logger.info("---")
    
    logger.info("Test modulu source_relevance dokončený")
    logger.info("")

def test_article_processor():
    """Test modulu pre spracovanie článkov."""
    logger.info("=== Test modulu article_processor ===")
    processor = ArticleProcessor()
    
    # Testovací článok
    test_url = "https://www.zdravezpravy.cz/2023/05/01/vedci-objevili-novy-zpusob-jak-lepe-diagnostikovat-rakovinu/"
    
    # Alternatívne testovacie články
    alternative_urls = [
        "https://www.tribune.cz/medicina/dlouhodobe-uzivani-nsaid-zvysuje-riziko-srdecniho-selhani",
        "https://www.seznamzpravy.cz/clanek/domaci-zivot-v-cesku-zdravi-plicni-fibrozou-trpi-az-30-tisic-cechu-mnozi-o-ni-ani-nevedi-232142"
    ]
    
    # Skúšame sťahovať, kým nezískame aspoň jeden úspešný článok
    success = False
    for url in [test_url] + alternative_urls:
        logger.info(f"Skúšam spracovať článok: {url}")
        
        try:
            result = processor.process_article(url)
            if result:
                logger.info(f"Článok úspešne spracovaný: {result['title']}")
                logger.info(f"Pôvodný jazyk: {result['language']}")
                
                if 'translated_title' in result:
                    logger.info(f"Preložený názov: {result['translated_title']}")
                
                if 'summary_text' in result and result['summary_text']:
                    logger.info("AI sumár bol vygenerovaný:")
                    logger.info(result['summary_text'][:200] + "...")
                
                if 'appendix_text' in result and result['appendix_text']:
                    logger.info("AI dovetok bol vygenerovaný:")
                    logger.info(result['appendix_text'])
                
                success = True
                break
            else:
                logger.warning(f"Spracovanie článku zlyhalo.")
        
        except Exception as e:
            logger.error(f"Chyba pri spracovaní článku: {str(e)}")
    
    if not success:
        logger.error("Nepodarilo sa spracovať žiadny testovací článok.")
    
    logger.info("Test modulu article_processor dokončený")
    logger.info("")

def test_file_manager():
    """Test modulu pre správu súborov."""
    logger.info("=== Test modulu file_manager ===")
    manager = FileManager()
    
    # Test vytvorenia priečinkov
    daily_dir = manager.create_daily_directory()
    logger.info(f"Vytvorený denný priečinok: {daily_dir}")
    
    hourly_dir = manager.create_hourly_directory()
    logger.info(f"Vytvorený hodinový priečinok: {hourly_dir}")
    
    # Testovací článok
    test_article = {
        'title': 'Testovací článok',
        'translated_title': 'Preložený testovací článok',
        'url': 'https://example.com/article1',
        'text': 'Toto je originálny text článku, ktorý simuluje obsah skutočného článku o zdraví a vede.',
        'summary_text': 'Toto je sarkastický sumár. Obsahuje niekoľko viet, ktoré simulujú vtipný obsah o zdraví.',
        'appendix_text': 'Vedeli ste, že pravidelná konzumácia zeleniny znižuje riziko srdcových ochorení o 25%?'
    }
    
    # Test vytvorenia DOCX a HTML súborov
    docx_file, html_file = manager.create_hourly_files([test_article])
    logger.info(f"Vytvorené hodinové súbory: {docx_file}, {html_file}")
    
    summary_docx, summary_html = manager.create_or_update_summary_files([test_article])
    logger.info(f"Vytvorené súhrnné súbory: {summary_docx}, {summary_html}")
    
    # Test FTP uploadu (len ak sú nastavené FTP údaje)
    if all([os.getenv("FTP_HOST"), os.getenv("FTP_USER"), os.getenv("FTP_PASS")]):
        logger.info("Testujem FTP upload...")
        ftp_results = manager.upload_multiple_to_ftp([docx_file, html_file])
        logger.info(f"FTP upload výsledky: {['Úspešný' if res else 'Neúspešný' for res in ftp_results]}")
    else:
        logger.warning("FTP údaje nie sú nastavené, preskakujem test FTP uploadu.")
    
    logger.info("Test modulu file_manager dokončený")
    logger.info("")

def test_email_processor():
    """Test modulu pre spracovanie e-mailov."""
    logger.info("=== Test modulu email_processor ===")
    
    # Kontrola, či sú nastavené e-mailové údaje
    if not all([os.getenv("EMAIL_IMAP_SERVER"), os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD")]):
        logger.warning("E-mailové údaje nie sú nastavené, preskakujem test spracovania e-mailov.")
        return
    
    processor = EmailProcessor()
    
    # Test spracovania emailov z posledných 3 dní
    logger.info("Testujem spracovanie emailov...")
    emails = processor.process_emails(days=3)
    logger.info(f"Spracovaných {len(emails)} emailov.")
    
    # Zobrazenie detailov o emailoch
    for i, email_data in enumerate(emails, 1):
        logger.info(f"Email {i}: {email_data['subject']}")
        logger.info(f"Od: {email_data['from']}")
        
        if 'urls' in email_data and email_data['urls']:
            logger.info(f"Nájdené URL adresy ({len(email_data['urls'])}):")
            for url in email_data['urls'][:5]:  # Zobrazenie prvých 5 URL
                logger.info(f"- {url}")
            if len(email_data['urls']) > 5:
                logger.info(f"- a ďalších {len(email_data['urls']) - 5}...")
        
        if email_data['text']:
            logger.info(f"Text (prvých 100 znakov): {email_data['text'][:100]}...")
        
        logger.info("---")
    
    # Test získania URL adries z emailov
    logger.info("Testujem získanie URL adries z emailov...")
    urls = processor.get_urls_from_emails(days=3)
    logger.info(f"Získaných {len(urls)} unikátnych URL adries z emailov.")
    
    # Zobrazenie prvých 5 URL adries
    for i, url in enumerate(urls[:5], 1):
        logger.info(f"URL {i}: {url}")
    if len(urls) > 5:
        logger.info(f"... a ďalších {len(urls) - 5}")
    
    logger.info("Test modulu email_processor dokončený")
    logger.info("")

def main():
    """Hlavná funkcia testovania."""
    parser = argparse.ArgumentParser(description='Test komponentov projektu health-science-collector')
    parser.add_argument('--all', action='store_true', help='Spustí všetky testy')
    parser.add_argument('--source', action='store_true', help='Spustí test modulu relevance')
    parser.add_argument('--article', action='store_true', help='Spustí test modulu article processor')
    parser.add_argument('--file', action='store_true', help='Spustí test modulu file manager')
    parser.add_argument('--email', action='store_true', help='Spustí test modulu email processor')
    args = parser.parse_args()
    
    # Ak nie je špecifikovaný žiadny test, spustiť všetky
    run_all = args.all or not (args.source or args.article or args.file or args.email)
    
    logger.info("Spúšťam testy komponentov...")
    
    if run_all or args.source:
        test_source_relevance()
    
    if run_all or args.article:
        test_article_processor()
    
    if run_all or args.file:
        test_file_manager()
    
    if run_all or args.email:
        test_email_processor()
    
    logger.info("Všetky testy dokončené.")

if __name__ == "__main__":
    main()