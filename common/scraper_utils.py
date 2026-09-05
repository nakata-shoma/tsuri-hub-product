"""
各メーカーの商品データ収集スクリプト（0N_xxx_product/00_get_product.py, 01_get_item_spec.py）
で共通して使うユーティリティ。出力JSONの形式・制約は CONTRACT.md を参照。
"""
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

# Windowsのコンソール既定コードページ（cp932）ではエンコードできない文字
# （合成用結合文字等）を含む商品名をprintした際にUnicodeEncodeErrorで
# 処理全体が落ちるのを防ぐため、標準出力をUTF-8・置換モードに固定する。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

JST = timezone(timedelta(hours=9))

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}


def now_jst_iso():
    return datetime.now(JST).isoformat()


def get_soup(url, headers=None):
    """指定URLをrequestsで取得しBeautifulSoupにする（直接スクレイピング可能なサイト用）

    res.text（requestsのHTTPヘッダーベースのエンコーディング推測）は使わない。
    charsetをHTTPヘッダーで宣言していないサイト（例: スミス）ではISO-8859-1に
    誤フォールバックし、chardetのapparent_encodingも和文サイトでGB18030等に
    誤判定することがあるため、生バイトのままBeautifulSoupに渡し、HTML内の
    <meta charset>宣言に基づくBeautifulSoup自身のエンコーディング検出に委ねる。
    """
    res = requests.get(url, headers=headers or DEFAULT_HEADERS)
    res.raise_for_status()
    return BeautifulSoup(res.content, "html.parser")


def load_soup(html_path):
    """手動保存済みのHTMLファイルを読み込みBeautifulSoupにする（シマノのようにrequestsで直接取得できないサイト用）"""
    with open(html_path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def extract_canonical_url(soup):
    tag = soup.select_one('link[rel="canonical"]')
    if tag and tag.get("href"):
        return tag["href"]
    return None


def to_number(value):
    """"1,234"のようなカンマ区切り数値文字列をint/floatに変換する。変換できない場合は元の値を返す"""
    if value is None:
        return None
    v = value.replace(",", "")
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return value


def is_junk_spec_key(key):
    """スペック表の脚注マーカー列（ヘッダーが空欄や"*"のみ）かどうか。
    実データを持たない列で、specs辞書に含めると無意味なキーになるため除外用。"""
    return not key or key.strip() in ("", "*")


def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.replace(" ", "_").replace("　", "_")
    return name


def read_urls_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return [row[0] for row in reader if row]


def save_urls_csv(path, urls):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for url in urls:
            writer.writerow([url])


def save_json(filepath, data):
    """
    item_name（品番）をキーに既存JSONと突き合わせ、created_at は初回のみ保持し
    updated_at は毎回更新する。スペック表の行順や件数が変わってもcreated_atの
    対応がずれないよう、配列のインデックスではなくitem_nameで照合する。
    """
    now = now_jst_iso()

    old_by_item_name = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            old = json.load(f)
        for item in old:
            item_name = item.get("item_name")
            if item_name:
                old_by_item_name[item_name] = item

    for item in data:
        old_item = old_by_item_name.get(item.get("item_name"))
        if old_item and "created_at" in old_item:
            item["created_at"] = old_item["created_at"]
        else:
            item["created_at"] = now
        item["updated_at"] = now

    with open(filepath, "w", encoding="utf-8") as jf:
        json.dump(data, jf, ensure_ascii=False, indent=2)
