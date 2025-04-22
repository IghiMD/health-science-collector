#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modul pre spracovanie zdravotníckych a vedeckých newsletterov z e-mailovej schránky.
Implementuje pripojenie na IMAP server, čítanie e-mailov a extrakciu obsahu.
"""

import os
import logging
import imaplib
import email
import email.header
import re
import html2text
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
# Načítanie premenných z .env súboru
from dotenv import load_dotenv
load_dotenv()  # toto načíta premenné z .env súboru do prostredia

# Konfigurácia loggeru
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/email_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email_processor")

# Konfigurácia e-mailovej schránky
EMAIL_CONFIG = {
    'imap_server': os.getenv("EMAIL_IMAP_SERVER", ""),
    'imap_port': int(os.getenv("EMAIL_IMAP_PORT", "993")),
    'username': os.getenv("EMAIL_USER", ""),
    'password': os.getenv("EMAIL_PASSWORD", ""),
    'folder': os.getenv("EMAIL_FOLDER", "INBOX"),  # Priečinok, kde sú newslettery
    'processed_folder': os.getenv("EMAIL_PROCESSED_FOLDER", "Processed")  # Priečinok, kam sa presunú spracované e-maily
}

# Vzhľadom na to že spracovávame domácu schránku, prijímame všetky emaily
# Môžeme definovať filtre, ak by sme chceli vyfiltrovať len niektoré emaily
NEWSLETTER_FILTERS = []  # Prázdny zoznam znamená, že akceptujeme všetky emaily

class EmailProcessor:
    """Trieda pre spracovanie e-mailov."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializácia spracovateľa e-mailov.
        
        Args:
            config: Konfigurácia e-mailovej schránky. Ak None, použije sa predvolená konfigurácia.
        """
        self.config = config if config is not None else EMAIL_CONFIG
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.body_width = 0  # Neformátovať text
    
    def _connect_to_mailbox(self) -> Optional[imaplib.IMAP4_SSL]:
        """
        Pripojí sa k e-mailovej schránke cez IMAP.
        
        Returns:
            IMAP objekt alebo None v prípade chyby.
        """
        try:
            # Pripojenie na IMAP server
            mail = imaplib.IMAP4_SSL(self.config['imap_server'], self.config['imap_port'])
            mail.login(self.config['username'], self.config['password'])
            mail.select(self.config['folder'])
            
            logger.info(f"Úspešné pripojenie k e-mailovej schránke {self.config['username']}")
            return mail
        
        except Exception as e:
            logger.error(f"Chyba pri pripájaní k e-mailovej schránke: {str(e)}")
            return None
    
    def _ensure_processed_folder(self, mail: imaplib.IMAP4_SSL) -> bool:
        """
        Zabezpečí existenciu priečinka pre spracované e-maily.
        
        Args:
            mail: IMAP objekt.
            
        Returns:
            True ak priečinok existuje alebo bol vytvorený, inak False.
        """
        try:
            # Kontrola, či priečinok existuje
            status, mailbox_list = mail.list()
            if status != 'OK':
                logger.error(f"Chyba pri získavaní zoznamu priečinkov: {status}")
                return False
            
            # Kontrola, či priečinok pre spracované e-maily existuje
            processed_folder_exists = False
            for mailbox in mailbox_list:
                if mailbox:
                    mailbox_parts = mailbox.decode().split(' ')
                    if mailbox_parts[-1].strip('"\'') == self.config['processed_folder']:
                        processed_folder_exists = True
                        break
            
            # Vytvorenie priečinka, ak neexistuje
            if not processed_folder_exists:
                status, create_response = mail.create(self.config['processed_folder'])
                if status != 'OK':
                    logger.error(f"Chyba pri vytváraní priečinka {self.config['processed_folder']}: {status}")
                    return False
                logger.info(f"Vytvorený priečinok {self.config['processed_folder']} pre spracované e-maily")
            
            return True
        
        except Exception as e:
            logger.error(f"Chyba pri kontrole/vytváraní priečinka pre spracované e-maily: {str(e)}")
            return False
    
    def _search_for_emails(self, mail: imaplib.IMAP4_SSL, days: int = 1) -> List[str]:
        """
        Vyhľadá e-maily z posledných X dní.
        
        Args:
            mail: IMAP objekt.
            days: Počet dní do minulosti, z ktorých sa majú vyhľadať e-maily.
            
        Returns:
            Zoznam ID e-mailov.
        """
        try:
            # Vytvorenie dátumového filtra (SINCE)
            since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            
            # Vyhľadanie všetkých e-mailov od daného dátumu
            status, search_response = mail.search(None, f'SINCE {since_date}')
            if status != 'OK':
                logger.error(f"Chyba pri vyhľadávaní e-mailov: {status}")
                return []
            
            # Získanie ID všetkých e-mailov
            all_emails = search_response[0].decode().split()
            
            # Ak nemáme špecifické filtre, vrátime všetky emaily
            if not NEWSLETTER_FILTERS:
                logger.info(f"Nájdených {len(all_emails)} e-mailov z posledných {days} dní")
                return all_emails
            
            # Inak vyfiltrovanie e-mailov, ktoré zodpovedajú filtrom
            filtered_emails = []
            
            for email_id in all_emails:
                status, fetch_response = mail.fetch(email_id, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])')
                if status != 'OK':
                    continue
                
                header_data = fetch_response[0][1].decode()
                from_match = re.search(r'From: (.*)', header_data)
                subject_match = re.search(r'Subject: (.*)', header_data)
                
                from_address = from_match.group(1).strip() if from_match else ""
                subject = subject_match.group(1).strip() if subject_match else ""
                
                # Kontrola, či e-mail zodpovedá niektorému z filtrov
                for filter_config in NEWSLETTER_FILTERS:
                    matches = True
                    
                    # Kontrola odosielateľa
                    if 'from' in filter_config and filter_config['from'].lower() not in from_address.lower():
                        matches = False
                    
                    # Kontrola predmetu
                    if 'subject' in filter_config and filter_config['subject'].lower() not in subject.lower():
                        matches = False
                    
                    # Ak všetky podmienky boli splnené, pridaj e-mail do zoznamu
                    if matches:
                        filtered_emails.append(email_id)
                        break
            
            logger.info(f"Nájdených {len(filtered_emails)} vyfiltrovaných e-mailov z celkovo {len(all_emails)} e-mailov")
            return filtered_emails
        
        except Exception as e:
            logger.error(f"Chyba pri vyhľadávaní e-mailov: {str(e)}")
            return []
    
    def _extract_url_from_text(self, text: str) -> List[str]:
        """
        Extrahuje URL adresy z textu.
        
        Args:
            text: Text, z ktorého sa majú extrahovať URL adresy.
            
        Returns:
            Zoznam URL adries.
        """
        # Hľadanie URL v texte
        url_pattern = r'https?://[^\s\(\)\[\]<>"\']+(?:\([^\s\(\)]*\)|[^\s\(\)\[\]<>"\']*)'
        urls = re.findall(url_pattern, text)
        
        # Vyčistenie URL adries
        cleaned_urls = []
        for url in urls:
            # Odstránenie koncových znakov, ktoré nemajú byť súčasťou URL
            url = re.sub(r'[,.;:\"\')]*$', '', url)
            cleaned_urls.append(url)
        
        return cleaned_urls
    
    def _extract_email_content(self, mail: imaplib.IMAP4_SSL, email_id: str) -> Optional[Dict]:
        """
        Extrahuje obsah e-mailu.
        
        Args:
            mail: IMAP objekt.
            email_id: ID e-mailu.
            
        Returns:
            Dictionary s informáciami o e-maile alebo None v prípade chyby.
        """
        try:
            # Stiahnutie kompletného e-mailu
            status, fetch_response = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                logger.error(f"Chyba pri sťahovaní e-mailu {email_id}: {status}")
                return None
            
            # Parsovanie e-mailu
            raw_email = fetch_response[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extrakcia základných informácií
            subject = self._decode_header(email_message['Subject'])
            from_address = self._decode_header(email_message['From'])
            date = email_message['Date']
            
            # Extrakcia obsahu
            body_text = ""
            
            # Pokus o získanie textu z tela e-mailu
            if email_message.is_multipart():
                # Multipart správa - prejdi všetky časti
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Preskočenie príloh
                    if "attachment" in content_disposition:
                        continue
                    
                    # Extrakcia textu z HTML alebo plain text
                    if content_type == "text/plain":
                        body_text += part.get_payload(decode=True).decode(errors='replace')
                    elif content_type == "text/html":
                        html_content = part.get_payload(decode=True).decode(errors='replace')
                        body_text += self.h2t.handle(html_content)
                    
                    # Ak máme text, môžeme skončiť
                    if body_text:
                        break
            else:
                # Nejedná sa o multipart správu
                content_type = email_message.get_content_type()
                if content_type == "text/plain":
                    body_text = email_message.get_payload(decode=True).decode(errors='replace')
                elif content_type == "text/html":
                    html_content = email_message.get_payload(decode=True).decode(errors='replace')
                    body_text = self.h2t.handle(html_content)
            
            # Vyčistenie textu
            body_text = self._clean_text(body_text)
            
            # Extrakcia URL z textu
            urls = self._extract_url_from_text(body_text)
            
            # Vytvorenie výsledného dictionary
            result = {
                'id': email_id.decode() if isinstance(email_id, bytes) else email_id,
                'subject': subject,
                'from': from_address,
                'date': date,
                'text': body_text,
                'source_url': f"Email: {from_address}",
                'title': subject,
                'language': 'cs',  # Predpokladáme češtinu, prípadne sa to upraví neskôr
                'urls': urls
            }
            
            logger.info(f"Úspešne extrahovaný obsah e-mailu: {subject}")
            logger.info(f"Nájdené URL adresy ({len(urls)}): {', '.join(urls[:5])}..." if len(urls) > 5 else f"Nájdené URL adresy ({len(urls)}): {', '.join(urls)}")
            return result
        
        except Exception as e:
            logger.error(f"Chyba pri extrakcii obsahu e-mailu {email_id}: {str(e)}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """
        Dekóduje hlavičku e-mailu.
        
        Args:
            header: Hlavička na dekódovanie.
            
        Returns:
            Dekódovaná hlavička.
        """
        if not header:
            return ""
        
        try:
            decoded_header = email.header.decode_header(header)
            decoded_parts = []
            
            for part, encoding in decoded_header:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            decoded_parts.append(part.decode(encoding))
                        except:
                            decoded_parts.append(part.decode('utf-8', errors='replace'))
                    else:
                        decoded_parts.append(part.decode('utf-8', errors='replace'))
                else:
                    decoded_parts.append(part)
            
            return " ".join(decoded_parts)
        
        except Exception as e:
            logger.error(f"Chyba pri dekódovaní hlavičky: {str(e)}")
            return header
    
    def _clean_text(self, text: str) -> str:
        """
        Vyčistí text e-mailu od nepotrebných častí.
        
        Args:
            text: Text na vyčistenie.
            
        Returns:
            Vyčistený text.
        """
        if not text:
            return ""
        
        # Odstránenie viacerých prázdnych riadkov
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Odstránenie typického footer-u z newsletterov
        footers = [
            "Ak si neželáte dostávať tieto e-maily",
            "To unsubscribe from this newsletter",
            "Tento e-mail bol zaslaný na",
            "Odhlásiť odber",
            "Unsubscribe",
            "View in browser",
            "Zobraziť v prehliadači"
        ]
        
        for footer in footers:
            if footer in text:
                parts = text.split(footer, 1)
                text = parts[0]
        
        # Ďalšie čistenie - upresnite podľa potreby
        
        return text.strip()
    
    def _move_to_processed(self, mail: imaplib.IMAP4_SSL, email_id: str) -> bool:
        """
        Presunie e-mail do priečinka pre spracované e-maily.
        
        Args:
            mail: IMAP objekt.
            email_id: ID e-mailu.
            
        Returns:
            True ak presun prebehol úspešne, inak False.
        """
        try:
            # Označenie e-mailu
            status, _ = mail.store(email_id, '+FLAGS', '(\Seen)')
            if status != 'OK':
                logger.warning(f"Chyba pri označovaní e-mailu {email_id} ako prečítaný: {status}")
            
            # Presun e-mailu do priečinka pre spracované e-maily
            status, _ = mail.copy(email_id, self.config['processed_folder'])
            if status != 'OK':
                logger.warning(f"Chyba pri kopírovaní e-mailu {email_id} do priečinka {self.config['processed_folder']}: {status}")
                return False
            
            # Označenie e-mailu na zmazanie z aktuálneho priečinka
            status, _ = mail.store(email_id, '+FLAGS', '(\Deleted)')
            if status != 'OK':
                logger.warning(f"Chyba pri označovaní e-mailu {email_id} na zmazanie: {status}")
                return False
            
            # Vykonanie mazania
            mail.expunge()
            
            logger.info(f"E-mail {email_id} bol úspešne presunutý do priečinka {self.config['processed_folder']}")
            return True
        
        except Exception as e:
            logger.error(f"Chyba pri presúvaní e-mailu {email_id}: {str(e)}")
            return False
    
    def process_emails(self, days: int = 1) -> List[Dict]:
        """
        Spracuje všetky e-maily z posledných X dní.
        
        Args:
            days: Počet dní do minulosti, z ktorých sa majú spracovať e-maily.
            
        Returns:
            Zoznam spracovaných e-mailov.
        """
        processed_emails = []
        
        # Pripojenie k e-mailovej schránke
        mail = self._connect_to_mailbox()
        if not mail:
            return processed_emails
        
        try:
            # Kontrola existencie priečinka pre spracované e-maily
            if not self._ensure_processed_folder(mail):
                logger.error("Chyba pri zabezpečovaní priečinka pre spracované e-maily.")
                return processed_emails
            
            # Vyhľadanie e-mailov
            email_ids = self._search_for_emails(mail, days)
            
            # Spracovanie každého e-mailu
            for email_id in email_ids:
                # Extrakcia obsahu
                email_content = self._extract_email_content(mail, email_id)
                
                if email_content:
                    processed_emails.append(email_content)
                    
                    # Presun e-mailu do priečinka pre spracované e-maily
                    self._move_to_processed(mail, email_id)
                
                # Krátka pauza, aby sme nezaťažovali server
                time.sleep(0.5)
            
            logger.info(f"Spracovaných {len(processed_emails)} e-mailov.")
        
        except Exception as e:
            logger.error(f"Chyba pri spracovaní e-mailov: {str(e)}")
        
        finally:
            # Ukončenie spojenia
            try:
                mail.close()
                mail.logout()
                logger.info("Spojenie s e-mailovou schránkou úspešne ukončené")
            except:
                pass
        
        return processed_emails
    
    def get_urls_from_emails(self, days: int = 1) -> List[str]:
        """
        Získa všetky URL adresy z e-mailov.
        
        Args:
            days: Počet dní do minulosti, z ktorých sa majú spracovať e-maily.
            
        Returns:
            Zoznam URL adries.
        """
        emails = self.process_emails(days)
        all_urls = []
        
        for email_data in emails:
            if 'urls' in email_data and email_data['urls']:
                all_urls.extend(email_data['urls'])
        
        # Odstránenie duplikátov
        unique_urls = list(dict.fromkeys(all_urls))
        
        logger.info(f"Získaných {len(unique_urls)} unikátnych URL adries z e-mailov")
        return unique_urls

# Príklad použitia
if __name__ == "__main__":
    processor = EmailProcessor()
    emails = processor.process_emails(days=3)  # Spracovanie e-mailov z posledných 3 dní
    
    print(f"Spracovaných {len(emails)} e-mailov:")
    
    for i, email_data in enumerate(emails, 1):
        print(f"{i}. {email_data['subject']} - od: {email_data['from']}")
        print(f"   Text (prvých 100 znakov): {email_data['text'][:100]}...")
        
        if 'urls' in email_data and email_data['urls']:
            print(f"   Nájdené URL adresy ({len(email_data['urls'])}):")
            for url in email_data['urls'][:5]:  # Zobrazenie prvých 5 URL
                print(f"   - {url}")
            if len(email_data['urls']) > 5:
                print(f"   - a ďalších {len(email_data['urls']) - 5}...")
        
        print()
    
    # Získanie URL adries z e-mailov
    urls = processor.get_urls_from_emails(days=3)
    print(f"\nZískaných {len(urls)} unikátnych URL adries z e-mailov")
    for i, url in enumerate(urls[:10], 1):
        print(f"{i}. {url}")
    if len(urls) > 10:
        print(f"... a ďalších {len(urls) - 10}")