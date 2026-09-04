"""
スミスの個別商品ページ（ロッド）から品番・価格・スペック等を取得しJSONに出力する。

1ページに「ROD No.」をヘッダーに含む表（1ヘッダー行+1データ行）が
モデル数だけ複数存在する構成（例: calypso.htmlはSJ1/SJ2/LJ1/LJ2の4表）。
それぞれの表を1品番として扱い、同一ページ内の全表をまとめて1シリーズの
JSONとして出力する。
価格列は「price￥」のように末尾に通貨記号が付くため部分一致で判定する。
SuperStrike（スミスのサブブランド、superstrike/以下）はテンプレートが異なり
.pro_tittle_nameが無いため、その場合は<title>タグ（"｜SMITH Super Strike"の
接尾辞を除去）にフォールバックする。ヘッダーセルも<th>を使うページがあるため
th/td両方から取得する。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="smith", category="rod"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./12_smith_product/smith_urls/smith_products_rod.csv"
OUTPUT_DIR = "./12_smith_product/smith_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")


def extract_product_name(soup):
    name_div = soup.select_one(".pro_tittle_name")
    if name_div:
        text = name_div.get_text(strip=True)
        if text:
            return text
    title = soup.select_one("title")
    if title:
        text = title.get_text(strip=True).split("｜")[0].strip()
        return text or None
    return None


def find_key_containing(header, substr):
    return next((k for k in header if substr in k), None)


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def parse_rod_tables(soup, url, product_name):
    products = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        if "ROD No." not in header:
            continue

        price_key = find_key_containing(header, "price")

        for row in rows[1:]:
            cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            if len(cols) != len(header):
                continue

            raw = dict(zip(header, cols))
            item_name = raw.get("ROD No.")
            if not item_name:
                continue

            exclude = ["ROD No."]
            if price_key:
                exclude.append(price_key)
            specs = {k: to_number(v) for k, v in raw.items() if k not in exclude and v}

            products.append({
                "item_name": item_name,
                "jan": None,
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

        table_data = parse_rod_tables(soup, url, product_name)
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
