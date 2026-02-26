import os
import glob
from bs4 import BeautifulSoup

def patch():
    html_files = glob.glob("docs/*.html")
    for f in html_files:
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
        if "data-theme" in content and "const toggle" in content:
            print(f"Theme toggle exists in {f}")

patch()
