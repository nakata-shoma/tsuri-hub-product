"""
ジャッカル公式サイトのロッド商品一覧から個別商品ページのURLを収集する。

ジャッカルは釣種ごとにサブサイトが分かれており（バス/トラウト(timon)/
ソルトショア/ソルトオフショア）、各サブサイトの /products/category/rod/
自体には個別商品への直接リンクがない。サブカテゴリは各ページのナビゲーション
メニュー内、「ROD」への<a>を含む<li>配下の ul.nav-product__sub にある
（このリンクは1ページに複数回重複出現するため、実際にサブメニューを
持っている方を採用する）。

また商品ページのURL構造がサブサイトによって異なる点に注意:
- バス/トラウト/ソルトショア: /products/rod/<サブカテゴリ>/<スラッグ>/
- ソルトオフショア: /products/<スラッグ>/ （"rod"のセグメントを含まないフラット構造）
そのためURLパターンでの絞り込みはせず、各サブカテゴリページ内の
/products/ 配下（category以外）のリンクをそのまま収集する。
ROD以外のカテゴリ（ツール・ステッカー・ケース等のロッド関連グッズ）が
「ROD」ナビゲーション配下に混在しているが、これらの商品ページも比較表
テンプレート自体は共有しているため、URLの時点では区別できない
（01_get_item_spec.py側でLength列の有無により実際のロッドかどうかを判定する）。
"""
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://www.jackall.co.jp"

# 各サブサイトの ROD カテゴリ入口。
ENTRY_URLS = [
    "https://www.jackall.co.jp/timon/products/category/rod/",
    "https://www.jackall.co.jp/bass/products/category/rod/",
    "https://www.jackall.co.jp/saltwater/shore-casting/products/category/rod/",
    "https://www.jackall.co.jp/saltwater/offshore-casting/products/category/rod/",
]

OUTPUT_CSV = "./09_jackall_product/jackall_urls/jackall_products_rod.csv"


def products_root_of(entry_url):
    """".../<site>/products/category/rod/" → ".../<site>/products/" を返す"""
    idx = entry_url.index("products/") + len("products/")
    return entry_url[:idx]


def find_rod_subcategory_urls(soup, entry_url):
    """
    ナビゲーションの「ROD」メニュー配下（ul.nav-product__sub）にある
    サブカテゴリURL一覧を取得する。同じ「ROD」リンクがページ内に複数箇所
    出現するが、サブメニューを実際に持っている方だけを使う。
    """
    rod_href = entry_url.rstrip("/") + "/"

    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue
        if urljoin(BASE_URL, href).rstrip("/") + "/" != rod_href:
            continue
        li = a.find_parent("li")
        if not li:
            continue
        sub_links = li.select("ul.nav-product__sub a")
        if sub_links:
            return {urljoin(BASE_URL, a2.get("href")) for a2 in sub_links if a2.get("href")}

    return set()


def find_product_urls(soup, products_root):
    urls = set()
    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(BASE_URL, href)
        if not full.startswith(products_root):
            continue
        rest = full[len(products_root):]
        if not rest or rest == "/" or rest.startswith("category/"):
            continue
        urls.add(full)
    return urls


def scrape_site(entry_url):
    products_root = products_root_of(entry_url)
    entry_soup = get_soup(entry_url)

    subcategory_urls = find_rod_subcategory_urls(entry_soup, entry_url)
    subcategory_urls.add(entry_url)
    print(f"  RODサブカテゴリ数: {len(subcategory_urls)}")

    all_links = set(find_product_urls(entry_soup, products_root))
    for cat_url in sorted(subcategory_urls):
        print(f"  Scraping category: {cat_url}")
        soup = get_soup(cat_url)
        all_links.update(find_product_urls(soup, products_root))

    return all_links


if __name__ == "__main__":
    all_links = set()
    for entry_url in ENTRY_URLS:
        print(f"=== {entry_url} ===")
        links = scrape_site(entry_url)
        print(f"  → {len(links)} 件")
        all_links.update(links)

    urls = sorted(all_links)
    save_urls_csv(OUTPUT_CSV, urls)
    print(f"完了: {len(urls)} 件")
