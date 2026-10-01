"""Convert live Squarespace pages (saved in raw/) into Jekyll page sources.

Text is carried over verbatim; Squarespace chrome (streaming image-buttons,
spacers, newsletter/social widgets, decorative bouquet) is dropped because the
new layouts provide their own. Images and PDFs are downloaded locally.
"""
import os, re, json, html, hashlib, sys, io
from urllib.parse import urlparse, unquote
import requests
from bs4 import BeautifulSoup, NavigableString, Comment

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, '_build', 'raw')
IMG_DIR = os.path.join(ROOT, 'assets', 'img', 'site')
FILE_DIR = os.path.join(ROOT, 'assets', 'files')
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(FILE_DIR, exist_ok=True)
S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0'
SITE = 'https://www.lindamariefischer.com'

# Old path -> new path (aliases Squarespace redirected; keep old URLs working)
ALIASES = {'/albums': '/music/arc-of-love', '/music': '/music/arc-of-love', '/lyrics': '/arc-of-love-lyrics',
           '/songwriter-notes-1': '/arc-of-love-lyricist-notes', '/arc-of-love-songwriter-notes': '/arc-of-love-lyricist-notes',
           '/more': '/story', '/home': '/', '/inspirations': '/inspiration', '/blog': '/blog/'}

# raw file -> (source filename, permalink, section eyebrow, extra front matter)
PAGES = {
    'music__arc-of-love': ('arc-of-love.html', '/music/arc-of-love', 'Albums', {'layout': 'album', 'album': 'arc-of-love'}),
    'passages': ('passages.html', '/passages', 'Albums', {'layout': 'album', 'album': 'passages'}),
    'places': ('places.html', '/places', 'Albums', {'layout': 'album', 'album': 'places'}),
    'arc-of-love-lyrics': ('arc-of-love-lyrics.html', '/arc-of-love-lyrics', 'Lyrics', {'album': 'arc-of-love'}),
    'passages-lyrics': ('passages-lyrics.html', '/passages-lyrics', 'Lyrics', {'album': 'passages'}),
    'places-lyrics': ('places-lyrics.html', '/places-lyrics', 'Lyrics', {'album': 'places'}),
    'arc-of-love-lyricist-notes': ('arc-of-love-lyricist-notes.html', '/arc-of-love-lyricist-notes', 'Songwriter Notes', {'album': 'arc-of-love'}),
    'passages-lyricist-notes': ('passages-lyricist-notes.html', '/passages-lyricist-notes', 'Songwriter Notes', {'album': 'passages'}),
    'places-lyricist-notes': ('places-lyricist-notes.html', '/places-lyricist-notes', 'Songwriter Notes', {'album': 'places'}),
    'story': ('story.html', '/story', 'About', {}),
    'videos': ('videos.html', '/videos', 'Watch', {}),
    'spotify': ('spotify.html', '/spotify', 'Listen', {}),
    'inspiration': ('inspiration.html', '/inspiration', 'More', {}),
    'merch': ('merch.html', '/merch', 'Shop', {}),
    'reviews': ('reviews.html', '/reviews', 'Press', {}),
    'faq': ('faq.html', '/faq', 'More', {}),
    'media': ('media.html', '/media', 'Press', {}),
    'contact': ('contact.html', '/contact', 'Get in touch', {}),
    'privacy-policy': ('privacy-policy.html', '/privacy-policy', 'Legal', {}),
}

report = {'unknown': [], 'links': set(), 'skipped_imgs': []}
downloaded = {}


def fetch_asset(url, kind='img'):
    """Download an image/file once; return its site path."""
    if url.startswith('//'): url = 'https:' + url
    if url.startswith('/'): url = SITE + url
    url = re.sub(r'^http://', 'https://', url)
    base = url.split('?')[0]
    if base in downloaded: return downloaded[base]
    name = unquote(os.path.basename(urlparse(base).path)) or 'file'
    name = re.sub(r'[^\w.\-]+', '-', name).strip('-').lower()
    stem, ext = os.path.splitext(name)
    if kind == 'img' and not ext: ext = '.jpg'
    name = f'{stem}-{hashlib.md5(base.encode()).hexdigest()[:6]}{ext}'
    folder, web = (IMG_DIR, '/assets/img/site/') if kind == 'img' else (FILE_DIR, '/assets/files/')
    dest = os.path.join(folder, name)
    if not os.path.exists(dest):
        get = base + ('?format=1500w' if kind == 'img' and 'squarespace-cdn' in base else '')
        r = S.get(get, timeout=60)
        if r.status_code != 200:
            print('  !! download failed', r.status_code, get); downloaded[base] = url; return url
        open(dest, 'wb').write(r.content)
    downloaded[base] = web + name
    return web + name


