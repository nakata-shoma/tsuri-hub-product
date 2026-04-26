import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv

# 対象URL
url = "https://fish.shimano.com/ja-JP/product/list.html"

# Cloudflare対策版 requests
# ブラウザ情報を詳細に設定することで 403 エラーを回避します
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# ページ取得
res = scraper.get(url, headers={
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://fish.shimano.com/ja-JP"
})
res.raise_for_status()

# HTML解析
soup = BeautifulSoup(res.text, "html.parser")

products = []

# 各製品アイテムから情報を抽出
for item in soup.select(".thumbnail__item"):
    a_tag = item.select_one("a")
    if not a_tag:
        continue

    href = a_tag.get("href")
    product_url = urljoin(url, href) if href else ""

    # 製品名の取得（.thumbnail__item__name クラス内、またはaタグ内のテキスト）
    name_tag = item.select_one(".thumbnail__item__name")
    name = name_tag.get_text(strip=True) if name_tag else a_tag.get_text(strip=True)

    # 画像URLの取得
    img_tag = item.select_one("img")
    image_url = urljoin(url, img_tag.get("src")) if img_tag and img_tag.get("src") else ""

    products.append([name, product_url, image_url])

# CSV保存
csv_filename = "shimano_products.csv"

with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "url", "image_url"])  # ヘッダー
    writer.writerows(products)

print(f"抽出完了: {len(products)} 件の製品情報を {csv_filename} に保存しました。")
