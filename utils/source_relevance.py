#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modul pre testovanie relevancie zdrojov pre zdravotnícke a vedecké správy.
Implementuje logiku podobnú testu test_relevance.sh, ale ako Python modul.
"""

import requests
import re
import logging
from typing import List, Dict, Tuple, Set, Optional
# Načítanie premenných z .env súboru
from dotenv import load_dotenv
load_dotenv()  # toto načíta premenné z .env súboru do prostredia
from bs4 import BeautifulSoup
import os
import openai

# Konfigurácia loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/relevance.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("source_relevance")

# Kľúčové slová pre vyhľadávanie relevantných zdrojov
KEYWORDS = {
    'zdraví', 'medicína', 'nemoc', 'epidemie', 'bakterie', 
    'virus', 'infekce', 'léčba', 'prevence', 'studie', 
    'výzkum', 'nádor', 'srdce', 'mozek', 'operace', 
    'léky', 'zajímavost', 'věda'
}

# Minimálny počet kľúčových slov pre uznanie zdroja ako relevantný
MIN_KEYWORDS = 1  # Znížené z 3 na 1 podľa požiadavky

# Načítanie API kľúčov z prostredia
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_IGHI")  # Upravené podľa vášho .env
if not OPENAI_API_KEY:
    # Skús alternatívny kľúč
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_TASR")
    if not OPENAI_API_KEY:
        logger.warning("Žiadny OPENAI_API_KEY nie je nastavený v prostredí!")

# Konfigurácia OpenAI
openai.api_key = OPENAI_API_KEY

class SourceRelevanceTester:
    """Trieda pre testovanie relevancie zdrojov."""
    
    def __init__(self, keywords: Optional[Set[str]] = None, min_keywords: int = MIN_KEYWORDS):
        """
        Inicializácia testera relevancie.
        
        Args:
            keywords: Set kľúčových slov. Ak None, použijú sa predvolené.
            min_keywords: Minimálny počet kľúčových slov pre uznanie zdroja ako relevantný.
        """
        self.keywords = keywords if keywords is not None else KEYWORDS
        self.min_keywords = min_keywords
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    
    def download_content(self, url: str) -> Optional[str]:
        """
        Stiahne obsah webovej stránky.
        
        Args:
            url: URL adresa stránky na stiahnutie.
            
        Returns:
            Obsah stránky ako string alebo None v prípade chyby.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Chyba pri sťahovaní obsahu z {url}: {str(e)}")
            return None
    
    def find_keywords(self, content: str) -> Set[str]:
        """
        Vyhľadá kľúčové slová v obsahu.
        
        Args:
            content: Obsah stránky ako string.
            
        Returns:
            Set nájdených kľúčových slov.
        """
        # Odstránenie HTML značiek a whitespace
        if content:
            try:
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text().lower()
                
                # Hľadanie kľúčových slov
                found_keywords = set()
                for keyword in self.keywords:
                    if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text_content):
                        found_keywords.add(keyword)
                
                return found_keywords
            except Exception as e:
                logger.error(f"Chyba pri hľadaní kľúčových slov: {str(e)}")
                return set()
        return set()
    
    def check_ai_relevance(self, text: str, title: str = "") -> Tuple[bool, str]:
        """
        Kontrola relevancie textu pomocou AI.
        
        Args:
            text: Text na kontrolu.
            title: Názov článku/textu.
            
        Returns:
            Tuple (je_relevantný, dôvod)
        """
        # Ak text je príliš dlhý, skrátime ho
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        if not OPENAI_API_KEY:
            logger.warning("Nemôžem kontrolovať relevanciu pomocou AI - chýba API kľúč")
            return True, "AI kontrola nedostupná, predpokladám relevanciu"
        
        try:
            # Použitie OpenAI API na kontrolu relevancie
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Si asistent, ktorý hodnotí relevanciu článkov z oblasti zdravia, medicíny a vedy. Tvoja úloha je určiť, či je článok relevantný pre ľudí zaujímajúcich sa o zdravotnícke a vedecké informácie."},
                    {"role": "user", "content": f"Zhodnoť, či je nasledujúci článok relevantný z hľadiska zdravia, medicíny alebo vedy. Odpovedaj len 'ÁNO' alebo 'NIE' a dôvod.\n\nNÁZOV: {title}\n\nOBSAH: {text}"}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"AI relevancia: {result}")
            
            # Kontrola odpovede
            is_relevant = "ÁNO" in result.upper() or "ANO" in result.upper() or "YES" in result.upper()
            return is_relevant, result
        
        except Exception as e:
            logger.error(f"Chyba pri kontrole AI relevancie: {str(e)}")
            return True, f"Chyba pri AI kontrole: {str(e)}, predpokladám relevanciu"
    
    def test_source(self, name: str, url: str) -> Dict:
        """
        Otestuje relevantnosť zdroja.
        
        Args:
            name: Názov zdroja.
            url: URL adresa zdroja.
            
        Returns:
            Dictionary s výsledkami testu.
        """
        logger.info(f"Testujem relevanciu: {name}")
        logger.info(f"URL: {url}")
        
        result = {
            'name': name,
            'url': url,
            'downloaded': False,
            'content_size': 0,
            'found_keywords': set(),
            'keyword_count': 0,
            'is_relevant': False,
            'ai_relevance': None,
            'ai_reason': "",
            'error': None
        }
        
        # Stiahnutie obsahu
        content = self.download_content(url)
        if not content:
            result['error'] = "Chyba pri sťahovaní obsahu"
            return result
        
        result['downloaded'] = True
        result['content_size'] = len(content)
        logger.info(f"Veľkosť stiahnutého obsahu: {result['content_size']} bajtov")
        
        # Hľadanie kľúčových slov
        logger.info("Hľadám kľúčové slová...")
        found_keywords = self.find_keywords(content)
        result['found_keywords'] = found_keywords
        result['keyword_count'] = len(found_keywords)
        
        # Kontrola AI relevancie
        ai_relevant, ai_reason = self.check_ai_relevance(content, name)
        result['ai_relevance'] = ai_relevant
        result['ai_reason'] = ai_reason
        
        # Vyhodnotenie relevancie - zdroj je relevantný, ak má dostatok kľúčových slov ALEBO je označený ako relevantný AI
        result['is_relevant'] = (result['keyword_count'] >= self.min_keywords) or ai_relevant
        
        # Logovanie výsledkov
        if result['is_relevant']:
            if result['keyword_count'] >= self.min_keywords:
                logger.info(f"✅ Nájdené kľúčové slová ({result['keyword_count']}): {', '.join(found_keywords)}")
                logger.info(f"✅ Zdroj je relevantný - nájdených {result['keyword_count']} kľúčových slov")
            if ai_relevant:
                logger.info(f"✅ Zdroj je relevantný podľa AI: {ai_reason}")
        else:
            logger.info(f"❌ Nájdené kľúčové slová ({result['keyword_count']}): {', '.join(found_keywords)}")
            logger.info(f"❌ Zdroj nie je relevantný - nájdených len {result['keyword_count']} kľúčových slov (minimum {self.min_keywords})")
            if not ai_relevant:
                logger.info(f"❌ Zdroj nie je relevantný podľa AI: {ai_reason}")
        
        return result
    
    def test_sources(self, sources: List[Dict[str, str]]) -> List[Dict]:
        """
        Otestuje relevanciu viacerých zdrojov.
        
        Args:
            sources: Zoznam zdrojov na otestovanie. Každý zdroj je dictionary s kľúčmi 'name' a 'url'.
            
        Returns:
            Zoznam výsledkov testov.
        """
        results = []
        total_sources = len(sources)
        relevant_sources = 0
        error_sources = 0
        
        logger.info("==============================================")
        logger.info("TESTOVANIE RELEVANCIE ZDRAVOTNÍCKYCH A VEDECKÝCH ZDROJOV")
        logger.info("==============================================")
        
        for source in sources:
            logger.info("----------------------------------------------")
            result = self.test_source(source['name'], source['url'])
            results.append(result)
            
            if result['error']:
                error_sources += 1
            elif result['is_relevant']:
                relevant_sources += 1
        
        # Logovanie súhrnných výsledkov
        logger.info("==============================================")
        logger.info("SÚHRNNÉ VÝSLEDKY TESTOVANIA RELEVANCIE ZDROJOV")
        logger.info("==============================================")
        logger.info(f"Celkový počet testovaných zdrojov: {total_sources}")
        logger.info(f"✅ Relevantné zdroje: {relevant_sources}")
        logger.info(f"❌ Nerelevantné zdroje: {total_sources - relevant_sources - error_sources}")
        logger.info(f"⚠️ Chyba pri testovaní: {error_sources}")
        
        # Percentuálna relevancia
        if total_sources > 0:
            percentage = (relevant_sources / total_sources) * 100
            logger.info(f"Percentuálna relevancia zdrojov: {percentage:.1f}%")
            
            if percentage >= 70:
                logger.info("✅ Väčšina zdrojov je relevantná pre zdravotnícke a vedecké správy.")
            else:
                logger.info("⚠️ Menej ako 70% zdrojov je relevantných pre zdravotnícke a vedecké správy.")
        
        logger.info("==============================================")
        logger.info("KONIEC TESTOVANIA RELEVANCIE")
        logger.info("==============================================")
        
        return results

    def check_article_relevance(self, article: Dict) -> Tuple[bool, int, str]:
        """
        Skontroluje relevanciu článku kombináciou kľúčových slov a AI.
        
        Args:
            article: Dictionary s informáciami o článku.
            
        Returns:
            Tuple (je_relevantný, relevance_score, dôvod)
        """
        # Inicializácia skóre relevancie
        relevance_score = 0
        reasons = []
        
        # 1. Kontrola kľúčových slov v názve
        title = article.get('title', '').lower()
        title_keywords = []
        for keyword in self.keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', title):
                relevance_score += 2  # Názov má vyššiu váhu
                title_keywords.append(keyword)
        
        if title_keywords:
            reasons.append(f"Názov obsahuje kľúčové slová: {', '.join(title_keywords)}")
        
        # 2. Kontrola kľúčových slov v texte
        text = article.get('text', '').lower()
        text_keywords = []
        for keyword in self.keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
                relevance_score += 1
                text_keywords.append(keyword)
        
        if text_keywords:
            reasons.append(f"Text obsahuje kľúčové slová: {', '.join(text_keywords)}")
        
        # 3. AI kontrola relevancie
        article_text = article.get('text', '')
        article_title = article.get('title', '')
        
        if article_text:
            ai_relevant, ai_reason = self.check_ai_relevance(article_text, article_title)
            if ai_relevant:
                relevance_score += 5  # AI relevancia má najvyššiu váhu
                reasons.append(f"AI označilo článok ako relevantný: {ai_reason}")
            else:
                reasons.append(f"AI označilo článok ako nerelevantný: {ai_reason}")
        
        # Vyhodnotenie celkovej relevancie
        is_relevant = relevance_score >= 1  # Stačí aspoň 1 bod relevancie
        
        return is_relevant, relevance_score, " | ".join(reasons)