def fix_href(href):
    if not href: return href
    href = href.strip()
    if href.startswith('/s/') or re.search(r'\.pdf($|\?)', href, re.I) and 'lindamariefischer.com' in href:
        return '{{ site.baseurl }}' + fetch_asset(href, 'file')
    m = re.match(r'https?://(www\.)?lindamariefischer\.com(/.*)?$', href)
    if m: href = m.group(2) or '/'
    if href.startswith('/'):
        path = href.split('#')[0].split('?')[0].rstrip('/') or '/'
        frag = '#' + href.split('#', 1)[1] if '#' in href else ''
        path = ALIASES.get(path, path)
        report['links'].add(path)
        return '{{ site.baseurl }}' + (path if path != '/' else '/') + frag
    return href


KEEP = {'h1', 'h2', 'h3', 'h4', 'p', 'br', 'a', 'strong', 'em', 'ul', 'ol', 'li', 'blockquote', 'hr', 'sup', 'sub'}
RENAME = {'b': 'strong', 'i': 'em'}


def clean_fragment(node, extra=None):
    """Return cleaned HTML for the children of node, whitelisting tags.
    extra: {tag: [allowed attrs]} for additional tags to keep (e.g. blog images)."""
    extra = extra or {}
    soup = BeautifulSoup(str(node), 'lxml')
    root = soup.body.contents[0] if soup.body else soup
    for c in root.find_all(string=lambda s: isinstance(s, Comment)): c.extract()
    for t in root.find_all(['style', 'script', 'noscript']): t.decompose()
    for t in list(root.find_all(True)):
        if t is root: continue
        name = RENAME.get(t.name, t.name)
        t.name = name
        if name in extra:
            if name == 'div' and 'video' not in (t.get('class') or []):
                t.unwrap(); continue
            t.attrs = {k: v for k, v in t.attrs.items() if k in extra[name]}
            continue
        if name not in KEEP:
            t.unwrap(); continue
        attrs = {}
        if name == 'a' and t.get('href'):
            attrs['href'] = fix_href(t['href'])
        t.attrs = attrs
    out = ''.join(str(c) for c in root.contents)
    out = out.replace('\xa0', ' ')
    out = re.sub(r'<p>\s*(<br/?>\s*)*</p>', '', out)
    out = re.sub(r'<(h\d)>\s*</\1>', '', out)
    out = re.sub(r'<h1>(.*?)</h1>', r'<h2>\1</h2>', out, flags=re.S)
    out = re.sub(r'\n\s*\n+', '\n', out)
    return out.strip()


YT_EMBED = re.compile(r'<div class="video">\s*<iframe[^>]*src="(?:https?:)?//(?:www\.)?youtube(?:-nocookie)?\.com/embed/([\w-]{6,})[^"]*"[^>]*>\s*</iframe>\s*</div>')


def youtube_facade(s):
    """Swap YouTube iframes for a thumbnail + play button (player loads on click, see site.js)."""
    return YT_EMBED.sub(lambda m: (
        f'<div class="video" data-yt="{m.group(1)}"><a class="video-thumb" href="https://www.youtube.com/watch?v={m.group(1)}" aria-label="Play video">'
        f'<img src="https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg" alt="" loading="lazy"><span class="play" aria-hidden="true"></span></a></div>'), s)


def def_name(b):
    x = b if b.has_attr('data-definition-name') else b.select_one('[data-definition-name]')
    return (x.get('data-definition-name') if x else '').replace('website.components.', '')


def block_type(b):
    m = re.search(r'sqs-block-([\w-]+)', ' '.join(b.get('class', [])))
    return m.group(1) if m else ''


def img_src(img):
    return img.get('data-src') or img.get('data-image') or img.get('src') or ''


