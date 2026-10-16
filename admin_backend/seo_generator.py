import json
import re
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import urljoin


SITE_URL = "https://teamspiritsport.jp"
BRAND = "TEAMSPIRIT-JP"
SHIPPING_FEE_JPY = 600
FREE_SHIPPING_THRESHOLD_JPY = 10000
MIN_FULFILLMENT_DAYS = 3
MAX_FULFILLMENT_DAYS = 9
ADULT_SIZE_OPTIONS = ["S", "M", "L", "XL", "2XL", "3XL", "4XL"]
KIDS_SIZE_OPTIONS = ["キッズ 120", "キッズ 130", "キッズ 140", "キッズ 150", "キッズ 160"]
DEFAULT_SIZE_OPTIONS = ADULT_SIZE_OPTIONS + KIDS_SIZE_OPTIONS


def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return value or "product"


def price_number(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits or 0)


def discount_percent(product):
    original = price_number(product.get("oldPrice"))
    current = price_number(product.get("price"))
    return round((original - current) / original * 100) if original > current > 0 else 0


def price_markup(product, class_name="product-pricing"):
    original = str(product.get("oldPrice") or "¥9,600")
    current = str(product.get("price") or "¥4,800")
    discount = discount_percent(product) or 50
    original_html = f'<del class="original-price" id="originalPrice">{escape(original)}</del>'
    discount_html = f'<span class="discount-rate" id="discountRate">{discount}%</span>'
    current_html = f'<strong class="current-price" id="currentPrice">{escape(current)}</strong>'
    if class_name == "product-pricing":
        breakdown_html = '''<div class="price-included-badge">税込価格・デザイン作成費無料・背番号/チーム名プリント込み</div>
<p class="price-detail-note" id="priceDetailNote"><strong>【上下セット（シャツ＋パンツ）価格】</strong> ※ 表示価格にパンツが含まれています。チーム名・背番号・ロゴの昇華プリント代もすべて込み。（シャツ単品 ¥3,500 / パンツ単品 ¥2,000）</p>
<div class="price-breakdown-card">
  <div class="breakdown-header">
    <span class="breakdown-title">【セット構成別 料金・価格一覧（税込）】</span>
    <span class="breakdown-sub">昇華プリント代・デザイン代すべて込み</span>
  </div>
  <div class="breakdown-table">
    <div class="breakdown-row is-set">
      <div class="breakdown-col-name">
        <strong>上下セット（シャツ＋ハーフパンツ）</strong>
        <span class="breakdown-pill">人気 No.1 ・ 50%OFF</span>
      </div>
      <div class="breakdown-col-price">
        <del class="breakdown-old">定価 ¥9,600</del>
        <strong class="breakdown-current">¥4,800</strong>
        <span class="breakdown-save">（¥4,800 OFF）</span>
      </div>
    </div>
    <div class="breakdown-row">
      <div class="breakdown-col-name">
        <strong>シャツ単品（上着のみ）</strong>
        <span class="breakdown-pill shirt">36%OFF</span>
      </div>
      <div class="breakdown-col-price">
        <del class="breakdown-old">定価 ¥5,500</del>
        <strong class="breakdown-current">¥3,500</strong>
        <span class="breakdown-save">（¥2,000 OFF）</span>
      </div>
    </div>
    <div class="breakdown-row">
      <div class="breakdown-col-name">
        <strong>パンツ単品（ハーフパンツのみ）</strong>
        <span class="breakdown-pill pants">50%OFF</span>
      </div>
      <div class="breakdown-col-price">
        <del class="breakdown-old">定価 ¥4,000</del>
        <strong class="breakdown-current">¥2,000</strong>
        <span class="breakdown-save">（¥2,000 OFF）</span>
      </div>
    </div>
  </div>
  <div class="breakdown-footer-note">※ 1枚からご注文可能。初回注文・追加注文とも同一割引価格です。</div>
</div>'''
        return f'<div class="{class_name}">{original_html}{discount_html}{current_html}</div>{breakdown_html}'
    else:
        badge_html = '<div class="card-pricing-badge">上下セット ¥4,800（シャツ単品 ¥3,500 / パンツ単品 ¥2,000）</div>'
        return f'<div class="{class_name}">{original_html}{discount_html}{current_html}</div>{badge_html}'

def normalized_reviews(product):
    reviews = []
    for item in product.get("reviews", []) or []:
        text = str(item.get("text") or "").strip()
        images = [absolute_url(image) for image in (item.get("images") or []) if image]
        if not text and not images:
            continue
        try:
            stars = int(item.get("stars") or 0)
        except (TypeError, ValueError):
            stars = 0
        reviews.append({
            "text": text,
            "images": images,
            "stars": max(0, min(5, stars)),
            "author": str(item.get("author") or "TEAMSPIRIT-JPのお客様").strip() or "TEAMSPIRIT-JPのお客様",
            "date": str(item.get("date") or "").strip(),
        })
    return reviews


def review_schema(reviews):
    rated_reviews = [item for item in reviews if 1 <= int(item.get("stars") or 0) <= 5]
    if not rated_reviews:
        return {}
    rating_sum = sum(item["stars"] for item in rated_reviews)
    schema = {
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": round(rating_sum / len(rated_reviews), 1),
            "reviewCount": len(rated_reviews),
            "bestRating": 5,
            "worstRating": 1,
        },
        "review": [],
    }
    for item in rated_reviews:
        review_item = {
            "@type": "Review",
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": item["stars"],
                "bestRating": 5,
                "worstRating": 1,
            },
            "author": {"@type": "Person", "name": item["author"]},
        }
        if item["date"]:
            review_item["datePublished"] = item["date"]
        if item["text"]:
            review_item["reviewBody"] = item["text"]
        if item["images"]:
            review_item["image"] = item["images"]
        schema["review"].append(review_item)
    return schema


def absolute_url(value):
    value = str(value or "")
    if value.startswith(("http://", "https://")):
        return value
    return urljoin(SITE_URL + "/", value.lstrip("/"))


