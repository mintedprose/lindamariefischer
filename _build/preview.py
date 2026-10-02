"""Local preview builder for the Jekyll site (no Ruby needed).

Implements the small subset of Jekyll/Liquid this site uses so pages can be
rendered to _site/ for screenshots and the PDF proof. GitHub Pages does the
real build with Jekyll; this is only for previewing on Linda's PC.

    python _build/preview.py            -> builds _site/ with file:// links
"""
import os, re, sys, shutil, html, datetime, glob, json
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site')
BASE = 'file:///' + OUT.replace('\\', '/').replace(' ', '%20')

TOKEN = re.compile(r'({%-?.*?-?%}|{{-?.*?-?}})', re.S)


# ---------------------------------------------------------------- Liquid-lite
def split_filters(expr):
    parts, cur, q = [], '', None
    for ch in expr:
        if q:
            cur += ch
            if ch == q: q = None
        elif ch in '"\'':
            q = ch; cur += ch
        elif ch == '|':
            parts.append(cur); cur = ''
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts]


def lookup(path, ctx):
    path = path.strip()
    if not path: return None
    if path[0] in '"\'' and path[-1] == path[0]: return path[1:-1]
    if re.fullmatch(r'-?\d+', path): return int(path)
    if path in ('true', 'false'): return path == 'true'
    if path in ('nil', 'null', 'empty'): return None
    toks = re.findall(r'[^.\[\]]+|\[[^\]]+\]', path)
    cur = ctx
    for i, t in enumerate(toks):
        if t.startswith('['):
            key = lookup(t[1:-1], ctx)
        else:
            key = t
        if i == 0:
            cur = ctx.get(key); continue
        if cur is None: return None
        if key == 'size' and not (isinstance(cur, dict) and 'size' in cur): cur = len(cur); continue
        if key == 'first' and isinstance(cur, list): cur = cur[0] if cur else None; continue
        if key == 'last' and isinstance(cur, list): cur = cur[-1] if cur else None; continue
        if isinstance(cur, dict): cur = cur.get(key)
        elif isinstance(cur, list) and isinstance(key, int): cur = cur[key] if key < len(cur) else None
        else: return None
    return cur


def to_date(v):
    if isinstance(v, datetime.datetime): return v
    if isinstance(v, datetime.date): return datetime.datetime(v.year, v.month, v.day)
    if isinstance(v, str):
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try: return datetime.datetime.strptime(v[:19], fmt)
            except ValueError: pass
    return None


def fmt_date(d, f):
    d = to_date(d)
    if not d: return ''
    f = f.replace('%-d', str(d.day)).replace('%-m', str(d.month))
    return d.strftime(f)


def apply_filter(val, flt, ctx):
    name, _, arg = flt.partition(':')
    name = name.strip()
    args = [lookup(a, ctx) for a in re.findall(r'\s*("[^"]*"|\'[^\']*\'|[^,]+)', arg)] if arg.strip() else []
    if name == 'default': return val if val not in (None, '', [], False) else (args[0] if args else '')
    if name == 'escape': return html.escape(str(val if val is not None else ''), quote=True)
    if name == 'date': return fmt_date(val, args[0])
    if name == 'date_to_xmlschema': d = to_date(val); return d.isoformat() if d else ''
    if name == 'where':
        if args[1] is None: return list(val or [])   # Jekyll quirk: no value -> no filtering
        return [x for x in (val or []) if x.get(args[0]) == args[1]]
    if name == 'first': return val[0] if val else None
    if name == 'last': return val[-1] if val else None
    if name == 'size': return len(val or [])
    if name == 'strip_html': return re.sub(r'<[^>]+>', '', str(val or ''))
    if name == 'truncatewords':
        w = str(val or '').split(); n = int(args[0])
        return ' '.join(w[:n]) + ('…' if len(w) > n else '')
    if name == 'relative_url': return ctx['site'].get('baseurl', '') + str(val)
    if name == 'absolute_url': return ctx['site'].get('url', '') + str(val)
    raise ValueError('unsupported filter ' + name)


def evaluate(expr, ctx):
    parts = split_filters(expr)
    val = lookup(parts[0], ctx)
    for f in parts[1:]: val = apply_filter(val, f, ctx)
    return val


def truthy(v):
    return v not in (None, False) and not (isinstance(v, (list, str)) and len(v) == 0 and False)


def condition(expr, ctx):
    for op in (' or ', ' and '):
        if op in expr:
            l, r = expr.split(op, 1)
            return (condition(l, ctx) or condition(r, ctx)) if op == ' or ' else (condition(l, ctx) and condition(r, ctx))
    m = re.match(r'(.+?)\s*(==|!=|>=|<=|>|<|contains)\s*(.+)', expr)
    if m:
        a, op, b = evaluate(m.group(1), ctx), m.group(2), evaluate(m.group(3), ctx)
        if op == '==': return a == b
        if op == '!=': return a != b
        if op == 'contains': return b in (a or [])
        a, b = a or 0, b or 0
        return {'>': a > b, '<': a < b, '>=': a >= b, '<=': a <= b}[op]
    return truthy(evaluate(expr, ctx))


