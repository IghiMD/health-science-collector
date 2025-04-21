import requests
from bs4 import BeautifulSoup
from utils.logger import logger

def fetch_sme_direct():
    try:
        url = "https://zdravie.sme.sk"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        # Nový selektor pre SME Zdravie
        for article in soup.select('article.article-item'):
            title_elem = article.select_one('h2 a')
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            link = title_elem['href']
            link = f"https://zdravie.sme.sk{link}" if not link.startswith('http') else link
            
            articles.append({
                'title': title,
                'url': link,
                'source': 'SME Zdravie'
            })
        
        logger.info(f"Načítané {len(articles)} článkov z SME")
        return articles
        
    except Exception as e:
        logger.error(f"SME direct chyba: {e}")
        return []