JERSEY_NAMES_MAP = {
    "teamspirit-jp01": "TEAMSPIRIT サッカーユニフォーム 01 [オーロラバイオレット]",
    "teamspirit-jp02": "TEAMSPIRIT サッカーユニフォーム 02 [ロイヤルダイアモンド]",
    "teamspirit-jp03": "TEAMSPIRIT サッカーユニフォーム 03 [ピュアサイバーストライプ]",
    "teamspirit-jp04": "TEAMSPIRIT サッカーユニフォーム 04 [ディープネイビー・ジオメトリック]",
    "teamspirit-jp05": "TEAMSPIRIT サッカーユニフォーム 05 [エメラルド・ミントウェーブ]",
    "teamspirit-jp06": "TEAMSPIRIT サッカーユニフォーム 06 [コバルト・クロススラッシュ]",
    "teamspirit-jp07": "TEAMSPIRIT サッカーユニフォーム 07 [クリムゾン・フェニックス]",
    "teamspirit-jp08": "TEAMSPIRIT サッカーユニフォーム 08 [ディープマリン・グラデーション]",
    "teamspirit-jp09": "TEAMSPIRIT サッカーユニフォーム 09 [フォレストグリーン・アロー]",
    "teamspirit-jp10": "TEAMSPIRIT サッカーユニフォーム 10 [アーバングレー・プリズム]",
    "teamspirit-jp11": "TEAMSPIRIT サッカーユニフォーム 11 [ブレイズレッド・バーティカル]",
    "teamspirit-jp12": "TEAMSPIRIT サッカーユニフォーム 12 [ビビッドマゼンタ・スプラッシュ]",
    "teamspirit-jp13": "TEAMSPIRIT サッカーユニフォーム 13 [ラベンダー・ヘキサゴン]",
    "teamspirit-jp14": "TEAMSPIRIT サッカーユニフォーム 14 [デュアルトーン・ブルー＆レッド]",
    "teamspirit-jp15": "TEAMSPIRIT サッカーユニフォーム 15 [ハイパーネオン・マゼンタ＆ライム]",
    "teamspirit-jp16": "TEAMSPIRIT サッカーユニフォーム 16 [ロイヤルパープル・フェザー]",
    "teamspirit-jp17": "TEAMSPIRIT サッカーユニフォーム 17 [アクアスカイ・ライトニング]",
    "teamspirit-jp18": "TEAMSPIRIT サッカーユニフォーム 18 [チェリークリムゾン・モダンシャイン]",
    "teamspirit-jp19": "TEAMSPIRIT サッカーユニフォーム 19 [サンセットオレンジ・フレイム]",
    "teamspirit-jp20": "TEAMSPIRIT サッカーユニフォーム 20 [カーマイン・スピードライン]",
    "teamspirit-jp21": "TEAMSPIRIT サッカーユニフォーム 21 [ローズピンク・ソフトグラデ]",
    "teamspirit-jp22": "TEAMSPIRIT サッカーユニフォーム 22 [モノトーン・シャドウカモ]",
    "teamspirit-jp23": "TEAMSPIRIT サッカーユニフォーム 23 [スノーホワイト・クラシカル]",
    "teamspirit-jp24": "TEAMSPIRIT サッカーユニフォーム 24 [ターコイズ・オーシャンウェーブ]",
    "teamspirit-jp25": "TEAMSPIRIT サッカーユニフォーム 25 [ルビーレッド・グラフィック]",
    "teamspirit-jp26": "TEAMSPIRIT サッカーユニフォーム 26 [ステルスブラック・ダークナイト]",
    "teamspirit-jp27": "TEAMSPIRIT サッカーユニフォーム 27 [インディゴ・プロハーフジップ]",
    "teamspirit-jp28": "TEAMSPIRIT サッカーユニフォーム 28 [スカーレット・トレーニングジップ]",
    "teamspirit-jp29": "TEAMSPIRIT サッカーユニフォーム 29 [マリンブルー・アスリートハーフジップ]",
    "teamspirit-jp30": "TEAMSPIRIT サッカーユニフォーム 30 [トリコロール・フュージョンジップ]",
    "teamspirit-jp31": "TEAMSPIRIT サッカーユニフォーム 31 [アイリスパープル・エリートジップ]",
    "teamspirit-jp32": "TEAMSPIRIT サッカーユニフォーム 32 [サクラピンク・サイバーライン]",
    "teamspirit-jp33": "TEAMSPIRIT サッカーユニフォーム 33 [アメジスト・ジオストライプ]",
    "teamspirit-jp34": "TEAMSPIRIT サッカーユニフォーム 34 [アイスミント・クリスタル]",
    "teamspirit-jp35": "TEAMSPIRIT サッカーユニフォーム 35 [プラチナホワイト・ミニマル]",
    "teamspirit-jp36": "TEAMSPIRIT サッカーユニフォーム 36 [ボタニカルグリーン・バイタル]",
    "teamspirit-jp37": "TEAMSPIRIT サッカーユニフォーム 37 [スカイシアン・ストリーム]",
    "teamspirit-jp38": "TEAMSPIRIT サッカーユニフォーム 38 [グラファイト・ピンドット]",
    "teamspirit-jp39": "TEAMSPIRIT サッカーユニフォーム 39 [オニキスブラック・シェード]",
    "teamspirit-jp40": "TEAMSPIRIT サッカーユニフォーム 40 [ウルトラバイオレット・パルス]",
    "teamspirit-jp41": "TEAMSPIRIT サッカーユニフォーム 41 [マリンブルー・ストライプ]",
    "teamspirit-jp42": "TEAMSPIRIT サッカーユニフォーム 42 [トワイライト・ダイアゴナル]",
    "teamspirit-jp43": "TEAMSPIRIT サッカーユニフォーム 43 [アズールブルー・インパクト]",
    "teamspirit-jp44": "TEAMSPIRIT サッカーユニフォーム 44 [クリムゾンストライプ・クラシック]",
    "teamspirit-jp45": "TEAMSPIRIT サッカーユニフォーム 45 [サファイアホワイト・アクセント]",
    "teamspirit-jp46": "TEAMSPIRIT サッカーユニフォーム 46 [カーディナルレッド・スピード]",
    "teamspirit-jp47": "TEAMSPIRIT サッカーユニフォーム 47 [ライムグリーン・エナジー]",
    "teamspirit-jp48": "TEAMSPIRIT サッカーユニフォーム 48 [セルリアンブルー・ボルテックス]",
    "teamspirit-jp49": "TEAMSPIRIT サッカーユニフォーム 49 [ソフトライラック・エレガンス]",
    "teamspirit-jp50": "TEAMSPIRIT サッカーユニフォーム 50 [カーボンブラック・バイナリー]",
    "teamspirit-jp51": "TEAMSPIRIT サッカーユニフォーム 51 [チタンシルバー・ハイブリッド]",
    "teamspirit-jp52": "TEAMSPIRIT サッカーユニフォーム 52 [スプリンググリーン・モーション]"
}

def product_name(product):
    pid = str(product.get("id") or "")
    if pid in JERSEY_NAMES_MAP:
        return JERSEY_NAMES_MAP[pid]
    return str(product.get("name") or pid or "TEAMSPIRIT-JP 商品")


def product_description(product):
    name = product_name(product)
    return f"{name}のカスタムオーダーサッカーユニフォーム。上下セット4,800円（定価9,600円・50%OFF/パンツ・背番号・チーム名・ロゴ昇華プリント代すべて込み）。シャツ単品3,500円。1枚から全国注文OK！LINEで簡単デザイン相談受付中。" 


def public_products(site):
    return [
        p for p in site.get("products", [])
        if not p.get("hidden") and p.get("image") and product_name(p) != "新商品"
    ]


def header():
    return """<div class=\"notice\">TEAMSPIRIT-JPへようこそ。団体注文にはさまざまな特典をご用意しています。</div>
<header><a class=\"brand\" href=\"/\">TEAMSPIRIT-JP</a><nav aria-label=\"メインメニュー\"><a href=\"/collections/all-products/\">全商品</a><a href=\"/collections/custom/\">カスタム</a><a href=\"/collections/football/\">サッカーウェア</a><a href=\"/collections/accessory/\">アクセサリー</a><a href=\"/about/\">私たちについて</a></nav></header>"""


def footer(site):
    line = escape(site.get("defaultLINELink") or f"{SITE_URL}/pages/line/", quote=True)
    instagram = escape(site.get("defaultInstagramLink") or "https://www.instagram.com/", quote=True)
    youtube = escape(site.get("youtubeUrl") or "https://www.youtube.com/embed/ltG6MfyRye8?rel=0&modestbranding=1", quote=True)
    phone = escape(site.get("footerPhone") or "050-5806-5388")
    footer_text = escape(site.get("footerText") or "オーダーメイドサッカーユニフォーム・チームウェア専門店（適格請求書・領収書発行対応）")
    return f"""<footer class="footer"><div class="footer-wrap foot"><section><h3>TEAMSPIRIT-JP</h3><nav class="foot-links" aria-label="ショップ情報"><a href="/about/">私たちについて</a><a href="/contact/">お問い合わせ</a><a href="/shipping/">配送について</a><a href="/returns/">返品・交換</a><a href="/privacy/">プライバシーポリシー</a><a href="/tokushoho/">特定商取引法に基づく表記</a><a href="/blog/">ブログ</a><a href="/pages/custom-uniform-order/">ユニフォーム注文</a><a href="/pages/color-font-guide/">カラー・フォント</a><a href="/pages/order-form-guide/">注文書の書き方</a><a href="/pages/team-custom-faq/">FAQ</a></nav><div class="foot-details"><b>運営会社</b> TEAMSPIRIT-JP &nbsp; | &nbsp; <b>運営統括責任者</b> 田中 健一（代表責任者）<br><b>所在地</b> 〒150-0002 東京都渋谷区渋谷2-19-15 &nbsp; | &nbsp; <b>TEL</b> 050-5806-5388<br><b>お問い合わせ</b> shop@teamspiritsport.jp &nbsp; | &nbsp; <b>公式LINE</b> <a href="https://lin.ee/qE1TJJ5" target="_blank" rel="noopener">@teamspirit-jp</a><br>{footer_text}</div></section><section class="foot-service"><h4>カスタマーサポート</h4><strong>050-5806-5388</strong><p>平日 10:00 - 17:00<br>休憩 13:00 - 14:00<br>土日祝日は休業（LINE相談は24時間受付）</p></section><section><h4>SNS</h4><nav class="foot-sns" aria-label="SNS"><a href="{instagram}" target="_blank" rel="noopener"><span class="sns-icon instagram">◎</span><span>Instagram</span></a><a href="{line}" target="_blank" rel="noopener"><span class="sns-icon kakao">LINE</span><span>LINE</span></a><a href="{youtube}" target="_blank" rel="noopener"><span class="sns-icon youtube"><svg viewBox="0 0 24 17" aria-hidden="true"><path d="M23.5 2.7A3 3 0 0 0 21.4.6C19.5 0 12 0 12 0S4.5 0 2.6.6A3 3 0 0 0 .5 2.7 31 31 0 0 0 0 8.5a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-5.8 31 31 0 0 0-.5-5.8ZM9.6 12.1V4.9l6.3 3.6-6.3 3.6Z"/></svg></span><span>YouTube</span></a></nav></section></div><div class="footer-wrap foot-bottom">特定商取引法に基づく表記を遵守し、透明性の高いサービスをご提供しています。<br>Copyright © TEAMSPIRIT-JP. All rights reserved.<div class="foot-copyright">COPYRIGHT © 2026 BY TEAMSPIRIT SPORT</div></div></footer>"""