def parse(src):
    root = {'children': []}; root['_target'] = root['children']
    stack = [root]
    for t in TOKEN.split(src):
        if t.startswith('{%'):
            name, _, args = t[2:-2].strip('- ').strip().partition(' ')
            if name in ('if', 'unless', 'for', 'comment'):
                node = {'tag': name, 'args': args, 'children': [], 'else': []}
                node['_target'] = node['children']
                stack[-1]['_target'].append(node); stack.append(node)
            elif name == 'else':
                stack[-1]['_target'] = stack[-1]['else']
            elif name in ('endif', 'endunless', 'endfor', 'endcomment'):
                stack.pop()
            else:
                stack[-1]['_target'].append({'tag': name, 'args': args})
        elif t.startswith('{{'):
            stack[-1]['_target'].append({'out': t[2:-2].strip('- ').strip()})
        elif t:
            stack[-1]['_target'].append(t)
    return root['children']


def render_nodes(nodes, ctx):
    out = []
    for n in nodes:
        if isinstance(n, str): out.append(n); continue
        if 'out' in n:
            v = evaluate(n['out'], ctx); out.append('' if v is None else str(v)); continue
        tag, args = n['tag'], n['args']
        if tag == 'comment': continue
        if tag in ('if', 'unless'):
            c = condition(args, ctx)
            if tag == 'unless': c = not c
            out.append(render_nodes(n['children'] if c else n['else'], ctx))
        elif tag == 'for':
            m = re.match(r'(\w+)\s+in\s+(\S+)(.*)', args)
            var, coll, rest = m.groups()
            items = evaluate(coll, ctx) or []
            lim = re.search(r'limit:\s*(\d+)', rest)
            if lim: items = items[:int(lim.group(1))]
            for it in items:
                ctx[var] = it
                out.append(render_nodes(n['children'], ctx))
        elif tag == 'assign':
            var, _, expr = args.partition('=')
            ctx[var.strip()] = evaluate(expr.strip(), ctx)
        elif tag == 'include':
            fname, *kv = args.split()
            params = {}
            for p in kv:
                k, _, v = p.partition('=')
                params[k] = evaluate(v, ctx)
            src = open(os.path.join(ROOT, '_includes', fname), encoding='utf-8').read()
            saved = ctx.get('include'); ctx['include'] = params
            out.append(render_nodes(parse(src), ctx))
            ctx['include'] = saved
        else:
            raise ValueError('unsupported tag ' + tag)
    return ''.join(out)


def liquid(src, ctx):
    return render_nodes(parse(src), ctx)


# ---------------------------------------------------------------- Jekyll-lite
def read_doc(path):
    s = open(path, encoding='utf-8').read()
    m = re.match(r'---\s*\n(.*?)\n---\s*\n?(.*)', s, re.S)
    return (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else (None, s)


def out_path(url):
    u = url.lstrip('/')
    if u == '' or u.endswith('/'): u += 'index.html'
    elif not os.path.splitext(u)[1]: u += '.html'
    return os.path.join(OUT, *u.split('/'))


def local_links(s):
    """Make root-relative links work over file:// (add .html / index.html)."""
    def fix(m):
        attr, url = m.group(1), m.group(2)
        path, sep, frag = url.partition('#')
        rel = path[len(BASE):]
        if rel in ('', '/'): rel = '/index.html'
        elif rel.endswith('/'): rel += 'index.html'
        elif not os.path.splitext(rel)[1]: rel += '.html'
        return f'{attr}="{BASE}{rel}{sep}{frag}"'
    return re.sub(r'(href)="(' + re.escape(BASE) + r'[^"]*)"', fix, s)


def build(base=BASE):
    cfg = yaml.safe_load(open(os.path.join(ROOT, '_config.yml'), encoding='utf-8'))
    site = dict(cfg); site['baseurl'] = base
    site['data'] = {os.path.splitext(os.path.basename(f))[0]: yaml.safe_load(open(f, encoding='utf-8'))
                    for f in glob.glob(os.path.join(ROOT, '_data', '*.yml'))}
    skip_dirs = {'_site', '_build', '_source', '_shots', '_layouts', '_includes', '_data', '_posts', 'assets', '.git'}
    docs = []
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        for f in files:
            if f.endswith('.html'):
                fm, body = read_doc(os.path.join(dirpath, f))
                if fm is not None:
                    rel = os.path.relpath(os.path.join(dirpath, f), ROOT).replace('\\', '/')
                    fm.setdefault('url', fm.get('permalink') or '/' + rel)
                    docs.append((fm, body))
    posts = []
    for f in sorted(glob.glob(os.path.join(ROOT, '_posts', '*.html'))):
        fm, body = read_doc(f)
        fm['url'] = fm.get('permalink')
        fm['date'] = to_date(fm['date'])
        posts.append((fm, body))
    posts.sort(key=lambda p: p[0]['date'], reverse=True)
    site['posts'] = [p[0] for p in posts]

    if os.path.exists(OUT): shutil.rmtree(OUT, ignore_errors=True)   # a folder Windows still has open is skipped
    shutil.copytree(os.path.join(ROOT, 'assets'), os.path.join(OUT, 'assets'), dirs_exist_ok=True)
    layouts = {os.path.splitext(os.path.basename(f))[0]: read_doc(f) for f in glob.glob(os.path.join(ROOT, '_layouts', '*.html'))}

    built = []
    for fm, body in docs + posts:
        ctx = {'site': site, 'page': fm}
        content = liquid(body, ctx)
        lay = fm.get('layout')
        while lay:
            lfm, lbody = layouts[lay]
            ctx['content'] = content
            content = liquid(lbody, ctx)
            lay = (lfm or {}).get('layout')
        dest = out_path(fm['url'])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'w', encoding='utf-8').write(local_links(content) if base == BASE else content)
        built.append(fm['url'])
    return built


if __name__ == '__main__':
    b = build()
    print(len(b), 'pages built into', OUT)
