#!/bin/bash

# Farby pre lepšiu čitateľnosť
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Inicializácia počítadiel
uspesne_testy=0
neuspesne_testy=0
celkovy_pocet_testov=1  # Teraz testujeme len TASR scraper

# Funkcie pre výpis
print_header() {
    echo "=============================================="
    echo "$1"
    echo "=============================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

# Funkcia na testovanie TASR scrapera
test_tasr_scraper() {
    print_header "Testujem modul: utils.scraper_tasr_rss_ai"
    echo "Funkcia: fetch_tasr_articles"
    
    # Spustíme test TASR scrapera
    output=$(python3 -c "from utils.scraper_tasr_rss_ai import fetch_tasr_articles; result = fetch_tasr_articles(); print(len(result)); import json; print(json.dumps(result[0] if result else {}))")
    
    # Rozdelenie výstupu na počet článkov a ukážku prvého článku
    pocet_clankov=$(echo "$output" | head -n 1)
    prvy_clanok=$(echo "$output" | tail -n 1)
    
    # Vyhodnotenie výsledku
    if [ $? -eq 0 ]; then
        print_success "Test úspešný"
        echo "📊 Počet získaných článkov: $pocet_clankov"
        if [ "$pocet_clankov" -gt 0 ]; then
            echo "📰 Ukážka prvého článku:"
            echo "$prvy_clanok"
        fi
        uspesne_testy=$((uspesne_testy + 1))
        return 0
    else
        print_error "Test neúspešný"
        neuspesne_testy=$((neuspesne_testy + 1))
        return 1
    fi
}

# Funkcia na testovanie dostupnosti webových zdrojov
test_web_source() {
    local url="$1"
    local nazov="$2"
    
    echo "Testujem dostupnosť: $nazov"
    echo "URL: $url"
    
    # Použijeme curl na testovanie dostupnosti zdroja
    # -s: tichý mód, -L: sleduj presmerovania, -I: získaj len hlavičky, -o /dev/null: zahoď výstup
    # -w '%{http_code}': vráť len HTTP kód odpovede
    http_code=$(curl -s -L -I -o /dev/null -w '%{http_code}' "$url")
    
    if [ "$http_code" = "200" ]; then
        print_success "Zdroj je dostupný (HTTP $http_code)"
        return 0
    elif [ "$http_code" = "404" ]; then
        print_error "Zdroj nie je dostupný (HTTP $http_code)"
        return 1
    else
        print_warning "Zdroj vrátil neštandardnú odpoveď (HTTP $http_code)"
        return 2
    fi
}

# Hlavný testovací blok
print_header "TESTOVANIE ZBERAČOV ZDRAVOTNÍCKYCH A VEDECKÝCH DÁT"

# Test hlavného TASR scrapera
test_tasr_scraper

# Definícia zdrojov na testovanie
declare -a zdroje=(
    "Seznam Zprávy Tech|https://www.seznamzpravy.cz/sekce/tech-technologie-veda-431"
    "Seznam Zprávy Jídlo|https://www.seznamzpravy.cz/sekce/magazin-jidlo-485"
    "Seznam Zprávy Životní styl|https://www.seznamzpravy.cz/sekce/magazin-zivotni-styl-195"
    "Seznam Zprávy Návody|https://www.seznamzpravy.cz/sekce/tech-technologie-navody-434"
    "Seznam Zprávy Historie|https://www.seznamzpravy.cz/sekce/magazin-historie-231"
    "Aktuálně.cz Zdravotnictví|https://zpravy.aktualne.cz/zdravotnictvi/l~i:keyword:95/"
    "Ministr zdraví|https://www.ministrzdravi.cz/medialni-vystupy/"
    "Zdravé zprávy - Aktuality|https://www.zdravezpravy.cz/rubrika/aktuality/"
    "Zdravé zprávy - Zdravotnictví|https://www.zdravezpravy.cz/rubrika/zdravotnictvi/"
    "Medical Tribune|https://www.tribune.cz/vsechny-clanky/"
    "České noviny - RSS|https://www.ceskenoviny.cz/sluzby/rss/magazin.php"
    "České noviny - Magazín|https://www.ceskenoviny.cz/magazin/"
)

print_header "TESTOVANIE DOSTUPNOSTI ĎALŠÍCH ZDROJOV"

# Počítadlá pre zdroje
dostupne_zdroje=0
nedostupne_zdroje=0
nestandardne_zdroje=0
celkom_zdrojov=${#zdroje[@]}

# Testovanie dostupnosti zdrojov
for zdroj in "${zdroje[@]}"; do
    nazov=$(echo "$zdroj" | cut -d'|' -f1)
    url=$(echo "$zdroj" | cut -d'|' -f2)
    
    echo ""
    echo "----------------------------------------------"
    
    test_web_source "$url" "$nazov"
    vysledok=$?
    
    if [ $vysledok -eq 0 ]; then
        dostupne_zdroje=$((dostupne_zdroje + 1))
    elif [ $vysledok -eq 1 ]; then
        nedostupne_zdroje=$((nedostupne_zdroje + 1))
    else
        nestandardne_zdroje=$((nestandardne_zdroje + 1))
    fi
done

echo ""
print_header "SÚHRNNÉ VÝSLEDKY TESTOVANIA SCRAPEROVÝCH MODULOV"

uspesnost=0
if [ $celkovy_pocet_testov -gt 0 ]; then
    uspesnost=$((uspesne_testy * 100 / celkovy_pocet_testov))
fi

echo "Úspešné testy: $uspesne_testy z $celkovy_pocet_testov"
echo "Úspešnosť: $uspesnost%"
echo ""

if [ $uspesnost -eq 100 ]; then
    print_success "Všetky testy úspešné. Zbieranie dát funguje správne."
elif [ $uspesnost -ge 75 ]; then
    print_warning "Väčšina testov úspešná, ale niektoré zlyhali. Skontroluj problematické moduly."
else
    print_error "Výrazné problémy so zberom dát. Skontroluj moduly."
fi

echo ""
print_header "SÚHRNNÉ VÝSLEDKY TESTOVANIA DOSTUPNOSTI ZDROJOV"

dostupnost_percent=$((dostupne_zdroje * 100 / celkom_zdrojov))

echo "Celkový počet testovaných zdrojov: $celkom_zdrojov"
print_success "Dostupné zdroje: $dostupne_zdroje ($dostupnost_percent%)"
print_error "Nedostupné zdroje: $nedostupne_zdroje"
print_warning "Zdroje s neštandardnou odpoveďou: $nestandardne_zdroje"
echo ""

if [ $dostupnost_percent -eq 100 ]; then
    print_success "Všetky zdroje sú dostupné."
elif [ $dostupnost_percent -ge 75 ]; then
    print_warning "Väčšina zdrojov je dostupná, ale niektoré môžu vyžadovať ďalšiu kontrolu."
else
    print_error "Výrazné problémy s dostupnosťou zdrojov. Skontroluj ich dostupnosť manuálne."
fi

print_header "KONIEC TESTOVANIA"