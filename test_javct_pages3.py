import cloudscraper
from bs4 import BeautifulSoup
scraper = cloudscraper.create_scraper()

r = scraper.get("https://javct.net/models?page=2")
soup = BeautifulSoup(r.text, "html.parser")
cards = soup.select(".card__title a")
print(f"Models page 2: {len(cards)}")
if cards:
    print(cards[0].text.strip())
