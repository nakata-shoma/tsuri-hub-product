"""
がまかつの個別商品ページ（ロッド）から品番・価格・スペック等を取得しJSONに出力する。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="gamakatsu", category="rod"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import extract_canonical_url, get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./05_gamakatsu_product/gamakatsu_urls/gamakatsu_products_rod.csv"
OUTPUT_DIR = "./05_gamakatsu_product/gamakatsu_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_price(value):
    """"29,800●"のように脚注記号（●等）が混ざることがあるため数字部分のみ抽出する"""
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def find_spec_heading(soup):
    for tag in soup.find_all("h3"):
        if "製品スペック" in tag.get_text(strip=True):
            return tag
    return None


def extract_product_name(soup):
    """
    「製品スペック」見出し直後の productsBlock-tableTtl から
    シリーズ名（例: "がま磯 カゴSPECIAL5　(がま磯 カゴスペシャルファイブ)"）を取得する。
    まれに productsBlock-tableTtl が未設定で見出しと同じ"製品スペック"という
    プレースホルダー文字列になっている製品があるため、その場合は <title> から補う。
    """
    h3 = find_spec_heading(soup)
    if h3:
        ttl = h3.find_next("p", class_="productsBlock-tableTtl")
        if ttl:
            text = ttl.get_text(strip=True)
            if text and text != "製品スペック":
                return text

    title = soup.select_one("title")
    if title:
        name = title.get_text(strip=True).split("|")[0].strip()
        return name or None
    return None


def parse_spec_table(soup, url, product_name):
    h3 = find_spec_heading(soup)
    if not h3:
        return []

    table = h3.find_next("table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

    products = []

    for row in rows[1:]:
        cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cols) != len(header):
            continue

        raw = dict(zip(header, cols))

        item_name = raw.get("品番")
        jan = raw.get("JANコード")
        product_code = raw.get("品名コード")

        price = extract_price(raw.get("希望本体価格(円)"))

        exclude = ["", "品番", "JANコード", "品名コード", "希望本体価格(円)"]
        specs = {k: to_number(v) for k, v in raw.items() if k not in exclude}

        products.append({
            "item_name": item_name,
            "jan": jan,
            "product_code": product_code,
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

        canonical = extract_canonical_url(soup) or url

        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        table_data = parse_spec_table(soup, canonical, product_name)
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