# Zoznam predvolených zdrojov na testovanie
DEFAULT_SOURCES = [
    {"name": "Seznam Zprávy Tech", "url": "https://www.seznamzpravy.cz/sekce/tech-technologie-veda-431"},
    {"name": "Seznam Zprávy Jídlo", "url": "https://www.seznamzpravy.cz/sekce/magazin-jidlo-485"},
    {"name": "Seznam Zprávy Životní styl", "url": "https://www.seznamzpravy.cz/sekce/magazin-zivotni-styl-195"},
    {"name": "Seznam Zprávy Návody", "url": "https://www.seznamzpravy.cz/sekce/tech-technologie-navody-434"},
    {"name": "Seznam Zprávy Historie", "url": "https://www.seznamzpravy.cz/sekce/magazin-historie-231"},
    {"name": "Aktuálně.cz Zdravotnictví", "url": "https://zpravy.aktualne.cz/zdravotnictvi/l~i:keyword:95/"},
    {"name": "Ministr zdraví", "url": "https://www.ministrzdravi.cz/medialni-vystupy/"},
    {"name": "Zdravé zprávy - Aktuality", "url": "https://www.zdravezpravy.cz/rubrika/aktuality/"},
    {"name": "Zdravé zprávy - Zdravotnictví", "url": "https://www.zdravezpravy.cz/rubrika/zdravotnictvi/"},
    {"name": "Medical Tribune", "url": "https://www.tribune.cz/vsechny-clanky/"},
    {"name": "České noviny - RSS", "url": "https://www.ceskenoviny.cz/sluzby/rss/magazin.php"},
    {"name": "České noviny - Magazín", "url": "https://www.ceskenoviny.cz/magazin/"}
]

def test_default_sources():
    """
    Otestuje relevanciu predvolených zdrojov.
    
    Returns:
        Zoznam výsledkov testov.
    """
    tester = SourceRelevanceTester()
    return tester.test_sources(DEFAULT_SOURCES)

if __name__ == "__main__":
    # Spustenie testu relevancie predvolených zdrojov
    test_default_sources()