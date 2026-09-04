"""
エバーグリーンの個別商品ページ（バスロッド、1URL=1品番）から
品番・価格・スペックを取得しJSONに出力する。

他メーカーと異なり1ページ=1シリーズではなく1ページ=1品番のため、
#series-list-anchor のシリーズ名でページをグルーピングしてから
シリーズ単位で1ファイルにまとめて保存する。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="evergreen", category="rod"）。
"""
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./06_evergreen_product/evergreen_urls/evergreen_products_rod.csv"
OUTPUT_DIR = "./06_evergreen_product/evergreen_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_series_name(soup):
    anchor = soup.select_one("#series-list-anchor")
    if not anchor:
        return None
    strong = anchor.find("strong")
    return strong.get_text(strip=True) if strong else None


def extract_item_name(soup):
    h2 = soup.select_one(".productsBox .titleArea h2")
    if not h2:
        return None
    for span in h2.find_all("span"):
        span.decompose()
    return h2.get_text(strip=True) or None


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def parse_spec_table(soup):
    table = soup.select_one("table.spec")
    if not table:
        return {}

    pairs = {}
    for tr in table.select("tr"):
        cells = tr.find_all(["th", "td"])
        for i in range(0, len(cells) - 1, 2):
            key = cells[i].get_text(strip=True)
            value = cells[i + 1].get_text(strip=True)
            if key:
                pairs[key] = value
    return pairs


def parse_product_page(soup, url):
    product_name = extract_series_name(soup)
    item_name = extract_item_name(soup)
    if not product_name or not item_name:
        return None

    pairs = parse_spec_table(soup)
    if not pairs:
        return None

    price = extract_price(pairs.pop("価格", None))
    specs = {k: to_number(v) for k, v in pairs.items()}

    return {
        "item_name": item_name,
        "jan": None,
        "price": price,
        "url": url,
        "product_name": product_name,
        "specs": specs,
    }


def process_csv(input_csv, output_dir):
    groups = defaultdict(list)

    for url in read_urls_csv(input_csv):
        print(f"解析中: {url}")
        soup = get_soup(url)

        item = parse_product_page(soup, url)
        if not item:
            print("  → 製品名またはスペックなし（スキップ）")
            continue

        groups[item["product_name"]].append(item)

    for product_name, items in groups.items():
        filepath = os.path.join(output_dir, sanitize_filename(product_name) + ".json")
        save_json(filepath, items)
        print(f"保存: {filepath}（{len(items)}件）")


def main():
    process_csv(INPUT_CSV, OUTPUT_DIR)


if __name__ == "__main__":
    main()
