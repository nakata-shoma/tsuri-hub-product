import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.daiwa.com"
REEL_URL = "https://www.daiwa.com/jp/product/productlist?category1=%E3%83%AA%E3%83%BC%E3%83%AB"
ROD_URL  = "https://www.daiwa.com/jp/product/productlist?category1=%E3%83%AD%E3%83%83%E3%83%89"

def get_soup(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def extract_product_links(soup):
    links = []

    for a in soup.select("a"):
        href = a.get("href")

        # 空 or None は除外
        if not href:
            continue

        # /jp/product/ で始まるものだけ
        if not href.startswith("/jp/product/"):
            continue

        # productlist を含むものは除外
        if "productlist" in href:
            continue

        # /jp/product/ だけのダミーは除外
        if href.rstrip("/") == "/jp/product":
            continue

        # 本物の製品ページだけ追加
        links.append(urljoin(BASE_URL, href))

    return links


def find_next_page(soup):
    # ページネーションの「次へ」リンクを探す
    next_btn = soup.select_one("a[aria-label='次へ'], a.next")
    if next_btn:
        href = next_btn.get("href")
        return urljoin(BASE_URL, href)
    return None

def scrape_all_pages(start_url):
    url = start_url
    all_links = set()

    while url:
        print(f"Scraping: {url}")
        soup = get_soup(url)

        # 製品リンクを抽出
        links = extract_product_links(soup)
        all_links.update(links)

        # 次ページを探す
        url = find_next_page(soup)

    return sorted(all_links)

def save_to_csv(urls, filename="./03_daiwa_product/daiwa_urls/daiwa_products.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for url in urls:
            writer.writerow([url])

if __name__ == "__main__":
    # リール
    reel_urls = scrape_all_pages(REEL_URL)
    save_to_csv(
        reel_urls,
        filename="./03_daiwa_product/daiwa_urls/daiwa_products_reel.csv"
    )
    print(f"リール完了: {len(reel_urls)} 件")

    # ロッド
    rod_urls = scrape_all_pages(ROD_URL)
    save_to_csv(
        rod_urls,
        filename="./03_daiwa_product/daiwa_urls/daiwa_products_rod.csv"
    )
    print(f"ロッド完了: {len(rod_urls)} 件")

