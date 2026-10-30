"""Validate public pages, links/fragments, source assets and deployment isolation."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.ids = set()
        self.links = []
        self.forms = []
        self.language = None
        self.switches = {}
        self.visible_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "a" and attrs.get("hreflang"):
            self.switches[attrs["hreflang"]] = attrs["href"]
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "form":
            self.forms.append(attrs)
        for name in ("href", "src"):
            if attrs.get(name):
                self.links.append(attrs[name])

    def handle_data(self, data):
        self.visible_text.append(data)


def main():
    pages = {}
    content = json.loads((ROOT / "site/content.json").read_text(encoding="utf-8"))
    for path in OUT.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "{{" not in text and "{%" not in text, path
        assert 'name="csrf"' not in text and "/admin" not in text, path
        assert text.count('src="https://www.googletagmanager.com/gtag/js?id=G-NL9WDQ47C9"') == 1, (path, "Missing or duplicate GA loader")
        assert text.count("gtag('config', 'G-NL9WDQ47C9')") == 1, (path, "Missing or duplicate GA initialization")
        page = Page(path)
        page.feed(text)
        pages[path.resolve()] = page
    assert len(pages) == 2 * (1 + len(content["products"]))
    for page in pages.values():
        relative = page.path.relative_to(OUT)
        english = relative.parts[0] == "en"
        assert page.language == ("en" if english else "zh-Hant"), page.path
        assert set(page.switches) == {"zh-Hant", "en"}, page.path
        counterpart = Path(*relative.parts[1:]) if english else Path("en") / relative
        other_lang = "zh-Hant" if english else "en"
        assert (page.path.parent / page.switches[other_lang]).resolve() == (OUT / counterpart).resolve(), page.path
        if english:
            assert not re.search(r"[\u3400-\u9fff]", " ".join(page.visible_text).replace("中文", "")), (page.path, "Untranslated English content")
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            assert not url.path.startswith("/"), (page.path, link, "root-relative URL")
            target = (page.path.parent / unquote(url.path)).resolve() if url.path else page.path.resolve()
            assert OUT.resolve() in target.parents, (page.path, link, "outside public folder")
            if target.is_dir():
                target = target / "index.html"
            assert target.is_file(), (page.path, link, "missing file")
            if url.fragment and target in pages:
                assert unquote(url.fragment) in pages[target].ids, (page.path, link, "missing fragment")
    forms = [f for p in pages.values() for f in p.forms]
    assert len(forms) == 2 and all(f["id"] == "contact-form" and f["method"] == "post" for f in forms)
    translated = json.loads((ROOT / "site/content.en.json").read_text(encoding="utf-8"))
    for zh, en in zip(content["products"], translated["products"]):
        assert re.findall(r"\d[\d,]*", zh["price"]) == re.findall(r"\d[\d,]*", en["price"]), "Prices differ between languages"
    for path in OUT.rglob("*"):
        assert path.suffix not in (".sqlite3", ".key", ".py", ".pyc"), path
    for name in ("site.css", "line_qr.jpg"):
        assert (OUT / "assets" / name).read_bytes() == (ROOT / "site/assets" / name).read_bytes()
    print("STATIC CHECKS OK: {} bilingual pages, language switches, prices, GA, assets, links, forms and private-file isolation.".format(len(pages)))


if __name__ == "__main__":
    main()
