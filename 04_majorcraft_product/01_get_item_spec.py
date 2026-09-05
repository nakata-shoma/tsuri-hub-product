import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import (  # noqa: E402
    extract_canonical_url,
    get_soup,
    is_junk_spec_key,
    read_urls_csv,
    sanitize_filename,
    save_json,
    to_number,
)

INPUT_CSV = "./04_majorcraft_product/majorcraft_urls/majorcraft_rod_urls.csv"
OUTPUT_DIR = "./04_majorcraft_product/majorcraft_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# -----------------------------
# 製品名（title の先頭部分だけ）
# -----------------------------
def extract_product_name(soup):
    title = soup.select_one("title")
    if not title:
        return None

    text = title.get_text(strip=True)

    # MajorCraft の区切り文字パターン
    separators = ["–", "-", "｜", "|"]

    for sep in separators:
        if sep in text:
            return text.split(sep)[0].strip()

    return text.strip()


# -----------------------------
# SPEC TABLE（Lineup）解析
# -----------------------------
def extract_price(v):
    """
    "¥13400（税込 ¥14740）" → 13400 (税別価格の数字部分のみ)
    """
    if not v:
        return None
    match = re.search(r"[\d,]+", v)
    return to_number(match.group()) if match else None


JAN_HEADER_RE = re.compile(r"^JAN\s*[\(（]\s*(\d+)\s*[\)）]")


def parse_majorcraft_spec_table(soup, url, product_name):
    h2 = soup.find("h2", class_="rod-lineup__heading")
    if not h2:
        return []

    table = h2.find_next("table")
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

        # MajorCraft は Model が品番
        item_name = raw.get("Model") or raw.get("MODEL") or raw.get("品番")

        # JAN列は「JAN (4573236)」のようにメーカーコード（GS1事業者コード）が
        # ヘッダー名側に埋め込まれ、セルの値はそれに続く商品コードのみ（例: 269191）
        # という特殊な形式。他メーカーと揃えるため両者を連結してフルJANにする。
        # PRICEも specs に混在しているので、他メーカーと同じくトップレベルへ分離する。
        jan = None
        price = None
        specs = {}
        for key, value in raw.items():
            if is_junk_spec_key(key):
                continue
            jan_match = JAN_HEADER_RE.match(key)
            if jan_match:
                suffix = re.sub(r"\D", "", value) if value else ""
                jan = jan_match.group(1) + suffix if suffix else None
            elif key == "PRICE":
                price = extract_price(value)
            else:
                specs[key] = to_number(value)

        products.append({
            "item_name": item_name,
            "jan": jan,
            "price": price,
            "url": url,
            "product_name": product_name,
            "specs": specs,
        })

    return products


# -----------------------------
# CSV を処理する共通関数
# -----------------------------
def process_csv(input_csv, output_dir):
    for url in read_urls_csv(input_csv):
        print(f"解析中: {url}")

        soup = get_soup(url)

        # canonical URL
        canonical = extract_canonical_url(soup)
        if not canonical:
            print("  → canonical URL なし")
            continue

        # 製品名
        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし")
            continue

        safe_name = sanitize_filename(product_name)

        # SPEC TABLE
        table_data = parse_majorcraft_spec_table(soup, canonical, product_name)
        if not table_data:
            print("  → スペック表なし")
            continue

        filepath = os.path.join(output_dir, safe_name + ".json")
        save_json(filepath, table_data)

        print(f"  → 保存: {filepath}")


# -----------------------------
# メイン処理
# -----------------------------
def main():
    process_csv(INPUT_CSV, OUTPUT_DIR)

if __name__ == "__main__":
    main()
