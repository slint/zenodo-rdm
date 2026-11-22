"""Crawls help.zenodo.org and the developers.zenodo.org sections into docs/pages.json."""
import json, re, sys, urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links, self.heads, self.text, self.tag, self.title = [], [], [], None, ""
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("nav", "script", "style", "footer"): self.skip += 1
        if tag == "a" and a.get("href"): self.links.append(a["href"])
        if tag in ("h1", "h2", "h3", "title"): self.tag, self.cur = tag, {"level": tag, "id": a.get("id"), "text": ""}
    def handle_endtag(self, tag):
        if tag in ("nav", "script", "style", "footer"): self.skip = max(0, self.skip - 1)
        if tag == self.tag:
            if tag == "title": self.title = self.cur["text"].strip()
            else: self.cur["text"] = self.cur["text"].strip(); self.heads.append(self.cur)
            self.tag = None
    def handle_data(self, d):
        if self.tag: self.cur["text"] += d
        elif not self.skip and d.strip(): self.text.append(d.strip())

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "zenodo-feature-catalog"})
    with urllib.request.urlopen(req, timeout=30) as r:
        p = Page(); p.feed(r.read().decode("utf8", "replace")); p.url = r.geturl(); return p

def help_pages(root="https://help.zenodo.org/"):
    seen, todo, out, refs = set(), [(root, None)], [], {}
    while todo:
        url, ref = todo.pop()
        refs.setdefault(url, set()).add(ref)
        if url in seen: continue
        seen.add(url)
        try: p = fetch(url)
        except Exception as e:
            out.append({"site": "help", "url": url, "broken": str(e), "linked_from": refs[url]}); continue
        if p.url != url: seen.add(p.url)
        out.append({"site": "help", "url": p.url, "title": p.title,
                    "headings": [h["text"] for h in p.heads if h["level"] != "h1"],
                    "summary": " ".join(p.text)[:600]})
        for h in p.links:
            u = urldefrag(urljoin(p.url, h))[0]  # relative to the URL after redirects
            if u.startswith(root) and not re.search(r"\.(png|jpe?g|svg|css|js|ico|pdf|xml)$", u): todo.append((u, url))
    for o in out:
        if "broken" in o: o["linked_from"] = sorted(r for r in refs[o["url"]] if r)
    return sorted(out, key=lambda x: x["url"])

def developer_sections(root="https://developers.zenodo.org/"):
    p = fetch(root)
    return [{"site": "developers", "url": f"{root}#{h['id']}", "title": h["text"], "level": h["level"]}
            for h in p.heads if h["id"]]

if __name__ == "__main__":
    pages = help_pages() + developer_sections()
    json.dump(pages, open(sys.argv[1] if len(sys.argv) > 1 else "pages.json", "w"), indent=1)
    print(len(pages), "pages and sections")
