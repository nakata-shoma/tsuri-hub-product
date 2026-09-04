"""
Ripple Fisherの個別商品ページ（ロッドシリーズ）から品番・価格・スペック等を
取得しJSONに出力する。

1ページ = 1シリーズで、モデルごとに <div class="midashi3">モデル名</div> と
<div class="spec"><table>...スペック1行</table></div> のペアが並ぶ構成
（1ページに複数モデル）。テーブル自体に品番/型番列は無いため、直前の
midashi3見出しのテキストをitem_nameとして使う。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="ripplefisher", category="rod"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./14_ripplefisher_product/ripplefisher_urls/ripplefisher_products_rod.csv"
OUTPUT_DIR = "./14_ripplefisher_product/ripplefisher_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_product_name(soup):
    title = soup.select_one("title")
    if not title:
        return None
    text = title.get_text(strip=True).split("|")[0].strip()
    return text or None


def find_key_containing(header, substr):
    return next((k for k in header if substr in k), None)


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def parse_model_specs(soup, url, product_name):
    products = []

    for spec_div in soup.select("div.spec"):
        table = spec_div.find("table")
        if not table:
            continue

        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        cols = [c.get_text(strip=True) for c in rows[1].find_all(["th", "td"])]
        if len(cols) != len(header):
            continue

        heading = spec_div.find_previous(class_="midashi3")
        item_name = heading.get_text(strip=True) if heading else None
        if not item_name:
            continue

        raw = dict(zip(header, cols))
        price_key = find_key_containing(header, "Price")
        jan_key = find_key_containing(header, "JAN")

        exclude = [k for k in (price_key, jan_key) if k]
        specs = {k: to_number(v) for k, v in raw.items() if k not in exclude and v}

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
    groups = {}

    for url in read_urls_csv(input_csv):
        print(f"解析中: {url}")
        soup = get_soup(url)

        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        items = parse_model_specs(soup, url, product_name)
        if not items:
            print("  → テーブルなし")
            continue

        groups.setdefault(product_name, []).extend(items)

    for product_name, items in groups.items():
        filepath = os.path.join(output_dir, sanitize_filename(product_name) + ".json")
        save_json(filepath, items)
        print(f"保存: {filepath}（{len(items)}件）")


def main():
    process_csv(INPUT_CSV, OUTPUT_DIR)


if __name__ == "__main__":
    main()
