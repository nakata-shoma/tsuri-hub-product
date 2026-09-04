"""
アブガルシアの個別商品ページ（ロッド/リール）から品番・価格・スペック等を取得しJSONに出力する。

商品ページ上の「モデル比較表」(table.product-compare-models__table) に
製品コード・JAN・品番・スペック・価格がまとまっているため、これを解析する
（Shopify標準の products.json API にはこの詳細スペックが含まれないため、
 HTMLページ自体を取得する必要がある）。リールも同じテーブル構造
（ヘッダーに「製品名」「製品コード」「JAN/UPC」等を含む）のため、
ロッドと同じパーサーをそのまま使い回せる。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="abugarcia", category="rod"/"reel"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

ROD_INPUT_CSV = "./08_abugarcia_product/abugarcia_urls/abugarcia_products_rod.csv"
ROD_OUTPUT_DIR = "./08_abugarcia_product/abugarcia_rod_json"
REEL_INPUT_CSV = "./08_abugarcia_product/abugarcia_urls/abugarcia_products_reel.csv"
REEL_OUTPUT_DIR = "./08_abugarcia_product/abugarcia_reel_json"

os.makedirs(ROD_OUTPUT_DIR, exist_ok=True)
os.makedirs(REEL_OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_product_name(soup):
    h1 = soup.select_one("h1")
    return h1.get_text(strip=True) if h1 else None


def find_key_containing(header, substr):
    return next((k for k in header if substr in k), None)


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def parse_compare_table(soup, url, product_name):
    table = soup.select_one("table.product-compare-models__table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

    item_key = "製品名" if "製品名" in header else None
    code_key = "製品コード" if "製品コード" in header else None
    jan_key = find_key_containing(header, "JAN")
    price_key = find_key_containing(header, "価格")

    if not item_key:
        return []

    products = []

    for row in rows[1:]:
        cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cols) != len(header):
            continue

        raw = dict(zip(header, cols))
        item_name = raw.get(item_key)
        if not item_name:
            continue

        exclude = [item_key]
        if code_key:
            exclude.append(code_key)
        if jan_key:
            exclude.append(jan_key)
        if price_key:
            exclude.append(price_key)

        specs = {k: to_number(v) for k, v in raw.items() if k not in exclude and v}

        products.append({
            "item_name": item_name,
            "jan": raw.get(jan_key) if jan_key else None,
            "product_code": raw.get(code_key) if code_key else None,
            "price": extract_price(raw.get(price_key)) if price_key else None,
            "url": url,
            "product_name": product_name,
            "specs": specs,
        })

    return products


def process_csv(input_csv, output_dir):
    for url in read_urls_csv(input_csv):
        print(f"解析中: {url}")
        soup = get_soup(url)

        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        table_data = parse_compare_table(soup, url, product_name)
        if not table_data:
            print("  → テーブルなし")
            continue

        filepath = os.path.join(output_dir, sanitize_filename(product_name) + ".json")
        save_json(filepath, table_data)
        print(f"  → 保存: {filepath}")


def main():
    process_csv(ROD_INPUT_CSV, ROD_OUTPUT_DIR)
    process_csv(REEL_INPUT_CSV, REEL_OUTPUT_DIR)


if __name__ == "__main__":
    main()
