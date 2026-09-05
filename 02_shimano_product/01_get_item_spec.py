import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import extract_canonical_url, is_junk_spec_key, load_soup, sanitize_filename, save_json, to_number  # noqa: E402

REEL_HTML_DIR = "./02_shimano_product/input/reel"
ROD_HTML_DIR  = "./02_shimano_product/input/rod"

REEL_OUTPUT_DIR = "./02_shimano_product/shimano_reel_json"
ROD_OUTPUT_DIR  = "./02_shimano_product/shimano_rod_json"

os.makedirs(REEL_OUTPUT_DIR, exist_ok=True)
os.makedirs(ROD_OUTPUT_DIR, exist_ok=True)


# -----------------------------
# 製品名（日本語 + 英語）
# -----------------------------
def extract_product_name(soup):
    title = soup.select_one("title")
    if not title:
        return None

    text = title.get_text(strip=True)

    # 「 | 」で区切って最初の部分だけ取得
    main = text.split("|")[0].strip()

    return main


# -----------------------------
# SPECIFICATION テーブル解析
# -----------------------------
def parse_shimano_spec_table(soup, url, product_name):
    h2_list = soup.find_all("h2")
    target_h2 = None
    for h2 in h2_list:
        if "SPECIFICATION" in h2.get_text() or "スペック表" in h2.get_text():
            target_h2 = h2
            break

    if not target_h2:
        return []

    table = target_h2.find_next("table")
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
        code = raw.get("商品コード")
        price = raw.get("本体価格(円)")

        if price:
            price = to_number(price.replace("円", "").replace("（税別）", ""))

        exclude = ["品番", "JANコード", "商品コード", "本体価格(円)"]
        specs = {
            k: to_number(v)
            for k, v in raw.items()
            if k not in exclude and not is_junk_spec_key(k)
        }

        products.append({
            "item_name": item_name,
            "jan": jan,
            "product_code": code,
            "price": price,
            "url": url,  # ← canonical URL を入れる
            "product_name": product_name,
            "specs": specs,
        })

    return products


# -----------------------------
# HTML フォルダを処理する共通関数
# -----------------------------
def process_html_dir(html_dir, output_dir):
    files = [f for f in os.listdir(html_dir) if f.endswith(".html")]

    for filename in files:
        html_path = os.path.join(html_dir, filename)

        print("解析中:", html_path)

        soup = load_soup(html_path)

        # canonical URL を取得
        url = extract_canonical_url(soup)
        if not url:
            print("  → canonical URL が見つかりません")
            continue

        # 製品名
        product_name = extract_product_name(soup)
        if not product_name:
            print("  → 製品名なし（スキップ）")
            continue

        safe_name = sanitize_filename(product_name)

        # SPEC TABLE
        table_data = parse_shimano_spec_table(soup, url, product_name)
        if not table_data:
            print("  → スペック表なし")
            continue

        filepath = os.path.join(output_dir, safe_name + ".json")
        save_json(filepath, table_data)

        print("  → 保存:", filepath)


# -----------------------------
# メイン処理
# -----------------------------
def main():
    print("=== REEL ===")
    process_html_dir(REEL_HTML_DIR, REEL_OUTPUT_DIR)

    print("=== ROD ===")
    process_html_dir(ROD_HTML_DIR, ROD_OUTPUT_DIR)


if __name__ == "__main__":
    main()