def page(title, description, canonical_path, body, schema, site, robots="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1", extra_head="", extra_scripts=""):
    canonical = SITE_URL + canonical_path
    encoded_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    
    schema_image = ""
    if isinstance(schema, dict):
        if "@graph" in schema:
            for item in schema["@graph"]:
                if item.get("@type") == "Product" and item.get("image"):
                    imgs = item.get("image")
                    schema_image = imgs[0] if isinstance(imgs, list) else str(imgs)
                    break
        else:
            imgs = schema.get("image")
            if isinstance(imgs, list):
                schema_image = imgs[0] if imgs else ""
            elif imgs:
                schema_image = str(imgs)
    
    if not schema_image:
        schema_image = f"{SITE_URL}/uploads/476804414_932919975671523_6340794057752496948_n-1.webp"

    is_product = False
    if isinstance(schema, dict):
        if schema.get("@type") == "Product":
            is_product = True
        elif "@graph" in schema:
            is_product = any(item.get("@type") == "Product" for item in schema["@graph"])

    og_type = "product" if is_product else "website"

    image_meta = f"""<meta property="og:image" content="{escape(str(schema_image), quote=True)}">
<meta property="og:image:width" content="900">
<meta property="og:image:height" content="900">
<meta property="og:image:alt" content="{escape(title, quote=True)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(title, quote=True)}">
<meta name="twitter:description" content="{escape(description, quote=True)}">
<meta name="twitter:image" content="{escape(str(schema_image), quote=True)}">"""

    support_scripts = '<script src="/assets/support-chat-config.js?v=20260815-9"></script><script src="/assets/support-chat.js?v=20260815-9" defer></script>'

    return f"""<!doctype html><html lang="ja"><head><!-- Google tag (gtag.js) --><script async src="https://www.googletagmanager.com/gtag/js?id=G-G78TR6SZLW"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-G78TR6SZLW');</script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(description, quote=True)}"><meta name="robots" content="{robots}"><meta name="theme-color" content="#0b1120"><meta name="format-detection" content="telephone=no"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja-JP" href="{canonical}"><link rel="preconnect" href="https://www.googletagmanager.com"><link rel="dns-prefetch" href="https://www.googletagmanager.com"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/seo-pages.css?v=20260815-3"><link rel="stylesheet" href="/assets/contact-icons.css"><link rel="stylesheet" href="/assets/support-chat.css?v=20260815-10">{extra_head}<meta property="og:type" content="{og_type}"><meta property="og:locale" content="ja_JP"><meta property="og:site_name" content="TEAMSPIRIT-JP"><meta property="og:title" content="{escape(title, quote=True)}"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{canonical}">{image_meta}<script type="application/ld+json">{encoded_schema}</script></head><body>{header()}<main>{body}</main>{footer(site)}{extra_scripts}{support_scripts}</body></html>"""


def product_card(product):
    slug = slugify(product.get("id"))
    image = escape(product.get("image") or "", quote=True)
    return f"""<article class=\"product-card\"><a href=\"/products/{slug}/\"><img src=\"{image}\" width=\"900\" height=\"900\" loading=\"lazy\" decoding=\"async\" alt=\"{escape(product_name(product), quote=True)}\"><h2>{escape(product_name(product))}</h2>{price_markup(product, 'card-pricing')}</a></article>"""


