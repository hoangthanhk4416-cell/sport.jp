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
DEFAULT_SIZE_OPTIONS = [
    "60(S)", "65(M)", "70(L)", "75(XL)", "80(2XL)", "85(3XL)",
    "90(S)", "95(M)", "100(L)", "105(XL)", "110(2XL)", "115(3XL)",
    "120(4XL)",
]


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
    original = str(product.get("oldPrice") or "")
    current = str(product.get("price") or "価格はお問い合わせください")
    discount = discount_percent(product)
    original_html = f'<del class="original-price">{escape(original)}</del>' if discount else '<span class="original-price is-empty" aria-hidden="true">—</span>'
    discount_html = f'<span class="discount-rate">{discount}%</span>' if discount else '<span class="discount-rate is-empty" aria-hidden="true">—</span>'
    return f'<div class="{class_name}">{original_html}{discount_html}<strong class="current-price">{escape(current)}</strong></div>'


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


def product_name(product):
    return str(product.get("name") or product.get("id") or "TEAMSPIRIT-JP 商品")


def product_description(product):
    name = product_name(product)
    category = str(product.get("category") or "custom")
    descriptions = {
        "custom": f"{name}は、チームカラー・ロゴ・背番号に合わせて製作できるカスタムサッカーユニフォームです。デザインと数量はLINEまたはInstagramでご相談ください。",
        "professional": f"{name}のデザイン、サイズ、注文情報をご確認ください。サッカーチームやクラブ向けのカスタムユニフォーム製作をご案内します。",
        "popular": f"{name}の商品情報とサイズをご確認ください。団体チームウェアのカスタム注文はTEAMSPIRIT-JPへご相談ください。",
    }
    return descriptions.get(category, f"{name}の商品情報、サイズ、団体注文方法をご確認ください。TEAMSPIRIT-JPのカスタムスポーツウェアです。")


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
    phone = escape(site.get("footerPhone") or "LINE相談")
    footer_text = escape(site.get("footerText") or "맞춤 축구 유니폼·단체 팀복 제작 전문 스토어")
    return f"""<footer class=\"footer\"><div class=\"footer-wrap foot\"><section><h3>TEAMSPIRIT-JP</h3><nav class=\"foot-links\" aria-label=\"ショップ情報\"><a href=\"/about/\">私たちについて</a><a href=\"/contact/\">お問い合わせ</a><a href=\"/shipping/\">配送について</a><a href=\"/returns/\">返品・交換</a><a href=\"/privacy/\">プライバシーポリシー</a><a href=\"/blog/\">ブログ</a><a href=\"/pages/custom-uniform-order/\">ユニフォーム注文</a><a href=\"/pages/color-font-guide/\">カラー・フォント</a><a href=\"/pages/order-form-guide/\">注文書の書き方</a><a href=\"/pages/team-custom-faq/\">FAQ</a></nav><div class=\"foot-details\"><b>ショップ</b> TEAMSPIRIT-JP &nbsp; | &nbsp; <b>お問い合わせ</b> {phone}<br>{footer_text}</div></section><section class=\"foot-service\"><h4>カスタマーサポート</h4><strong>{phone}</strong><p>平日 10:00 - 17:00<br>休憩 13:00 - 14:00<br>土日祝日は休業</p></section><section><h4>SNS</h4><nav class=\"foot-sns\" aria-label=\"SNS\"><a href=\"{instagram}\" target=\"_blank\" rel=\"noopener\"><span class=\"sns-icon instagram\">◎</span><span>Instagram</span></a><a href=\"{line}\" target=\"_blank\" rel=\"noopener\"><span class=\"sns-icon kakao\">LINE</span><span>LINE</span></a><a href=\"{youtube}\" target=\"_blank\" rel=\"noopener\"><span class=\"sns-icon youtube\"><svg viewBox=\"0 0 24 17\" aria-hidden=\"true\"><path d=\"M23.5 2.7A3 3 0 0 0 21.4.6C19.5 0 12 0 12 0S4.5 0 2.6.6A3 3 0 0 0 .5 2.7 31 31 0 0 0 0 8.5a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1C4.5 17 12 17 12 17s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-5.8 31 31 0 0 0-.5-5.8ZM9.6 12.1V4.9l6.3 3.6-6.3 3.6Z\"/></svg></span><span>YouTube</span></a></nav></section></div><div class=\"footer-wrap foot-bottom\">安全な注文相談サービスをご提供しています。<br>Copyright © TEAMSPIRIT-JP. All rights reserved.<div class=\"foot-copyright\">COPYRIGHT © 2026 BY TEAMSPIRIT SPORT</div></div></footer>"""


