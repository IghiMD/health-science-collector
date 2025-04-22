#!/bin/bash

# Farby pre lepšiu čitateľnosť
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Všeobecné kľúčové slová pre zdravotnícke a vedecké témy
KLUCOVE_SLOVA="zdravie,medicína,choroba,liečba,prevencia,vakcína,epidémia,vírus,baktéria,infekcia,štúdia,výskum,klinické testy,anestézia,nádor,rakovina,mozog,srdce,cukrovka,operacia,zaujimavost,lieky,resuscitacia,sanitka,anestezia,zazrak,veda"

# České ekvivalenty kľúčových slov pre české zdroje
CESKE_KLUCOVE_SLOVA="zdraví,medicína,nemoc,léčba,prevence,vakcína,epidemie,virus,bakterie,infekce,studie,výzkum,klinické testy,anestezie,nádor,rakovina,mozek,srdce,cukrovka,operace,zajímavost,léky,resuscitace,sanitka,anestezie,zázrak,věda"

# Funkcia na testovanie relevancie zdroja
test_source_relevance() {
    local url="$1"
    local nazov="$2"
    local klucove_slova="$3"
    local min_najdenych="${4:-3}"  # Minimálny počet nájdených slov pre relevanciu, predvolene 3
    
    echo ""
    echo "----------------------------------------------"
    echo "Testujem relevanciu: $nazov"
    echo "URL: $url"
    
    # Použijeme curl na stiahnutie obsahu stránky
    echo "Sťahujem obsah stránky..."
    obsah=$(curl -s -L "$url")
    
    # Kontrola, či sa podarilo stiahnuť obsah
    if [ -z "$obsah" ]; then
        print_error "Nepodarilo sa stiahnuť obsah"
        return 1
    fi
    
    # Kontrola veľkosti obsahu
    velkost=${#obsah}
    echo "Veľkosť stiahnutého obsahu: $velkost bajtov"
    
    # Ak je obsah príliš malý, pravdepodobne došlo k chybe
    if [ $velkost -lt 1000 ]; then
        print_warning "Stiahnutý obsah je príliš malý, možno je stránka prázdna alebo blokuje prístup"
        return 2
    fi
    
    # Hľadanie kľúčových slov
    found=0
    found_words=""
    
    # Rozdelenie kľúčových slov podľa čiarky
    IFS=',' read -ra SLOVA <<< "$klucove_slova"
    
    echo "Hľadám kľúčové slová..."
    for slovo in "${SLOVA[@]}"; do
        # Odstránenie medzier na začiatku a konci
        slovo=$(echo "$slovo" | xargs)
        
        # Hľadanie slova v obsahu (bez rozlišovania veľkých a malých písmen)
        if echo "$obsah" | grep -i -q "$slovo"; then
            found=$((found + 1))
            found_words="$found_words $slovo,"
        fi
    done
    
    # Odstránenie poslednej čiarky
    found_words=${found_words%,}
    
    # Výpis nájdených slov
    if [ $found -gt 0 ]; then
        print_success "Nájdené kľúčové slová ($found): $found_words"
    else
        print_warning "Nenašli sa žiadne kľúčové slová"
    fi
    
    # Vyhodnotenie relevancie
    if [ $found -ge $min_najdenych ]; then
        print_success "Zdroj je relevantný - nájdených $found kľúčových slov"
        return 0
    else
        print_error "Zdroj nie je dostatočne relevantný - nájdených len $found kľúčových slov (minimum: $min_najdenych)"
        return 3
    fi
}

# Hlavný testovací blok
print_header "TESTOVANIE RELEVANCIE ZDRAVOTNÍCKYCH A VEDECKÝCH ZDROJOV"

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

# Počítadlá pre relevanciu
relevantne=0
nerelevantne=0
chyba_testu=0
celkom_zdrojov=${#zdroje[@]}

# Testovanie relevancie zdrojov
for zdroj in "${zdroje[@]}"; do
    # Rozdelenie informácií o zdroji
    nazov=$(echo "$zdroj" | cut -d'|' -f1)
    url=$(echo "$zdroj" | cut -d'|' -f2)
    
    # Výber kľúčových slov podľa jazyka
    if [[ "$url" == *".cz"* ]]; then
        # Pre české zdroje použijeme české kľúčové slová
        klucove_slova="$CESKE_KLUCOVE_SLOVA"
    else
        # Pre ostatné zdroje použijeme slovenské kľúčové slová
        klucove_slova="$KLUCOVE_SLOVA"
    fi
    
    # Testovanie relevancie s minimálnou požiadavkou 3 nájdených slov
    test_source_relevance "$url" "$nazov" "$klucove_slova" 3
    vysledok=$?
    
    # Vyhodnotenie výsledku
    case $vysledok in
        0) relevantne=$((relevantne + 1)) ;;
        3) nerelevantne=$((nerelevantne + 1)) ;;
        *) chyba_testu=$((chyba_testu + 1)) ;;
    esac
done

# Zobrazenie súhrnných výsledkov
print_header "SÚHRNNÉ VÝSLEDKY TESTOVANIA RELEVANCIE ZDROJOV"

echo "Celkový počet testovaných zdrojov: $celkom_zdrojov"
print_success "Relevantné zdroje: $relevantne"
print_error "Nerelevantné zdroje: $nerelevantne"
print_warning "Chyba pri testovaní: $chyba_testu"
echo ""

# Výpočet percentuálnej relevancie
percentualna_relevancia=0
if [ $((relevantne + nerelevantne)) -gt 0 ]; then
    percentualna_relevancia=$((relevantne * 100 / (relevantne + nerelevantne)))
fi

echo "Percentuálna relevancia zdrojov: $percentualna_relevancia%"
if [ $percentualna_relevancia -ge 75 ]; then
    print_success "Väčšina zdrojov je relevantná pre zdravotnícke a vedecké správy."
elif [ $percentualna_relevancia -ge 50 ]; then
    print_warning "Približne polovica zdrojov je relevantná, zvážte revíziu niektorých zdrojov."
else
    print_error "Väčšina zdrojov nie je relevantná, odporúčame prehodnotiť výber zdrojov."
fi

print_header "KONIEC TESTOVANIA RELEVANCIE"