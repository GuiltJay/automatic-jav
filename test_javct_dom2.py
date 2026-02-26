import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()
url = "https://javct.net/models"
print(f"Fetching {url}")
r = scraper.get(url)
soup = BeautifulSoup(r.text, "html.parser")

model_cards = soup.select(".card, .actor, figure")
print(f"Found {len(model_cards)} potential model elements.")
for m in model_cards[:2]:
    print("---")
    print(m.prettify()[:500])

url_cats = "https://javct.net/categories"
print(f"\nFetching {url_cats}")
r = scraper.get(url_cats)
soup = BeautifulSoup(r.text, "html.parser")
cat_links = soup.select(".card a, ul.categories li a, a.category")
print(f"Found {len(cat_links)} potential category elements.")
for c in cat_links[:5]:
    print("---", c.get('href'), c.text.strip())

