import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

REEL_INPUT_CSV = "./03_daiwa_product/daiwa_urls/daiwa_products_reel.csv"
ROD_INPUT_CSV = "./03_daiwa_product/daiwa_urls/daiwa_products_rod.csv"
REEL_OUTPUT_DIR = "./03_daiwa_product/daiwa_reel_json"
ROD_OUTPUT_DIR = "./03_daiwa_product/daiwa_rod_json"

os.makedirs(ROD_OUTPUT_DIR, exist_ok=True)
os.makedirs(REEL_OUTPUT_DIR, exist_ok=True)

def find_price_key(raw_dict):
    pattern = re.compile(r"価格")
    for key in raw_dict.keys():
        if pattern.search(key):
            return key
    return None

def extract_product_name(soup):
    """
    h1.font_Midashi から日本語名 + (英名) を取得
    """
    h1 = soup.select_one("h1.font_Midashi")
    if not h1:
        return None

    # 日本語名（h1 の最初のテキスト）
    jp_name = h1.contents[0].strip() if h1.contents else h1.get_text(strip=True)

    # 英語名（span.font_nimbus）
    span = h1.select_one("span.font_nimbus")
    en_name = span.get_text(strip=True) if span else None

    if en_name:
        return f"{jp_name} ({en_name})"
    return jp_name

def parse_multi_spec_table(soup, url, product_name):
    # 見出しは基本「製品スペック」だが、一部製品ページ（例: dg8tkt6）では「スペック概要」表記
    h2 = None
    for tag in soup.select("h2.font_Midashi"):
        text = tag.get_text(strip=True)
        if "製品スペック" in text or "スペック概要" in text:
            h2 = tag
            break

    if not h2:
        return []

    table = h2.find_next("table")
    if not table:
        return []

    rows = table.select("tr")
    if len(rows) < 2:
        return []

    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]

    products = []

    for row in rows[1:]:
        value_cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]

        if len(value_cells) != len(header_cells):
            continue

        raw = dict(zip(header_cells, value_cells))

        price_key = find_price_key(raw)
        price = to_number(raw.get(price_key)) if price_key else None

        item_name = raw.get("アイテム")
        jan = raw.get("JAN")

        exclude_keys = ["アイテム", "JAN"]
        if price_key:
            exclude_keys.append(price_key)

        specs = {k: v for k, v in raw.items() if k not in exclude_keys}

        for key in specs:
            specs[key] = to_number(specs[key])

        product = {
            "item_name": item_name,
            "jan": jan,
            "price": price,
            "url": url,
            "product_name": product_name,
            "specs": specs,
        }

        products.append(product)

    return products

def process_csv(input_csv, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # product_name（表示名）が異なるURL間で偶然一致するケースがある
    # （例: HRF® SXの通常仕様とGR仕様は別ページだがh1が同一）。
    # URLごとに毎回save_jsonすると後勝ちで前のURLのアイテムが消えるため、
    # 同一product_nameのアイテムを全URL分集約してから1回だけ保存する。
    groups = {}

    for url in read_urls_csv(input_csv):
        print(f"解析中: {url}")
        soup = get_soup(url)

        # 製品名取得
        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        table_data = parse_multi_spec_table(soup, url, product_name)
        if not table_data:
            print("  → テーブルなし")
            continue

        groups.setdefault(product_name, []).extend(table_data)

    for product_name, items in groups.items():
        safe_name = sanitize_filename(product_name)
        filepath = os.path.join(output_dir, safe_name + ".json")
        save_json(filepath, items)
        print(f"保存: {filepath}（{len(items)}件）")

def main():
    process_csv(REEL_INPUT_CSV, REEL_OUTPUT_DIR)
    process_csv(ROD_INPUT_CSV, ROD_OUTPUT_DIR)

if __name__ == "__main__":
    main()
