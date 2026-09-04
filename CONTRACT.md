# turi連携データ仕様（制約事項）

このリポジトリで生成するJSONは、turi側の `import_products_from_repo` management command が読み込む。
スクリプトを変更する際は、以下の制約を壊さないこと。

## 対象ディレクトリとturi側の対応表

`import_products_from_repo.py` の `SOURCE_DIRS` に、ディレクトリと `manufacturer_slug` / `category` の対応が固定で登録されている。

| ディレクトリ | manufacturer_slug | category |
|---|---|---|
| `03_daiwa_product/daiwa_reel_json` | daiwa | reel |
| `03_daiwa_product/daiwa_rod_json` | daiwa | rod |
| `02_shimano_product/shimano_reel_json` | shimano | reel |
| `02_shimano_product/shimano_rod_json` | shimano | rod |
| `04_majorcraft_product/majorcraft_rod_json` | majorcraft | rod |
| `05_gamakatsu_product/gamakatsu_rod_json` | gamakatsu | rod |
| `06_evergreen_product/evergreen_rod_json` | evergreen | rod |
| `07_goldenmean_product/goldenmean_rod_json` | goldenmean | rod |
| `08_abugarcia_product/abugarcia_reel_json` | abugarcia | reel |
| `08_abugarcia_product/abugarcia_rod_json` | abugarcia | rod |
| `09_jackall_product/jackall_rod_json` | jackall | rod |
| `10_tenryu_product/tenryu_rod_json` | tenryu | rod |
| `11_prox_product/prox_reel_json` | prox | reel |
| `11_prox_product/prox_rod_json` | prox | rod |
| `12_smith_product/smith_rod_json` | smith | rod |
| `13_beet_product/beet_rod_json` | beet | rod |

**ディレクトリ名を変更・追加する場合、tsuri_tools側の変更だけでは連携されない。** turi側の `SOURCE_DIRS` にも同時に追記してもらう必要がある。新しいメーカー・カテゴリ（例: gamakatsu）を追加する場合も同様。

## manufacturer_slug / category の値

- `manufacturer_slug`（上表の値）は、turi側の `ManufacturerModel.slug` と完全一致していること（全角/半角・大文字小文字の違いも不可）。
- turi側で対象メーカーが未登録の場合、そのメーカーのJSONは**エラーにならず全件スキップされる**。取り込んだのに反映されない場合はまずここを疑う。
- `category` は turi側の `ManufacturerConst.ITEM` に定義された値（`rod` / `reel` など）と完全一致させること。

## JSONファイルの形式

1ファイル = 1製品（シリーズ）。トップレベルはJSON配列で、各要素が品番（`ProductModel`）1件に対応する。

```json
[
  {
    "item_name": "２５ＳＡＬＴＩＧＡ　８０００－Ｐ",
    "product_name": "ソルティガ (SALTIGA)",
    "jan": "4550133351419",
    "price": 155000,
    "url": "https://www.daiwa.com/jp/product/i25pggl",
    "specs": { "標準自重（ｇ）": 670, "ギア比": 4.8 },
    "created_at": "...",
    "updated_at": "..."
  }
]
```

| キー | 必須 | 型 | 備考 |
|---|---|---|---|
| `item_name` | ほぼ必須 | 文字列 | 品番。無いレコードは取り込み時にスキップされる |
| `product_name` | 必須 | 文字列 | シリーズ名。無い場合はファイル名で代用されるが、ファイル名はサニタイズ済みで元の製品名と完全一致しないため、必ず入れること |
| `jan` | 任意 | 文字列 |  |
| `price` | 任意 | 数値 or 数値文字列 | turi側で`int`変換される。カンマ区切りは自動除去される |
| `url` | 任意 | 文字列 | 配列内の**先頭要素**の値のみが `Product.url` として採用される。2件目以降の値は無視される |
| `specs` | 必須 | object | 「ラベル文字列: 値」のdict。値の型は自由。turi側importerの`mapping`辞書に無いラベルはそのままの文字列・値で保存される（変換されない） |

- 文字エンコーディングはUTF-8。
- ファイル名（拡張子除く）は `product_name` のフォールバック用途のみで、turiの`Product`は`manufacturer + category + product_name`の組で識別する。ファイル名自体に一意性の制約はない。

## 冪等性・更新時の挙動

turi側は `manufacturer + category + product_name` と `item_name` の組でupsertする。

- 同じ`item_name`のJSONを再度流すと**上書き更新**される。
- **`product_name`や`item_name`を後から変更すると、turi側では別レコード扱いになり、旧レコードは自動削除されずに残る。** 改名した場合はturi側の管理画面で手動整理が必要（事前に連絡すること）。

## 既知の注意点（現状のスクリプトのクセ）

- Daiwaの`specs`には`"*"`のようなゴミキーが混入することがある（テーブルの脚注セルの誤読）。実害はないが管理画面のspecs表示にノイズとして出る。
- MajorCraftの `ライン` / `ルアー` はレンジ表記（例: `"0.2 - 3g"`）をturi側で正規表現パースしている。区切りが半角スペース-ハイフン-半角スペース（` - `）以外（全角ダッシュ等）に変わると解析できず、値がそのまま保存される。
- MajorCraftの`PRICE`が「税込」「税別」など複数の数値を含む文字列の場合、turi側は文字列中で最初に出てくる数値のみを採用する（通常は税別価格）。

## 変更時の連絡フロー

以下に該当する変更を行う場合は、事前にturi側（`apps/manufacturer/importers/`）と連携すること。turi側のimporterまたは`import_products_from_repo.py`の追従が必要になる。

- 出力ディレクトリのパス変更・新規追加
- `item_name` / `product_name` / `specs` のキー構造の変更
- `category` / `manufacturer_slug` に使う値の変更
- specsの値のフォーマット変更（区切り文字、単位の位置など）
