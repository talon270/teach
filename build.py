"""Fix links in the mirrored pages and generate the landing page index.html."""
import html, os, re, datetime, urllib.parse, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
SEM = "Monsoon 2026"
NOTES_RE = re.compile(r'(?:\.\./)+Notes/Monsoon%202026%20-%201/')

def title_of(path, default):
    try:
        t = re.search(r'<title>(.*?)</title>', open(path, encoding='utf8').read(), re.S)
        return html.unescape(t.group(1).strip()) if t else default
    except OSError:
        return default

courses = sorted(d for d in os.listdir('.') if os.path.isfile(os.path.join(d, 'index.html')))

# 1. rewrite links to the notes folder (they point outside the repo in the source tree)
for c in courses:
    for f in glob.glob(f'{c}/**/*.html', recursive=True):
        depth = f.count('/')
        s = open(f, encoding='utf8').read()
        n = NOTES_RE.sub('../' * depth + 'notes/', s)
        if n != s:
            open(f, 'w', encoding='utf8').write(n)

# 2. gather items
def mtime(p): return os.path.getmtime(p)
data, recent = [], []
for c in courses:
    lessons = []
    for f in sorted(glob.glob(f'{c}/lessons/*.html')):
        name = os.path.basename(f)
        m = re.match(r'(\d+)-', name)
        lessons.append((f, (m.group(1).lstrip('0') or '0') + ' · ' + title_of(f, name)))
    refs = [(f, title_of(f, os.path.basename(f))) for f in sorted(glob.glob(f'{c}/reference/*.html'))]
    notes = [(f, title_of(f, os.path.basename(f)[:-5])) for f in sorted(glob.glob(f'notes/{c}/*.html'))]
    data.append((c, f'{c}/index.html', lessons, refs, notes))
    for kind, items in (('Lesson', lessons), ('Reference', refs), ('Notes', notes)):
        for f, t in items:
            recent.append((mtime(f), c, kind, f, t))
recent.sort(reverse=True)

# 3. fonts: reuse the @font-face rules (data: URIs) from the day plan so the page works offline
fonts = ''
if os.path.exists('plan.html'):
    fonts = ''.join(re.findall(r'@font-face\s*\{.*?\}', open('plan.html', encoding='utf8').read(), re.S))

def esc(s): return html.escape(s, quote=True)
def href(p): return urllib.parse.quote(p)
def li(p, t): return f'<li><a href="{href(p)}">{esc(t)}</a></li>'

blocks = []
for c, idx, lessons, refs, notes in data:
    parts = []
    for label, items in (('Lessons', lessons), ('Reference', refs), ('Notes and drills', notes)):
        if items:
            parts.append(f'<h3>{label} <span class="n">{len(items)}</span></h3><ul>' + ''.join(li(p, t) for p, t in items) + '</ul>')
    blocks.append(f'<section class="course" id="{esc(c)}"><h2><a href="{href(idx)}">{esc(c)}</a>'
                  f'<span class="m">{len(lessons)} lessons · {len(notes)} notes</span></h2>' + ''.join(parts) + '</section>')

rec = ''.join(
    f'<li><span class="c">{esc(c)}</span><a href="{href(f)}">{esc(t)}</a>'
    f'<span class="d">{esc(k)} · {datetime.date.fromtimestamp(m).isoformat()}</span></li>'
    for m, c, k, f, t in recent[:10])
nav = ''.join(f'<a href="#{esc(c)}">{esc(c)}</a>' for c, *_ in data)
total = sum(len(l) + len(r) + len(n) for _, _, l, r, n in data)
today = datetime.date.today().isoformat()

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teach · {SEM}</title>
<style>
{fonts}
:root {{ --bg:#f8efd9; --surface:#fff; --ink:#111; --muted:#4a443b; --accent:#e23a28; --accent-soft:#ffd9cf;
  --bw:3px; --sh:5px 5px 0 var(--ink); --r:10px;
  --display:"Archivo Black","Arial Black",sans-serif; --body:"Inter","Helvetica Neue",Arial,sans-serif; color-scheme:light; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 var(--body); }}
