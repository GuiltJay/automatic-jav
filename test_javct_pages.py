import cloudscraper
from bs4 import BeautifulSoup
scraper = cloudscraper.create_scraper()

def check_pagin(url):
    r = scraper.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    pag = soup.select(".pagination a")
    print(f"{url} pagination links: {[a.get('href') for a in pag]}")

check_pagin("https://javct.net/categories")
check_pagin("https://javct.net/models")
