"""Validate public pages, links/fragments, source assets and deployment isolation."""
import json
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

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "form":
            self.forms.append(attrs)
        for name in ("href", "src"):
            if attrs.get(name):
                self.links.append(attrs[name])


def main():
    pages = {}
    content = json.loads((ROOT / "site/content.json").read_text(encoding="utf-8"))
    for path in OUT.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "{{" not in text and "{%" not in text, path
        assert 'name="csrf"' not in text and "/admin" not in text, path
        page = Page(path)
        page.feed(text)
        pages[path.resolve()] = page
    assert len(pages) == 1 + len(content["products"])
    for page in pages.values():
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
    assert len(forms) == 1 and forms[0]["id"] == "contact-form" and forms[0]["method"] == "post"
    for path in OUT.rglob("*"):
        assert path.suffix not in (".sqlite3", ".key", ".py", ".pyc"), path
    for name in ("site.css", "line_qr.jpg"):
        assert (OUT / "assets" / name).read_bytes() == (ROOT / "site/assets" / name).read_bytes()
    print("STATIC CHECKS OK: {} pages, assets, links, fragments, form and private-file isolation.".format(len(pages)))


if __name__ == "__main__":
    main()