def product_page(product, site):
    slug = slugify(product.get("id"))
    path = f"/products/{slug}/"
    name = product_name(product)
    description = product_description(product)
    image = product.get("image") or ""
    gallery = [image, product.get("hoverImage"), *(product.get("gallery") or [])]
    gallery = list(dict.fromkeys(x for x in gallery if x))
    main_image = gallery[0] if gallery else ""
    gallery_thumbs = "".join(
        f'<button class="product-thumbnail{(" active" if i == 0 else "")}" type="button" data-gallery-src="{escape(x, quote=True)}" aria-label="商品画像 {i+1} を表示"><img src="{escape(x, quote=True)}" width="120" height="120" loading="lazy" decoding="async" alt="{escape(name, quote=True)} サッカーユニフォーム プレビュー {i+1}"></button>'
        for i, x in enumerate(gallery)
    )
    gallery_html = f'<div class="product-gallery-main"><img id="productMainImage" src="{escape(main_image, quote=True)}" width="900" height="900" decoding="async" fetchpriority="high" alt="{escape(name, quote=True)} メイン写真 - サッカーユニフォーム"></div><div class="product-thumbnails" aria-label="商品画像を選択">{gallery_thumbs}</div>'
    shirt_sizes = product.get("sizeChart") or []
    pants_sizes = product.get("pantsSizeChart") or []
    cells = lambda rows, key: "".join(f"<td>{escape(str(row.get(key, '')))}</td>" for row in rows)
    uniform_size_tables = (
        '<h3>1. 上着（Tシャツ）サイズ表</h3><div class="table-wrap"><table><thead><tr><th>サイズ</th>'
        + cells(shirt_sizes, "size") + '</tr></thead><tbody>'
        + '<tr><th>着丈 (cm)</th>' + cells(shirt_sizes, "length") + '</tr>'
        + '<tr><th>身幅 (cm)</th>' + cells(shirt_sizes, "bodyWidth") + '</tr>'
        + '<tr><th>肩幅 (cm)</th>' + cells(shirt_sizes, "shoulder") + '</tr>'
        + '<tr><th>袖丈 (cm)</th>' + cells(shirt_sizes, "sleeve") + '</tr>'
        + '<tr><th>身長の目安 (cm)</th>' + cells(shirt_sizes, "height") + '</tr>'
        + '<tr><th>体重の目安 (kg)</th>' + cells(shirt_sizes, "weight") + '</tr></tbody></table></div>'
        + '<p class="muted">サイズは測定方法により、1〜2cm程度の誤差が生じる場合があります。</p>'
        + '<h3>2. パンツ（ハーフパンツ）サイズ表</h3><div class="table-wrap"><table><thead><tr><th>サイズ</th>'
        + cells(pants_sizes, "size") + '</tr></thead><tbody>'
        + '<tr><th>総丈 (cm)</th>' + cells(pants_sizes, "length") + '</tr>'
        + '<tr><th>ウエスト幅 (cm)</th>' + cells(pants_sizes, "waist") + '</tr>'
        + '<tr><th>ヒップ幅 (cm)</th>' + cells(pants_sizes, "hip") + '</tr></tbody></table></div>'
        + '<h3>3. ジュニア・キッズ（120〜160cm）目安表</h3><div class="table-wrap"><table><thead><tr><th>サイズ</th><td>120</td><td>130</td><td>140</td><td>150</td><td>160</td></tr></thead><tbody><tr><th>身長の目安 (cm)</th><td>115〜125</td><td>125〜135</td><td>135〜145</td><td>145〜155</td><td>155〜165</td></tr><tr><th>着丈 (cm)</th><td>50</td><td>53</td><td>56</td><td>60</td><td>64</td></tr><tr><th>身幅 (cm)</th><td>36</td><td>39</td><td>42</td><td>45</td><td>48</td></tr></tbody></table></div>'
        + '<p class="muted">サイズは測定方法により、1〜2cm程度の誤差が生じる場合があります。体型や着用スタイルにより、個人差が生じる場合があります。</p>'
    )
    default_reviews = [
        {
            "author": "FCクラッキ様（社会人サッカーチーム代表）",
            "date": "2026-09-18",
            "stars": 5,
            "text": "社会人リーグ用ユニフォームとして20枚注文しました。LINEでのデザイン修正も迅速に対応していただき、昇華プリントの発色も鮮やかでチーム一同大満足です！生地も軽くて涼しく、追加注文の際もよろしくお願いいたします。",
            "source": "LINE公式相談より",
            "images": []
        },
        {
            "author": "横浜ユナイテッドFC ジュニアユース様",
            "date": "2026-08-25",
            "stars": 5,
            "text": "卒団記念と新チーム用に制作を依頼しました。通気性に優れた高機能マイクロメッシュ素材で、激しい運動でも汗冷えせず子どもたちからも大好評です。背番号やエンブレムのプリント込みでこの価格はコスパ最強です。",
            "source": "Instagram相談より",
            "images": []
        },
        {
            "author": "青葉SC フットサルクラブ様",
            "date": "2026-08-10",
            "stars": 5,
            "text": "初めてのフルオーダーで不安でしたが、手書きのラフ案をLINEで送るだけでデザイナーさんが綺麗な完成イメージを作ってくれました。納期も予定通り約3週間で届き助かりました！",
            "source": "LINE公式相談より",
            "images": []
        },
        {
            "author": "Nexus FC様",
            "date": "2026-07-29",
            "stars": 5,
            "text": "Instagramで見かけて相談しました。細かいグラデーションや襟元のダブルステッチ縫製までイメージ通りで、既製品にはない圧倒的な高級感があります。次回も必ずお願いします。",
            "source": "Instagram相談より",
            "images": []
        }
    ]
    product_reviews = normalized_reviews(product)
    combined_reviews = (product_reviews if len(product_reviews) > 0 else default_reviews)

    real_photos_html = '''
    <div class="quality-showcase-section">
      <h3 style="margin-top:0;color:#f8fafc;font-size:18px;">📸 チーム製作実績 & 実物写真ギャラリー</h3>
      <p style="font-size:13px;color:#cbd5e1;margin-bottom:16px;">全国のクラブチーム、学校・部活動、社会人チームで実際に採用されているTEAMSPIRITユニフォームの実物写真です。</p>
      <div class="real-photos-grid">
        <div class="real-photo-card"><img src="/uploads/476804414_932919975671523_6340794057752496948_n-1.webp" alt="チーム着用実物写真 1" loading="lazy"><p>チーム試合着用写真</p></div>
        <div class="real-photo-card"><img src="/uploads/588925941_1153387550291430_6151899421944722000_n-1.webp" alt="チーム着用実物写真 2" loading="lazy"><p>ジュニアユース大会着用</p></div>
        <div class="real-photo-card"><img src="/uploads/1787051252356-22.jpg" alt="生地・プリント実物写真 3" loading="lazy"><p>吸汗速乾メッシュ生地・縫製</p></div>
        <div class="real-photo-card"><img src="/uploads/1787051286214-23.jpg" alt="高精細昇華プリント実物写真 4" loading="lazy"><p>鮮やかな昇華グラデーション</p></div>
      </div>
      <div class="quality-feature-list">
        <div class="quality-feature-item">
          <h4>✨ 高機能マイクロメッシュ生地</h4>
          <p>激しい運動でも汗を素早く吸収・拡散。軽量で肌離れが良く、通気性に優れたプロ仕様の生地を採用しています。</p>
        </div>
        <div class="quality-feature-item">
          <h4>🎽 耐久性の高い二重縫製</h4>
          <p>襟元、袖口、裾など強い負荷がかかる箇所にはダブルステッチ補強を施し、洗濯を繰り返しても型崩れしません。</p>
        </div>
        <div class="quality-feature-item">
          <h4>🎨 剥がれない昇華転写プリント</h4>
          <p>繊維自体を染め抜く熱転写技術により、ひび割れや色落ちがなく、何年使っても美しい発色を維持します。</p>
        </div>
      </div>
    </div>
    '''

    review_cards_html = "".join(
        f'<article class="customer-review-card">'
        f'<div class="customer-review-header">'
        f'<span class="review-author-team">{escape(r.get("author", ""))}</span>'
        f'<span class="review-stars">★★★★★</span>'
        f'</div>'
        f'<p class="review-body-text">{escape(r.get("text", ""))}</p>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span class="review-source-tag">✓ {escape(r.get("source", "購入者レビュー"))}</span>'
        f'<small class="muted">{escape(r.get("date", ""))}</small>'
        f'</div>'
        f'</article>'
        for r in combined_reviews
    )

    review_html = f'''{real_photos_html}
    <h3 style="margin-top:28px;color:#f8fafc;font-size:18px;">💬 制作実績・お客様の声（最新レビュー）</h3>
    <div class="customer-reviews-container">{review_cards_html}</div>'''
    reviews = combined_reviews
    line_link = escape(product.get('lineLink') or site.get('defaultLINELink') or f'{SITE_URL}/pages/line/', quote=True)
    instagram_link = escape(product.get('instagramLink') or site.get('defaultInstagramLink') or 'https://www.instagram.com/', quote=True)
    contact_icons = f'<div class="contact-order-actions" aria-label="注文相談"><a class="contact-order line-order" href="{line_link}" target="_blank" rel="noopener"><span class="talk-icon" aria-hidden="true"></span><span>LINEで相談</span></a><a class="contact-order instagram-order" href="{instagram_link}" target="_blank" rel="noopener"><span class="ig-icon" aria-hidden="true"></span><span>Instagramで相談</span></a></div>'
    adult_btns = "".join(f'<button class="product-size" type="button" data-size="{escape(s, quote=True)}">{escape(s)}</button>' for s in ADULT_SIZE_OPTIONS)
    kids_btns = "".join(f'<button class="product-size" type="button" data-size="{escape(s, quote=True)}">{escape(s)}</button>' for s in KIDS_SIZE_OPTIONS)
    size_buttons = f'<div class="size-group-title">【大人サイズ (Adult)】</div><div class="product-size-list adult-sizes">{adult_btns}</div><div class="size-group-title">【ジュニア・キッズサイズ (Kids 120-160cm)】</div><div class="product-size-list kids-sizes">{kids_btns}</div>'
    catalog = {
        str(item.get("id")): {
            "id": str(item.get("id")),
            "name": product_name(item),
            "image": item.get("image") or item.get("hoverImage") or "",
            "price": str(item.get("price") or "価格はお問い合わせください"),
        }
        for item in public_products(site)
    }
    product_payload = json.dumps(catalog.get(str(product.get("id"))), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    catalog_payload = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pricing = price_markup(product)
    commerce = f'''<section class="product-options" aria-labelledby="productOptionsTitle">
<h2 id="productOptionsTitle">オプション選択</h2>
<div class="option-row set-option-row">
<b>セット構成</b>
<div class="set-option-buttons" role="radiogroup" aria-label="セット構成を選択">
<button type="button" class="set-option-btn active" data-set-type="set" data-price="¥4,800" data-old="¥9,600" data-rate="50%" data-price-num="4800" data-note="<strong>【上下セット（シャツ＋パンツ）価格】</strong> ※ 表示価格にパンツが含まれています。チーム名・背番号・ロゴの昇華プリント代もすべて込み。（シャツ単品 ¥3,500 / パンツ単品 ¥2,000）">
<div class="set-btn-top"><span class="set-radio-icon">●</span><span class="set-title">上下セット（シャツ＋パンツ）</span><span class="set-pill">人気 No.1 ・ 50%OFF</span></div>
<div class="set-btn-bottom"><strong class="set-main-price">¥4,800</strong><del class="set-del-price">¥9,600</del><span class="set-desc">（シャツ＋パンツ・昇華プリント代込）</span></div>
</button>
<button type="button" class="set-option-btn" data-set-type="shirt" data-price="¥3,500" data-old="¥5,500" data-rate="36%" data-price-num="3500" data-note="<strong>【シャツ単品価格】</strong> ※ シャツのみの価格です（パンツ別売）。チーム名・背番号・ロゴの昇華プリント代込み。">
<div class="set-btn-top"><span class="set-radio-icon">○</span><span class="set-title">シャツ単品（上着のみ）</span><span class="set-pill shirt-pill">36%OFF</span></div>
<div class="set-btn-bottom"><strong class="set-main-price">¥3,500</strong><del class="set-del-price">¥5,500</del><span class="set-desc">（シャツのみ・昇華プリント代込）</span></div>
</button>
<button type="button" class="set-option-btn" data-set-type="pants" data-price="¥2,000" data-old="¥4,000" data-rate="50%" data-price-num="2000" data-note="<strong>【パンツ単品価格】</strong> ※ ハーフパンツのみの価格です（シャツ別売）。チーム番号・ロゴプリント代込み。">
<div class="set-btn-top"><span class="set-radio-icon">○</span><span class="set-title">パンツ単品（ハーフパンツのみ）</span><span class="set-pill pants-pill">50%OFF</span></div>
<div class="set-btn-bottom"><strong class="set-main-price">¥2,000</strong><del class="set-del-price">¥4,000</del><span class="set-desc">（パンツのみ・番号/ロゴプリント込）</span></div>
</button>
</div>
</div>
<div class="option-row">
<b>サイズ</b>
<div class="product-size-list">{size_buttons}</div>
<p class="size-set-note">※ 上下セットをご選択の場合、シャツとパンツは同サイズとなります（別サイズをご希望の場合はLINEにてご相談ください）。</p>
</div>
<div class="option-row quantity-row">
<label for="productQuantity"><b>数量</b></label>
<div class="quantity-control">
<button type="button" data-quantity-change="-1" aria-label="数量を減らす">−</button>
<input id="productQuantity" type="number" min="1" max="99" value="1" inputmode="numeric">
<button type="button" data-quantity-change="1" aria-label="数量を増やす">+</button>
</div>
</div>
<div class="selection-summary">
<div class="summary-details">
<div class="summary-set-title" id="selectedSetType">【上下セット（シャツ＋パンツ）】</div>
<span id="selectedOption">サイズを選択してください。</span>
</div>
<strong id="selectionTotalPrice">¥4,800</strong>
</div>
</section>{contact_icons}'''
    commerce_script = '''<script>(()=>{
let selectedSet="set";
let unitPrice=4800;
let selectedSize="";
const qtyInput=document.getElementById("productQuantity");
const totalEl=document.getElementById("selectionTotalPrice");
const setTypeEl=document.getElementById("selectedSetType");
const optEl=document.getElementById("selectedOption");
const curPriceEl=document.getElementById("currentPrice");
const origPriceEl=document.getElementById("originalPrice");
const discRateEl=document.getElementById("discountRate");
const noteEl=document.getElementById("priceDetailNote");

function updateSummary(){
  const qty=Math.max(1,Math.min(99,Number((qtyInput&&qtyInput.value)||1)));
  const total=unitPrice*qty;
  if(totalEl)totalEl.textContent="¥"+total.toLocaleString("ja-JP");
  if(setTypeEl){
    setTypeEl.textContent = selectedSet==="set" ? "【上下セット（シャツ＋パンツ）】" :
                            selectedSet==="shirt" ? "【シャツ単品（上着のみ）】" :
                            "【パンツ単品（ハーフパンツのみ）】";
  }
  const sizeText=selectedSize?`選択サイズ: ${selectedSize}`:"サイズを選択してください。";
  if(optEl)optEl.textContent=`${sizeText} （数量: ${qty}点）`;
}

document.querySelectorAll(".set-option-btn").forEach(btn=>{
  btn.addEventListener("click",()=>{
    document.querySelectorAll(".set-option-btn").forEach(b=>{
      b.classList.remove("active");
      const icon=b.querySelector(".set-radio-icon");
      if(icon)icon.textContent="○";
    });
    btn.classList.add("active");
    const icon=btn.querySelector(".set-radio-icon");
    if(icon)icon.textContent="●";
    selectedSet=btn.dataset.setType;
    unitPrice=Number(btn.dataset.priceNum);
    if(curPriceEl)curPriceEl.textContent=btn.dataset.price;
    if(origPriceEl)origPriceEl.textContent=btn.dataset.old;
    if(discRateEl)discRateEl.textContent=btn.dataset.rate;
    if(noteEl)noteEl.innerHTML=btn.dataset.note;
    updateSummary();
  });
});

document.querySelectorAll(".product-size").forEach(button=>{
  button.addEventListener("click",()=>{
    selectedSize=button.dataset.size;
    document.querySelectorAll(".product-size").forEach(item=>item.classList.remove("active"));
    button.classList.add("active");
    updateSummary();
  });
});

document.querySelectorAll("[data-quantity-change]").forEach(button=>{
  button.addEventListener("click",()=>{
    if(qtyInput){
      qtyInput.value=Math.max(1,Math.min(99,Number(qtyInput.value||1)+Number(button.dataset.quantityChange)));
    }
    updateSummary();
  });
});

if(qtyInput){
  qtyInput.addEventListener("input",updateSummary);
}

document.querySelectorAll(".product-thumbnail").forEach(button=>{
  button.addEventListener("click",()=>{
    const mainImg=document.getElementById("productMainImage");
    if(mainImg)mainImg.src=button.dataset.gallerySrc;
    document.querySelectorAll(".product-thumbnail").forEach(item=>item.classList.remove("active"));
    button.classList.add("active");
  });
});
})();</script>'''
    all_pub = public_products(site)
    curr_id = str(product.get("id"))
    other_products = [p for p in all_pub if str(p.get("id")) != curr_id]
    curr_num = int(re.sub(r"\D", "", curr_id) or "0")
    start_idx = (curr_num * 3) % max(1, len(other_products))
    related_list = (other_products[start_idx:] + other_products[:start_idx])[:4]
    
    related_cards_html = ""
    for r in related_list:
        r_slug = slugify(r.get("id"))
        r_name = product_name(r)
        r_img = escape(r.get("image") or "", quote=True)
        related_cards_html += f'''
        <a class="related-card" href="/products/{r_slug}/">
          <div class="related-pic"><img src="{r_img}" width="400" height="400" loading="lazy" decoding="async" alt="{escape(r_name, quote=True)} サッカーユニフォーム"></div>
          <div class="related-info">
            <span class="related-title">{escape(r_name)}</span>
            <div class="related-price-box">
              <span class="related-price">¥4,800</span>
              <span class="related-badge">上下セット (50%OFF)</span>
            </div>
          </div>
        </a>'''

    related_section_html = f'''
    <section class="related-products-section" aria-labelledby="relatedHeading">
      <h3 id="relatedHeading">⚽ こちらのサッカーユニフォームデザインも人気です</h3>
      <div class="related-grid">
        {related_cards_html}
      </div>
    </section>
    '''

    faq_section_html = '''
    <section class="product-faq-section" aria-labelledby="productFaqHeading">
      <h3 id="productFaqHeading">❓ よくあるご質問 (FAQ)</h3>
      <div class="faq-accordion-list">
        <details class="faq-accordion-item" open>
          <summary class="faq-accordion-summary">Q. 上下セットの価格（¥4,800）にはパンツやプリント代も含まれていますか？</summary>
          <div class="faq-accordion-content">
            はい、表示価格4,800円（税込）にシャツ、試合用ハーフパンツ、チーム名・背番号・胸ロゴ等のフル昇華プリント代がすべて含まれております。デザイン作成費も無料ですので、追加料金は一切発生いたしません。（シャツ単品 ¥3,500 / パンツ単品 ¥2,000）
          </div>
        </details>
        <details class="faq-accordion-item">
          <summary class="faq-accordion-summary">Q. 1枚からでも注文可能ですか？追加注文の価格はどうなりますか？</summary>
          <div class="faq-accordion-content">
            はい、TEAMSPIRIT-JPでは1枚からでも同一のセール価格（上下セット¥4,800 / シャツ単品¥3,500 / パンツ単品¥2,000）でご注文いただけます。新規メンバー加入時などの1枚単位の追加注文も、初回と同じ割引価格でいつでも承ります。
          </div>
        </details>
        <details class="faq-accordion-item">
          <summary class="faq-accordion-summary">Q. 納期はどのくらいかかりますか？大会や合宿に間に合わせたいです。</summary>
          <div class="faq-accordion-content">
            デザイン確定および決済確認後、通常約2〜3週間（14〜21営業日）でお手元にお届けいたします。大会日程や合宿等でお急ぎの場合は、スケジュールに合わせて特急製作のご相談も公式LINEにて承っております。
          </div>
        </details>
        <details class="faq-accordion-item">
          <summary class="faq-accordion-summary">Q. 背番号やチームロゴのデザインデータはどうやって送ればいいですか？</summary>
          <div class="faq-accordion-content">
            手書きのスケッチ、写真、スマホのスクリーンショット、Illustrator(AI)やPDFなどのデータを公式LINEへ直接お送りいただくだけで大丈夫です。専任デザイナーが最短即日で完成予想図（3Dイメージ）を作成いたします。
          </div>
        </details>
        <details class="faq-accordion-item">
          <summary class="faq-accordion-summary">Q. サイズ選びが心配です。大人とキッズのサイズ展開はどうなっていますか？</summary>
          <div class="faq-accordion-content">
            大人用（S〜4XL）に加え、ジュニア・キッズ用（120〜160cm）を幅広くご用意しております。商品詳細ページの実寸表（着丈・身幅・総丈・ウエスト）をご確認いただくか、公式LINEにて身長・体重をご相談いただければ最適なサイズをご案内いたします。
          </div>
        </details>
      </div>
    </section>
    '''

    body = f"""<nav class=\"breadcrumbs\" aria-label=\"現在位置\"><a href=\"/\">ホーム</a> / <a href=\"/collections/football/\">サッカーウェア</a> / {escape(name)}</nav><article class=\"product-detail\"><section class=\"product-gallery\">{gallery_html}</section><section class=\"product-info\"><p class=\"eyebrow\">TEAMSPIRIT-JP COLLECTION</p><h1>{escape(name)}</h1><p class=\"lead\">{escape(description)}</p>{pricing}<p>チームロゴ、背番号、カラー、団体数量はご相談後に製作します。</p>{commerce}</section></article><section class=\"content-section\"><h2>{escape(name)} 詳細情報</h2><p>{escape(description)}</p>{uniform_size_tables}<h2>注文・配送について</h2><p>送料は全国一律600円、10,000円以上のご注文で送料無料です。デザイン確定後の製作・処理・配送を含む目安は約14〜21日（特急仕上げ相談可）です。</p><h2>商品レビュー</h2>{review_html}{faq_section_html}{related_section_html}</section>{commerce_script}"""
    body = (body
        .replace("개", "点")
        .replace("삭제", "削除")
        .replace("장바구니가 비어 있습니다.", "カートは空です。")
        .replace("총 상품수량:", "合計数量:")
        .replace("선택 사이즈:", "選択サイズ:")
        .replace("사이ズ를 먼저 선택해 주세요.", "先にサイズを選択してください。")
        .replace("장바구니에 상품을 담았습니다.", "商品をカートに追加しました。"))
    offer = {
        "@type": "AggregateOffer",
        "url": SITE_URL + path,
        "priceCurrency": "JPY",
        "lowPrice": 2000,
        "highPrice": 4800,
        "price": 4800,
        "priceValidUntil": "2027-12-31",
        "offerCount": 3,
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {
            "@type": "Organization",
            "name": BRAND,
            "url": SITE_URL + "/"
        },
        "shippingDetails": {
            "@type": "OfferShippingDetails",
            "shippingRate": {
                "@type": "MonetaryAmount",
                "value": SHIPPING_FEE_JPY,
                "currency": "JPY",
            },
            "shippingDestination": {
                "@type": "DefinedRegion",
                "addressCountry": "JP",
            },
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {
                    "@type": "QuantitativeValue",
                    "minValue": MIN_FULFILLMENT_DAYS,
                    "maxValue": MAX_FULFILLMENT_DAYS,
                    "unitCode": "DAY",
                },
                "transitTime": {
                    "@type": "QuantitativeValue",
                    "minValue": 1,
                    "maxValue": 3,
                    "unitCode": "DAY",
                },
            },
        },
        "hasMerchantReturnPolicy": {
            "@type": "MerchantReturnPolicy",
            "applicableCountry": "JP",
            "returnPolicyCategory": "https://schema.org/MerchantReturnNotPermitted",
            "merchantReturnLink": SITE_URL + "/returns/",
        },
    }
    
    product_schema = {
        "@type": "Product",
        "name": name,
        "sku": str(product.get("id") or slug),
        "mpn": "TS-" + str(product.get("id") or slug).upper(),
        "category": "Sporting Goods > Team Sports > Soccer > Soccer Uniforms",
        "description": description,
        "image": [absolute_url(x) for x in gallery],
        "brand": {"@type": "Brand", "name": BRAND},
        "offers": offer,
    }
    product_schema.update(review_schema(combined_reviews))

    breadcrumb_schema = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "ホーム",
                "item": SITE_URL + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "サッカーウェア",
                "item": SITE_URL + "/collections/football/",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": name,
                "item": SITE_URL + path,
            },
        ],
    }

    faq_schema = {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "上下セットの価格（¥4,800）にはパンツやプリント代も含まれていますか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "はい、表示価格4,800円にシャツ、試合用ハーフパンツ、チーム名・背番号・胸ロゴ等のフル昇華プリント代がすべて含まれております。デザイン作成費も無料ですので、追加料金は一切発生いたしません。（シャツ単品 ¥3,500 / パンツ単品 ¥2,000）",
                },
            },
            {
                "@type": "Question",
                "name": "1枚からでも注文可能ですか？追加注文の価格はどうなりますか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "はい、TEAMSPIRIT-JPでは1枚からでも同一のセール価格（上下セット¥4,800 / シャツ単品¥3,500 / パンツ単品¥2,000）でご注文いただけます。新規メンバー加入時などの1枚単位の追加注文も、初回と同じ割引価格でいつでも承ります。",
                },
            },
            {
                "@type": "Question",
                "name": "納期はどのくらいかかりますか？大会や合宿に間に合わせたいです。",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "デザイン確定および決済確認後、通常約2〜3週間（14〜21営業日）でお手元にお届けいたします。大会日程や合宿等でお急ぎの場合は、スケジュールに合わせて特急製作のご相談も公式LINEにて承っております。",
                },
            },
            {
                "@type": "Question",
                "name": "背番号やチームロゴのデザインデータはどうやって送ればいいですか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "手書きのスケッチ、写真、スマホのスクリーンショット、Illustrator(AI)やPDFなどのデータを公式LINEへ直接お送りいただくだけで大丈夫です。専任デザイナーが最短即日で完成予想図（3Dイメージ）を作成いたします。",
                },
            },
            {
                "@type": "Question",
                "name": "サイズ選びが心配です。大人とキッズのサイズ展開はどうなっていますか？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "大人用（S〜4XL）に加え、ジュニア・キッズ用（120〜160cm）を幅広くご用意しております。商品詳細ページの実寸表（着丈・身幅・総丈・ウエスト）をご確認いただくか、公式LINEにて身長・体重をご相談いただければ最適なサイズをご案内いたします。",
                },
            },
        ],
    }

    schema = {
        "@context": "https://schema.org",
        "@graph": [product_schema, breadcrumb_schema, faq_schema],
    }

    order_head = '<link rel="stylesheet" href="/assets/order-flow.css?v=20260814-1">'
    order_scripts = '<script src="/assets/order-config.js"></script><script src="/assets/order-flow.js?v=20260814-1" defer></script>'
    page_title = f"{name} | サッカーユニフォーム オーダー・上下セット | TEAMSPIRIT-JP"
    return path, page(page_title, description, path, body, schema, site, extra_head=order_head, extra_scripts=order_scripts)


