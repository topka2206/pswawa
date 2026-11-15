#!/usr/bin/env python3
"""
Сборка сайта ps.wawa → папка dist/ (готовый статичный HTML).

Запуск:  pip install -r requirements.txt && python3 _src/build.py
На Netlify запускается автоматически при каждом изменении (см. netlify.toml).

Где что лежит:
  content/       — данные, которые правятся через админку /admin: цены, FAQ, игры, настройки
  templates/     — разметка и тексты страниц (ru/, uk/, en/) + ui.<lang>.json (подписи, title, description)
  static/        — стили, скрипты, шрифты, картинки; копируются в dist как есть
"""
import json, re, shutil, datetime, pathlib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
LANGS = ["ru", "uk", "en"]
DEFAULT_LANG = "ru"

# Адреса страниц на каждом языке
SLUGS = {
    "home":     {"ru": "",                        "uk": "",                        "en": ""},
    "consoles": {"ru": "arenda-ps5-varshava/",    "uk": "orenda-ps5-varshava/",    "en": "ps5-rental-warsaw/"},
    "gta":      {"ru": "arenda-ps5-gta-6-varshava/", "uk": "orenda-ps5-gta-6-varshava/", "en": "gta-6-ps5-rental-warsaw/"},
    "vr":       {"ru": "arenda-ps-vr2-varshava/", "uk": "orenda-ps-vr2-varshava/", "en": "ps-vr2-rental-warsaw/"},
    "hookah":   {"ru": "kalyan-na-dom-varshava/", "uk": "kalyan-dodomu-varshava/", "en": "hookah-delivery-warsaw/"},
    "games":    {"ru": "igry/",                   "uk": "igry/",                   "en": "games/"},
    "terms":    {"ru": "usloviya/",               "uk": "umovy/",                  "en": "terms-faq/"},
}
PAGE_KEYS = list(SLUGS)


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


settings = load("content/settings.json")
prices = load("content/prices.json")
games = load("content/games.json")["games"]
SITE = settings["domain"].rstrip("/")
TODAY = datetime.date.today().isoformat()

# Языки, для которых уже есть шаблоны
ENABLED = [l for l in LANGS if (ROOT / f"templates/{l}/home.j2").exists()]

# ---------- SVG: логотип и спрайт вставляются прямо в HTML (быстрее, без лишних запросов) ----------
LOGO = (ROOT / "_src/logo.svg").read_text(encoding="utf-8")
SPRITE = (ROOT / "static/assets/svg/sprite.svg").read_text(encoding="utf-8")
SPRITE = re.sub(r"\s*<!--.*?-->", "", SPRITE, flags=re.S).replace('xmlns="http://www.w3.org/2000/svg" ', "")


def url(key, lang, absolute=False):
    path = f"/{lang}/{SLUGS[key][lang]}"
    return SITE + path if absolute else path


def zl(n):
    """Число → «80». None → None (шаблон покажет «в Direct»)."""
    if n is None:
        return None
    return str(int(n)) if float(n).is_integer() else str(n)


def all_prices():
    vals = [c[k] for c in prices["consoles"] for k in ("d1",) if c.get(k)]
    vals += [prices["vr"]["d1"], prices["hookah"]["d1"]]
    tops = [c.get("d7") for c in prices["consoles"] if c.get("d7")]
    return min(vals), max(vals + tops)


# ---------- JSON-LD ----------
def offer(name, url_, price, extra=None):
    o = {
        "@type": "Offer", "name": name, "url": url_, "price": zl(price), "priceCurrency": "PLN",
        "priceSpecification": {"@type": "UnitPriceSpecification", "price": zl(price), "priceCurrency": "PLN",
                               "unitText": "DAY", "unitCode": "DAY"},
        "availability": "https://schema.org/InStock",
        "areaServed": {"@type": "City", "name": "Warszawa"},
    }
    if extra:
        o.update(extra)
    return o


def offers_for(key, lang, ui):
    names = ui["offer_names"]
    out = []
    if key in ("home", "consoles"):
        for c in prices["consoles"]:
            out.append(offer(names[c["id"]], url("consoles", lang, True), c["d1"]))
    if key == "gta":
        for c in prices["consoles"]:
            if c["id"] in ("ps5", "ps5pro"):
                out.append(offer(names["gta_" + c["id"]], url("gta", lang, True), c["d1"]))
    if key in ("home", "vr"):
        out.append(offer(names["vr2"], url("vr", lang, True), prices["vr"]["d1"]))
    if key in ("home", "hookah"):
        out.append(offer(names["hookah"], url("hookah", lang, True), prices["hookah"]["d1"],
                         {"eligibleCustomerType": "18+"}))
    return out


