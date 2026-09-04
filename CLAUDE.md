# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code に向けたガイドです。

## リポジトリの目的

このリポジトリでは、Webアプリ「TSURI HUB」の商品データベースに登録するための商品データ（メーカー、カテゴリ、製品名、品番、価格、スペック等）を、各釣具メーカーの公式サイトから収集・整形して JSON として出力するスクリプト群を管理する。

- TSURI HUB 本体（Django アプリ）のソースコードは別リポジトリ: `C:\Users\nakat\Desktop\main\100_WebApp\turi`
- このリポジトリで生成した JSON は、turi 側の `import_products_from_repo` management command が読み込む。turi 側との連携仕様・制約は [CONTRACT.md](CONTRACT.md) に記載されており、**このリポジトリの出力形式やディレクトリ構成を変更する際は必ず遵守すること**（違反すると turi 側でエラーにならず静かにデータが取り込まれない、または誤ったデータで上書きされる）。
  - 特に、出力先ディレクトリ名の変更・追加、`item_name` / `product_name` / `specs` のキー構造変更、`manufacturer_slug` / `category` の値変更、specs値のフォーマット変更を行う場合は、事前に turi 側（`apps/manufacturer/importers/`）との連携が必要（CONTRACT.md「変更時の連絡フロー」参照）。

## データ取得パイプラインの構成

メーカーごとにディレクトリを分け、番号順に実行する2段階パイプラインが基本パターン。

```
01_manufacturer/          … 展示会サイトからメーカー一覧を取得（fishing.or.jp）
02_shimano_product/       … シマノ
03_daiwa_product/         … ダイワ
04_majorcraft_product/    … メジャークラフト
05_gamakatsu_product/     … がまかつ（未着手・ディレクトリのみ存在）
```

各メーカーディレクトリの基本パターン:

- `00_get_product.py` … 商品一覧ページから個別商品ページのURLを収集し、`<maker>_urls/*.csv` に保存
- `01_get_item_spec.py` … 個別商品ページから品番・価格・スペック等を取得し、`<maker>_<category>_json/*.json` に1シリーズ1ファイルで出力

**メーカーごとに実装方式が異なる点に注意**:
- ダイワ・メジャークラフトは `00`/`01` とも `requests` で対象サイトへ直接アクセスする。
- シマノは `fish.shimano.com` 側の事情により、一覧ページのHTMLを手動保存したもの（`02_shimano_product/input/shimano.html`）から `00_get_product.py` がURLを抽出し、`01_get_item_spec.py` も個別商品ページのHTMLを事前に `input/reel/` `input/rod/` に保存したものを読み込む方式になっている。新規メーカー追加時は、対象サイトが直接スクレイピング可能かをまず確認すること。

新しいメーカーを追加する場合は、既存ディレクトリ（`02_shimano_product` 等）の構成をテンプレートとして流用しつつ、出力先ディレクトリ名と `manufacturer_slug` / `category` を CONTRACT.md の対応表・turi側 `SOURCE_DIRS` に必ず追記してもらうこと。

## 出力JSONの形式

CONTRACT.md に詳細な仕様があるが、要点:

- 1ファイル = 1製品シリーズ、トップレベルはJSON配列、各要素が品番1件
- `product_name`（シリーズ名）は必須。無い場合ファイル名がフォールバックされるが元の製品名と一致しない可能性があるため、スクレイピング側で必ず埋めること
- `url` は配列内の**先頭要素のみ**が採用される
- 文字エンコーディングは UTF-8
- 変更前に必ず CONTRACT.md の該当セクションを確認する

## その他のディレクトリ（商品データ収集とは別用途）

このリポジトリには商品データ収集パイプライン以外のものも同居している。関連性はないため、商品データ収集ロジックとは混同しないこと。

- `10_tsuri_hub_index/` … TSURI HUB のトップページ（index.html / mypage.html とその css/js/img）の静的ファイル一式。
- `100_fit_repair/` … 破損した Garmin 等の `.fit` ファイル（アクティビティログ）を修復するためのスタンドアロンツール（`fitdecode` / `pandas` / `tkinter` を使用）。ルート直下の `broken.fit` / `repaired.fit` はこのツールの動作確認用サンプル。

## 実行環境

- Python 仮想環境は `.toolvenv/`（gitignore対象、リポジトリ直下）。主な依存: `requests`, `beautifulsoup4`, `charset-normalizer`, `pandas`, `fitdecode` 等。
- 各スクリプトはリポジトリルートからの相対パス（例: `./02_shimano_product/...`）を前提にしているため、実行時のカレントディレクトリはリポジトリルートにすること。

## 機密情報・破壊的操作

- グローバルルール（`.env` / 認証情報の扱い、ファイル削除時のUI確認、破壊的操作の事前確認）に従うこと。
