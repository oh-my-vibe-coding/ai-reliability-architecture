"""Keep existing MkDocs anchors and add Unicode anchors used by GitHub links."""

from html import escape, unescape
from html.parser import HTMLParser
import re


class _HeadingText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.in_permalink = False

    def handle_starttag(self, tag, attrs):
        if tag == "a" and "headerlink" in dict(attrs).get("class", "").split():
            self.in_permalink = True

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_permalink = False

    def handle_data(self, data):
        if not self.in_permalink:
            self.parts.append(data)


def on_page_content(html: str, **kwargs) -> str:
    """Add aliases without changing existing TOC/permalink URLs."""
    used = set(unescape(x) for x in re.findall(r'\bid="([^"]+)"', html))
    counts = {}

    def alias(match):
        parser = _HeadingText()
        parser.feed(match.group(2))
        text = "".join(parser.parts).strip().lower()
        # GitHub removes punctuation but retains Unicode letters and repeated dashes.
        slug = re.sub(r"[^\w\-\s]", "", text)
        slug = re.sub(r"\s", "-", slug)
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        slug = f"{slug}-{count}" if count else slug
        if not slug or slug in used:
            return match.group(0)
        used.add(slug)
        return f'<a id="{escape(slug, quote=True)}"></a>\n' + match.group(0)

    result = re.sub(r"(<h[1-6]\b[^>]*>)(.*?)(</h[1-6]>)", alias, html, flags=re.DOTALL)
    page = kwargs.get("page")
    if page is not None and page.present_anchor_ids is not None:
        page.present_anchor_ids.update(used)
    return result
