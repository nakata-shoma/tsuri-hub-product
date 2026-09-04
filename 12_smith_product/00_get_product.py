"""
スミス公式サイトのロッド商品一覧から個別商品ページのURLを収集する。

サイトはカテゴリページ（例: html/03-basstacle.html）内の <div id="rod_waku">
セクションに製品リンクが並ぶが、このdiv/クラスはロッド専用ではなく、
一部のワーム等ルアー製品（イチワーム等）にも使い回されているため、
リンク先ページの内容（スペック表の有無）で最終判定する。

さらにリンク先は2パターンある。
- シリーズ紹介ページ（例: hiroism.html）が各モデルの個別ページ
  （例: hiroism/calypso/calypso.html）にリンクしているだけで、
  スペック表自体はモデル別ページ側にしかない場合。
- シリーズページ自体に直接スペック表がある場合（例: bareafun.html）。

そのため rod_waku 内のリンク（レベル0）を取得したら、各ページを実際に開いて
スペック表（ヘッダーに「ROD No.」を含むtable）があるか確認し、無ければ同一
ディレクトリ配下（レベル0ページより深い階層）のリンクを辿って（レベル1）
再度確認する。SuperStrike（superstrike/top.html）は別ドメイン構成のサブ
ブランドサイトで、このレベル1探索の対象外（別途調査が必要なため今回は
スコープ外）。
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://www.smith.jp"
CATEGORY_PAGES = [
    "https://www.smith.jp/html/03-basstacle.html",
    "https://www.smith.jp/html/03-cattacle.html",
    "https://www.smith.jp/html/03-snaketacle.html",
    "https://www.smith.jp/html/03-trouttacle.html",
    "https://www.smith.jp/html/03-microtackle.html",
    "https://www.smith.jp/html/03-saltwater.html",
    "https://www.smith.jp/html/03-expedition.html",
]
OUTPUT_CSV = "./12_smith_product/smith_urls/smith_products_rod.csv"


def find_rod_waku_links(soup, page_url):
    links = set()
    for waku in soup.find_all("div", id="rod_waku"):
        for a in waku.select("a"):
            href = a.get("href")
            if href:
                links.add(urljoin(page_url, href))
    return links


def has_rod_spec_table(soup):
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        if "ROD No." in header:
            return True
    return False


def find_deeper_links(soup, page_url):
    """page_urlのディレクトリ配下（より深い階層）を指す.htmlリンクのみ拾う。"""
    page_dir = page_url.rsplit("/", 1)[0] + "/"
    links = set()
    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(page_url, href)
        if full == page_url:
            continue
        if not full.startswith(page_dir):
            continue
        if not full.endswith(".html"):
            continue
        links.add(full)
    return links


def resolve_spec_page_urls(entry_url, visited):
    if entry_url in visited:
        return set()
    visited.add(entry_url)

    print(f"確認中: {entry_url}")
    soup = get_soup(entry_url)

    if has_rod_spec_table(soup):
        return {entry_url}

    found = set()
    for deeper_url in sorted(find_deeper_links(soup, entry_url)):
        if deeper_url in visited:
            continue
        visited.add(deeper_url)
        print(f"  → 深堀り: {deeper_url}")
        try:
            deeper_soup = get_soup(deeper_url)
        except Exception as e:  # noqa: BLE001
            print(f"    取得失敗: {e}")
            continue
        if has_rod_spec_table(deeper_soup):
            found.add(deeper_url)
    return found


if __name__ == "__main__":
    entry_links = set()
    for category_url in CATEGORY_PAGES:
        print(f"=== {category_url} ===")
        category_soup = get_soup(category_url)
        links = find_rod_waku_links(category_soup, category_url)
        print(f"  rod_waku候補リンク数: {len(links)}")
        entry_links.update(links)

    visited = set()
    spec_urls = set()
    for entry_url in sorted(entry_links):
        spec_urls.update(resolve_spec_page_urls(entry_url, visited))

    urls = sorted(spec_urls)
    save_urls_csv(OUTPUT_CSV, urls)
    print(f"完了: {len(urls)} 件（候補{len(entry_links)}件中）")
