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

**運用方針**: 新規追加分だけでなく、定期的に全件を再ダウンロードして
シマノ側の価格・スペック変更を検知する（差分は`01_get_item_spec.py`実行後の
JSON側`updated_at`や`git diff`で確認できる）。そのため`todo_list.html`は
保存済み・未保存を問わず**常に全件**を一覧表示する。

```bash
python 02_shimano_product/make_todo_list.py
```

生成された`02_shimano_product/todo_list.html`をブラウザで開き、リンクを
中クリック（またはCtrl+クリック）で数件ずつ新規タブで開き、各タブで
`Ctrl+S`を連打して保存していく運用が効率的。実際にブラウザで人間が閲覧する
だけなので、ダウンロード自体の自動化（＝WAF回避）にはあたらない。
一覧では前回保存済みのURLに`[済]`マークが付く（除外はされない＝再ダウンロード
対象として表示され続ける）。

1. `todo_list.html`のリンク、またはCSV内のURLをブラウザで開く。
2. `Ctrl+S`でページを保存する（「ウェブページ、完全」「ウェブページ、HTMLのみ」
   どちらでも可。スペック表は初回HTMLに含まれており、画像等の付随ファイルは
   スクリプトが参照しないため不要）。
3. カテゴリに応じて以下のフォルダへ保存する。既存ファイルを再保存する場合は
   同名で上書き保存する（ブラウザが自動的に`(1)`等を付けて別名保存した場合、
   重複ファイルが残るだけでJSON生成上は問題ないが、`input/`配下が増え続ける
   ため上書きを推奨）。
   - ロッド: `input/rod/`
   - リール: `input/reel/`
4. 一覧のURLをすべて保存し終える必要はない。保存できた分だけその都度
   `01_get_item_spec.py`を実行すれば、保存済みファイルの分だけJSONが更新される
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
