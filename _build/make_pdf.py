"""Build a PDF proof of every page, exactly as it looks on a desktop screen.

Each page is captured as a full-page screenshot at 1280px wide, cut into PDF
pages at quiet gaps (so breaks don't slice through text or pictures), with a
cover/contents page and a bookmark per page.

    python _build/preview.py && python _build/make_pdf.py      (run from PowerShell)
Output: "LMF Website Proof.pdf" in the project folder.
"""
import os, re, io, json, glob, html, datetime, tempfile
import fitz
from PIL import Image
import shoot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, '_site')
OUTPDF = os.path.join(ROOT, 'LMF Website Proof.pdf')
PAGE_H = 1810          # target PDF page height in screenshot pixels (1280 wide)
SEARCH = 450           # how far up to look for a quiet row to cut at

MAIN = [('/', 'Home'), ('/music/arc-of-love', 'Arc of Love'), ('/passages', 'Passages'), ('/places', 'Places'),
        ('/arc-of-love-lyrics', 'Arc of Love Lyrics'), ('/passages-lyrics', 'Passages Lyrics'), ('/places-lyrics', 'Places Lyrics'),
        ('/arc-of-love-lyricist-notes', 'Arc of Love Songwriter Notes'), ('/passages-lyricist-notes', 'Passages Songwriter Notes'),
        ('/places-lyricist-notes', 'Places Songwriter Notes'), ('/story', 'Story'), ('/videos', 'Videos'),
        ('/spotify', 'Spotify'), ('/inspiration', 'Inspiration'), ('/merch', 'Merch'), ('/reviews', 'Reviews'),
        ('/faq', 'FAQ'), ('/media', 'Media'), ('/contact', 'Contact'), ('/privacy-policy', 'Privacy Policy'),
        ('/blog/', 'Blog')]


def posts():
    out = []
    for f in glob.glob(os.path.join(ROOT, '_posts', '*.html')):
        s = open(f, encoding='utf-8').read()
        title = json.loads(re.search(r'^title: (.*)$', s, re.M).group(1))
        url = json.loads(re.search(r'^permalink: (.*)$', s, re.M).group(1))
        out.append((os.path.basename(f)[:10], url, title))
    return [(u, t, d) for d, u, t in sorted(out, reverse=True)]


def page_name(url):
    u = url.strip('/') or 'index'
    return u + ('/index' if url.endswith('/') and u != 'index' else '')


def quiet_row(im, y):
    """True if row y is a single flat colour (safe place to cut)."""
    row = im.crop((0, y, im.width, y + 1)).convert('L')
    lo, hi = row.getextrema()
    return hi - lo <= 3


def quiet_band(im, y, h):
    return all(quiet_row(im, r) for r in range(y - h, y + 1, 5))


def slices(im):
    y = 0
    while y < im.height:
        if im.height - y <= PAGE_H + 420:          # short leftover: keep it on this page
            yield im.crop((0, y, im.width, im.height)); return
        end = y + PAGE_H
        # Prefer a wide gap between sections, then a narrower one, then any flat row
        for band in (60, 24, 6):
            found = next((c for c in range(y + PAGE_H, y + PAGE_H - SEARCH, -1) if quiet_band(im, c, band)), None)
            if found: end = found; break
        yield im.crop((0, y, im.width, end))
        y = end


def add_image_page(doc, im):
    buf = io.BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=80, optimize=True)
    w, h = im.width * 0.75, im.height * 0.75          # px -> pt at 96 dpi
    page = doc.new_page(width=w, height=max(h, PAGE_H * 0.75))
    page.insert_image(fitz.Rect(0, 0, w, h), stream=buf.getvalue())


def cover_html(entries):
    today = datetime.date.today()
    rows = ''.join(f'<li><span>{html.escape(t)}</span><code>lindamariefischer.com{html.escape(u)}</code></li>' for u, t in entries)
    logo = 'file:///' + os.path.join(SITE, 'assets', 'img', 'logo-full.png').replace(os.sep, '/').replace(' ', '%20')
    doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500&family=Jost:wght@400;500&display=swap" rel="stylesheet">
<style>body{{margin:0;font:400 15px/1.5 Jost,sans-serif;color:#1f2624;background:#fff}}
.top{{background:linear-gradient(160deg,#fff,#f3f7f4 60%,#e8f3ef);padding:90px 110px 60px}}
.top img{{height:74px}} h1{{font:500 66px/1.1 'Cormorant Garamond',serif;margin:44px 0 14px}}
.meta{{color:#4a5552;font-size:17px;margin:0}} .eyebrow{{font:500 12px/1 Jost;letter-spacing:.22em;text-transform:uppercase;color:#00758f;margin:0 0 16px}}
.list{{padding:44px 110px 70px}} ol{{columns:2;column-gap:64px;padding-left:24px;margin:0}} li{{break-inside:avoid;margin:0 0 8px;font-size:14px}}
li span{{display:block}} li code{{font:12px/1.3 Consolas,monospace;color:#00758f}}
h2{{font:500 32px 'Cormorant Garamond',serif;margin:0 0 20px}}</style></head><body>
<div class="top"><img src="{logo}">
<h1>Website proof</h1><p class="eyebrow">Refreshed design · built for GitHub Pages</p>
<p class="meta">{len(entries)} pages, each shown as it appears on a desktop screen · {today.strftime('%B')} {today.day}, {today.year}<br>
Open the bookmarks panel to jump to any page.</p></div>
<div class="list"><h2>Contents</h2><ol>{rows}</ol></div></body></html>"""
    path = os.path.join(SITE, '__cover.html')
    open(path, 'w', encoding='utf-8').write(doc)
    return '__cover'


def main():
    blog = posts()
    entries = MAIN + [(u, t) for u, t, _ in blog]
    doc = fitz.open(); toc = []

    name = cover_html(entries)
    png, _ = shoot.shoot(name, width=1280, height=3200)
    for im in slices(Image.open(png)): add_image_page(doc, im)
    toc.append([1, 'Cover & contents', 1])
    os.remove(os.path.join(SITE, '__cover.html')); os.remove(png)

    blog_titles = {u: f'{t} ({d})' for u, t, d in blog}
    for i, (url, title) in enumerate(entries, 1):
        png, h = shoot.shoot(page_name(url), width=1280, height=14000)
        start = doc.page_count + 1
        for im in slices(Image.open(png)): add_image_page(doc, im)
        if url in blog_titles:
            if not any(t[1] == 'Blog posts' for t in toc): toc.append([1, 'Blog posts', start])
            toc.append([2, blog_titles[url], start])
        else:
            toc.append([1, title, start])
        os.remove(png)
        print(f'{i:3d}/{len(entries)} {url}  ({h}px)')
    doc.set_toc(toc)
    doc.set_metadata({'title': 'Linda Marie Fischer — Website Proof', 'author': 'Linda Marie Fischer'})
    doc.save(OUTPDF, garbage=4, deflate=True)
    print('PDF pages:', doc.page_count, f'({os.path.getsize(OUTPDF) / 1e6:.1f} MB) ->', OUTPDF)


if __name__ == '__main__':
    main()
