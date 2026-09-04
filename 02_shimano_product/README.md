# 02_shimano_product 手動保存手順

## なぜ手動保存が必要か

`fish.shimano.com`（および`www.shimano.com`等の関連ドメイン）はAkamai系WAFにより
自動アクセスを一律ブロックしている（`robots.txt`含め全リクエストが403 Access Denied、
一般的なブラウザUser-Agentを付けても同様）。このリポジトリの方針として、
アクセス制御の迂回（プロキシ・ヘッダ偽装・ヘッダレスブラウザでの検知回避等）は行わない。

そのためシマノのみ、`requests`による直接取得（`get_soup`）ではなく、
**人間が普段どおりブラウザで閲覧・保存したHTMLファイルを読み込む**方式
（`load_soup`）を採用している。

## 対象URL一覧

保存が必要なページのURLは以下のCSVに一覧化済み（`00_get_product.py`が
`input/shimano.html`＝製品一覧ページの手動保存HTMLから抽出したもの）。

- ロッド: [shimano_urls/shimano_products_rod.csv](shimano_urls/shimano_products_rod.csv)
- リール: [shimano_urls/shimano_products_reel.csv](shimano_urls/shimano_products_reel.csv)

## 保存手順（タブ一括オープン補助あり）

CSVを手作業で1件ずつコピペする代わりに、以下を実行すると未保存分だけの
リンク一覧ページ（`todo_list.html`）が生成される。

```bash
python 02_shimano_product/make_todo_list.py
```

生成された`02_shimano_product/todo_list.html`をブラウザで開き、リンクを
中クリック（またはCtrl+クリック）で数件ずつ新規タブで開き、各タブで
`Ctrl+S`を連打して保存していく運用が効率的。実際にブラウザで人間が閲覧する
だけなので、ダウンロード自体の自動化（＝WAF回避）にはあたらない。

保存が進んだら`make_todo_list.py`を再実行すると、保存済みURL（canonical URLで
既存の`input/rod`・`input/reel`内HTMLと突き合わせ判定）がリストから除外される。

1. CSV内のURL、または`todo_list.html`のリンクをブラウザで開く。
2. `Ctrl+S`でページを保存する（「ウェブページ、完全」「ウェブページ、HTMLのみ」
   どちらでも可。スペック表は初回HTMLに含まれており、画像等の付随ファイルは
   スクリプトが参照しないため不要）。
3. カテゴリに応じて以下のフォルダへ保存する。ファイル名は任意（フォルダ内の
   `.html`ファイルを全件処理するため、ブラウザの自動命名のままでよい）。
   - ロッド: `input/rod/`
   - リール: `input/reel/`
4. 一覧のURLをすべて保存し終える必要はない。保存できた分だけその都度
   `01_get_item_spec.py`を実行すれば、保存済みファイルの分だけJSONが生成される
   （未保存分はスキップされるだけで、エラーにはならない）。

## 進捗確認

保存済み件数は以下で確認できる。

```bash
ls 02_shimano_product/input/rod  | wc -l   # ロッド保存済み件数
ls 02_shimano_product/input/reel | wc -l   # リール保存済み件数
```

CSVの行数（対象件数）と比較することで残り件数が分かる。

## JSON生成

保存後は通常どおり実行する。

```bash
python 02_shimano_product/01_get_item_spec.py
```

`save_json`は`item_name`（品番）キーで既存JSONとの`created_at`を突き合わせるため、
同じページを再保存して再実行しても`created_at`は初回のまま保持される。
