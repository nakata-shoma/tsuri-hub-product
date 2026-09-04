"""
テンリュウ公式サイトの商品一覧ページから個別商品ページのURLを収集する。

サイトマップ（/sitemap.html）に全カテゴリ（offshore/shore/bass/trout/fly/
tenkara/snakehead）の全シリーズ（廃盤・旧モデル含む）へのリンクが直接
掲載されているため、それをそのまま利用する。廃盤製品もデータとして
保持する方針のため、旧モデル（"_v1"等のサフィックスが付いたページ）も
除外せず収集する。
テンリュウは全製品がロッドのため、カテゴリ（rod）を絞り込む必要はない。
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://fishing.tenryu-magna.com"
SITEMAP_URL = "https://fishing.tenryu-magna.com/sitemap.html"
OUTPUT_CSV = "./10_tenryu_product/tenryu_urls/tenryu_products_rod.csv"

PRODUCT_LINK_RE = re.compile(
    r"^/(?:offshore|shore|bass|trout|fly|tenkara|snakehead)/[^/#]+\.html$"
)


def extract_product_links(soup):
    links = set()
    for a in soup.select("a"):
        href = a.get("href")
        if href and PRODUCT_LINK_RE.match(href.strip()):
            links.add(urljoin(BASE_URL, href.strip()))
    return links


if __name__ == "__main__":
    soup = get_soup(SITEMAP_URL)
    urls = sorted(extract_product_links(soup))
    save_urls_csv(OUTPUT_CSV, urls)
    print(f"完了: {len(urls)} 件")
