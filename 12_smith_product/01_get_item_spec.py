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

SuperStrikeの一部ページ（例: go-102.html）は1機種のスペックが1つの<table>内で
「ROD No.を含むヘッダー行+データ行」→「lure/line等の別ヘッダー行+データ行」の
ように2段（ヘッダー行が2回出現）に分かれている。単純に先頭行だけをヘッダーとして
以降を全部データ行扱いすると、2段目のヘッダー行自体がデータ行として誤認識され
（例: item_nameが"lure"になる）ゴミデータが混入するため、各行がヘッダー行か
データ行かをセルのタグ/クラスで判定し、「ROD No.」を含まない後続ヘッダー行は
新規モデルではなく直前モデルの続き（列の追加）として同じアイテムにマージする。
ヘッダー行の判定は、セルが全て<th>であるか、全て`rodt`で始まるclassを持つか
（本体サイトのtd見出し行はclass="rodt1"、データ行はclass="rodb1"）で行う。
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


def extract_price(value):
    if not value:
        return None
    match = PRICE_NUMBER_RE.search(value)
    return to_number(match.group()) if match else None


def _has_class_prefix(cell, prefix):
    classes = cell.get("class") or []
    return any(cls.startswith(prefix) for cls in classes)


def is_header_row(cells):
    if not cells:
        return False
    if all(c.name == "th" for c in cells):
        return True
    return all(_has_class_prefix(c, "rodt") for c in cells)


def split_into_blocks(rows):
    """表の行を (ヘッダーセル文字列リスト, [データ行の文字列リスト, ...]) のブロック列に分割する。
    1つの<table>内にヘッダー行が複数回（=2段構成）出現する場合、それぞれ別ブロックになる。"""
    blocks = []
    current_header = None
    current_data = []

    for row in rows:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        if is_header_row(cells):
            if current_header is not None:
                blocks.append((current_header, current_data))
            current_header = [c.get_text(strip=True) for c in cells]
            current_data = []
        else:
            current_data.append([c.get_text(strip=True) for c in cells])

    if current_header is not None:
        blocks.append((current_header, current_data))

    return blocks


def build_item(raw, url, product_name):
    item_name = raw.get("ROD No.")
    if not item_name:
        return None

    price_keys = [k for k in raw if "price" in k]
    price_key = price_keys[0] if price_keys else None

    exclude = ["ROD No."] + price_keys
    specs = {k: to_number(v) for k, v in raw.items() if k not in exclude and v}

    return {
        "item_name": item_name,
        "jan": None,
        "price": extract_price(raw.get(price_key)) if price_key else None,
        "url": url,
        "product_name": product_name,
        "specs": specs,
    }


def parse_rod_tables(soup, url, product_name):
    products = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        blocks = split_into_blocks(rows)
        pending_raw = None

        for header, data_rows in blocks:
            if "ROD No." in header:
                if pending_raw is not None:
                    item = build_item(pending_raw, url, product_name)
                    if item:
                        products.append(item)
                    pending_raw = None

                if len(data_rows) == 1 and len(data_rows[0]) == len(header):
                    # 続きの（ROD No.を持たない）ヘッダー行が後続する可能性があるため
                    # 即座に確定せず一旦保留する。
                    pending_raw = dict(zip(header, data_rows[0]))
                else:
                    # 1ヘッダー+複数データ行 = 複数モデルの一覧（各行が独立した完成品）
                    for cols in data_rows:
                        if len(cols) != len(header):
                            continue
                        item = build_item(dict(zip(header, cols)), url, product_name)
                        if item:
                            products.append(item)
            else:
                # ROD No.を含まない後続ヘッダー行 = 直前モデルの続きの列
                if (
                    pending_raw is not None
                    and len(data_rows) == 1
                    and len(data_rows[0]) == len(header)
                ):
                    pending_raw.update(dict(zip(header, data_rows[0])))
                # 想定外の形（保留中アイテムが無い等）は安全側に倒して無視する

        if pending_raw is not None:
            item = build_item(pending_raw, url, product_name)
            if item:
                products.append(item)

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