def page(title, description, canonical_path, body, schema, site, robots="index,follow", extra_head="", extra_scripts=""):
    canonical = SITE_URL + canonical_path
    encoded_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    schema_image = schema.get("image") if isinstance(schema, dict) else None
    if isinstance(schema_image, list):
        schema_image = schema_image[0] if schema_image else ""
    image_meta = f'<meta property="og:image" content="{escape(str(schema_image), quote=True)}"><meta name="twitter:card" content="summary_large_image">' if schema_image else '<meta name="twitter:card" content="summary">'
    image_meta = '<link rel="stylesheet" href="/assets/contact-icons.css"><link rel="stylesheet" href="/assets/support-chat.css?v=20260815-10">' + image_meta
    og_type = "product" if schema.get("@type") == "Product" else "website"
    support_scripts = '<script src="/assets/support-chat-config.js?v=20260815-9"></script><script src="/assets/support-chat.js?v=20260815-9" defer></script>'
    return f"""<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(title)}</title><meta name=\"description\" content=\"{escape(description, quote=True)}\"><meta name=\"robots\" content=\"{robots}\"><link rel=\"canonical\" href=\"{canonical}\"><link rel=\"icon\" href=\"/assets/favicon.svg\"><link rel=\"stylesheet\" href=\"/assets/seo-pages.css?v=20260815-2\">{extra_head}<meta property=\"og:type\" content=\"{og_type}\"><meta property=\"og:site_name\" content=\"TEAMSPIRIT-JP\"><meta property=\"og:title\" content=\"{escape(title, quote=True)}\"><meta property=\"og:description\" content=\"{escape(description, quote=True)}\"><meta property=\"og:url\" content=\"{canonical}\">{image_meta}<script type=\"application/ld+json\">{encoded_schema}</script></head><body>{header()}<main>{body}</main>{footer(site)}{extra_scripts}{support_scripts}</body></html>"""


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
        f'<button class="product-thumbnail{(" active" if i == 0 else "")}" type="button" data-gallery-src="{escape(x, quote=True)}" aria-label="商品画像 {i+1} を表示"><img src="{escape(x, quote=True)}" width="120" height="120" loading="lazy" decoding="async" alt="{escape(name, quote=True)} プレビュー {i+1}"></button>'
        for i, x in enumerate(gallery)
    )
    gallery_html = f'<div class="product-gallery-main"><img id="productMainImage" src="{escape(main_image, quote=True)}" width="900" height="900" decoding="async" alt="{escape(name, quote=True)} メイン画像"></div><div class="product-thumbnails" aria-label="商品画像を選択">{gallery_thumbs}</div>'
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
        + '<p class="muted">サイズは測定方法により、1〜2cm程度の誤差が生じる場合があります。体型や着用スタイルにより、個人差が生じる場合があります。</p>'
    )
    reviews = normalized_reviews(product)
    review_html = "".join(
        f'<article class="review">'
        f'<div class="review-rating" aria-label="{("5点満点中" + str(r["stars"]) + "点") if r["stars"] else "レビュー"}">{("★" * r["stars"]) if r["stars"] else "レビュー"}</div>'
        f'<p>{escape(r["text"])}</p>'
        f'<small>{escape(r["author"])}{(" · " + escape(r["date"])) if r["date"] else ""}</small>'
        f'</article>'
        for r in reviews
    ) or '<p class="muted">登録済みの購入レビューはまだありません。</p>'
    line_link = escape(product.get('lineLink') or site.get('defaultLINELink') or f'{SITE_URL}/pages/line/', quote=True)
    instagram_link = escape(product.get('instagramLink') or site.get('defaultInstagramLink') or 'https://www.instagram.com/', quote=True)
    contact_icons = f'<div class="contact-order-actions" aria-label="注文相談"><a class="contact-order line-order" href="{line_link}" target="_blank" rel="noopener"><span class="talk-icon" aria-hidden="true"></span><span>LINEで相談</span></a><a class="contact-order instagram-order" href="{instagram_link}" target="_blank" rel="noopener"><span class="ig-icon" aria-hidden="true"></span><span>Instagramで相談</span></a></div>'
    size_options = product.get("sizes") or DEFAULT_SIZE_OPTIONS
    size_buttons = "".join(f'<button class="product-size" type="button" data-size="{escape(str(size), quote=True)}">{escape(str(size))}</button>' for size in size_options)
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
    commerce = f'''<section class="product-options" aria-labelledby="productOptionsTitle"><h2 id="productOptionsTitle">オプション選択</h2><div class="option-row"><b>サイズ</b><div class="product-size-list">{size_buttons}</div></div><div class="option-row quantity-row"><label for="productQuantity"><b>数量</b></label><div class="quantity-control"><button type="button" data-quantity-change="-1" aria-label="数量を減らす">−</button><input id="productQuantity" type="number" min="1" max="99" value="1" inputmode="numeric"><button type="button" data-quantity-change="1" aria-label="数量を増やす">+</button></div></div><div class="selection-summary"><span id="selectedOption">サイズを選択してください。</span><strong>{escape(str(product.get('price') or '価格はお問い合わせください'))}</strong></div></section>{contact_icons}'''
    commerce_script = '''<script>(()=>{let selectedSize="";document.querySelectorAll(".product-thumbnail").forEach(button=>button.addEventListener("click",()=>{document.getElementById("productMainImage").src=button.dataset.gallerySrc;document.querySelectorAll(".product-thumbnail").forEach(item=>item.classList.remove("active"));button.classList.add("active")}));document.querySelectorAll(".product-size").forEach(button=>button.addEventListener("click",()=>{selectedSize=button.dataset.size;document.querySelectorAll(".product-size").forEach(item=>item.classList.remove("active"));button.classList.add("active");document.getElementById("selectedOption").textContent=`選択サイズ: ${selectedSize}`}));document.querySelectorAll("[data-quantity-change]").forEach(button=>button.addEventListener("click",()=>{const input=document.getElementById("productQuantity");input.value=Math.max(1,Math.min(99,Number(input.value||1)+Number(button.dataset.quantityChange)))}))})();</script>'''
    body = f"""<nav class=\"breadcrumbs\" aria-label=\"現在位置\"><a href=\"/\">ホーム</a> / <a href=\"/collections/all-products/\">商品</a> / {escape(name)}</nav><article class=\"product-detail\"><section class=\"product-gallery\">{gallery_html}</section><section class=\"product-info\"><p class=\"eyebrow\">TEAMSPIRIT-JP COLLECTION</p><h1>{escape(name)}</h1><p class=\"lead\">{escape(description)}</p>{pricing}<p>チームロゴ、背番号、カラー、団体数量はご相談後に製作します。</p>{commerce}</section></article><section class=\"content-section\"><h2>{escape(name)} 詳細情報</h2><p>{escape(description)}</p>{uniform_size_tables}<h2>注文・配送について</h2><p>送料は600円、10,000円以上のご注文で送料無料です。製作・処理・配送を含む目安は約3〜9日です。</p><h2>商品レビュー</h2>{review_html}</section>{commerce_script}"""
    body = (body
        .replace("개", "点")
        .replace("삭제", "削除")
        .replace("장바구니가 비어 있습니다.", "カートは空です。")
        .replace("총 상품수량:", "合計数量:")
        .replace("선택 사이즈:", "選択サイズ:")
        .replace("사이즈를 먼저 선택해 주세요.", "先にサイズを選択してください。")
        .replace("장바구니에 상품을 담았습니다.", "商品をカートに追加しました。"))
    offer = {
        "@type": "Offer",
        "url": SITE_URL + path,
        "priceCurrency": "JPY",
        "price": price_number(product.get("price")),
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
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
                    "minValue": 0,
                    "maxValue": 0,
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
    schema = {"@context":"https://schema.org","@type":"Product","name":name,"sku":str(product.get("id") or slug),"description":description,"image":[absolute_url(x) for x in gallery],"brand":{"@type":"Brand","name":BRAND},"offers":offer}
    schema.update(review_schema(reviews))
    order_head = '<link rel="stylesheet" href="/assets/order-flow.css?v=20260814-1">'
    order_scripts = '<script src="/assets/order-config.js"></script><script src="/assets/order-flow.js?v=20260814-1" defer></script>'
    return path, page(f"{name} | TEAMSPIRIT-JP", description, path, body, schema, site, extra_head=order_head, extra_scripts=order_scripts)


COLLECTIONS = {
    "all-products": ("全商品", "TEAMSPIRIT-JPのカスタムサッカーユニフォームと団体チームウェアをご覧ください。"),
    "custom": ("カスタムユニフォーム", "チームロゴ、カラー、背番号を反映できるカスタムユニフォームです。"),
    "football": ("サッカーウェア", "サッカーチームやクラブ向けの団体ユニフォームをご覧ください。"),
    "accessory": ("アクセサリー", "チーム活動やトレーニングに必要なスポーツアクセサリーです。"),
    "uniform": ("ユニフォーム", "団体注文に対応するユニフォーム商品一覧です。"),
    "halfzip": ("ハーフジップ", "トレーニングや移動に適したハーフジップ商品一覧です。"),
    "trackjacket": ("トラックジャケット", "団体チームウェアとして製作できるトラックジャケットです。"),
    "windbreaker": ("ウィンドブレーカー", "チーム向けにカスタム製作できるウィンドブレーカーです。"),
    "paddedvest": ("패딩베스트", "겨울 팀복용 패딩베스트 상품 목록입니다."),
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
    body = f'<nav class="breadcrumbs"><a href="/">ホーム</a> / カテゴリー</nav><section class="page-heading"><p class="eyebrow">TEAMSPIRIT-JP COLLECTION</p><h1>{escape(label)}</h1><p>{escape(description)}</p></section><nav class="chips" aria-label="商品カテゴリー">{tabs}</nav><section class="product-grid">{cards}</section>'
    schema = {"@context":"https://schema.org","@type":"CollectionPage","name":label,"description":description,"url":SITE_URL+path,"mainEntity":{"@type":"ItemList","itemListElement":[{"@type":"ListItem","position":i+1,"url":SITE_URL+f"/products/{slugify(p.get('id'))}/","name":product_name(p)} for i,p in enumerate(selected)]}}
    return path, page(f"{label} | TEAMSPIRIT-JP", description, path, body, schema, site)


BUSINESS_PAGES = {
    "about": ("TEAMSPIRIT-JPについて", "カスタムサッカーユニフォームと団体チームウェアを製作するTEAMSPIRIT-JPをご紹介します。", "TEAMSPIRIT-JPは、チームの個性をユニフォームに表現するカスタムスポーツウェアショップです。デザイン相談からロゴ・背番号の配置、製作案内までサポートします。"),
    "contact": ("お問い合わせ", "LINEまたはInstagramからカスタムユニフォーム製作をご相談ください。", "商品名、予定数量、希望カラー、チームロゴ、希望納期をご用意いただくとスムーズにご案内できます。下記の公式相談窓口をご利用ください。"),
    "shipping": ("配送について", "カスタム製作商品の送料、製作期間、配送手順をご案内します。", "送料は600円、10,000円以上のご注文で送料無料です。デザイン確定後に製作を開始し、製作・処理・配送を含む目安は約3〜9日です。"),
    "returns": ("返品・交換について", "カスタム製作商品の返品、交換、キャンセル条件をご確認ください。", "ロゴ、氏名、背番号などを個別に製作するため、製作開始後のお客様都合によるキャンセルや交換は制限される場合があります。誤配送や製作不良は、受取後すぐに写真と注文情報をお送りください。"),
    "privacy": ("プライバシーポリシー", "TEAMSPIRIT-JPウェブサイトの個人情報とブラウザ保存情報についてご案内します。", "このサイトはカートとお気に入り商品をブラウザ内に保存する場合があります。注文相談にはLINEまたはInstagramのプライバシーポリシーが適用されます。"),
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
        body = f'<nav class="breadcrumbs"><a href="/">ホーム</a> / <a href="/blog/">ガイド</a></nav><article class="article"><p class="eyebrow">TEAMSPIRIT-JP GUIDE</p><h1>{escape(title)}</h1><p class="lead">{escape(description)}</p>{sections}<section class="cta"><h2>カスタム製作相談</h2><p>商品、数量、希望日程をご用意のうえ、LINEまたはInstagramからお問い合わせください。</p></section></article>'
        schema_type = "Article"
    else:
        extra = f'<div class="contact-actions" aria-label="相談窓口"><a class="contact-icon kakao-icon" href="{escape(site.get("defaultLINELink") or SITE_URL + "/pages/line/", quote=True)}" target="_blank" rel="noopener" aria-label="LINE相談" title="LINE相談"><span class="talk-icon" aria-hidden="true">LINE</span></a><a class="contact-icon instagram-icon" href="{escape(site.get("defaultInstagramLink") or "https://www.instagram.com/", quote=True)}" target="_blank" rel="noopener" aria-label="Instagram相談" title="Instagram相談"><span class="ig-icon" aria-hidden="true"></span></a></div>' if slug == "contact" else ""
        body = f'<nav class="breadcrumbs"><a href="/">ホーム</a> / ご利用案内</nav><article class="article"><p class="eyebrow">TEAMSPIRIT-JP INFO</p><h1>{escape(title)}</h1><p class="lead">{escape(description)}</p><section><p>{escape(content)}</p></section>{extra}</article>'
        schema_type = "WebPage"
    schema = {"@context":"https://schema.org","@type":schema_type,"name":title,"headline":title,"description":description,"url":SITE_URL+path,"inLanguage":"ja-JP","publisher":{"@type":"Organization","name":BRAND,"url":SITE_URL+"/"}}
    return path, page(f"{title} | TEAMSPIRIT-JP", description, path, body, schema, site)


def generate_seo_pages(site_root: Path, site: dict):
    products = public_products(site)
    outputs = []
    for product in products:
        outputs.append(product_page(product, site))
    for slug in COLLECTIONS:
        outputs.append(collection_page(slug, products, site))
    for slug, item in BUSINESS_PAGES.items():
        outputs.append(content_page(slug, item, site))
    for slug, item in BLOGS.items():
        outputs.append(content_page(slug, item, site, blog=True))
    blog_cards = "".join(f'<article><a href="/blog/{slug}/"><h2>{escape(item[0])}</h2><p>{escape(item[1])}</p></a></article>' for slug,item in BLOGS.items())
    blog_schema = {"@context":"https://schema.org","@type":"CollectionPage","name":"カスタムユニフォーム製作ガイド","url":SITE_URL+"/blog/"}
    outputs.append(("/blog/", page("カスタムユニフォーム製作ガイド | TEAMSPIRIT-JP", "サッカーユニフォーム製作と団体注文に必要なガイドをご覧ください。", "/blog/", f'<section class="page-heading"><p class="eyebrow">TEAMSPIRIT-JP GUIDE</p><h1>カスタムユニフォーム製作ガイド</h1></section><section class="article-grid">{blog_cards}</section>', blog_schema, site)))
    for path, html in outputs:
        target = site_root / path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8", newline="\n")
    urls = ["/", *[path for path,_ in outputs], "/pages/custom-uniform-order/", "/pages/color-font-guide/", "/pages/order-form-guide/", "/pages/team-custom-faq/"]
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in dict.fromkeys(urls):
        xml.append(f"  <url><loc>{SITE_URL}{path}</loc><lastmod>{today}</lastmod></url>")
    xml.append("</urlset>")
    (site_root / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")
    return [path for path,_ in outputs]