COLLECTIONS = {
    "all-products": ("全商品", "TEAMSPIRIT-JPのカスタムサッカーユニフォームと団体チームウェアをご覧ください。"),
    "custom": ("カスタムユニフォーム", "チームロゴ、カラー、背番号を反映できるカスタムユニフォームです。"),
    "football": ("サッカーウェア", "サッカーチームやクラブ向けの団体ユニフォームをご覧ください。"),
    "accessory": ("アクセサリー", "チーム活動やトレーニングに必要なスポーツアクセサリーです。"),
    "uniform": ("ユニフォーム", "団体注文に対応するユニフォーム商品一覧です。"),
    "halfzip": ("ハーフジップ", "トレーニングや移動に適したハーフジップ商品一覧です。"),
    "trackjacket": ("トラックジャケット", "団体チームウェアとして製作できるトラックジャケットです。"),
    "windbreaker": ("ウィンドブレーカー", "チーム向けにカスタム製作できるウィンドブレーカーです。"),
    "paddedvest": ("中綿ベスト", "冬季チームウェア用の中綿ベスト商品一覧です。"),
}


def products_for_collection(products, slug):
    if slug == "all-products": return products
    exact = [p for p in products if slug in (p.get("collections") or []) or p.get("category") == slug]
    if exact: return exact
    if slug in ("custom", "football", "uniform"): return [p for p in products if p.get("category") in ("custom", "professional")]
    if slug == "accessory": return [p for p in products if p.get("category") == "popular"]
    return []


