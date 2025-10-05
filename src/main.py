# src/main.py
from playwright.sync_api import sync_playwright
from .scraper import run

def main():
    print("Iniciando Scrapping")
    with sync_playwright() as playwright:
        run(playwright)

if __name__ == "__main__":
    main()