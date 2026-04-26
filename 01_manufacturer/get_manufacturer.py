import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from charset_normalizer import from_bytes

BASE_URL = "https://www.fishing.or.jp/index.jsp?pub.pram=exhibitors/contents/{}"


# -----------------------------
# 文字化け完全対策：charset-normalizer
# -----------------------------
def decode_html(response):
    """meta charset ではなく、実際のバイト列から文字コードを推測してデコード"""
    raw = response.content
    detected = from_bytes(raw).best()

    if detected:
        try:
            return raw.decode(detected.encoding, errors="replace")
        except:
            pass

    return raw.decode("utf-8", errors="replace")


# -----------------------------
# 展示会ページ取得
# -----------------------------
def fetch_page(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        html = decode_html(r)
        return BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


# -----------------------------
# HP内から会社名（株式会社）抽出
# -----------------------------
def extract_company_name_from_hp(soup):
    text = soup.get_text(separator="\n", strip=True)
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if "株式会社" in line and len(line) <= 80:
            return line

    return ""


# -----------------------------
# ロゴURL抽出
# -----------------------------
def extract_logo_url(soup, base_url):
    # 1. header 内の img
    header = soup.find("header")
    if header:
        img = header.find("img")
        if img and img.get("src"):
            return urljoin(base_url, img["src"])

    # 2. nav 内の img
    nav = soup.find("nav")
    if nav:
        img = nav.find("img")
        if img and img.get("src"):
            return urljoin(base_url, img["src"])

    # 3. class/id に logo を含む img
    img = soup.find("img", class_=lambda x: x and "logo" in x.lower())
    if img and img.get("src"):
        return urljoin(base_url, img["src"])

    img = soup.find("img", id=lambda x: x and "logo" in x.lower())
    if img and img.get("src"):
        return urljoin(base_url, img["src"])

    # 4. src に logo を含む img
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "logo" in src.lower():
            return urljoin(base_url, src)

    return ""


# -----------------------------
# ドメイン抽出（TLD削除）
# -----------------------------
def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    parts = domain.split(".")
    if len(parts) >= 2:
        return parts[0]

    return domain


# -----------------------------
# HPへアクセスして情報取得
# -----------------------------
def fetch_hp_info(hp_url):
    try:
        r = requests.get(hp_url, timeout=10)
        r.raise_for_status()
        html = decode_html(r)
        soup = BeautifulSoup(html, "html.parser")

        hp_title = soup.title.string.strip() if soup.title and soup.title.string else ""
        company = extract_company_name_from_hp(soup)
        logo = extract_logo_url(soup, hp_url)

        return hp_title, company, logo

    except Exception as e:
        print(f"HP fetch error for {hp_url}: {e}")
        return "", "", ""


# -----------------------------
# メイン処理
# -----------------------------
def main():
    with open("fishing_exhibitors.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["出展メーカー", "タイトル", "HP", "HPの要約", "会社名", "ドメイン", "ロゴURL"])

        for i in range(1, 171):
            url = BASE_URL.format(i)
            print(f"Fetching {url}")
            soup = fetch_page(url)
            if not soup:
                continue

            h1 = soup.find("h1")
            exhibitor = h1.get_text(strip=True) if h1 else ""

            hp_list = []
            for dd in soup.find_all("dd", class_="hp"):
                a = dd.find("a")
                if a and a.get("href"):
                    hp_list.append(a["href"])

            if not hp_list:
                writer.writerow([exhibitor, "", "", "", "", "", ""])
                continue

            for hp in hp_list:
                hp_title, company, logo = fetch_hp_info(hp)
                domain = extract_domain(hp)
                writer.writerow([exhibitor, hp_title, hp, "", company, domain, logo])

    print("CSV 出力完了: fishing_exhibitors.csv")


if __name__ == "__main__":
    main()