main {{ max-width:60rem; margin:0 auto; padding:2rem 1rem 4rem; }}
h1 {{ font:2.6rem/1.05 var(--display); margin:.4rem 0 .6rem; }}
h2 {{ font:1.5rem/1.2 var(--display); margin:0 0 .6rem; display:flex; flex-wrap:wrap; gap:.4rem 1rem; align-items:baseline; }}
h3 {{ font:600 .85rem/1 var(--body); text-transform:uppercase; letter-spacing:.06em; margin:1.1rem 0 .4rem; color:var(--muted); }}
a {{ color:var(--ink); text-decoration-thickness:2px; text-underline-offset:3px; }}
a:hover, a:focus-visible {{ background:var(--accent-soft); outline:none; }}
.lede {{ color:var(--muted); max-width:40rem; }}
.top {{ display:flex; flex-wrap:wrap; gap:.6rem; margin:1rem 0 1.6rem; }}
.top a {{ border:var(--bw) solid var(--ink); border-radius:var(--r); background:var(--surface); padding:.35rem .8rem; font-weight:600; text-decoration:none; box-shadow:3px 3px 0 var(--ink); }}
.top a.plan {{ background:var(--accent); color:#fff; }}
.top a:hover {{ background:var(--accent-soft); }}
.top a.plan:hover {{ background:#c92f1f; }}
.card, .course {{ background:var(--surface); border:var(--bw) solid var(--ink); border-radius:var(--r); box-shadow:var(--sh); padding:1.1rem 1.3rem; margin:0 0 1.6rem; }}
.m, .n, .d {{ font:500 .8rem var(--body); color:var(--muted); }}
ul {{ margin:0; padding-left:1.1rem; columns:2 18rem; column-gap:2rem; }}
li {{ break-inside:avoid; margin:.15rem 0; }}
.recent {{ list-style:none; padding:0; columns:1; }}
.recent li {{ display:flex; flex-wrap:wrap; gap:.2rem .7rem; align-items:baseline; }}
.c {{ background:var(--ink); color:var(--bg); border-radius:6px; padding:0 .45rem; font:600 .75rem var(--body); }}
footer {{ color:var(--muted); font-size:.85rem; }}
@media (max-width:30rem) {{ h1 {{ font-size:2rem; }} }}
</style>
</head>
<body>
<main>
<h1>Teach · {SEM}</h1>
<p class="lede">Every lesson, reference page, drill and study note, by course. {total} pages. This page is rebuilt each time new material is published.</p>
<nav class="top" aria-label="Courses"><a class="plan" href="plan.html">Day plan</a>{nav}</nav>
<section class="card"><h2>Newest</h2><ul class="recent">{rec}</ul></section>
{''.join(blocks)}
<footer>Rebuilt {today}. Course readings (PDFs) are not published, so links to them do not open here.</footer>
</main>
</body>
</html>
'''
open('index.html', 'w', encoding='utf8').write(page)

# 4. report links that do not resolve (course PDFs are expected to be missing)
bad = {}
for f in glob.glob('**/*.html', recursive=True):
    for m in re.findall(r'(?:href|src)="([^"#]+)"', open(f, encoding='utf8').read()):
        if re.match(r'(data:|https?:|mailto:)', m): continue
        p = os.path.normpath(os.path.join(os.path.dirname(f), urllib.parse.unquote(m.replace('&amp;', '&'))))
        if not os.path.exists(p):
            bad.setdefault(os.path.splitext(p)[1] or 'other', []).append((f, m))
print('pages:', total, '| broken links by type:', {k: len(v) for k, v in bad.items()} or 'none')
for k, v in bad.items():
    if k not in ('.pdf', '.docx', '.pptx', '.ppt', '.doc', '.xlsx'):
        for f, m in v[:15]: print('  UNEXPECTED', f, '->', m)