def jsonld(key, lang, ui, faq_items):
    lo, hi = all_prices()
    biz_id = f"{SITE}/#business"
    graph = [{
        "@type": "LocalBusiness", "@id": biz_id, "name": "ps.wawa",
        "alternateName": ["ps wawa", "PS Wawa"],
        "description": ui["business_description"], "slogan": ui["slogan"],
        "url": url("home", lang, True), "logo": f"{SITE}/assets/img/logo-512.png",
        "image": f"{SITE}/assets/img/og/{lang}-home.jpg",
        "sameAs": [settings["instagram_profile"]],
        "areaServed": {"@type": "City", "name": "Warszawa", "sameAs": "https://www.wikidata.org/wiki/Q270"},
        "address": {"@type": "PostalAddress", "addressLocality": "Warszawa", "addressCountry": "PL"},
        "priceRange": f"{lo}–{hi} zł", "currenciesAccepted": "PLN",
        "knowsLanguage": ["ru", "uk", "en"],
        "contactPoint": {"@type": "ContactPoint", "contactType": "customer service",
                         "url": settings["instagram_dm"], "availableLanguage": ["Russian", "Ukrainian", "English"]},
        # openingHours — [УТОЧНИТЬ] добавить, когда будут часы работы
    }]
    if key == "home":
        graph[0]["hasOfferCatalog"] = {"@type": "OfferCatalog", "name": ui["pages"]["home"]["og_title"],
                                       "itemListElement": offers_for("home", lang, ui)}
        graph.append({"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/", "name": "ps.wawa",
                      "inLanguage": ENABLED, "publisher": {"@id": biz_id}})
    page_url = url(key, lang, True)
    graph.append({"@type": "WebPage", "@id": page_url + "#webpage", "url": page_url,
                  "name": ui["pages"][key]["title"], "inLanguage": lang,
                  "isPartOf": {"@id": f"{SITE}/#website"}, "about": {"@id": biz_id}})
    if key in ("consoles", "gta", "vr", "hookah"):
        graph.append({"@type": "Service", "name": ui["pages"][key]["og_title"], "serviceType": ui["pages"][key]["crumb"],
                      "provider": {"@id": biz_id}, "areaServed": {"@type": "City", "name": "Warszawa"},
                      "url": page_url, "offers": offers_for(key, lang, ui)})
    if key != "home":
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": ui["breadcrumb_home"], "item": url("home", lang, True)},
            {"@type": "ListItem", "position": 2, "name": ui["pages"][key]["crumb"], "item": page_url}]})
    if faq_items:
        graph.append({"@type": "FAQPage", "@id": page_url + "#faq", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faq_items]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)


# ---------- Рендер ----------
env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), undefined=StrictUndefined,
                  autoescape=True, trim_blocks=True, lstrip_blocks=True)
env.filters["zl"] = zl