def collection_page(slug, products, site):
    label, description = COLLECTIONS[slug]
    selected = products_for_collection(products, slug)
    cards = "".join(product_card(p) for p in selected) or '<p class="empty">このカテゴリーには公開中の商品がありません。</p>'
    path = f"/collections/{slug}/"
    tabs = "".join(f'<a class="chip{(" active" if s == slug else "")}" href="/collections/{s}/">{escape(v[0])}</a>' for s,v in COLLECTIONS.items())
    body = f'<nav class="breadcrumbs" aria-label="現在位置"><a href="/">ホーム</a> / <a href="/collections/all-products/">カテゴリー</a> / {escape(label)}</nav><section class="page-heading"><p class="eyebrow">TEAMSPIRIT-JP COLLECTION</p><h1>{escape(label)}</h1><p>{escape(description)}</p></section><nav class="chips" aria-label="商品カテゴリー">{tabs}</nav><section class="product-grid">{cards}</section>'
    
    collection_schema = {
        "@type": "CollectionPage",
        "name": label,
        "description": description,
        "url": SITE_URL + path,
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "url": SITE_URL + f"/products/{slugify(p.get('id'))}/",
                    "name": product_name(p),
                }
                for i, p in enumerate(selected)
            ],
        },
    }
    
    breadcrumb_schema = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "ホーム",
                "item": SITE_URL + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": label,
                "item": SITE_URL + path,
            },
        ],
    }

    schema = {
        "@context": "https://schema.org",
        "@graph": [collection_schema, breadcrumb_schema],
    }
    page_title = f"{label} | カスタムサッカーユニフォーム・チームオーダー | TEAMSPIRIT-JP"
    meta_desc = f"{description} 1枚から上下セット4,800円（定価9,600円・パンツ＆昇華プリント代込み）。全国対応・LINEで簡単相談。"
    return path, page(page_title, meta_desc, path, body, schema, site)


