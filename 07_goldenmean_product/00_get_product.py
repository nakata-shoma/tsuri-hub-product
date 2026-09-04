"""
ゴールデンミーン公式サイトのロッド製品一覧ページから個別商品ページのURLを収集する。
/item/rod/ に全シリーズへのリンクが1ページに収まっており、ページネーションはない。
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://www.golden-mean.co.jp"
LIST_URL = "https://www.golden-mean.co.jp/item/rod/"
OUTPUT_CSV = "./07_goldenmean_product/goldenmean_urls/goldenmean_products_rod.csv"

PRODUCT_LINK_RE = re.compile(r"^(?:https://www\.golden-mean\.co\.jp)?/item/rod/[^/]+/?$")


def extract_product_links(soup):
    links = set()
    for a in soup.select("a"):
        href = a.get("href")
        if href and PRODUCT_LINK_RE.match(href):
            links.add(urljoin(BASE_URL, href))
    return links


if __name__ == "__main__":
    soup = get_soup(LIST_URL)
    urls = sorted(extract_product_links(soup))
    save_urls_csv(OUTPUT_CSV, urls)
    print(f"完了: {len(urls)} 件")
