import cloudscraper
from bs4 import BeautifulSoup
scraper = cloudscraper.create_scraper()

r = scraper.get("https://javct.net/models")
soup = BeautifulSoup(r.text, "html.parser")
cards = soup.select(".card__title a")
print(f"Models: {len(cards)}")
if cards:
    print(cards[0].text.strip(), cards[-1].text.strip())

r = scraper.get("https://javct.net/categories")
soup = BeautifulSoup(r.text, "html.parser")
cards = soup.select(".card__title a")
print(f"Categories: {len(cards)}")

