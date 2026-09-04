"""
がまかつ公式サイトの商品一覧（ロッドカテゴリ）から個別商品ページのURLを収集する。

商品一覧はWordPressの管理画面Ajaxエンドポイント（wp-admin/admin-ajax.php,
action=get_products_search）にPOSTしてJSONで取得する方式（静的HTMLには
商品リンクが含まれない）。s_product に親カテゴリ値 "rod" を渡すと
ロッド配下の全サブカテゴリの商品がまとめて取得できる。
"鈎"（hook）カテゴリはサブカテゴリが100以上あり構造も異なるため未対応。
"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import save_urls_csv  # noqa: E402

AJAX_URL = "https://www.gamakatsu.co.jp/wp-admin/admin-ajax.php"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_CSV = "./05_gamakatsu_product/gamakatsu_urls/gamakatsu_products_rod.csv"

PRODUCT_LINK_RE = re.compile(r'href="(https://www\.gamakatsu\.co\.jp/products/\d+/)"')


def fetch_search_page(s_product, page):
    res = requests.post(
        AJAX_URL,
        headers=HEADERS,
        data={"action": "get_products_search", "pages": page, "s_product": s_product},
    )
    res.raise_for_status()
    return res.json()["data"]


def scrape_category(s_product):
    all_links = set()
    page = 1

    while True:
        print(f"Scraping: s_product={s_product} page={page}")
        data = fetch_search_page(s_product, page)
        all_links.update(PRODUCT_LINK_RE.findall(data["html"]))

        if not data.get("has_next"):
            break
        page += 1

    return sorted(all_links)


if __name__ == "__main__":
    rod_urls = scrape_category("rod")
    save_urls_csv(OUTPUT_CSV, rod_urls)
    print(f"完了: {len(rod_urls)} 件")