def render_image_block(b):
    img = b.find('img')
    if not img: return ''
    src = img_src(img)
    low = src.lower()
    if '_with+button' in low or 'bouquet' in low or 'leaf-37' in low:
        report['skipped_imgs'].append(os.path.basename(src)); return ''
    local = fetch_asset(src)
    dims = img.get('data-image-dimensions', '')
    w, h = (dims.split('x') + ['', ''])[:2] if dims else ('', '')
    alt = html.escape(img.get('alt', '') or '', quote=True)
    if re.search(r'\.(jpe?g|png|gif)$', alt, re.I): alt = ''
    a = b.find('a', href=True)
    cap_el = b.select_one('.image-caption, .image-card, figcaption, .image-title-wrapper, .image-subtitle-wrapper')
    caption = ''
    caps = b.select('.image-title, .image-subtitle, .image-caption')
    if caps:
        caption = ' '.join(clean_fragment(c) for c in caps)
    wh = f' width="{w}" height="{h}"' if w and h else ''
    tag = f'<img src="{{{{ site.baseurl }}}}{local}" alt="{alt}"{wh} loading="lazy">'
    if a: tag = f'<a href="{fix_href(a["href"])}">{tag}</a>'
    btn = ''
    return f'<figure class="figure">{tag}' + (f'<figcaption>{caption}</figcaption>' if caption else '') + '</figure>'


def render_gallery(b):
    items = []
    for slide in b.select('.slide'):
        img = slide.find('img')
        if not img: continue
        local = fetch_asset(img_src(img))
        title = img.get('alt', '')
        meta = slide.select_one('.meta')
        desc = ''
        items.append((local, title, desc))
    # Gallery meta (titles/descriptions) live in a separate list in Squarespace markup
    metas = b.select('.meta')
    if metas and len(metas) == len(items):
        items = [(l, (m.select_one('.meta-title').get_text(' ', strip=True) if m.select_one('.meta-title') else t),
                  clean_fragment(m.select_one('.meta-description')) if m.select_one('.meta-description') else '')
                 for (l, t, _), m in zip(items, metas)]
    out = ['<div class="gallery">']
    for local, title, desc in items:
        t = html.escape(title)
        if re.search(r'\.(jpe?g|png)$', title, re.I): t = ''
        cap = (f'<strong>{t}</strong>' if t else '') + (f' {desc}' if desc else '')
        out.append(f'<figure><img src="{{{{ site.baseurl }}}}{local}" alt="{t}" loading="lazy">' + (f'<figcaption>{cap}</figcaption>' if cap else '') + '</figure>')
    out.append('</div>')
    return '\n'.join(out)


def render_block(b, page):
    t, dn = block_type(b), def_name(b)
    if t == 'html':
        c = b.select_one('.sqs-html-content') or b.select_one('.sqs-block-content')
        return clean_fragment(c) if c else ''
    if t == 'image': return render_image_block(b)
    if t == 'gallery': return render_gallery(b)
    if dn in ('spacer', 'social', 'newsletter', ''):
        if dn == '' and b.get_text(strip=True): report['unknown'].append((page, t, b.get_text(' ', strip=True)[:60]))
        return ''
    if dn == 'horizontalrule': return '<hr>'
    if dn == 'button':
        a = b.find('a', href=True)
        return f'<p class="btn-wrap"><a class="btn" href="{fix_href(a["href"])}">{html.escape(a.get_text(" ", strip=True))}</a></p>' if a else ''
    if dn == 'video':
        w = b.select_one('[data-html]')
        m = re.search(r'src="([^"]+)"', html.unescape(w['data-html'])) if w else None
        if not m: report['unknown'].append((page, 'video-no-src', '')); return ''
        src = html.unescape(m.group(1))
        if src.startswith('//'): src = 'https:' + src
        src = src.split('?')[0]
        return f'<div class="video"><iframe src="{src}" title="Video" loading="lazy" allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>'
    if dn == 'code':
        c = b.select_one('.sqs-code-container') or b
        ifr = c.find('iframe')
        if ifr:
            src = ifr.get('src', '')
            cls = 'embed embed--spotify' if 'spotify' in src else 'embed'
            h = ifr.get('height', '380')
            return f'<div class="{cls}"><iframe src="{src}" height="{h}" loading="lazy" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe></div>'
        if c.select_one('.sig'):
            return f'<p class="signature">{html.escape(c.select_one(".sig").get_text(" ", strip=True))}</p>'
        txt = clean_fragment(c)
        if txt: report['unknown'].append((page, 'code-text', txt[:80]))
        return txt
    if dn in ('embed',):
        w = b.select_one('[data-html]')
        return html.unescape(w['data-html']) if w else ''
    report['unknown'].append((page, 'component:' + dn, b.get_text(' ', strip=True)[:60]))
    return ''