BUSINESS_PAGES = {
    "about": ("私たちについて", "カスタムサッカーユニフォームと団体チームウェアを製作するTEAMSPIRIT-JPをご紹介します。", "TEAMSPIRIT-JPは、チームの個性をユニフォームに表現するカスタムスポーツウェアショップです。デザイン相談からロゴ・背番号の配置、製作案内までサポートします。"),
    "contact": ("お問い合わせ", "LINEまたはInstagramからカスタムユニフォーム製作をご相談ください。", "商品名、予定数量、希望カラー、チームロゴ、希望納期をご用意いただくとスムーズにご案内できます。下記の公式相談窓口をご利用ください。"),
    "shipping": ("配送について", "カスタム製作商品の送料、製作期間、配送手順をご案内します。", "送料は全国一律600円、10,000円以上のご注文で送料無料です。デザイン確定後に製作を開始し、製作・処理・配送を含む目安は約14〜21日です。"),
    "returns": ("返品・交換について", "カスタム製作商品の返品、交換、キャンセル条件をご確認ください。", "ロゴ、氏名、背番号などを個別に製作するため、製作開始後のお客様都合によるキャンセルや交換は制限される場合があります。誤配送や製作不良は、受取後すぐに写真と注文情報をお送りください。"),
    "privacy": ("プライバシーポリシー", "TEAMSPIRIT-JPウェブサイトの個人情報とブラウザ保存情報についてご案内します。", "このサイトはカートとお気に入り商品をブラウザ内に保存する場合があります。注文相談にはLINEまたはInstagramのプライバシーポリシーが適用されます。"),
    "tokushoho": ("特定商取引法に基づく表記", "特定商取引に関する法律に基づく事業者情報、販売価格、支払方法、配送期間および返品ポリシーを開示しています。", "TEAMSPIRIT-JPは特定商取引法を遵守し、透明性の高いサービスを提供しています。オーダーメイド製作のため、デザイン確定後のキャンセルは制限されます。不良品は到着後7日以内に無償交換いたします。"),
}


BLOGS = {
    "football-uniform-production": ("サッカーユニフォーム製作ガイド", "製作前に確認したいデザイン、生地、サイズ、団体注文の流れをご案内します。", ["チームカラーとロゴを決める", "選手ごとのサイズと背番号を整理する", "生地と動きやすさを確認する", "デザイン案を確認する", "製作日程と配送を確認する"]),
    "group-uniform-order": ("団体ユニフォームの注文方法", "団体注文を早く正確に進めるための準備をご紹介します。", ["注文担当者を決める", "メンバーとサイズをまとめる", "氏名と背番号を確認する", "数量別の見積もりを相談する", "最終デザインを承認する"]),
    "custom-football-uniform": ("カスタムサッカーユニフォームの選び方", "チームに合うカラー、パターン、マーキングの選び方です。", ["ホームとアウェイの色を分ける", "ロゴの見やすさを確保する", "背番号フォントを選ぶ", "スポンサー位置を整理する", "着用環境を考慮する"]),
    "teamwear-custom-production": ("チームウェア製作チェックリスト", "追加注文も考慮した確認事項をまとめました。", ["用途と季節を決める", "共通サイズ表を活用する", "サンプルや実寸を確認する", "追加注文の基準を決める", "洗濯と保管方法を共有する"]),
}


def content_page(slug, item, site, blog=False):
    title, description, content = item
    path = f"/blog/{slug}/" if blog else f"/{slug}/"
    if blog:
        sections = "".join(f"<section><h2>{i+1}. {escape(heading)}</h2><p>{escape(heading)}では、チーム内で情報を共有し、確定内容を一つの資料にまとめることが重要です。製作前にデザインと表記を再確認すると、修正や日程の遅れを減らせます。</p></section>" for i, heading in enumerate(content))
        body = f'<nav class="breadcrumbs" aria-label="現在位置"><a href="/">ホーム</a> / <a href="/blog/">ガイド</a> / {escape(title)}</nav><article class="article"><p class="eyebrow">TEAMSPIRIT-JP GUIDE</p><h1>{escape(title)}</h1><p class="lead">{escape(description)}</p>{sections}<section class="cta"><h2>カスタム製作相談</h2><p>商品、数量、希望日程をご用意のうえ、LINEまたはInstagramからお問い合わせください。</p></section></article>'
        main_schema = {
            "@type": "Article",
            "headline": title,
            "description": description,
            "url": SITE_URL + path,
            "inLanguage": "ja-JP",
            "author": {"@type": "Organization", "name": BRAND, "url": SITE_URL + "/"},
            "publisher": {"@type": "Organization", "name": BRAND, "url": SITE_URL + "/"},
            "datePublished": "2026-08-01",
            "dateModified": "2026-10-16",
        }
    else:
        if slug == "tokushoho":
            body = f'''<nav class="breadcrumbs" aria-label="現在位置"><a href="/">ホーム</a> / 特定商取引法に基づく表記</nav><article class="article legal-article"><p class="eyebrow">LEGAL INFORMATION</p><h1>特定商取引法に基づく表記</h1><p class="lead">「特定商取引に関する法律」第11条（通信販売についての広告）に基づき、以下の通り事業者情報および取引条件を開示いたします。</p><div class="legal-table-wrap"><table class="legal-table"><tbody>
            <tr><th>販売業者名</th><td>TEAMSPIRIT-JP（チームスピリット ジェイピー）</td></tr>
            <tr><th>運営統括責任者</th><td>田中 健一（代表責任者）</td></tr>
            <tr><th>所在地</th><td>〒150-0002 東京都渋谷区渋谷2-19-15</td></tr>
            <tr><th>電話番号</th><td>050-5806-5388<br><small class="muted">※お電話でのご注文受付・デザイン確認は聞き間違い防止のため承っておりません。公式LINEまたはメールでのお問い合わせを推奨しております。</small></td></tr>
            <tr><th>メールアドレス</th><td>shop@teamspiritsport.jp</td></tr>
            <tr><th>公式相談窓口</th><td>LINE公式アカウント: <a href="https://lin.ee/qE1TJJ5" target="_blank" rel="noopener">@teamspirit-jp</a>（受付: 24時間受付 / 返信: 平日10:00〜18:00）<br>Instagram公式: <a href="https://www.instagram.com/" target="_blank" rel="noopener">@teamspirit-jp</a></td></tr>
            <tr><th>販売価格</th><td>各商品詳細ページに表示（表示価格は消費税込み）。昇華プリント・デザイン作成費・背番号/チーム名マーキング費用は商品代金に含まれます。</td></tr>
            <tr><th>商品代金以外の必要料金</th><td>・配送料：全国一律600円（税込）。商品合計金額10,000円（税込）以上のご注文で送料無料。<br>・銀行振込手数料（銀行振込をご利用の場合、振込手数料はお客様負担となります）。</td></tr>
            <tr><th>お支払い方法</th><td>・クレジットカード決済（VISA, Mastercard, JCB, American Express）<br>・銀行振込（前払い）<br>・学校・公的団体・法人様向け請求書払い（後払い要事前相談）</td></tr>
            <tr><th>お支払い時期</th><td>・クレジットカード：各カード会社の引き落とし日<br>・銀行振込：デザイン最終確認完了後、製作開始前までにお振込み（前払い）</td></tr>
            <tr><th>商品の引き渡し時期</th><td>デザイン最終確定および決済確認後、通常約2〜3週間（14〜21営業日）でお届けいたします。※大会日程等による特急仕上げのご相談は事前にお問い合わせください。</td></tr>
            <tr><th>返品・交換・キャンセルについて</th><td>
              <p><b>【お客様都合によるキャンセル・返品】</b><br>
              当店で取り扱う商品は、お客様のご指定に合わせた完全オーダーメイド品（チーム名、背番号、エンブレム、個別カスタムプリント等）のため、デザイン確定・製作着手後のお客様都合によるキャンセル、仕様変更、返品、交換はお受けいたしかねます。</p>
              <p><b>【不良品・誤配送について】</b><br>
              万全を期して製造・検品を行っておりますが、万が一お届けした商品に縫製不良、プリント剥が延・ミス、生地の破損・著しい汚損、またはご注文内容と著しく異なる瑕疵があった場合は、商品到着後7日以内にメールまたは公式LINEより写真添付の上ご連絡ください。当店の全額負担（着払い）にて速やかに再製作・無償交換対応をさせていただきます。</p>
            </td></tr>
            <tr><th>不良品の返品送料</th><td>当店負担（着払いにてご返送ください）</td></tr>
            <tr><th>適格請求書発行事業者登録番号</th><td>登録済み（領収書・適格請求書インボイスの発行に対応しております）</td></tr>
            </tbody></table></div></article>'''
        elif slug == "about":
            body = f'''<nav class="breadcrumbs" aria-label="現在位置"><a href="/">ホーム</a> / 私たちについて</nav><article class="article"><p class="eyebrow">ABOUT TEAMSPIRIT-JP</p><h1>私たちについて</h1><p class="lead">TEAMSPIRIT-JPは、サッカー・フットサルチームのためのカスタムユニフォーム・チームウェア専門店です。</p><section><h2>情熱を纏う。チームだけの1着を。</h2><p>全国の社会人サッカーチーム、ジュニア・ユースクラブ、学校部活動、大学サークル、フットサルチームに向けて、ハイクオリティなフル昇華プリントユニフォームをお届けしています。デザイン作成費無料、背番号・チーム名・エンブレムプリント込みの明確なワンプライスで、初めてのチームオーダーでも安心してお任せいただけます。</p></section><section><h2>3つのこだわり</h2><div class="quality-feature-list"><div class="quality-feature-item"><h4>✨ 高機能マイクロメッシュ素材</h4><p>激しいプレーでもベタつかず、軽量で通気性・吸汗速乾性に優れたプロ仕様の生地を採用しています。</p></div><div class="quality-feature-item"><h4>🎨 剥がれないフル昇華転写プリント</h4><p>生地自体にインクを浸透させる昇華転写技術を採用。何度洗濯してもプリントがひび割れたり剥がれる心配がありません。</p></div><div class="quality-feature-item"><h4>💬 LINEで簡単マンツーマン対応</h4><p>手書きのラフ画やイメージ画像を送るだけで、専任デザイナーが最短即日で完成イメージを作成します。</p></div></div></section><section><h2>運営会社概要・事業者情報</h2><div class="legal-table-wrap"><table class="legal-table"><tbody><tr><th>屋号 / サービス名</th><td>TEAMSPIRIT-JP（チームスピリット ジェイピー）</td></tr><tr><th>運営統括責任者</th><td>田中 健一（代表責任者）</td></tr><tr><th>所在地</th><td>〒150-0002 東京都渋谷区渋谷2-19-15</td></tr><tr><th>電話番号</th><td>050-5806-5388</td></tr><tr><th>メールアドレス</th><td>shop@teamspiritsport.jp</td></tr><tr><th>公式LINE</th><td><a href="https://lin.ee/qE1TJJ5" target="_blank" rel="noopener">@teamspirit-jp</a></td></tr><tr><th>事業内容</th><td>オーダーメイドサッカー・フットサルユニフォーム、チームウェアの企画・昇華プリント製造・販売</td></tr><tr><th>法令遵守表記</th><td><a href="/tokushoho/" style="color:#38bdf8;text-decoration:underline;font-weight:600;">特定商取引法に基づく表記はこちら &gt;</a></td></tr></tbody></table></div></section></article>'''
        else:
            extra = f'<div class="contact-actions" aria-label="相談窓口"><a class="contact-icon kakao-icon" href="{escape(site.get("defaultLINELink") or SITE_URL + "/pages/line/", quote=True)}" target="_blank" rel="noopener" aria-label="LINE相談" title="LINE相談"><span class="talk-icon" aria-hidden="true">LINE</span></a><a class="contact-icon instagram-icon" href="{escape(site.get("defaultInstagramLink") or "https://www.instagram.com/", quote=True)}" target="_blank" rel="noopener" aria-label="Instagram相談" title="Instagram相談"><span class="ig-icon" aria-hidden="true"></span></a></div>' if slug == "contact" else ""
            body = f'<nav class="breadcrumbs" aria-label="現在位置"><a href="/">ホーム</a> / ご利用案内</nav><article class="article"><p class="eyebrow">TEAMSPIRIT-JP INFO</p><h1>{escape(title)}</h1><p class="lead">{escape(description)}</p><section><p>{escape(content)}</p></section>{extra}</article>'
        main_schema = {
            "@type": "WebPage",
            "name": title,
            "description": description,
            "url": SITE_URL + path,
            "inLanguage": "ja-JP",
            "publisher": {"@type": "Organization", "name": BRAND, "url": SITE_URL + "/"},
        }

    breadcrumb_schema = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "ホーム",
                "item": SITE_URL + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": title,
                "item": SITE_URL + path,
            },
        ],
    }

    schema = {
        "@context": "https://schema.org",
        "@graph": [main_schema, breadcrumb_schema],
    }
    page_title = f"{title} | TEAMSPIRIT-JP"
    return path, page(page_title, description, path, body, schema, site)


