---
name: add-manufacturer-scraper
description: Add a new fishing-tackle manufacturer's product-data scraper to the tsuri_tools repo (a `0N_<slug>_product/` folder with `00_get_product.py` + `01_get_item_spec.py` producing CONTRACT.md-compliant JSON for TSURI HUB), or review/refresh an existing one. Use this whenever asked to "add <manufacturer>'s products", "start scraping <maker>", "○○の商品データを取得/追加して", "○○のデータを見直して", to extend an existing manufacturer folder to a new category (reel/rod) or sub-site, or to re-run/verify a manufacturer that was already implemented. Also consult it when a scrape's output file count doesn't match the input URL count, when non-target-category items (accessories, line, apparel) are leaking into a category's JSON output, when saved filenames come out mojibake/garbled, or when a target site returns 403/Access Denied to all automated requests — these are all classic symptoms this skill exists to prevent and fix.
---

# Add a manufacturer scraper to tsuri_tools

This captures the workflow, pitfalls, and fixes discovered while adding scrapers for
gamakatsu, evergreen, goldenmean, abugarcia, jackall, tenryu, prox, smith, and beet,
and while reviewing/refreshing daiwa and shimano (2026-09-03, tsuri_tools repo).
Every one of those sites turned out to violate some assumption that held for the
earlier daiwa/shimano/majorcraft scrapers — treat "the site will probably be
different in some way" as the default expectation, not the exception.

## Before touching any code

Read these three things — skipping this step is the single biggest cause of rework:

1. **`CONTRACT.md`** — the output JSON shape is a contract with the separate `turi`
   Django app, not a style preference. Get it wrong and data silently fails to
   import (wrong `manufacturer_slug`/`category`) or overwrites the wrong records.
2. **`CLAUDE.md`** — repo conventions, and the boundary of this repo's job (produce
   correct JSON; wiring turi's `SOURCE_DIRS` + an importer class is a *separate*,
   later coordination step — don't touch the turi repo as part of this task unless
   explicitly asked).
3. **One existing sibling folder** (e.g. `03_daiwa_product/` or `05_gamakatsu_product/`)
   as a concrete template, plus `common/scraper_utils.py`, which every manufacturer
   script imports for: `get_soup`/`load_soup`, `extract_canonical_url`, `to_number`,
   `sanitize_filename`, `read_urls_csv`/`save_urls_csv`, `save_json`. Extend this
   module (not a manufacturer-local copy) when you find a genuinely reusable helper —
   that's how the item_name-based `created_at` fix, the UTF-8 stdout fix, and the
   raw-bytes encoding fix (see Known pitfalls) reached every manufacturer at once
   instead of living in one file.

