"""One-off text cleanup (2026-10-01): export leftovers and clear typos.

- [caption ...]<figure>…</figure> text [/caption]  ->  <figure>…<figcaption>text</figcaption></figure>
- trim spaces inside alt="…"
- no space before . , ; : ! ? (keeps spaced ellipses ". . .")
- straight double quotes -> curly in visible text
- collapse double spaces in visible text
- specific typos (listed in FIXES)
Run from the site folder:  python _build/cleanup_text.py
"""
import re, glob, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
SPLIT = re.compile(r'(<[^>]*>|\{\{.*?\}\}|\{%.*?%\})', re.S)

FIXES = [  # (old, new) exact text; verified against the source material
    ('sings about the the thrill', 'sings about the thrill'),
    ('The the mist is love’s flower', 'The mist is love’s flower'),          # lyric sheet: "The mist is love's flower"
    ('Map Of Ice', 'Map of Ice'),
    ('>map of Ice<', '>Map of Ice<'),
    ('International Woman’s Day', 'International Women’s Day'),
    ('called Arc of Love a “a very elegant listen”', 'called Arc of Love “a very elegant listen”'),
]


def curly_double(t):
    t = re.sub(r'(^|[\s(\[—–-])"', lambda m: m.group(1) + '“', t)
    return t.replace('"', '”')


def fix_text_node(t):
    t = curly_double(t)
    t = re.sub(r'(?<=\S)  +(?=\S)', ' ', t)
    t = re.sub(r'(?<=[\w”’)])[  ]+([.,;:!?])(?![ ]?\.)', r'\1', t)
    return t


def fix_html(body):
    # caption shortcodes -> real captions
    def cap(m):
        inner, text = m.group(1), m.group(2).strip()
        return f'<figure class="figure">{inner}<figcaption>{text}</figcaption></figure>' if text else f'<figure class="figure">{inner}</figure>'
    body = re.sub(r'\[caption[^\]]*\]\s*<figure class="figure">(.*?)</figure>\s*(.*?)\s*\[/caption\]', cap, body, flags=re.S)
    body = re.sub(r'\[/?caption[^\]]*\]', '', body)
    body = re.sub(r'alt="\s*(.*?)\s*"', r'alt="\1"', body)
    parts = SPLIT.split(body)
    for i in range(0, len(parts), 2):
        parts[i] = fix_text_node(parts[i])
        # space between a closing inline tag and punctuation:  </a> .
        if i >= 2 and re.match(r'</(a|em|strong|span|i|b)>', parts[i - 1]) and re.match(r'[  ]+[.,;:!?](?![ ]?\.)', parts[i]):
            parts[i] = parts[i].lstrip('  ')
    return ''.join(parts)


def fix_front(fm):
    return re.sub(r'^((?:title|heading|excerpt|description): )(.*)$',
                  lambda m: m.group(1) + fix_fm_value(m.group(2)), fm, flags=re.M)


def fix_fm_value(v):
    if v.startswith('"') and v.endswith('"'):           # JSON-style quoted value: fix inside only
        inner = fix_text_node(v[1:-1].replace('\\"', '"'))  # all quotes become curly, so no escaping needed
        return '"' + inner + '"'
    return fix_text_node(v)


files = sorted(glob.glob('*.html') + glob.glob('_posts/*.html') + glob.glob('blog/*.html'))
changed = 0
for f in files:
    s = open(f, encoding='utf-8').read()
    m = re.match(r'(---\n)(.*?\n)(---\n?)(.*)$', s, re.S)
    new = (m.group(1) + fix_front(m.group(2)) + m.group(3) + fix_html(m.group(4))) if m else fix_html(s)
    for old, rep in FIXES:
        new = new.replace(old, rep)
    if new != s:
        open(f, 'w', encoding='utf-8').write(new); changed += 1
print('files cleaned:', changed)
