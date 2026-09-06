"""
テンリュウの個別商品ページ（ロッド）から品番・価格・スペック等を取得しJSONに出力する。

スペック表 table.spec.list の列構成はカテゴリ（オフショア/ショア/バス/トラウト/
フライ/テンカラ）ごとに異なるが、「品名」「本体価格」「JANコード」の3列は共通。
それ以外の列はすべてspecsとして扱う。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="tenryu", category="rod"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./10_tenryu_product/tenryu_urls/tenryu_products_rod.csv"
OUTPUT_DIR = "./10_tenryu_product/tenryu_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")

# テンリュウのJANコード欄には企業（GS1事業者）コードを含まない商品コードのみが
# 入っていることが多いため、無ければ補う。
JAN_COMPANY_CODE = "4533933"


def extract_product_name(soup):
    title = soup.select_one("title")
    if not title:
        return None
    return title.get_text(strip=True).split("｜")[0].strip() or None


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def extract_jan(value):
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if digits.startswith(JAN_COMPANY_CODE):
        return digits
    return JAN_COMPANY_CODE + digits


def parse_spec_table(soup, url, product_name):
    table = soup.select_one("table.spec.list")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    if "品名" not in header:
        return []

    price_key = "本体価格" if "本体価格" in header else None
    jan_key = "JANコード" if "JANコード" in header else None

    products = []

    for row in rows[1:]:
        cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cols) != len(header):
            continue

        raw = dict(zip(header, cols))
        item_name = raw.get("品名")
        if not item_name:
            continue

        exclude = ["品名"]
        if price_key:
            exclude.append(price_key)
        if jan_key:
            exclude.append(jan_key)
        specs = {k: to_number(v) for k, v in raw.items() if k not in exclude}

        products.append({
            "item_name": item_name,
            "jan": extract_jan(raw.get(jan_key)) if jan_key else None,
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

        table_data = parse_spec_table(soup, url, product_name)
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
