#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modul pre sťahovanie a spracovanie článkov zo zdravotníckych a vedeckých zdrojov.
Implementuje sťahovanie, extrakciu, preklad do slovenčiny a štylizáciu textov.
"""

import requests
import logging
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from newspaper import Article
import openai
import os
# Načítanie premenných z .env súboru
from dotenv import load_dotenv
load_dotenv()  # toto načíta premenné z .env súboru do prostredia
from datetime import datetime

# Konfigurácia loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/article_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("article_processor")

# Načítanie API kľúčov z prostredia
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_IGHI")  # Upravené podľa vášho .env
if not OPENAI_API_KEY:
    # Skús alternatívny kľúč
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_TASR")
    if not OPENAI_API_KEY:
        logger.warning("Žiadny OPENAI_API_KEY nie je nastavený v prostredí!")

# Konfigurácia OpenAI
openai.api_key = OPENAI_API_KEY

# Načítanie ďalších API kľúčov, ktoré môžu byť potrebné
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")  # Alternatívny prekladač
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Alternatívny AI model

# Načítanie AI promptu pre sumarizáciu
AI_PROMPT_PATH = "ai_sumar_prompt.txt"
try:
    with open(AI_PROMPT_PATH, 'r', encoding='utf-8') as f:
        AI_SUMMARY_PROMPT = f.read()
except Exception as e:
    logger.error(f"Chyba pri načítaní AI promptu: {str(e)}")
    AI_SUMMARY_PROMPT = """
    🧠 AI Prompt na generovanie sarkastického, medicínsky korektného a virálneho AI sumáru (štýl „pikosky do rádia")

    Pôsobíš ako inteligentný komentátor s ironickým nadhľadom a skúsenosťami v oblasti medicíny a médií. Na základe nasledovného článku vytvor dve jasne oddelené časti:

    1. **Sarkastický a virálny sumár (cca 6–8 viet)**  
    Tvoj cieľ je pobaviť, zaujať a zároveň edukovať. Použi čierny humor, trefné prirovnania, klikbaitový jazyk – ale vždy buď medicínsky korektný. Tento sumár by mal zaujať pozornosť už po prvej vete, byť vhodný na čítanie v rádiu ako rýchla „pikoska" či zaujímavosť, ktorú si ľudia zapamätajú. Vyhni sa infantilnosti – cieliš na dospelého, inteligentného poslucháča vo veku 20 až 55 rokov.

    2. **Edukačný dovetok (1–2 vety)**  
    Krátke, ale úderné vysvetlenie alebo doplnenie témy. Môžeš pridať zaujímavý vedecký fakt, jednoduché vysvetlenie alebo štatistiku, ktorá podporí tému článku. Mal by to byť taký "racionálny šplech", ktorý zakončí správu s inteligentnou pointou.

    🎯 Celý výstup píš v slovenčine. Tón má byť moderný, ostrý, ale nie útočný. Môžeš byť provokatívny, ale nikdy lacno šokujúci.

    Výstup má byť vhodný do podcastu, rádia alebo virálneho statusu na webe.
    """

class ArticleProcessor:
    """Trieda pre spracovanie článkov."""
    
    def __init__(self):
        """Inicializácia procesora článkov."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    
    def download_article(self, url: str) -> Optional[Article]:
        """
        Stiahne a spracuje článok pomocou knižnice newspaper3k.
        
        Args:
            url: URL adresa článku.
            
        Returns:
            Objekt Article alebo None v prípade chyby.
        """
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article
        except Exception as e:
            logger.error(f"Chyba pri sťahovaní článku z {url}: {str(e)}")
            return None
    
    def extract_article_info(self, article: Article) -> Dict:
        """
        Extrahuje informácie z článku.
        
        Args:
            article: Objekt Article.
            
        Returns:
            Dictionary s informáciami o článku.
        """
        return {
            'title': article.title,
            'text': article.text,
            'publish_date': article.publish_date,
            'authors': article.authors,
            'top_image': article.top_image,
            'url': article.url,
            'source_url': article.source_url,
            'keywords': article.keywords,
            'summary': article.summary,
            'html': article.html,
            'language': self._detect_language(article.text)
        }
    
    def _detect_language(self, text: str) -> str:
        """
        Detekuje jazyk textu (jednoduchá implementácia).
        
        Args:
            text: Text na detekciu jazyka.
            
        Returns:
            Kód jazyka (sk, cs, en, ...).
        """
        # Jednoduchá detekcia - hľadáme typické české/slovenské znaky
        sk_chars = {'ž', 'ý', 'á', 'í', 'é', 'ú', 'ä', 'ô', 'ň', 'č', 'ť', 'ď', 'ľ', 'š', 'ĺ', 'ŕ', 'ó'}
        cs_chars = {'ž', 'ý', 'á', 'í', 'é', 'ú', 'ů', 'ě', 'š', 'č', 'ř', 'ň', 'ť', 'ď', 'ó'}
        
        text_lower = text.lower()
        sample = text_lower[:1000]  # Analyzujeme prvých 1000 znakov
        
        # Kontrola na slovenské a české znaky
        contains_sk = any(char in sample for char in sk_chars)
        contains_cs = any(char in sample for char in cs_chars)
        
        # Špecifická kontrola pre slovenčinu a češtinu
        if 'ľ' in sample or 'ĺ' in sample or 'ŕ' in sample or 'ô' in sample or 'ä' in sample:
            return 'sk'
        elif 'ř' in sample or 'ů' in sample or 'ě' in sample:
            return 'cs'
        elif contains_sk and contains_cs:
            # Ďalšia heuristika - typické slová/koncovky/vzory
            if 'nie je' in text_lower or 'môže' in text_lower or 'bude' in text_lower:
                return 'sk'
            elif 'není' in text_lower or 'může' in text_lower or 'bude' in text_lower:
                return 'cs'
            else:
                return 'sk'  # Predvolene slovenčina
        elif contains_sk:
            return 'sk'
        elif contains_cs:
            return 'cs'
        else:
            # Predpokladáme angličtinu alebo iný jazyk
            return 'en'
    
    def translate_to_slovak(self, text: str, source_lang: str) -> str:
        """
        Preloží text do slovenčiny. Primárne používa DeepL, ak zlyhá, použije Google Translate.
        
        Args:
            text: Text na preklad.
            source_lang: Zdrojový jazyk textu.
            
        Returns:
            Preložený text.
        """
        if source_lang == 'sk':
            return text  # Už je v slovenčine
        
        # Skrátenie textu ak je príliš dlhý (pre prípad API limitov)
        if len(text) > 10000:
            text = text[:10000] + "..."
        
        # 1. Pokus: DeepL (primárna metóda)
        if DEEPL_API_KEY:
            try:
                import requests
                headers = {
                    'Authorization': f'DeepL-Auth-Key {DEEPL_API_KEY}',
                    'Content-Type': 'application/json',
                }
                data = {
                    'text': [text],
                    'target_lang': 'SK',
                    'source_lang': source_lang.upper() if source_lang != 'en' else 'EN'
                }
                response = requests.post('https://api.deepl.com/v2/translate', 
                                         headers=headers, 
                                         json=data,
                                         timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'translations' in result and len(result['translations']) > 0:
                        logger.info("Text preložený pomocou DeepL API")
                        return result['translations'][0]['text']
                logger.warning(f"DeepL API vrátilo chybový kód: {response.status_code}")
            except Exception as e:
                logger.warning(f"Chyba pri preklade pomocou DeepL: {str(e)}")
        else:
            logger.warning("DEEPL_API_KEY nie je nastavený, skúšam Google Translate")
        
        # 2. Pokus: Google Translate (fallback)
        if GOOGLE_TRANSLATE_API_KEY:
            try:
                import requests
                url = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_TRANSLATE_API_KEY}"
                payload = {
                    'q': text,
                    'target': 'sk',
                    'source': source_lang
                }
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'data' in result and 'translations' in result['data'] and len(result['data']['translations']) > 0:
                        logger.info("Text preložený pomocou Google Translate API")
                        return result['data']['translations'][0]['translatedText']
                logger.warning(f"Google Translate API vrátilo chybový kód: {response.status_code}")
            except Exception as e:
                logger.warning(f"Chyba pri preklade pomocou Google Translate: {str(e)}")
        else:
            logger.warning("GOOGLE_TRANSLATE_API_KEY nie je nastavený, preklad nebude vykonaný")
        
        logger.error("Všetky metódy prekladu zlyhali. Vraciam originálny text.")
        return text  # Vraciam originálny text, keď zlyhajú všetky možnosti
    
    def generate_stylized_summary(self, article_info: Dict) -> Dict:
        """
        Generuje štylizovaný súhrn článku podľa zadaného promptu.
        Postupne skúša: OpenAI, DeepSeek, Anthropic, Gemini.
        
        Args:
            article_info: Informácie o článku.
            
        Returns:
            Dictionary s pôvodnými informáciami a pridaným štylizovaným súhrnom.
        """
        # Zaistíme, že máme slovenský text
        if article_info['language'] != 'sk':
            text_to_process = self.translate_to_slovak(article_info['text'], article_info['language'])
            title_to_process = self.translate_to_slovak(article_info['title'], article_info['language'])
        else:
            text_to_process = article_info['text']
            title_to_process = article_info['title']
        
        # Inicializácia výsledných dát
        result = article_info.copy()
        result['stylized_summary'] = ""
        result['summary_text'] = ""
        result['appendix_text'] = ""
        result['processed_date'] = datetime.now()
        result['translated_title'] = title_to_process
        
        # 1. Pokus: OpenAI s primárnym API kľúčom
        stylized_summary = None
        
        if OPENAI_API_KEY:  # Používame primárny kľúč (OPENAI_API_KEY_IGHI)
            try:
                # Nastavíme aktuálny kľúč
                openai.api_key = OPENAI_API_KEY
                
                # Použitie OpenAI API na generovanie štylizovaného súhrnu
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": AI_SUMMARY_PROMPT},
                        {"role": "user", "content": f"Článok:\n\nNázov: {title_to_process}\n\nObsah:\n{text_to_process}"}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                stylized_summary = response.choices[0].message.content
                logger.info("Štylizovaný súhrn vygenerovaný pomocou OpenAI primárneho API")
            
            except Exception as e:
                logger.warning(f"Chyba pri generovaní štylizovaného súhrnu pomocou primárneho OpenAI API: {str(e)}")
        
        # 2. Pokus: OpenAI s alternatívnym API kľúčom
        if not stylized_summary and os.getenv("OPENAI_API_KEY_TASR"):
            try:
                # Nastavíme alternatívny kľúč
                alt_api_key = os.getenv("OPENAI_API_KEY_TASR")
                openai.api_key = alt_api_key
                
                # Použitie OpenAI API na generovanie štylizovaného súhrnu
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": AI_SUMMARY_PROMPT},
                        {"role": "user", "content": f"Článok:\n\nNázov: {title_to_process}\n\nObsah:\n{text_to_process}"}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                stylized_summary = response.choices[0].message.content
                logger.info("Štylizovaný súhrn vygenerovaný pomocou OpenAI alternatívneho API")
            
            except Exception as e:
                logger.warning(f"Chyba pri generovaní štylizovaného súhrnu pomocou alternatívneho OpenAI API: {str(e)}")
        
        # 3. Pokus: DeepSeek API
        if not stylized_summary and os.getenv("DEEPSEEK_API_KEY"):
            try:
                import requests
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}"
                }
                
                data = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": AI_SUMMARY_PROMPT},
                        {"role": "user", "content": f"Článok:\n\nNázov: {title_to_process}\n\nObsah:\n{text_to_process}"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        stylized_summary = response_data["choices"][0]["message"]["content"]
                        logger.info("Štylizovaný súhrn vygenerovaný pomocou DeepSeek API")
                else:
                    logger.warning(f"DeepSeek API vrátilo chybový kód: {response.status_code}")
            
            except Exception as e:
                logger.warning(f"Chyba pri generovaní štylizovaného súhrnu pomocou DeepSeek API: {str(e)}")
        
        # 4. Pokus: Anthropic API
        if not stylized_summary and os.getenv("ANTHROPIC_API_KEY"):
            try:
                import requests
                
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                    "anthropic-version": "2023-06-01"
                }
                
                data = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "system": AI_SUMMARY_PROMPT,
                    "messages": [
                        {"role": "user", "content": f"Článok:\n\nNázov: {title_to_process}\n\nObsah:\n{text_to_process}"}
                    ]
                }
                
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "content" in response_data and len(response_data["content"]) > 0:
                        stylized_summary = response_data["content"][0]["text"]
                        logger.info("Štylizovaný súhrn vygenerovaný pomocou Anthropic API")
                else:
                    logger.warning(f"Anthropic API vrátilo chybový kód: {response.status_code}")
            
            except Exception as e:
                logger.warning(f"Chyba pri generovaní štylizovaného súhrnu pomocou Anthropic API: {str(e)}")
        
        # 5. Pokus: Google Gemini API
        if not stylized_summary and os.getenv("GOOGLE_API_KEY"):
            try:
                import requests
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                data = {
                    "contents": [
                        {
                            "parts": [
                                {"text": AI_SUMMARY_PROMPT},
                                {"text": f"Článok:\n\nNázov: {title_to_process}\n\nObsah:\n{text_to_process}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1000
                    }
                }
                
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={os.getenv('GOOGLE_API_KEY')}",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "candidates" in response_data and len(response_data["candidates"]) > 0:
                        if "content" in response_data["candidates"][0] and "parts" in response_data["candidates"][0]["content"]:
                            stylized_summary = response_data["candidates"][0]["content"]["parts"][0]["text"]
                            logger.info("Štylizovaný súhrn vygenerovaný pomocou Google Gemini API")
                else:
                    logger.warning(f"Google Gemini API vrátilo chybový kód: {response.status_code}")
            
            except Exception as e:
                logger.warning(f"Chyba pri generovaní štylizovaného súhrnu pomocou Google Gemini API: {str(e)}")
        
        # Spracovanie výsledku
        if stylized_summary:
            # Rozdelenie na sumár a dovetok
            summary_parts = self._split_summary_and_appendix(stylized_summary)
            
            result['stylized_summary'] = stylized_summary
            result['summary_text'] = summary_parts[0]
            result['appendix_text'] = summary_parts[1]
        else:
            logger.error("Všetky pokusy o generovanie štylizovaného súhrnu zlyhali.")
            # V prípade zlyhania všetkých API vytvoríme aspoň základný súhrn
            result['stylized_summary'] = "Generovanie súhrnu zlyhalo. Prosím, prečítajte si originálny článok."
            result['summary_text'] = "Generovanie súhrnu zlyhalo. Prosím, prečítajte si originálny článok."
            result['appendix_text'] = "Generovanie dovetku zlyhalo."
        
        return result
    
    def _split_summary_and_appendix(self, text: str) -> Tuple[str, str]:
        """
        Rozdelí text na sumár a dovetok (appendix).
        
        Args:
            text: Text na rozdelenie.
            
        Returns:
            Dvojica (sumár, dovetok).
        """
        # Hľadáme edukačný dovetok, ktory by mal byť na konci
        # Môže byť označený rôznymi spôsobmi
        patterns = [
            r'Edukačný dovetok:(.+)$',
            r'Dovetok:(.+)$',
            r'\*\*Edukačný dovetok\*\*:(.+)$',
            r'\*\*Edukačný dovetok\*\* \((.+)\)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                appendix = match.group(1).strip()
                summary = text[:match.start()].strip()
                return summary, appendix
        
        # Ak nenájdeme explicitné označenie, skúsime rozdeliť podľa blokov textu
        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 2:
            appendix = paragraphs[-1].strip()
            summary = '\n\n'.join(paragraphs[:-1]).strip()
            return summary, appendix
        
        # Ak nie je možné rozdeliť, vrátime celý text ako sumár a prázdny dovetok
        return text.strip(), ""
    
    def process_article(self, url: str) -> Optional[Dict]:
        """
        Kompletne spracuje článok - stiahne, extrahuje informácie, preloží a štylizuje.
        
        Args:
            url: URL adresa článku.
            
        Returns:
            Dictionary so všetkými informáciami o spracovanom článku alebo None v prípade chyby.
        """
        logger.info(f"Spracovávam článok: {url}")
        
        # Stiahnutie článku
        article = self.download_article(url)
        if not article:
            return None
        
        # Extrakcia informácií
        article_info = self.extract_article_info(article)
        
        # Generovanie štylizovaného súhrnu
        result = self.generate_stylized_summary(article_info)
        
        logger.info(f"Článok úspešne spracovaný: {article_info['title']}")
        return result

# Príklad použitia
if __name__ == "__main__":
    processor = ArticleProcessor()
    test_url = "https://www.zdravezpravy.cz/2023/05/01/vedci-objevili-novy-zpusob-jak-lepe-diagnostikovat-rakovinu/"
    result = processor.process_article(test_url)
    
    if result:
        print(f"Názov: {result['title']}")
        print(f"Jazyk: {result['language']}")
        print("\nŠtylizovaný súhrn:")
        print(result['stylized_summary'])