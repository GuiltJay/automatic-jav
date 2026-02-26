import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()
url = "https://javct.net/amateur"
r = scraper.get(url)
soup = BeautifulSoup(r.text, "html.parser")
cards = soup.select(".card")
if cards:
    c = cards[0]
    print(c.prettify())