def render(el, page):
    out = []
    for ch in el.find_all(recursive=False):
        cls = ch.get('class') or []
        if 'row' in cls:
            cols = []
            for col in ch.find_all(recursive=False):
                ccls = col.get('class') or []
                span = next((int(c[5:]) for c in ccls if re.fullmatch(r'span-\d+', c)), 12)
                inner = render(col, page).strip()
                if inner: cols.append((span, inner))
            if len(cols) == 1: out.append(cols[0][1])
            elif cols:
                prev = out[-1] if out else None
                # A row of short labels ("Linda's Take" | "Phil's View") directly above a row of
                # text: join each label to its column so they stay together when stacked on phones.
                if (isinstance(prev, tuple) and len(prev) == len(cols)
                        and all(re.fullmatch(r'\s*<h[2-4]>[^<]{1,40}</h[2-4]>\s*', c) for _, c in prev)):
                    cols = [(s, f'{lc}\n{c}') for (_, lc), (s, c) in zip(prev, cols)]
                    out.pop()
                out.append(tuple(cols))
        elif 'sqs-block' in cls:
            r = render_block(ch, page)
            if r: out.append(r)
        else:
            r = render(ch, page)
            if r.strip(): out.append(r)
    return '\n'.join(cols_html(o) if isinstance(o, tuple) else o for o in out)


def cols_html(cols):
    spans = [s for s, _ in cols]
    style = '' if len(set(spans)) == 1 else ' style="--cols: ' + ' '.join(f'{s}fr' for s in spans) + '"'
    return f'<div class="cols cols-{len(cols)}"{style}>\n' + '\n'.join(f'<div class="col">\n{c}\n</div>' for _, c in cols) + '\n</div>'


def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    for raw, (fname, permalink, eyebrow, extra) in PAGES.items():
        soup = BeautifulSoup(open(os.path.join(RAW, raw + '.html'), encoding='utf-8').read(), 'lxml')
        title_full = soup.title.get_text().strip()
        title = title_full.split(' — ')[0].strip()
        desc = (soup.find('meta', attrs={'name': 'description'}) or {}).get('content', '') or \
               (soup.find('meta', attrs={'property': 'og:description'}) or {}).get('content', '')
        # Page banner heading (lives outside the content layout on Squarespace)
        main_el = soup.find('main')
        banner = main_el.select_one('.page-header h1, .banner-thumbnail-wrapper h1, .page-title, #page-header h1') if main_el else None
        heading = banner.get_text(' ', strip=True) if banner else title
        lay = main_el.select_one('.sqs-layout')
        body = render(lay, raw)
        # Drop a leading heading that just repeats the page title
        body = re.sub(r'^\s*<h2>\s*' + re.escape(heading) + r'\s*</h2>', '', body, flags=re.I)
        desc = re.sub(r'\s+', ' ', html.unescape(desc).replace(' ', ' ')).strip()
        fm = {'title': title, 'heading': heading, 'eyebrow': eyebrow, 'description': desc,
              'permalink': permalink, 'layout': 'page'}
        fm.update(extra)
        front = '---\n' + ''.join(f'{k}: {yaml_str(v)}\n' for k, v in fm.items()) + '---\n'
        open(os.path.join(ROOT, fname), 'w', encoding='utf-8').write(front + youtube_facade(body) + '\n')
        print(f'{fname:34} {len(body):6} chars  heading={heading!r}')
    print('\nUNKNOWN:', *report['unknown'], sep='\n  ')
    print('\nINTERNAL LINKS:', sorted(report['links']))
    print('SKIPPED IMGS:', len(report['skipped_imgs']), 'downloaded:', len(downloaded))


if __name__ == '__main__':
    main()
