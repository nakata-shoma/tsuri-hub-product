"""
アブガルシア公式サイト（Shopifyストア）のロッド/リール商品一覧から
個別商品ページのURLを収集する。
Shopify標準の /collections/<handle>/products.json エンドポイントを使う
（レンダリング済みHTMLをスクレイピングするより確実・軽量）。
ロッドは collection handle "rods"、リールは "reels"（スピニング/ベイト
両方を含む横断コレクション）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import save_urls_csv  # noqa: E402
import requests

BASE_URL = "https://abugarcia.jp"
HEADERS = {"User-Agent": "Mozilla/5.0"}

ROD_HANDLE = "rods"
ROD_OUTPUT_CSV = "./08_abugarcia_product/abugarcia_urls/abugarcia_products_rod.csv"
REEL_HANDLE = "reels"
REEL_OUTPUT_CSV = "./08_abugarcia_product/abugarcia_urls/abugarcia_products_reel.csv"


def fetch_collection_urls(handle):
    urls = []
    page = 1
    while True:
        res = requests.get(
            f"{BASE_URL}/collections/{handle}/products.json",
            headers=HEADERS,
            params={"limit": 250, "page": page},
        )
        res.raise_for_status()
        products = res.json().get("products", [])
        if not products:
            break

        for p in products:
            urls.append(f"{BASE_URL}/products/{p['handle']}")
        page += 1

    return urls


if __name__ == "__main__":
    rod_urls = sorted(set(fetch_collection_urls(ROD_HANDLE)))
    save_urls_csv(ROD_OUTPUT_CSV, rod_urls)
    print(f"ロッド完了: {len(rod_urls)} 件")

    reel_urls = sorted(set(fetch_collection_urls(REEL_HANDLE)))
    save_urls_csv(REEL_OUTPUT_CSV, reel_urls)
    print(f"リール完了: {len(reel_urls)} 件")
