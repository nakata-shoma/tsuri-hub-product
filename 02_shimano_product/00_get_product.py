# https://fish.shimano.com/ja-JP/product/list.html
# を保存して input に保存

from bs4 import BeautifulSoup
import csv

HTML_FILE = "./02_shimano_product/input/shimano.html"  # 保存したHTMLファイル名

BASE_URL = "https://fish.shimano.com"

def extract_urls():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    reel_urls = []
    rod_urls = []

    # <div class="thumbnail__item"> の直下の <a> を取得
    items = soup.select("div.thumbnail__item > a")

    for a in items:
        href = a.get("href")
        if not href:
            continue

        # 必要なカテゴリだけ抽出
        if "/product/reel/" in href:
            reel_urls.append(href)
        elif "/product/rod/" in href:
            rod_urls.append(href)
        else:
            # lure, item, parts などは無視
            continue

    return reel_urls, rod_urls


def save_csv_with_base(filename, urls):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for u in urls:
            # すでに絶対URLならそのまま
            if u.startswith("http"):
                full = u
            else:
                full = BASE_URL + u

            writer.writerow([full])  # ヘッダーなし


if __name__ == "__main__":
    reel, rod = extract_urls()

    save_csv_with_base("./02_shimano_product/shimano_urls/shimano_products_reel.csv", reel)
    save_csv_with_base("./02_shimano_product/shimano_urls/shimano_products_rod.csv", rod)

    print("Reel:", len(reel), "件")
    print("Rod:", len(rod), "件")
