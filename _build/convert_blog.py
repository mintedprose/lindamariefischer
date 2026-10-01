"""Convert blog posts from the Squarespace WordPress export into Jekyll _posts.

Post text is carried over verbatim. Images are downloaded locally; embedded
videos become responsive iframes. Each post keeps its old URL (/blog/<slug>).
"""
import os, re, json, html, sys, io
from bs4 import BeautifulSoup
import convert_pages as cp

XML = r'C:\Users\LindaPurpura\Desktop\Squarespace-Wordpress-Export-09-27-2026.xml'
POSTS = os.path.join(cp.ROOT, '_posts')
os.makedirs(POSTS, exist_ok=True)
EXTRA = {'img': ['src', 'alt', 'loading'], 'figure': ['class'], 'figcaption': [],
         'iframe': ['src', 'title', 'loading', 'allow', 'allowfullscreen'], 'div': ['class']}


def cdata(s):
    m = re.match(r'\s*<!\[CDATA\[(.*)\]\]>\s*$', s or '', re.S)
    return m.group(1) if m else (s or '')


def field(item, tag):
    m = re.search(rf'<{tag}>(.*?)</{tag}>', item, re.S)
    return cdata(m.group(1)).strip() if m else ''


def convert_content(raw):
    soup = BeautifulSoup(f'<div id="root">{raw}</div>', 'lxml')
    root = soup.find(id='root')
    # Embedded videos (Squarespace keeps the iframe in data-html)
    for w in root.select('[data-html]'):
        m = re.search(r'src="([^"]+)"', html.unescape(w['data-html']))
        if m:
            src = html.unescape(m.group(1)); src = ('https:' + src if src.startswith('//') else src).split('?')[0]
            new = soup.new_tag('div', attrs={'class': 'video'})
            new.append(soup.new_tag('iframe', attrs={'src': src, 'title': 'Video', 'loading': 'lazy', 'allowfullscreen': ''}))
            w.replace_with(new)
    for f in root.find_all('iframe'):
        if f.parent.name != 'div' or 'video' not in (f.parent.get('class') or []):
            src = f.get('src', '')
            if src.startswith('//'): f['src'] = 'https:' + src
            wrap = soup.new_tag('div', attrs={'class': 'video'}); f.wrap(wrap)
    # Images -> local figures
    for img in root.find_all('img'):
        src = img.get('data-src') or img.get('src') or ''
        if not src or src.startswith('data:'): img.decompose(); continue
        local = cp.fetch_asset(src)
        alt = img.get('alt', '')
        if re.search(r'\.(jpe?g|png|gif)$', alt, re.I): alt = ''
        fig = soup.new_tag('figure', attrs={'class': 'figure'})
        a = img.find_parent('a')
        new_img = soup.new_tag('img', attrs={'src': '{{ site.baseurl }}' + local, 'alt': alt, 'loading': 'lazy'})
        if a and a.get('href'):
            link = soup.new_tag('a', href=a['href']); link.append(new_img); fig.append(link)
            target = a
        else:
            fig.append(new_img); target = img
        target.replace_with(fig)
    for cap in root.select('.image-caption'):
        cap.name = 'figcaption'
    return cp.clean_fragment(root, EXTRA)


def main():
    t = open(XML, encoding='utf-8').read()
    items = re.findall(r'<item>(.*?)</item>', t, re.S)
    attach = {}
    for i in items:
        if field(i, 'wp:post_type') == 'attachment':
            attach[field(i, 'wp:post_id')] = field(i, 'wp:attachment_url')
    n = 0
    for i in items:
        if field(i, 'wp:post_type') != 'post' or field(i, 'wp:status') != 'publish': continue
        title = html.unescape(field(i, 'title'))
        slug = field(i, 'wp:post_name') or field(i, 'link').rsplit('/', 1)[-1]
        date = field(i, 'wp:post_date')
        tags = [html.unescape(cdata(m)) for m in re.findall(r'<category domain="post_tag"[^>]*>(.*?)</category>', i, re.S)]
        cats = [html.unescape(cdata(m)) for m in re.findall(r'<category domain="category"[^>]*>(.*?)</category>', i, re.S)]
        thumb_id = re.search(r'<wp:meta_key>_thumbnail_id</wp:meta_key>\s*<wp:meta_value>(.*?)</wp:meta_value>', i, re.S)
        thumb = attach.get(cdata(thumb_id.group(1)).strip()) if thumb_id else None
        body = convert_content(field(i, 'content:encoded'))
        image = cp.fetch_asset(thumb) if thumb else ''
        if not image:
            m = re.search(r'src="\{\{ site\.baseurl \}\}([^"]+)"', body)
            image = m.group(1) if m else ''
        # Don't repeat the featured image at the very top of the post
        if image:
            body = re.sub(r'^\s*<figure class="figure"><img src="\{\{ site\.baseurl \}\}' + re.escape(image) + r'"[^>]*/?>\s*</figure>', '', body)
        exc = BeautifulSoup(field(i, 'excerpt:encoded'), 'lxml').get_text(' ', strip=True)
        if not exc:
            exc = BeautifulSoup(body, 'lxml').get_text(' ', strip=True)[:220].rsplit(' ', 1)[0] + '…'
        exc = re.sub(r'\s+', ' ', exc.replace('\xa0', ' ')).strip()
        fm = {'layout': 'post', 'title': title, 'date': date, 'permalink': f'/blog/{slug}',
              'image': image, 'excerpt': exc, 'categories': cats, 'tags': tags}
        # Post already opens with its own picture: don't stack the featured image on top
        if body.lstrip().startswith('<figure'): fm['show_lead'] = False
        front = '---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in fm.items()) + '---\n'
        fname = f'{date[:10]}-{slug}.html'
        open(os.path.join(POSTS, fname), 'w', encoding='utf-8').write(front + cp.youtube_facade(body) + '\n')
        n += 1
        print(f'{fname:70} img={"Y" if image else "-"} {len(body):5}')
    print('posts:', n, 'assets so far:', len(cp.downloaded))


if __name__ == '__main__':
    main()
