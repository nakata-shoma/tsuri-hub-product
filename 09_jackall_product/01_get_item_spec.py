"""
ジャッカルの個別商品ページ（ロッド）から品番・価格・スペック等を取得しJSONに出力する。
バス/トラウト(timon)/ソルトショア/ソルトオフショアの4サブサイトに対応。

スペック表は #spec-pc 配下の table にある（#spec-sp はスマホ表示用の同一内容のため無視）。
このテンプレートはウェア・小物・アクセサリー等ロッド以外の商品ページでも
使い回されているため、ロッド固有の"Length"列を持つ表だけをロッドとして扱う。
先頭行は各行へのアンカーリンク一覧の凡例行（"適合表"、全列"ー"）でデータではないためスキップする。
品番セルには "【2026 NEW】" のような角括弧の注記が前置されることがあるため取り除く。
出力形式はCONTRACT.mdに従う（1ファイル=1シリーズ、product_name必須、
urlは配列内の先頭要素のみ採用、specsはラベル文字列:値のdict）。

実装が完了したら、出力先ディレクトリと manufacturer_slug / category を
CONTRACT.md の対応表と turi 側 import_products_from_repo.py の SOURCE_DIRS に追記すること
（manufacturer_slug="jackall", category="rod"）。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402

INPUT_CSV = "./09_jackall_product/jackall_urls/jackall_products_rod.csv"
OUTPUT_DIR = "./09_jackall_product/jackall_rod_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

PRICE_NUMBER_RE = re.compile(r"[\d,]+")
BRACKET_PREFIX_RE = re.compile(r"^【[^】]*】")
LEGEND_ROW_ITEM_NAME = "適合表"


def extract_product_name(soup):
    title = soup.select_one("title")
    if not title:
        return None
    text = title.get_text(strip=True)
    text = text.split("｜")[0]
    text = text.split(" - ")[0]
    return text.strip() or None


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def clean_item_name(value):
    if not value:
        return None
    return BRACKET_PREFIX_RE.sub("", value).strip()


def parse_spec_table(soup, url, product_name):
    table = soup.select_one("#spec-pc table")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    if "Name" not in header:
        return []
    # #spec-pc の比較表テンプレートはロッド以外（ウェア・小物・アクセサリー等）の
    # 商品ページでも使い回されており、Name/Price列だけでは区別できない。
    # Length列だけではPEライン等（長さの概念を持つ）も誤って含まれてしまうため、
    # ロッド特有の列（継数 または Power）のいずれかも併せて必須とする。
    # （PRIZA FUGUのようにPowerを持たないがLength+継数を持つロッドや、
    # Nazzy Choiceのように継数を持たないがPowerを持つロッドの両方があるため、
    # AND条件ではなくOR条件にする。カスタムハンドル等のロッド部品は
    # 継数もPowerも持たないため、これにより完成品のロッドと区別できる。）
    if not any("Length" in h for h in header):
        return []
    if not any("継数" in h for h in header) and not any("Power" in h for h in header):
        return []

    price_key = "Price" if "Price" in header else None

    products = []

    for row in rows[1:]:
        cols = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cols) != len(header):
            continue

        raw = dict(zip(header, cols))
        item_name = clean_item_name(raw.get("Name"))
        if not item_name or item_name == LEGEND_ROW_ITEM_NAME:
            continue

        exclude = ["Name"]
        if price_key:
            exclude.append(price_key)
        specs = {k: to_number(v) for k, v in raw.items() if k not in exclude}

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