Every new manufacturer script starts with this boilerplate to reach the shared module:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.scraper_utils import get_soup, read_urls_csv, sanitize_filename, save_json, to_number  # noqa: E402
```

## Step 1 — Investigate the real site structure with raw `requests`, not summarizers

Don't use WebFetch (or anything that feeds HTML through a small summarizing model) to
find selectors or links — it silently drops hrefs and misreads JS-rendered content,
and every wrong assumption here costs a full round trip later. Instead:

```python
import requests
res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
res.encoding = res.apparent_encoding   # many JP sites mis-declare their charset
```

Save the raw HTML to a scratch file and grep/BeautifulSoup it directly. Figure out,
in order:

1. **Where is the product list?** Top nav → category page. Don't assume the first
   plausible-looking link is the real catalog — evergreen's `/products/*-products/`
   looked like a catalog but was actually a news feed; the real catalog lived under
   `/freshwater/`, `/trout/`, `/saltwater/`.
2. **Does the category page contain product links directly, or just sub-category
   links?** If a category page has zero product-shaped links, it's a nav hub — you
   need to go one level deeper (or several: jackall's per-subsite "ROD" tab only
   revealed its real children inside a specific `<li>`'s nested dropdown, because the
   same "ROD" link text/href appeared 2-3 times on the page for desktop/mobile/other
   nav variants, only one of which had the populated submenu).
3. **Is pagination static HTML, or an AJAX/JSON endpoint?** If a "load more" button
   exists with no corresponding `?page=N` links, search the raw HTML for
   `admin-ajax.php`, `action:`, or similar — gamakatsu's entire catalog was fetched
   by POSTing `{action: "get_products_search", pages: N, s_product: "rod"}` to
   `wp-admin/admin-ajax.php`, which also let a *parent* category value (`"rod"`)
   pull every child subcategory's products in one paginated sweep instead of
   enumerating ~15 child slugs by hand.
4. **Is it a Shopify store?** Check `<domain>/collections/<handle>/products.json` —
   if it 200s, use it for the URL list (reliable, no HTML parsing needed) but still
   check whether the *detailed* spec table you need is actually in that JSON's
   `body_html`, or only rendered into the live page by a separate theme section
   (abugarcia's per-model spec comparison table was **not** in the Shopify product
   JSON at all — only on the rendered HTML page). Check `<domain>/collections.json`
   too — abugarcia had a top-level cross-cutting `reels` collection (spanning both
   spinning and baitcasting sub-collections) that was a much simpler URL source than
   enumerating every sub-collection by hand.
5. **Does every product page use the same template?** Don't assume yes after
   checking one page. goldenmean mixed an old template (`<div class="spec"><table>`,
   no class, English headers) with a new template (`<table class="spec_table2">`,
   Japanese headers, sometimes several tables per page) *and* a third, single-model
   template with no item-code column at all (see Step 3's single-row fallback) —
   the parser had to try several selectors and pick whichever matched.
6. **Is it "1 page = 1 series with N item rows" or "1 page = 1 item"?** Most sites
   match the first pattern (a spec table with one row per item_name). evergreen was
   the second: each URL was a single model, and the series name had to be read back
   off the page itself (`#series-list-anchor strong`) so items could be grouped into
   one file per series *after* fetching, not before.
7. **Is a listing "section"/class reused across multiple, unrelated product
   categories on the same page?** Don't trust a div id/class name as a category
   signal just because it looks purpose-built. smith's `<div id="rod_waku">` sounds
   rod-specific but was also reused verbatim for a pair of soft-plastic worm
   products on the same bass category page — the class name is a *layout* choice
   (large single-column cards) reused for "this needs the big-image treatment," not
   a semantic rod marker. And the true content can be one or two hops deeper than
   the candidate link: some smith `rod_waku` links pointed straight at a page with
   the real spec table, others pointed at a "series" landing page (e.g. HIROism)
   that only *linked to* each model's own page (e.g. Calypso, Capricorn) where the
   actual table lived. The robust fix in both cases is the same as Step 4's
   category-purity check applied *during collection*, not just after: define a
   strong, unique content signal for "this is really the target category" (for
   smith, a table whose header row contains the literal cell text `"ROD No."` — no
   lure/worm page on the site has that), fetch the candidate page, and only if the
   signal is absent look one directory-level deeper for same-subtree links and
   check those too, recursively but shallowly (one extra hop was enough for every
   site seen so far). A link that resolves to nothing matching the signal, even
   after that hop, is correctly excluded — don't force it into the output.

## Step 2 — Decide category scope, and say so before running anything expensive

Default to the manufacturer's **primary rod/reel lineup** first, matching the
existing daiwa/shimano/majorcraft/gamakatsu pattern — not every category the site
sells. Ask the user (don't just guess) when:

- a secondary category is orders of magnitude larger than the primary one (gamakatsu's
  "hook" catalog was ~100+ subcategories vs. 178 rods — deferred, not silently skipped)
- the site's own navigation groups clearly non-catalog items (tools, line, apparel,
  stickers, car seat covers…) under the same top-level tab as the real products
  (jackall's "ROD" nav tab — see Step 4)
- it's unclear whether a manufacturer even sells a given category at all

A brand-focused single-category manufacturer (beat/beet — a jigging-rod-only brand
with one `/rod` listing page and no risk of cross-category contamination) needs none
of this deliberation; the scope decision itself can be nearly instant. Don't add
unneeded category-purity machinery when the site structurally can't mix categories.

## Step 3 — Write `00_get_product.py`, then `01_get_item_spec.py`

`00_get_product.py` collects candidate product URLs into
`<slug>_urls/<slug>_products_<category>.csv` via `save_urls_csv` (which auto-creates
the parent dir). `01_get_item_spec.py` reads that CSV, parses each page's spec table,
and calls `save_json` once per output series file — `save_json` already handles the
`item_name`-keyed `created_at`/`updated_at` preservation correctly; never reimplement
that matching by list index (that was the original bug this session fixed everywhere).

**Default to grouping items by `product_name` across the *entire* CSV before writing
any file, not saving once per URL as you go.** `save_json` fully replaces whatever
file already exists at that path with the list you pass it — it does not merge
across separate calls. Two different URLs can legitimately produce the identical
`product_name` (and therefore the identical sanitized filename):

- the well-known "1 page = 1 item" case (Step 1.6 — evergreen), where grouping is
  obviously required, and
- the easy-to-miss case where two genuinely different sub-lineups share one display
  name. daiwa's "HRF® SX" has two separate product pages — a base line (8 models)
  and a "GR" line (4 models) — with byte-identical `<h1>` text on both. Processing
  URL-by-URL and saving immediately meant whichever URL was processed second
  silently overwrote the first URL's 4 (or 8) items with no error, no warning, and
  no file-count anomaly (Step 4's count check doesn't catch this, since one file
  legitimately exists — it's the *contents* that silently lost data).

The safe pattern, used across every scraper in this repo now:

```python
def process_csv(input_csv, output_dir):
    groups = {}
    for url in read_urls_csv(input_csv):
        soup = get_soup(url)
        product_name = extract_product_name(soup)
        if not product_name:
            continue
        items = parse_spec_table(soup, url, product_name)
        if not items:
            continue
        groups.setdefault(product_name, []).extend(items)

    for product_name, items in groups.items():
        filepath = os.path.join(output_dir, sanitize_filename(product_name) + ".json")
        save_json(filepath, items)
```

(Note this means only the *first* URL contributing to a given `product_name` ends up
as that file's `url` field, per CONTRACT.md's "first array element wins" rule — an
accepted, existing limitation, not a new one.)

Some product pages have no item-code column at all because the whole page is a
single SKU (goldenmean's テンカラマスター360: one spec row, no "品番"/"Model"
column). Don't just skip these — fall back to using `product_name` itself as
`item_name` when the table has exactly one data row and no recognizable item-code
column, so the product isn't silently dropped.

When a spec table's header naming is inconsistent across pages of the *same* site
(e.g. `商品コード` vs. `品コード`, a plain typo/variant seen on prox), match column
keys by substring/contains rather than exact string equality, and always exclude the
known item_name/jan/price keys from the leftover `specs` dict rather than allow-listing
spec columns (spec sets vary by category and you don't want to hand-maintain that list).
The same substring/variant tolerance applies to the *section heading* used to locate
the table in the first place — daiwa's spec section is normally an `h2` containing
"製品スペック", but at least one newer product page (a renewal/relaunch template)
used "スペック概要" instead. Match against a short list of known variants, not a
single exact string, and expect the list to grow the next time you review the site
(see "Reviewing an existing manufacturer" below).

## Step 4 — Verify before trusting a full-batch run

**Test on 2-3 known-different sample URLs first.** Read the actual JSON output, not
just "did it crash." A script that silently produces wrong data is worse than one
that errors.

**After the full run, always check these things**, because every one of them
silently produced wrong data at some point this session and none raised an exception:

- `len(output files) == len(input URLs)` (or the expected relationship, e.g. one file
  per distinct product_name). A mismatch means two different products' fallback
  filenames collided — this happened on gamakatsu when a handful of pages had an
  unset title field that fell back to literally rendering the section heading text
  ("製品スペック") as the title, so three unrelated products all wrote to the same
  file and silently overwrote each other. Fix: detect the fallback placeholder value
  specifically and fall back further (e.g. to `<title>`), then re-run *only* the
  affected URLs and diff before/after.
- **Grep the run log for duplicate save paths, even when the file count checks out.**
  `grep "^保存:" run.log | sort | uniq -c | awk '$1>1'` (adapt to whatever your
  save-line format is). If you've already switched to the group-then-save pattern
  above this specific symptom can't happen anymore, but it's the fastest way to
  confirm an *existing* per-URL-save scraper (or one you're reviewing, not
  authoring) has the daiwa-style collision bug before you decide whether a rewrite
  is warranted.
- **Does every saved item actually belong to the target category?** A spec table
  existing (or even having plausible-looking columns) is not proof of category
  membership if the site reuses one comparison-table template across product types.
  jackall reused the exact same `#spec-pc` table (with generic `Name`/`Price`
  columns) for rods *and* tackle boxes *and* car seat covers *and* PE line — filtering
  on "has a table" or even one rod-ish-sounding column (`Length` alone: PE line also
  has a length spec) let 150+ non-rod items through. What actually worked: requiring
  the header contain `Length` **and** (`継数` *or* `Power`) — real rods reliably have
  at least one of those two, PE line/handles reliably have neither. When you hit this
  kind of contamination, inspect the `specs` keys of a few suspicious outputs side by
  side with a few confirmed-good ones and find the smallest header signal that cleanly
  separates them — don't just add one more substring check and hope.
- **Open a couple of the actual output filenames/JSON values and read the Japanese
  text, don't just check the run exited cleanly.** A charset bug can produce
  perfectly well-formed JSON full of mojibake with zero exceptions anywhere in the
  pipeline (see Known pitfalls) — file-count and category-purity checks both pass
  while every string is garbage.

Only after both checks pass should you consider the category done. If contamination
is found after files were already written, regenerate and then clean up the stale
files that no longer correspond to any correctly-processed URL (see cleanup note below).

## Reviewing an existing manufacturer, not just adding a new one

"Review/見直して this manufacturer" or a plain "add this manufacturer's data" for a
folder that already exists and already has JSON files in it is a *different* task
from Step 1-4, even though it reuses the same verification techniques. Manufacturer
sites are not static — new products launch, old templates get partially replaced,
URL counts drift. Re-running periodically finds real, previously-invisible bugs, not
just refreshed data:

1. Re-run `00_get_product.py` fresh (don't assume the existing CSV is current) and
   compare the new URL count to the old one — growth or shrinkage is expected and
   fine, but note it.
2. Re-run `01_get_item_spec.py` and apply every Step 4 check to the fresh output:
   file-count-vs-URL-count, duplicate-save-path grep, category purity, and a spot
   read of the actual JSON content.
3. **Don't wave away "スキップ"/"テーブルなし" log lines as expected noise.** Fetch
   that one specific URL by hand and look at *why* it didn't match — it is often a
   genuine, previously-unhandled template or heading-text variant (daiwa's
   "スペック概要" heading, found this way, was a real 1-product gap that had existed
   silently since the folder was first implemented) rather than a URL that's
   legitimately out of scope. Confirming "yes, this one really doesn't apply" is a
   one-page fetch; assuming it without checking is how silent gaps survive multiple
   reviews.
4. A file count *higher* than the current live URL count is expected and correct
   for this repo (see CLAUDE.md / this project's confirmed policy: discontinued
   products are deliberately retained, never deleted just because a manufacturer
   removed them from their own site) — don't treat that direction of mismatch as a
   bug. Only a file count *at or below* what a full, successful run should produce
   (or duplicate save paths) indicates a real problem.
5. If you touch `common/scraper_utils.py` while investigating one manufacturer
   (e.g. the encoding fix below), re-run at least one *other*, already-verified
   manufacturer afterward and diff its output against a saved-aside copy — the diff
   should show only `updated_at` timestamp changes. That's the regression check for
   a shared-module change; do it before reporting the fix as safe.

## Sites that block automated access entirely (WAF / bot management)

Some sites don't just lack a scraper-friendly structure — they actively reject
automated requests outright. shimano's `fish.shimano.com` (and every other
`shimano.com` subdomain) returns HTTP 403 "Access Denied" from an Akamai-style edge
WAF for *every* request, including `robots.txt` itself, even with a realistic
browser `User-Agent` string. This is a different situation from "the HTML is just
awkward to parse" and needs a different, more conservative response:

1. **Confirm it's real** before concluding a manual workflow is required: try
   `robots.txt` and one real content page with a normal browser UA. A 403 from an
   edge WAF product (Akamai/Cloudflare-style "Access Denied" page, a reference ID in
   the body) on both is a strong, deliberate signal — not a fluke worth retrying.
2. **Do not attempt to circumvent it.** No proxy rotation, no TLS/HTTP fingerprint
   spoofing, no headless-browser automation configured to evade bot-detection
   (hiding `navigator.webdriver`, faking mouse movement, etc.), no CAPTCHA solving.
   This holds even though the underlying purpose (building a product catalog) is
   entirely legitimate — the site owner has made a deliberate technical choice to
   reject automated access, and defeating that choice is a different act from
   parsing awkward-but-permitted HTML, regardless of intent.
3. **Check genuinely separate, legitimate channels before falling back to manual
   work**, but expect them to be limited:
   - A different subdomain or `sitemap.xml` is usually behind the *same* WAF —
     confirm rather than assume it's separate.
   - The Wayback Machine CDX API
     (`https://web.archive.org/cdx/search/cdx?url=<domain>/<path>&matchType=prefix&output=json`)
     can have historical snapshots of individual product pages. Useful for a
     one-off historical check, but not a reliable primary source: coverage is
     patchy, skews to old years, and increasingly-aggressive site-side blocking
     shows up as archive.org's *own* crawler getting 403'd on recent snapshot
     attempts too. Don't build a pipeline around it without flagging the staleness
     risk to the user first — stale price/spec data flowing into TSURI HUB via
     CONTRACT.md's importer is worse than a smaller but current dataset.
   - Official PDF catalogs often exist but are (a) usually linked from a page on the
     same blocked domain, and (b) marketing documents, not structured per-SKU
     price/spec tables — treat as a separate, lower-priority follow-up requiring its
     own PDF-parsing implementation, not a quick substitute.
4. **Fall back to a manual-save workflow**: read pages in a real browser (the
   user's own, normal interactive session — this is not automation of any kind) and
   save the HTML locally; the scraper then reads those local files with
   `load_soup(html_path)` instead of `get_soup(url)`, and never makes a network
   request to the blocked site at all. `02_shimano_product/01_get_item_spec.py` /
   `input/reel/`, `input/rod/` is the reference implementation of this pattern.
5. **It's fine — encouraged — to automate the *bookkeeping* around a manual
   workflow, as long as the fetch itself stays human.** A helper script that reads
   the full target-URL CSV, checks which ones are already saved (extract each saved
   file's `<link rel="canonical">` via `extract_canonical_url` and diff against the
   URL list), and emits a plain local HTML page of `target="_blank"` links for the
   remaining ones is legitimate: it only reduces the human's copy-paste friction for
   navigation, and the human still actually loads every page in their own browser
   and presses Ctrl+S themselves. See `02_shimano_product/make_todo_list.py`. Do
   not extend a tool like this toward auto-clicking, auto-saving, or driving a
   browser programmatically — that crosses back into automated fetching.

## Known pitfalls checklist

- **Windows console encoding crash**: `print()`-ing a Japanese product name can raise
  `UnicodeEncodeError` under cp932 partway through a long batch, losing all progress
  after that point. `common/scraper_utils.py` already reconfigures `sys.stdout`/
  `sys.stderr` to UTF-8 with `errors="replace"` on import — don't remove that, and
  don't `print()` before importing it.
- **Response body mis-decoded into mojibake even though the run "succeeded"**: sites
  that declare their charset only in an HTML `<meta charset>` tag, not in the HTTP
  `Content-Type` header, get silently mis-decoded if you build `BeautifulSoup` from
  `res.text` — `requests` falls back to ISO-8859-1 with no charset in the header, and
  `res.apparent_encoding` (chardet) can *also* guess wrong for Japanese pages (seen
  guessing GB18030 for actual Shift_JIS content on smith's site). `get_soup()` in
  `common/scraper_utils.py` now builds `BeautifulSoup(res.content, "html.parser")` —
  raw bytes, not `res.text` — so BeautifulSoup's own `<meta>`-aware encoding sniffer
  handles it correctly. Never "fix" a single manufacturer's mojibake by setting
  `res.encoding` locally; fix `get_soup()` once, then verify no regression on an
  already-working manufacturer (diff its re-run output — only `updated_at` should
  change) before trusting the fix repo-wide.
- **Pagination that 404s instead of returning empty**: some sites return HTTP 404 for
  `page/N` past the last page rather than a 200 with no items — catch
  `requests.exceptions.HTTPError` and treat 404 as "no more pages", don't let it
  crash the crawl.
- **A category nav "tab"/div class is not the same thing as "this product's
  category"** — see Step 1.7 and Step 4. When a site's own IA (or a reused layout
  class) lumps unrelated items under the same tab/section as real products, trust
  the product page's own spec content over the URL/class/nav-label it was found
  under.
- **Reading your own log output on Windows**: when a subprocess's stdout was captured
  before the UTF-8 stdout fix (or via a tool that re-encodes for terminal display),
  decode saved log files as `cp932`/`errors="replace"` if `utf-8` garbles them, or
  vice versa — check both if one looks wrong. This is a *display* issue in your own
  terminal/log-reading tool, distinct from the mojibake-in-saved-JSON bug above —
  confirm which one you're looking at (read the actual output file with the right
  encoding) before "fixing" the wrong layer.

## Cleanup discipline

This repo's global rules require confirming with the user before deleting *any*
file, with no exception for files you created yourself this session (scratch HTML
dumps, throwaway check scripts, stale contaminated JSON, or stale mojibake-named
JSON left behind after fixing an encoding bug). Default to `mv`-ing investigation
scratch files out of the repo (to the session scratchpad dir) instead of deleting —
that needs no confirmation. Only ask-then-`rm` for things that must actually leave
the repo (e.g. a JSON file proven to be a duplicate/contaminated/mojibake leftover
from a bug you just fixed) — build the exact list of files first (diff against a
freshly-computed "expected filenames" set, don't guess by eyeballing a directory
listing) so the confirmation question is concrete and reviewable.

## Definition of done for one manufacturer/category

- `0N_<slug>_product/00_get_product.py` and `01_get_item_spec.py` exist, import
  shared helpers from `common.scraper_utils`, and have real (non-placeholder,
  non-`NotImplementedError`) logic — or, for a WAF-blocked site, `01_get_item_spec.py`
  reads from a local `input/` directory via `load_soup`, with a `README.md`
  documenting the manual-save workflow and (if built) a todo-list helper script.
- A full-batch run completed with every Step 4 check applied: file count vs. URL
  count, duplicate-save-path grep, category purity, and a manual read of a couple of
  actual output values for mojibake.
- Report to the user: URL count, saved file count, total item count, anything
  scoped out on purpose (and why), and the reminder that turi-side `SOURCE_DIRS`
  + importer wiring is still a separate follow-up before the data actually reaches
  TSURI HUB.
