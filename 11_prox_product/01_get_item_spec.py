"""
プロックスの個別商品ページ（ロッド・リール）から品番・価格・スペック等を取得しJSONに出力する。

商品名はページ最初の h2 から取得する（h1はサイト共通の会社名見出しのため使えない。
h2のclassはブランドラインにより prox / viceo 等いくつかの種類があるため、
class名では絞り込まずページ内最初のh2をそのまま使う）。
スペック表には「品番」列が無く、「商品コード」列がそのまま品番として機能している
（ページによっては「品コード」のように表記が揺れることがあるため、
「コード」を含み「JAN」を含まない列を商品コード列とみなす）。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="prox", category="rod"/"reel"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

CATEGORIES = {
    "rod": {
        "input_csv": "./11_prox_product/prox_urls/prox_products_rod.csv",
        "output_dir": "./11_prox_product/prox_rod_json",
    },
    "reel": {
        "input_csv": "./11_prox_product/prox_urls/prox_products_reel.csv",
        "output_dir": "./11_prox_product/prox_reel_json",
    },
}

PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_product_name(soup):
    h2 = soup.find("h2")
    return h2.get_text(strip=True) if h2 else None


def find_key_containing(header, substr):
    return next((k for k in header if substr in k), None)


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def parse_spec_table(soup, url, product_name):
    table = soup.select_one("table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

    item_key = next((k for k in header if "コード" in k and "JAN" not in k), None)
    if not item_key:
        return []
    jan_key = find_key_containing(header, "JAN")
    price_key = find_key_containing(header, "価格")

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
        if jan_key:
            exclude.append(jan_key)
        if price_key:
            exclude.append(price_key)
        specs = {k: to_number(v) for k, v in raw.items() if k not in exclude}

        products.append({
            "item_name": item_name,
            "jan": raw.get(jan_key) if jan_key else None,
            "price": extract_price(raw.get(price_key)) if price_key else None,
            "url": url,
            "product_name": product_name,
            "specs": specs,
        })

    return products


def process_csv(input_csv, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for url in read_urls_csv(input_csv):
        print(f"解析中: {url}")
        soup = get_soup(url)

        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        table_data = parse_spec_table(soup, url, product_name)
        if not table_data:
            print("  → テーブルなし")
            continue

        filepath = os.path.join(output_dir, sanitize_filename(product_name) + ".json")
        save_json(filepath, table_data)
        print(f"  → 保存: {filepath}")


def main():
    for category, paths in CATEGORIES.items():
        print(f"=== {category} ===")
        process_csv(paths["input_csv"], paths["output_dir"])


if __name__ == "__main__":
    main()
