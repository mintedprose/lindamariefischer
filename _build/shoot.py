"""Screenshot built pages with headless Edge (full page, trimmed).

    python _build/shoot.py story videos blog/index   -> _shots/<name>.png
"""
import os, sys, subprocess, tempfile, time
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
SHOTS = os.path.join(ROOT, '_shots')
os.makedirs(SHOTS, exist_ok=True)


def shoot(page, width=1280, height=9000, phone=False):
    src = os.path.join(ROOT, '_site', *(page + '.html').split('/'))
    url = 'file:///' + src.replace('\\', '/').replace(' ', '%20') + '?t=' + str(int(time.time()))   # defeat browser cache
    name = page.replace('/', '__') + ('-phone' if phone else '')
    out = os.path.join(SHOTS, name + '.png')
    if phone:  # headless Edge won't go below ~490px, so frame the page at 375px
        wrap = os.path.join(tempfile.gettempdir(), 'lmf_phone.html')
        open(wrap, 'w', encoding='utf-8').write(f'<body style="margin:0"><iframe src="{url}" style="width:375px;height:{height}px;border:0;display:block"></iframe></body>')
        url, width = 'file:///' + wrap.replace('\\', '/'), 500
    if os.path.exists(out): os.remove(out)   # never show a stale screenshot
    subprocess.run([EDGE, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                    '--user-data-dir=' + tempfile.mkdtemp(prefix='edgeshot-'),   # fresh profile = no stale cache
                    f'--window-size={width},{height}', '--virtual-time-budget=10000', '--screenshot=' + out, url],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    im = Image.open(out).convert('RGB')
    if phone: im = im.crop((0, 0, 375, im.height))
    # Trim trailing blank rows (a row counts as blank only if the WHOLE row is white)
    gray = im.convert('L'); h = im.height
    while h > 1 and gray.crop((0, h - 1, im.width, h)).getextrema()[0] >= 254: h -= 1
    im.crop((0, 0, im.width, h)).save(out)
    return out, h


if __name__ == '__main__':
    phone = '--phone' in sys.argv
    for p in [a for a in sys.argv[1:] if not a.startswith('--')]:
        print(shoot(p, phone=phone))
