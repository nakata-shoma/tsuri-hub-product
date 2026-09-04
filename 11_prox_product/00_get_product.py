"""
プロックス公式サイトのロッド・リール商品一覧ページから個別商品ページのURLを収集する。
/lineup/category/<rod|reel> をページネーション（/page/N）に沿って巡回し、
/lineup/item/<id> 形式の個別商品リンクを収集する。
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://www.proxinc.co.jp"
CATEGORY_URLS = {
    "rod": "https://www.proxinc.co.jp/lineup/category/rod",
    "reel": "https://www.proxinc.co.jp/lineup/category/reel",
}

PRODUCT_LINK_RE = re.compile(r"^(?:https://www\.proxinc\.co\.jp)?/lineup/item/(\d+)/?$")


def extract_product_links(soup):
    links = set()
    for a in soup.select("a"):
        href = a.get("href")
        if href and PRODUCT_LINK_RE.match(href):
            links.add(urljoin(BASE_URL, href))
    return links


def scrape_category(category_url):
    all_links = set()
    page = 1

    while True:
        url = category_url if page == 1 else f"{category_url}/page/{page}"
        print(f"Scraping: {url}")
        try:
            soup = get_soup(url)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                break
            raise
        links = extract_product_links(soup)
        if not links:
            break
        all_links.update(links)
        page += 1

    return all_links


if __name__ == "__main__":
    for category, url in CATEGORY_URLS.items():
        urls = sorted(scrape_category(url))
        save_urls_csv(f"./11_prox_product/prox_urls/prox_products_{category}.csv", urls)
        print(f"{category} 完了: {len(urls)} 件")
