#!/bin/bash

# Farby pre výstup
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Nastavenie pracovného adresára na adresár so skriptom
cd "$(dirname "$0")"

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}      TESTOVANIE ZBERAČOV ZDRAVOTNÍCKYCH     ${NC}"
echo -e "${BLUE}              A VEDECKÝCH DÁT                ${NC}"
echo -e "${BLUE}==============================================${NC}"
echo

# Funkcia na testovanie konkrétneho Python modulu
test_module() {
    local module_name=$1
    local function_name=$2
    
    echo -e "${YELLOW}Testujem modul:${NC} $module_name"
    echo -e "${YELLOW}Funkcia:${NC} $function_name"
    
    # Vytvoríme dočasný Python skript pre testovanie
    cat > temp_test.py << EOF
import sys
from $module_name import $function_name
from utils.logger import logger
import json

try:
    # Vypneme štandardný výstup loggera počas testovania
    logger.handlers = []

    # Spustíme funkciu
    results = $function_name()
    
    # Vypíšeme počet výsledkov
    print(f"SUCCESS:{len(results)}")
    
    # Vypíšeme prvý výsledok ako ukážku (ak existuje)
    if results and len(results) > 0:
        print("SAMPLE:" + json.dumps(results[0], ensure_ascii=False))
except Exception as e:
    print(f"ERROR:{str(e)}")
    sys.exit(1)
EOF

    # Spustíme testovací skript
    result=$(python3 temp_test.py)
    
    # Spracujeme výsledok
    if [[ $result == ERROR:* ]]; then
        error_msg=${result#ERROR:}
        echo -e "${RED}❌ Testovanie zlyhalo: $error_msg${NC}"
        echo
        success=false
    else
        count=$(echo "$result" | grep "SUCCESS:" | cut -d':' -f2)
        sample=$(echo "$result" | grep "SAMPLE:" | cut -d':' -f2-)
        
        echo -e "${GREEN}✅ Test úspešný${NC}"
        echo -e "${GREEN}📊 Počet získaných článkov:${NC} $count"
        
        if [ ! -z "$sample" ]; then
            echo -e "${GREEN}📰 Ukážka prvého článku:${NC}"
            echo "$sample" | python3 -m json.tool
        fi
        echo
        success=true
    fi
    
    # Odstránime dočasný skript
    rm temp_test.py
    
    return $success
}

# Príprava zhrnutia výsledkov
declare -A results
total_sources=0
successful_sources=0

echo -e "${BLUE}Začínam testovanie modulov zberu dát...${NC}"
echo

# Test 1: Hlavný news_scraper
echo -e "${BLUE}==============================================${NC}"
if test_module "utils.news_scraper" "scrape_all"; then
    results["Hlavný news_scraper"]="✅ Úspešné"
    ((successful_sources++))
else
    results["Hlavný news_scraper"]="❌ Zlyhalo"
fi
((total_sources++))

# Test 2: SITA scraper
echo -e "${BLUE}==============================================${NC}"
if test_module "utils.scraper_sita_rss" "fetch_sita_articles"; then
    results["SITA scraper"]="✅ Úspešné"
    ((successful_sources++))
else
    results["SITA scraper"]="❌ Zlyhalo"
fi
((total_sources++))

# Test 3: SME direct scraper
echo -e "${BLUE}==============================================${NC}"
if test_module "utils.scraper_sme_direct" "fetch_sme_direct"; then
    results["SME direct scraper"]="✅ Úspešné"
    ((successful_sources++))
else
    results["SME direct scraper"]="❌ Zlyhalo"
fi
((total_sources++))

# Test 4: TASR RSS scraper
echo -e "${BLUE}==============================================${NC}"
if test_module "utils.scraper_tasr_rss_ai" "fetch_tasr_articles"; then
    results["TASR RSS scraper"]="✅ Úspešné"
    ((successful_sources++))
else
    results["TASR RSS scraper"]="❌ Zlyhalo"
fi
((total_sources++))

# Zobraz súhrnné výsledky
echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}               SÚHRNNÉ VÝSLEDKY              ${NC}"
echo -e "${BLUE}==============================================${NC}"
echo

for source in "${!results[@]}"; do
    echo -e "${YELLOW}$source:${NC} ${results[$source]}"
done

echo
echo -e "${GREEN}Úspešné testy:${NC} $successful_sources z $total_sources"

# Hodnotenie úspešnosti
success_rate=$((successful_sources * 100 / total_sources))
echo -e "${BLUE}Úspešnosť:${NC} $success_rate%"

# Záverečné zhrnutie
echo
if [ $success_rate -eq 100 ]; then
    echo -e "${GREEN}🎉 Všetky zdroje fungujú správne!${NC}"
elif [ $success_rate -ge 75 ]; then
    echo -e "${YELLOW}⚠️ Väčšina zdrojov funguje, ale niektoré zlyhali.${NC}"
else
    echo -e "${RED}❌ Výrazné problémy so zberom dát. Skontroluj moduly.${NC}"
fi

echo
echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}              KONIEC TESTOVANIA              ${NC}"
echo -e "${BLUE}==============================================${NC}"
