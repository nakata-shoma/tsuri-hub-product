"""
エバーグリーン公式サイト（バス/トラウト/ソルトの全ジャンル・ロッド）の
商品一覧ページから個別商品ページのURLを収集する。

サイトは旧式の静的HTML/PHP構成。ジャンルごとの製品一覧ページ（/freshwater/,
/trout/, /saltwater/）に、ロッドの各シリーズ一覧ページ
（goods_list_22rod.php?...）へのリンクがあり、各シリーズ一覧ページに
個別商品ページ（/goods_list/<Code>.html）へのリンクがある。
ルアー（goods_list_22lure.php）やアパレル等（goods_list_2.php）は
URLパターンが明確に異なるため混入の心配はない。
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://www.evergreen-fishing.com"
CATALOG_URLS = [
    "https://www.evergreen-fishing.com/freshwater/",
    "https://www.evergreen-fishing.com/trout/",
    "https://www.evergreen-fishing.com/saltwater/",
]
OUTPUT_CSV = "./06_evergreen_product/evergreen_urls/evergreen_products_rod.csv"

SERIES_LIST_RE = re.compile(r"goods_list_22rod\.php\?")
PRODUCT_LINK_RE = re.compile(r"^/goods_list/[A-Za-z0-9]+\.html$")


def find_rod_series_urls(soup):
    urls = set()
    for a in soup.select("a"):
        href = a.get("href")
        if href and SERIES_LIST_RE.search(href):
            urls.add(urljoin(BASE_URL, href))
    return sorted(urls)


def find_product_urls(soup):
    urls = set()
    for a in soup.select("a"):
        href = a.get("href")
        if href and PRODUCT_LINK_RE.match(href):
            urls.add(urljoin(BASE_URL, href))
    return urls


def scrape_all():
    series_urls = set()
    for catalog_url in CATALOG_URLS:
        print(f"=== {catalog_url} ===")
        catalog_soup = get_soup(catalog_url)
        found = find_rod_series_urls(catalog_soup)
        print(f"  ロッドシリーズ数: {len(found)}")
        series_urls.update(found)

    all_links = set()
    for series_url in sorted(series_urls):
        print(f"Scraping series: {series_url}")
        soup = get_soup(series_url)
        all_links.update(find_product_urls(soup))

    return sorted(all_links)


if __name__ == "__main__":
    urls = scrape_all()
    save_urls_csv(OUTPUT_CSV, urls)
    print(f"完了: {len(urls)} 件")
