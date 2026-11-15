#!/usr/bin/env python3
"""
Генерация картинок: og-превью 1200×630 для каждой страницы, фавиконки, иконки PWA, logo-512.
Запускается вручную (нужен playwright), результат коммитится в static/assets/img.
"""
import json, pathlib, base64
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "static/assets/img"; (IMG / "og").mkdir(parents=True, exist_ok=True)
FONTDIR = ROOT / "static/assets/fonts"
def furl(name):  # шрифт как data: URI — иначе about:blank не грузит файлы
    return "data:font/woff2;base64," + base64.b64encode((FONTDIR / name).read_bytes()).decode()
LOGO = (ROOT / "_src/logo.svg").read_text()
SPRITE = (ROOT / "static/assets/svg/sprite.svg").read_text()
BUST = "data:image/webp;base64," + base64.b64encode((IMG / "hero-bust-631.webp").read_bytes()).decode()
prices = json.loads((ROOT / "content/prices.json").read_text())

FF = f"""
@font-face{{font-family:SofiaX;src:url({furl('sofia-sans-extra-condensed-cyrillic-wght-normal.woff2')});font-weight:100 900;unicode-range:U+0400-04FF}}
@font-face{{font-family:SofiaX;src:url({furl('sofia-sans-extra-condensed-latin-wght-normal.woff2')});font-weight:100 900}}
@font-face{{font-family:Mono;src:url({furl('jetbrains-mono-cyrillic-wght-normal.woff2')});font-weight:100 900;unicode-range:U+0400-04FF}}
@font-face{{font-family:Mono;src:url({furl('jetbrains-mono-latin-wght-normal.woff2')});font-weight:100 900}}
"""
ACC = {"home": "#E03CFF", "consoles": "#B6FF3B", "gta": "#B6FF3B", "vr": "#B6FF3B", "games": "#B6FF3B", "hookah": "#FF6B2C", "terms": "#E03CFF"}
ICON = {"consoles": "i-gamepad", "gta": "i-gamepad", "vr": "i-vr", "games": "i-gamepad", "hookah": "i-hookah", "terms": "i-chat"}

def og_html(lang, key, title, sub):
    a = ACC[key]
    art = (f'<div class="stripe"></div><img class="bust" src="{BUST}">' if key == "home"
           else f'<svg class="ico" viewBox="0 0 96 96"><use href="#{ICON[key]}"/></svg>')
    badge = '<span class="b18">18+</span>' if key == "hookah" else ""
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{FF}
*{{margin:0;box-sizing:border-box}}body{{width:1200px;height:630px;overflow:hidden;background:#0A0A0B;color:#F2EFE9;position:relative}}
.bg{{position:absolute;inset:0;background:radial-gradient(ellipse 60% 50% at 30% 0,rgba(242,239,233,.10),transparent 70%),radial-gradient(circle at 92% 70%,{a}55,transparent 42%)}}
.copy{{position:absolute;left:72px;top:64px;bottom:64px;width:640px;display:flex;flex-direction:column;justify-content:space-between}}
.logo{{width:250px;height:auto;align-self:flex-start;color:#F2EFE9}} .logo-dot{{fill:#E03CFF}}
h1{{font:900 112px/.86 SofiaX;text-transform:uppercase;letter-spacing:.005em}}
p{{font:600 26px/1.3 Mono;color:{a};letter-spacing:.02em}}
.b18{{display:inline-block;margin-left:14px;border:3px solid #FF6B2C;color:#FF6B2C;border-radius:10px;padding:4px 10px;font:700 24px/1 Mono;vertical-align:middle}}
.art{{position:absolute;right:0;top:0;width:500px;height:630px}}
.stripe{{position:absolute;left:170px;top:0;width:150px;height:520px;background:linear-gradient(#E03CFF,#B92BD6 70%,transparent);box-shadow:0 0 60px #E03CFF88}}
.bust{{position:absolute;left:-10px;bottom:-10px;height:600px}}
.ico{{position:absolute;left:110px;top:175px;width:280px;height:280px;color:{a};filter:drop-shadow(0 0 22px {a})}}
</style></head><body>{SPRITE}<div class=bg></div><div class=art>{art}</div>
<div class=copy>{LOGO}<h1>{title}</h1><p>{sub}{badge}</p></div></body></html>"""

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        for ui_file in sorted((ROOT / "templates").glob("ui.*.json")):
            lang = ui_file.stem.split(".")[1]
            ui = json.loads(ui_file.read_text())
            for key, meta in ui["pages"].items():
                if key == "404": continue
                pg.set_content(og_html(lang, key, meta["og_title"], meta.get("og_sub", "")), wait_until="load")
                pg.wait_for_timeout(150)
                pg.screenshot(path=str(IMG / "og" / f"{lang}-{key}.jpg"), type="jpeg", quality=86)
        # Фавиконки и иконки — монограмма «ps.»
        mono = """<!doctype html><html><head><style>""" + FF.replace("SofiaX", "x") + """
@font-face{font-family:U;src:local('Arial Black')}
*{margin:0}body{width:512px;height:512px;background:transparent}
</style></head><body>""" + (ROOT / "static/favicon.svg").read_text().replace("<svg ", '<svg width="512" height="512" ') + "</body></html>"
        for size, name in [(32, "favicon-32.png"), (180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")]:
            p2 = b.new_page(viewport={"width": 512, "height": 512}, device_scale_factor=size / 512)
            p2.set_content(mono); p2.screenshot(path=str(IMG / name), omit_background=True); p2.close()
        p3 = b.new_page(viewport={"width": 512, "height": 512})
        p3.set_content(f'<body style="margin:0;background:#0A0A0B;display:grid;place-items:center;width:512px;height:512px;color:#F2EFE9">{LOGO.replace("class=\"logo\"", "style=\"width:420px\"")}<style>.logo-dot{{fill:#E03CFF}}</style></body>')
        p3.screenshot(path=str(IMG / "logo-512.png")); p3.close()
        b.close()
    print("ok")

if __name__ == "__main__":
    main()
