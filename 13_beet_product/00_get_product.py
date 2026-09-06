"""
beat（ジギングロッド専門ブランド）公式サイトのロッド商品一覧ページから
個別商品ページのURLを収集する。

https://beat-jig.com/rod は全掲載製品がロッド（beatはジギングロッド専業
ブランドのため他カテゴリと混在する心配はない）。各製品は
https://beat-jig.com/product-item/<id> へのリンクとしてカード形式で
並んでいるだけで、ページネーションはない。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

LIST_URL = "https://beat-jig.com/rod"
OUTPUT_CSV = "./13_beat_product/beat_urls/beat_products_rod.csv"

PRODUCT_LINK_RE = re.compile(r"^https://beat-jig\.com/product-item/\d+/?$")


def extract_product_links(soup):
    links = set()
    for a in soup.select("a"):
        href = a.get("href")
        if href and PRODUCT_LINK_RE.match(href):
            links.add(href)
    return links


if __name__ == "__main__":
    soup = get_soup(LIST_URL)
    urls = sorted(extract_product_links(soup))
    save_urls_csv(OUTPUT_CSV, urls)
    print(f"完了: {len(urls)} 件")
