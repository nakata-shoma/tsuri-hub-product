import csv
import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST).isoformat()

REEL_INPUT_CSV = "./03_daiwa_product/daiwa_urls/daiwa_products_reel.csv"
ROD_INPUT_CSV = "./03_daiwa_product/daiwa_urls/daiwa_products_rod.csv"
REEL_OUTPUT_DIR = "./03_daiwa_product/daiwa_reel_json"
ROD_OUTPUT_DIR = "./03_daiwa_product/daiwa_rod_json"

os.makedirs(ROD_OUTPUT_DIR, exist_ok=True)
os.makedirs(REEL_OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_soup(url):
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def to_number(value):
    if value is None:
        return None
    v = value.replace(",", "")
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return value

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

def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.replace(" ", "_").replace("　", "_")
    return name

def parse_multi_spec_table(soup, url):
    h2 = None
    for tag in soup.select("h2.font_Midashi"):
        if "製品スペック" in tag.get_text(strip=True):
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
            "specs": specs,
        }

        products.append(product)

    return products

def save_json(filepath, data):
    """
    created_at は初回だけ保持し、updated_at は毎回更新する
    """
    now = datetime.now(JST).isoformat()

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            old = json.load(f)

        for i in range(len(data)):
            if i < len(old) and "created_at" in old[i]:
                data[i]["created_at"] = old[i]["created_at"]
            else:
                data[i]["created_at"] = now

            data[i]["updated_at"] = now

    else:
        for item in data:
            item["created_at"] = now
            item["updated_at"] = now

    with open(filepath, "w", encoding="utf-8") as jf:
        json.dump(data, jf, ensure_ascii=False, indent=2)

def process_csv(input_csv, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        urls = [row[0] for row in reader]

    for url in urls:
        print(f"解析中: {url}")
        soup = get_soup(url)

        # 製品名取得
        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        safe_name = sanitize_filename(product_name)

        table_data = parse_multi_spec_table(soup, url)
        if not table_data:
            print("  → テーブルなし")
            continue

        filepath = os.path.join(output_dir, safe_name + ".json")

        save_json(filepath, table_data)

        print(f"  → 保存: {filepath}")

def main():
    # process_csv(REEL_INPUT_CSV, REEL_OUTPUT_DIR)
    process_csv(ROD_INPUT_CSV, ROD_OUTPUT_DIR)

if __name__ == "__main__":
    main()
