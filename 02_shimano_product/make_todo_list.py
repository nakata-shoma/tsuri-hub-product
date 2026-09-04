"""
input/rod, input/reel に未保存のURLだけを抽出し、タブ一括オープン用の
ローカルHTML（todo_list.html）を生成する。

fish.shimano.comはWAFで自動アクセスをブロックしているため、各商品ページは
人間が実際にブラウザで開いてCtrl+Sで保存する必要がある（詳細はREADME.md参照）。
このスクリプトは取得の自動化ではなく、「どのURLがまだ未保存か」の把握と、
ブラウザでの一括タブオープンを補助するだけのもの。
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
    remaining = [u for u in all_urls if u not in done_urls]
    items = "\n".join(
        f'<li><a href="{u}" target="_blank" rel="noopener">{u}</a></li>' for u in remaining
    )
    return f"""
<h2>{title}（残り {len(remaining)} / {len(all_urls)} 件）</h2>
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
p.note {{ background: #fff3cd; padding: 10px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>shimano 未保存URL一覧</h1>
<p class="note">
各リンクをクリックしてページを開き、Ctrl+Sで保存してください。
保存先はロッドなら input/rod/、リールなら input/reel/。ファイル名は任意です。<br>
このページは自動生成物です。保存が進んだら
<code>python 02_shimano_product/make_todo_list.py</code> を再実行すると
保存済み分がリストから消えます。
</p>
{build_section("ロッド", rod_all, rod_done)}
{build_section("リール", reel_all, reel_done)}
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"ロッド 残り{len(rod_all) - len(rod_done)}/{len(rod_all)}件")
    print(f"リール 残り{len(reel_all) - len(reel_done)}/{len(reel_all)}件")
    print(f"生成: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
