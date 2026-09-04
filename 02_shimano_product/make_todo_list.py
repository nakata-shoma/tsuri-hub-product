"""
rod/reelの全URLを一覧化し、タブ一括オープン用のローカルHTML
（todo_list.html）を生成する。

fish.shimano.comはWAFで自動アクセスをブロックしているため、各商品ページは
人間が実際にブラウザで開いてCtrl+Sで保存する必要がある（詳細はREADME.md参照）。
このスクリプトは取得の自動化ではなく、ブラウザでの一括タブオープンを補助する
だけのもの。

定期的に全件を再ダウンロードして差分を確認する運用のため、既に保存済みの
URLも含めて全件を出力する（保存済みかどうかは目印として表示するのみで、
一覧からは除外しない）。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import extract_canonical_url, load_soup, read_urls_csv  # noqa: E402

ROD_CSV = "./02_shimano_product/shimano_urls/shimano_products_rod.csv"
REEL_CSV = "./02_shimano_product/shimano_urls/shimano_products_reel.csv"
ROD_HTML_DIR = "./02_shimano_product/input/rod"
REEL_HTML_DIR = "./02_shimano_product/input/reel"
OUTPUT_HTML = "./02_shimano_product/todo_list.html"


def saved_urls(html_dir):
    urls = set()
    if not os.path.isdir(html_dir):
        return urls
    for filename in os.listdir(html_dir):
        if not filename.endswith(".html"):
            continue
        soup = load_soup(os.path.join(html_dir, filename))
        url = extract_canonical_url(soup)
        if url:
            urls.add(url)
    return urls


def build_section(title, all_urls, done_urls):
    done_count = sum(1 for u in all_urls if u in done_urls)
    items = "\n".join(
        '<li class="done"><span class="mark">[済]</span> '
        f'<a href="{u}" target="_blank" rel="noopener">{u}</a></li>'
        if u in done_urls else
        f'<li><a href="{u}" target="_blank" rel="noopener">{u}</a></li>'
        for u in all_urls
    )
    return f"""
<h2>{title}（全{len(all_urls)}件・保存済み{done_count}件）</h2>
<ol>
{items}
</ol>
"""


def main():
    rod_all = read_urls_csv(ROD_CSV)
    reel_all = read_urls_csv(REEL_CSV)

    rod_done = saved_urls(ROD_HTML_DIR)
    reel_done = saved_urls(REEL_HTML_DIR)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>shimano 未保存URL一覧</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 20px auto; padding: 0 20px; }}
li {{ margin-bottom: 4px; }}
li.done {{ color: #888; }}
li.done .mark {{ color: #2a7a2a; font-weight: bold; }}
p.note {{ background: #fff3cd; padding: 10px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>shimano 全URL一覧（定期再ダウンロード用）</h1>
<p class="note">
各リンクをクリックしてページを開き、Ctrl+Sで保存してください（既存ファイルは
上書きでよい）。保存先はロッドなら input/rod/、リールなら input/reel/。
ファイル名は任意です。<br>
[済]は前回時点で保存済みだったURL（再ダウンロードして更新確認する対象）。
定期的に全件をこのページから開き直し、保存後に
<code>python 02_shimano_product/01_get_item_spec.py</code> を実行すると、
価格・スペックの変更やJSONの差分（`updated_at`）で更新を検知できる。<br>
このページ自体は<code>python 02_shimano_product/make_todo_list.py</code>を
再実行すれば最新の保存状況で再生成される。
</p>
{build_section("ロッド", rod_all, rod_done)}
{build_section("リール", reel_all, reel_done)}
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"ロッド 全{len(rod_all)}件（保存済み{len(rod_done)}件）")
    print(f"リール 全{len(reel_all)}件（保存済み{len(reel_done)}件）")
    print(f"生成: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