def render_lang(lang):
    ui = load(f"templates/ui.{lang}.json")
    faq_all = load(f"content/faq.{lang}.json")["items"]
    out_pages = []
    for key in PAGE_KEYS + ["404"]:
        tpl_path = f"{lang}/{key}.j2"
        if not (ROOT / "templates" / tpl_path).exists():
            continue
        if key == "404":
            faq_items = []
        elif key == "terms":
            faq_items = faq_all
        else:
            faq_items = [f for f in faq_all if key in f.get("pages", [])]
        if key != "home" and key != "404" and not settings["blocks"].get("faq", True) and key != "terms":
            faq_items = []
        if key == "home" and not settings["blocks"].get("faq", True):
            faq_items = []
        alternates = {l: url(key, l, True) for l in ENABLED} if key != "404" else {}
        ctx = dict(
            lang=lang, key=key, ui=ui, page=ui["pages"][key], settings=settings, prices=prices, games=games,
            faq=faq_items, alternates=alternates, enabled_langs=ENABLED, default_lang=DEFAULT_LANG,
            url=lambda k, l=lang: url(k, l), abs_url=lambda k, l=lang: url(k, l, True),
            page_url=url(key, lang, True) if key != "404" else None, slugs=SLUGS,
            jsonld=Markup(jsonld(key, lang, ui, faq_items)) if key != "404" else None,
            LOGO=Markup(LOGO), LOGO_DECOR=Markup(LOGO.replace('role="img" aria-label="ps.wawa"', 'aria-hidden="true"')),
            SPRITE=Markup(SPRITE), site=SITE,
        )
        html = env.get_template(tpl_path).render(**ctx)
        target = DIST / lang / ("404.html" if key == "404" else SLUGS[key][lang] + "index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        if key != "404":
            out_pages.append(key)
    return out_pages


def write_meta_files():
    # sitemap.xml с hreflang-альтернативами
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for key in PAGE_KEYS:
        for l in ENABLED:
            rows.append(f"  <url><loc>{url(key, l, True)}</loc><lastmod>{TODAY}</lastmod>")
            for l2 in ENABLED:
                rows.append(f'    <xhtml:link rel="alternate" hreflang="{l2}" href="{url(key, l2, True)}"/>')
            rows.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url(key, DEFAULT_LANG, True)}"/>')
            rows.append("  </url>")
    rows.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # robots.txt — открыт для поисковиков и AI-ассистентов
    (DIST / "robots.txt").write_text(
        "# ps.wawa — открыты для поисковиков и AI-ассистентов\nUser-agent: *\nAllow: /\nDisallow: /admin/\n\n"
        + "".join(f"User-agent: {b}\nAllow: /\nDisallow: /admin/\n\n" for b in
                  ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Claude-SearchBot", "Claude-User",
                   "Google-Extended", "Applebot", "Bingbot"])
        + f"Sitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    # llms.txt — короткая справка для AI (цены берутся из content/prices.json)
    P = prices
    lines = ["# ps.wawa", "",
             f"> Аренда игровых приставок (PS5, PS5 Pro, PS4 Pro, Xbox), шлема PS VR2 и кальянов с доставкой на дом по Варшаве (Польша). "
             f"Привозим, подключаем, потом забираем. Бронирование только через Instagram Direct: {settings['instagram_dm']}. "
             "Общаемся на русском и украинском.", "", "## Цены (zł за сутки)"]
    for c in P["consoles"]:
        lines.append(f"- {c['name']}: {zl(c['d1'])} zł (1 день), {zl(c['d2'])} zł/день (2 дня), {zl(c['d3'])} zł/день (от 3 дней)")
    v, h = P["vr"], P["hookah"]
    lines += [f"- PS VR2: {zl(v['d1'])} zł (1 день), {zl(v['d3'])} zł/день (от 3 дней); вместе с PS5 — скидка {v['bundle_discount']}%",
              f"- Кальян (18+): {zl(h['d1'])} zł (1 день), {zl(h['d3'])} zł/день (от 3 дней); возвратный залог {h['deposit']} zł",
              f"- Залог за приставку: {P['console_deposit']} zł (возвратный)", "",
              "## Новинка", f"- GTA VI (релиз {settings['gta_release']}.2026) — на наших PS5 с первого дня. Покупать приставку и игру не нужно.", "",
              "## Что входит",
              "- Приставка: 2 геймпада, аккаунт с играми, диски, доставка и подключение. Нужен только Wi‑Fi.",
              "- Кальян: 2 готовые чаши, уголь ×6, плитка для розжига, одноразовые мундштуки ×6. Мыть не нужно.", "",
              "## Игры", "- " + ", ".join(g["name"] for g in games), "", "## Страницы"]
    names = load(f"templates/ui.{DEFAULT_LANG}.json")["pages"]
    for key in PAGE_KEYS:
        lines.append(f"- [{names[key]['og_title']}]({url(key, DEFAULT_LANG, True)})")
    for l in ENABLED:
        if l != DEFAULT_LANG:
            lines.append(f"- [{l.upper()}]({url('home', l, True)})")
    (DIST / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Корень «/»: открываем язык пользователя.
    # 1) ручной выбор (localStorage) → 2) языки браузера по порядку (uk / ru / be→ru / en) → 3) русский (x-default).
    # Пример: телефон на польском + украинском → /uk/; только польский → /ru/; английский → /en/.
    alts = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{url("home", l, True)}">' for l in ENABLED)
    links = " · ".join(f'<a href="/{l}/" hreflang="{l}">{load(f"templates/ui.{l}.json")["lang_name"]}</a>' for l in ENABLED)
    (DIST / "index.html").write_text(f"""<!doctype html>
<html lang="{DEFAULT_LANG}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ps.wawa — аренда PS5 и кальянов в Варшаве · оренда PS5 · PS5 rental Warsaw</title>
<meta name="description" content="ps.wawa — аренда PS5, PS VR2 и кальянов с доставкой по Варшаве. Українською · English.">
<link rel="canonical" href="{url('home', DEFAULT_LANG, True)}">
{alts}
<link rel="alternate" hreflang="x-default" href="{url('home', DEFAULT_LANG, True)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<script>
(function(){{var S={json.dumps(ENABLED)},c=null;
try{{c=localStorage.getItem('pswawa_lang')}}catch(e){{}}
if(S.indexOf(c)<0){{c=null;var L=navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language||''];
for(var i=0;i<L.length&&!c;i++){{var l=String(L[i]).toLowerCase().slice(0,2);if(l==='be')l='ru';if(S.indexOf(l)>-1)c=l}}}}
location.replace('/'+(c||'{DEFAULT_LANG}')+'/'+location.search+location.hash)}})();
</script>
<noscript><meta http-equiv="refresh" content="0; url=/{DEFAULT_LANG}/"></noscript>
<style>body{{margin:0;background:#0A0A0B;color:#F2EFE9;font:16px system-ui;display:grid;place-items:center;min-height:100vh}}a{{color:#E03CFF;padding:12px}}</style>
</head><body><p>{links}</p></body></html>
""", encoding="utf-8")

    # 404 по языкам (Netlify / Cloudflare Pages читают _redirects; корневой 404.html — русский)
    shutil.copy(DIST / DEFAULT_LANG / "404.html", DIST / "404.html")
    (DIST / "_redirects").write_text(
        "".join(f"/{l}/* /{l}/404.html 404\n" for l in ENABLED), encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST)
    for l in ENABLED:
        pages = render_lang(l)
        print(f"{l}: {', '.join(pages)} + 404")
    write_meta_files()
    print("Готово →", DIST)


if __name__ == "__main__":
    main()