def generate_seo_pages(site_root: Path, site: dict):
    products = public_products(site)
    outputs = []
    
    # 1. Product Detail Pages
    for product in products:
        outputs.append(product_page(product, site))
        
    # 2. Collection Pages
    for slug in COLLECTIONS:
        outputs.append(collection_page(slug, products, site))
        
    # 3. Business & Content Pages
    for slug, item in BUSINESS_PAGES.items():
        outputs.append(content_page(slug, item, site))
        
    # 4. Blog Guides
    for slug, item in BLOGS.items():
        outputs.append(content_page(slug, item, site, blog=True))
        
    # 5. Blog Index Page
    blog_cards = "".join(f'<article class="product-card"><a href="/blog/{slug}/"><h2>{escape(item[0])}</h2><p>{escape(item[1])}</p></a></article>' for slug, item in BLOGS.items())
    blog_schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "name": "カスタムユニフォーム製作ガイド", "url": SITE_URL + "/blog/"},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "ホーム", "item": SITE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": "ガイド一覧", "item": SITE_URL + "/blog/"}
            ]}
        ]
    }
    outputs.append(("/blog/", page("カスタムユニフォーム製作ガイド | TEAMSPIRIT-JP", "サッカーユニフォーム製作と団体注文に必要なガイド・ノウハウをご覧ください。", "/blog/", f'<nav class="breadcrumbs" aria-label="現在位置"><a href="/">ホーム</a> / ガイド一覧</nav><section class="page-heading"><p class="eyebrow">TEAMSPIRIT-JP GUIDE</p><h1>カスタムユニフォーム製作ガイド</h1><p>ユニフォームの選び方、サイズ計測、団体注文の流れを分かりやすく解説します。</p></section><section class="article-grid">{blog_cards}</section>', blog_schema, site)))
    
    # Write all output files
    for path, html in outputs:
        target = site_root / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8", newline="\n")
        
    # Generate Google Image Sitemap compliant XML
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        f'  <url><loc>{SITE_URL}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>',
    ]
    
    # Add products with Google Image Sitemap tags
    for p in products:
        p_slug = slugify(p.get("id"))
        p_name = product_name(p)
        p_img = absolute_url(p.get("image") or "")
        xml.append('  <url>')
        xml.append(f'    <loc>{SITE_URL}/products/{p_slug}/</loc>')
        xml.append(f'    <lastmod>{today}</lastmod>')
        xml.append('    <changefreq>weekly</changefreq>')
        xml.append('    <priority>0.8</priority>')
        if p_img:
            xml.append('    <image:image>')
            xml.append(f'      <image:loc>{escape(p_img)}</image:loc>')
            xml.append(f'      <image:title>{escape(p_name)}</image:title>')
            xml.append(f'      <image:caption>{escape(p_name)} - オーダーサッカーユニフォーム上下セット4,800円</image:caption>')
            xml.append('    </image:image>')
        xml.append('  </url>')
        
    # Add collections
    for c_slug in COLLECTIONS:
        xml.append(f'  <url><loc>{SITE_URL}/collections/{c_slug}/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>')
        
    # Add blogs and business pages
    for b_slug in BLOGS:
        xml.append(f'  <url><loc>{SITE_URL}/blog/{b_slug}/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
    xml.append(f'  <url><loc>{SITE_URL}/blog/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
    
    for u_slug in BUSINESS_PAGES:
        xml.append(f'  <url><loc>{SITE_URL}/{u_slug}/</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>')
        
    # Add extra guide pages
    extra_pages = ["/pages/custom-uniform-order/", "/pages/color-font-guide/", "/pages/order-form-guide/", "/pages/team-custom-faq/"]
    for ep in extra_pages:
        xml.append(f'  <url><loc>{SITE_URL}{ep}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>')

    xml.append("</urlset>")
    (site_root / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")
    return [path for path, _ in outputs]
