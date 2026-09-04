import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.scraper_utils import get_soup, save_urls_csv  # noqa: E402

BASE_URL = "https://www.majorcraft.co.jp"
START_URL = "https://www.majorcraft.co.jp/rod/"

def extract_rod_links(soup):
    links = []

    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue

        # /rod/ を含むリンクだけ抽出
        if "/rod/" in href:
            full = urljoin(BASE_URL, href)
            links.append(full)

    return links

if __name__ == "__main__":
    print("Scraping MajorCraft rods...")
    soup = get_soup(START_URL)

    rod_urls = extract_rod_links(soup)
    rod_urls = sorted(set(rod_urls))  # 重複除去

    save_urls_csv("./04_majorcraft_product/majorcraft_urls/majorcraft_rod_urls.csv", rod_urls)

    print(f"完了: {len(rod_urls)} 件のURLをCSVに保存しました。")
