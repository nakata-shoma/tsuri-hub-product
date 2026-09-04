"""
ゴールデンミーンの個別商品ページ（ロッドシリーズ）から品番・価格・スペック等を
取得しJSONに出力する。

サイト内に新旧2種類のテンプレートが混在している。
- 旧テンプレート: <div class="spec"><table>（クラス指定なし）、英語ヘッダー（Model, Price(yen)等）
- 新テンプレート: <table class="spec_table2">等、日本語ヘッダー（品番, 価格等）。
  1ページに複数テーブル（モデル種別ごと）を持つことがあり、テーブル内に
  説明文だけのtr（colspanでセル数が header と食い違う）が混在するがそれは
  自動的にスキップされる。
- 単一モデルテンプレート: <table class="spec_table">で品番列自体が存在せず、
  データ行が1行のみ（例: テンカラマスター360）。この場合はproduct_nameを
  item_nameとして扱う。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="goldenmean", category="rod"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./07_goldenmean_product/goldenmean_urls/goldenmean_products_rod.csv"
OUTPUT_DIR = "./07_goldenmean_product/goldenmean_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

ITEM_NAME_KEYS = ["品番", "Model", "MODEL"]
PRICE_KEYS = ["価格", "Price(yen)", "Price"]
PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_product_name(soup):
    title = soup.select_one("title")
    if not title:
        return None
    text = title.get_text(strip=True)
    return text.split("｜")[0].strip() or None


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def parse_spec_tables(soup, url, product_name):
    tables = soup.select('div.spec table, table[class*="spec_table"]')

    products = []

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

        item_key = next((k for k in ITEM_NAME_KEYS if k in header), None)
        price_key = next((k for k in PRICE_KEYS if k in header), None)

        if not item_key:
            # 品番列がない単一モデル商品（例: テンカラマスター360）。
            # データ行が1行のみならproduct_nameをitem_nameとして扱う。
            data_rows = rows[1:]
            if len(data_rows) != 1:
                continue
            cols = [c.get_text(strip=True) for c in data_rows[0].find_all(["th", "td"])]
            if len(cols) != len(header):
                continue
            raw = dict(zip(header, cols))
            price = extract_price(raw.get(price_key)) if price_key else None
            exclude = [price_key] if price_key else []
            specs = {k: to_number(v) for k, v in raw.items() if k not in exclude}
            products.append({
                "item_name": product_name,
                "jan": None,
                "price": price,
                "url": url,
                "product_name": product_name,
                "specs": specs,
            })
            continue

        for row in rows[1:]:
            cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cols) != len(header):
                continue

            raw = dict(zip(header, cols))
            item_name = raw.get(item_key)
            if not item_name:
                continue

            price = extract_price(raw.get(price_key)) if price_key else None

            exclude = [item_key]
            if price_key:
                exclude.append(price_key)
            specs = {k: to_number(v) for k, v in raw.items() if k not in exclude}

            products.append({
                "item_name": item_name,
                "jan": None,
                "price": price,
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

        table_data = parse_spec_tables(soup, url, product_name)
        if not table_data:
            print("  → テーブルなし")
            continue

        filepath = os.path.join(output_dir, sanitize_filename(product_name) + ".json")
        save_json(filepath, table_data)
        print(f"  → 保存: {filepath}")


def main():
    process_csv(INPUT_CSV, OUTPUT_DIR)


if __name__ == "__main__":
    main()
