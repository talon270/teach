"""Fix links in the mirrored pages and generate the landing page index.html."""
import html, os, re, datetime, urllib.parse, glob, json

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

def write_keep(path, text):
    st = os.stat(path)
    open(path, 'w', encoding='utf8').write(text)
    os.utime(path, (st.st_atime, st.st_mtime))

courses = sorted(d for d in os.listdir('.') if os.path.isfile(os.path.join(d, 'index.html')))

# 1. rewrite links to the notes folder (they point outside the repo in the source tree)
for c in courses:
    for f in glob.glob(f'{c}/**/*.html', recursive=True):
        depth = f.count('/')
        s = open(f, encoding='utf8').read()
        n = NOTES_RE.sub('../' * depth + 'notes/', s)
        if n != s:
            write_keep(f, n)

# 1b. each course map links the day plan as "../index.html", which is the plan in the source
# tree but the landing page here (the plan is published as plan.html)
for c in courses:
    f = f'{c}/index.html'
    s = open(f, encoding='utf8').read()
    n = s.replace('href="../index.html"', 'href="../plan.html"')
    if n != s:
        write_keep(f, n)

# 2. gather items
# Labels say what the page covers. A lesson drops the course code its card already shows
# ("FAC102 · What accounting is" -> "What accounting is"). A note is labelled from its filename,
# which carries the week and the reading ("B07 Ghosh - Inferential statistics..."). The page
# <title> is often an invented name ("Chance on Trial"), so it is shown, small, only when the
# filename has no "<source> - <topic>" part to say what the page covers ("Slides 1-2").
REVISION_RE = re.compile(r'cheat sheet|formula sheet|revision|crash course|study guide|course drill', re.I)

def strip_course(t, c):
    return re.sub(rf'^{re.escape(c)}\s*·\s*', '', t)

def norm(t): return re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()

def note_item(f, c):
    stem = os.path.basename(f)[:-5]
    label = re.sub(rf'^{re.escape(c)}\s+', '', stem).replace(' - ', ' — ')
    sub = strip_course(re.sub(r'\s*\|\s*' + re.escape(c) + r'$', '', title_of(f, '')), c)
    if ' - ' in stem or not sub or norm(sub) in norm(stem) or norm(stem) in norm(sub):
        sub = ''
    return (f, label, sub)

def natural(p):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', os.path.basename(p))]

data = []
for c in courses:
    lessons = []
    for f in sorted(glob.glob(f'{c}/lessons/*.html')):
        name = os.path.basename(f)
        m = re.match(r'(\d+)-', name)
        lessons.append((f, (m.group(1).lstrip('0') or '0') + ' · ' + strip_course(title_of(f, name), c), ''))
    refs = [(f, strip_course(title_of(f, os.path.basename(f)), c), '') for f in sorted(glob.glob(f'{c}/reference/*.html'))]
    notes = [note_item(f, c) for f in sorted(glob.glob(f'notes/{c}/*.html'), key=natural)]
    revision = [n for n in notes if REVISION_RE.search(n[1] + ' ' + n[2])]
    weekly = [n for n in notes if n not in revision]
    data.append((c, f'{c}/index.html', lessons, refs, revision, weekly))

# 3. fonts: reuse the @font-face rules (data: URIs) from the day plan so the page works offline
fonts = ''
if os.path.exists('plan.html'):
    fonts = ''.join(re.findall(r'@font-face\s*\{.*?\}', open('plan.html', encoding='utf8').read(), re.S))

def esc(s): return html.escape(s, quote=True)
def href(p): return urllib.parse.quote(p)
def li(p, t, sub=''):
    return f'<li><a href="{href(p)}">{esc(t)}</a>' + (f' <span class="sub">{esc(sub)}</span>' if sub else '') + '</li>'

# The Today card: plan.html carries its days as JSON (written by plan.py). The card picks the
# viewer's local date in the browser, so a page built on Monday still shows Thursday on Thursday.
# Ticks go to the plan's own localStorage key: one store, never a second copy.
plan_json, plan_data = 'null', {}
if os.path.exists('plan.html'):
    m = re.search(r'<script type="application/json" id="plan-data">(.*?)</script>', open('plan.html', encoding='utf8').read(), re.S)
    if m:
        plan_data = json.loads(m.group(1).replace('<\\/', '</'))  # fail the build here, not in the browser
        plan_json = m.group(1)
# End-sem scope per course, written in plan.py next to the exam dates (one source).
SCOPE = plan_data.get('scope', {})

blocks = []
for c, idx, lessons, refs, revision, weekly in data:
    parts = []
    for label, items in (('Lessons', lessons), ('Reference', refs), ('Cheat sheets and revision', revision), ('Notes and drills, by week', weekly)):
        if items:
            parts.append(f'<h3>{label} <span class="n">{len(items)}</span></h3><ul>' + ''.join(li(*x) for x in items) + '</ul>')
    blocks.append(f'<section class="course" id="{esc(c)}"><h2><a href="{href(idx)}">{esc(c)}</a>'
                  f'<span class="m">{len(lessons)} lessons · {len(revision) + len(weekly)} notes</span></h2>'
                  + (f'<p class="scope">{esc(SCOPE[c])}</p>' if c in SCOPE else '') + ''.join(parts) + '</section>')

nav = ''.join(f'<a href="#{esc(c)}">{esc(c)}</a>' for c, *_ in data)
total = sum(len(l) + len(r) + len(a) + len(b) for _, _, l, r, a, b in data)
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
.m, .n {{ font:500 .8rem var(--body); color:var(--muted); }}
ul {{ margin:0; padding-left:1.1rem; columns:2 18rem; column-gap:2rem; }}
li {{ break-inside:avoid; margin:.15rem 0; }}
.sub {{ font:500 .8rem var(--body); color:var(--muted); }}
.scope {{ margin:.2rem 0 .4rem; padding:.45rem .7rem; border-left:4px solid var(--accent); background:var(--accent-soft); font-size:.92rem; max-width:52rem; }}
.today h2 .when {{ font:500 1rem var(--body); color:var(--muted); }}
.exams {{ display:flex; flex-wrap:wrap; gap:.5rem; margin:.2rem 0 .9rem; padding:0; list-style:none; columns:1; }}
.exams li {{ border:2px solid var(--ink); border-radius:6px; padding:.15rem .55rem; font:600 .85rem var(--body); margin:0; }}
.exams li.soon {{ background:var(--ink); color:var(--bg); border-color:var(--ink); outline:2px solid var(--accent); outline-offset:1px; }}
.tasks {{ list-style:none; padding:0; columns:1; }}
.tasks li {{ margin:0; border-top:1px solid color-mix(in srgb, var(--ink) 18%, transparent); }}
.tasks li:first-child {{ border-top:0; }}
.tasks label {{ display:grid; grid-template-columns:26px 5.5rem 1fr; gap:.6rem; align-items:start; padding:.5rem 0; min-height:44px; cursor:pointer; }}
.tasks input {{ width:20px; height:20px; margin:.15rem 0 0; accent-color:var(--accent); cursor:pointer; }}
.tasks .tag {{ font:700 .75rem/1.9 var(--body); letter-spacing:.04em; }}
.tasks li.extra .tag {{ color:var(--muted); }}
.tasks li.done .body, .tasks li.done .body a {{ text-decoration:line-through; color:var(--muted); }}
.today .foot {{ margin:.7rem 0 0; font-size:.9rem; color:var(--muted); }}
.today .foot a {{ font-weight:600; }}
@media (max-width:30rem) {{ .tasks label {{ grid-template-columns:26px 1fr; }} .tasks .body {{ grid-column:2; }} }}
footer {{ color:var(--muted); font-size:.85rem; }}
@media (max-width:30rem) {{ h1 {{ font-size:2rem; }} }}
</style>
</head>
<body>
<main>
<h1>Teach · {SEM}</h1>
<p class="lede">Every lesson, reference page, drill and study note, by course. {total} pages. This page is rebuilt each time new material is published.</p>
<nav class="top" aria-label="Courses"><a class="plan" href="plan.html">Day plan</a>{nav}</nav>
<section class="card today" id="today" aria-live="polite"><h2>Today</h2><p class="foot">Loading the day plan.</p></section>
{''.join(blocks)}
<script type="application/json" id="plan-data">{plan_json}</script>
<script>
(function () {{
  "use strict";
  const box = document.getElementById("today");
  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({{"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}})[ch]);
  let plan = null;
  try {{ plan = JSON.parse(document.getElementById("plan-data").textContent); }} catch (e) {{ plan = null; }}
  if (!plan || !plan.days || !plan.days.length) {{
    box.innerHTML = '<h2>Today</h2><p class="foot">The day plan was not found when this page was built. <a href="plan.html">Open the day plan</a>.</p>';
    return;
  }}
  // Local date, never UTC: at 01:00 IST the UTC date is still yesterday.
  const t = new Date(), pad = (x) => String(x).padStart(2, "0");
  const iso = (d) => `${{d.getFullYear()}}-${{pad(d.getMonth() + 1)}}-${{pad(d.getDate())}}`;
  const today = iso(t);
  const dayDiff = (a) => Math.round((new Date(a + "T00:00") - new Date(today + "T00:00")) / 864e5);
  let state = {{}};
  try {{ state = JSON.parse(localStorage.getItem(plan.key) || "{{}}"); }} catch (e) {{ state = {{}}; }}
  const save = () => {{ try {{ localStorage.setItem(plan.key, JSON.stringify(state)); }} catch (e) {{}} }};

  const exams = (plan.exams || []).filter((x) => dayDiff(x.date) >= 0).map((x) => {{
    const n = dayDiff(x.date);
    const when = n === 0 ? "today" : n === 1 ? "tomorrow" : `in ${{n}} days`;
    const d = new Date(x.date + "T00:00").toLocaleDateString("en-GB", {{ weekday: "short", day: "numeric", month: "short" }});
    return `<li class="${{n <= 2 ? "soon" : ""}}">${{esc(x.course)}} ${{esc(x.what)}} · ${{d}}${{x.time ? " " + esc(x.time) : ""}} · ${{when}}</li>`;
  }}).join("");
  const examList = exams ? `<ul class="exams" aria-label="Tests">${{exams}}</ul>` : "";

  const first = plan.days[0].date, last = plan.days[plan.days.length - 1].date;
  const day = plan.days.find((d) => d.date === today);
  if (!day) {{
    const msg = today < first
      ? `The day plan starts on ${{esc(plan.days[0].label)}}.`
      : `The day plan ended on ${{esc(plan.days[plan.days.length - 1].label)}}. Nothing is scheduled for today.`;
    box.innerHTML = `<h2>Today</h2>${{examList}}<p class="foot">${{msg}} <a href="plan.html">Open the day plan</a>.</p>`;
    return;
  }}
  const past = plan.days.filter((d) => d.date < today);
  const render = () => {{
    const missed = past.reduce((m, d) => m + d.items.filter((i) => !i.extra && !state[i.k]).length, 0);
    const rows = day.items.map((i) => `<li class="${{i.extra ? "extra" : ""}}${{state[i.k] ? " done" : ""}}"><label>`
      + `<input type="checkbox" data-k="${{esc(i.k)}}"${{state[i.k] ? " checked" : ""}}>`
      + `<span class="tag">${{esc(i.tag)}}</span><span class="body">${{i.html}}</span></label></li>`).join("");
    const back = past.length
      ? (missed ? `${{missed}} core item${{missed > 1 ? "s" : ""}} from earlier days not ticked. ` : "Every core item from earlier days is ticked. ")
      : "";
    box.innerHTML = `<h2>Today <span class="when">${{esc(day.label)}} · about ${{day.mins}} min + extra</span></h2>${{examList}}`
      + `<ul class="tasks">${{rows}}</ul><p class="foot">${{back}}<a href="plan.html#today">Open the day plan</a></p>`;
    box.querySelectorAll(".tasks input").forEach((b) => b.addEventListener("change", () => {{
      state[b.dataset.k] = b.checked; save(); render();
      const again = box.querySelector(`input[data-k="${{b.dataset.k}}"]`); if (again) again.focus();
    }}));
  }};
  render();
}})();
</script>
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


# 5. dark theme: injected into every published page that is light (the source files stay untouched)
THEME_CSS = """
html[data-theme="dark"]{color-scheme:dark;--bg:#16120e;--surface:#211c16;--surface-2:#1a1611;--ink:#eadfc6;--muted:#b1a58d;
--accent:#ff6a55;--accent-ink:#16120e;--accent-soft:#4a2b23;--term:#0a0907;--term-ink:#eadfc6;--sh:5px 5px 0 #000;--sh-sm:3px 3px 0 #000}
html[data-theme="dark"] :is(.chip.dark,th,.opt.right){color:#16120e}
html[data-theme="dark"] body{background:var(--bg);color:var(--ink)}
html[data-theme="dark"] ::selection{background:#ff6a55;color:#16120e}
#teach-theme-btn{position:fixed;right:12px;bottom:12px;z-index:99999;font:600 13px/1 system-ui,sans-serif;padding:9px 13px;
border-radius:999px;border:2px solid #111;background:#fff;color:#111;cursor:pointer;box-shadow:2px 2px 0 #111;opacity:.9}
#teach-theme-btn:hover,#teach-theme-btn:focus-visible{opacity:1;outline:2px solid #e23a28;outline-offset:2px}
html[data-theme="dark"] .teach-nav a{background:#eadfc6;color:#16120e;border-color:#000;box-shadow:2px 2px 0 #000}
html[data-theme="dark"] #teach-theme-btn{background:#eadfc6;color:#16120e;border-color:#000;box-shadow:2px 2px 0 #000}
@media print{#teach-theme-btn{display:none}}
"""
def theme_js(mode):
    return ("(function(){var d=document.documentElement,K='teach-theme',t=null;"
            "try{t=localStorage.getItem(K)}catch(e){}"
            "if(!t&&window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)t='dark';"
            f"d.setAttribute('data-tmode','{mode}');if(t==='dark')d.setAttribute('data-theme','dark');"
            "document.addEventListener('DOMContentLoaded',function(){var b=document.createElement('button');b.id='teach-theme-btn';b.type='button';"
            "function lab(){var dk=d.getAttribute('data-theme')==='dark';b.textContent=dk?'Light mode':'Dark mode';b.setAttribute('aria-pressed',dk)}"
            "b.onclick=function(){var dk=d.getAttribute('data-theme')==='dark';if(dk)d.removeAttribute('data-theme');else d.setAttribute('data-theme','dark');"
            "try{localStorage.setItem(K,dk?'light':'dark')}catch(e){}lab()};lab();document.body.appendChild(b)})})();")
MARK = re.compile(r'<!--teach-theme-->.*?<!--/teach-theme-->', re.S)

def lum(hexs):
    h = hexs.lstrip('#')
    if len(h) == 3: h = ''.join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

def classify(src):
    """tokens = pages on the shared cream token set; skip = anything else (own theme, own dark look, other palette)."""
    if re.search(r'data-theme|prefers-color-scheme|color-scheme:\s*dark', src):
        return 'skip'
    if re.search(r'--bg:\s*#f8efd9', src, re.I) or 'assets/lesson.css' in src:
        return 'tokens'
    return 'skip'

counts = {'tokens': 0, 'skip': 0}
for f in glob.glob('**/*.html', recursive=True):
    src = MARK.sub('', open(f, encoding='utf8').read())
    mode = classify(src)
    counts[mode] += 1
    if mode == 'skip':
        out = src
    else:
        block = f'<!--teach-theme--><style>{THEME_CSS}</style><script>{theme_js(mode)}</script><!--/teach-theme-->'
        out = src.replace('</head>', block + '</head>', 1) if '</head>' in src else block + src
    if out != open(f, encoding='utf8').read():
        write_keep(f, out)
print('dark mode:', counts)


# 6. site navigation: a bar at the top and the bottom of every published page except the landing
# page. "Back" returns to the previous page when you came from inside the site, and otherwise to
# the page one level up, so it never leaves the site. The bar is a plain block in the flow (not
# fixed, not a <nav>): 13 pages style `nav` as sticky and many have sticky top bars of their own.
NAV_CSS = """
.teach-nav{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 12px;margin:0;font:600 13px/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;position:static;background:transparent;border:0}
.teach-nav a{all:unset;display:inline-block;padding:7px 12px;min-height:16px;border-radius:999px;border:2px solid #111;background:#fff;color:#111;
box-shadow:2px 2px 0 #111;cursor:pointer;text-decoration:none;font:inherit;white-space:nowrap}
.teach-nav a:hover{background:#ffd9cf}
.teach-nav a:focus-visible{outline:2px solid #e23a28;outline-offset:2px}
@media print{.teach-nav{display:none}}
"""
NAV_JS = ("document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[data-teach-back]');if(!a)return;"
          "var r=document.referrer;try{if(r&&new URL(r).origin===location.origin&&history.length>1){e.preventDefault();history.back()}}catch(x){}});")
NAV = re.compile(r'<!--teach-nav-->.*?<!--/teach-nav-->', re.S)

def nav_links(f):
    parts = f.split('/')
    up = '../' * (len(parts) - 1)
    home, plan = up + 'index.html', up + 'plan.html'
    if f == 'plan.html':
        return [('&larr; Back', home, True), ('All courses', home, False)]
    if len(parts) == 2 and parts[1] == 'index.html':          # a course map
        return [('&larr; Back', home, True), ('All courses', home, False), ('Day plan', plan, False)]
    c = parts[1] if parts[0] == 'notes' else parts[0]
    cmap = up + f'{c}/index.html'
    return [('&larr; Back', cmap, True), (f'{esc(c)} course map', cmap, False), ('All courses', home, False)]

def nav_bar(f, where):
    links = ''.join(f'<a href="{href(u)}"' + (' data-teach-back' if back else '') + f'>{t}</a>' for t, u, back in nav_links(f))
    return f'<!--teach-nav--><div class="teach-nav" role="navigation" aria-label="Site, {where}">{links}</div><!--/teach-nav-->'

FIRST_BODY = re.compile(r'<style\b.*?</style>|<script\b.*?</script>|<!--.*?-->|<!doctype[^>]*>|<html[^>]*>|<head[^e>][^>]*>|<head>|'
                        r'<(?!(?:meta|title|link|base|style|script|noscript)\b)([a-z][a-z0-9]*)\b', re.S | re.I)
nav_count, nav_skipped = 0, []
for f in glob.glob('**/*.html', recursive=True):
    if f == 'index.html':
        continue
    cur = open(f, encoding='utf8').read()
    src = NAV.sub('', cur)
    head = f'<!--teach-nav--><style>{NAV_CSS}</style><script>{NAV_JS}</script><!--/teach-nav-->'
    if re.search(r'<body[^>]*>', src) and '</body>' in src and '</head>' in src:
        out = src.replace('</head>', head + '</head>', 1)
        m = re.search(r'<body[^>]*>', out)
        out = out[:m.end()] + nav_bar(f, 'top') + out[m.end():]
        i = out.rindex('</body>')
        out = out[:i] + nav_bar(f, 'bottom') + out[i:]
    else:
        # A fragment page (34 notes): no <head> or <body> tags. The top bar goes before the first
        # element that is not head content; the CSS goes at the end, so <meta charset> stays in
        # the first 1024 bytes.
        m = next((x for x in FIRST_BODY.finditer(src) if x.group(1)), None)
        if not m:
            nav_skipped.append(f)
            continue
        out = src[:m.start()] + nav_bar(f, 'top') + src[m.start():] + nav_bar(f, 'bottom') + head
    nav_count += 1
    if out != cur:
        write_keep(f, out)
print('nav bars:', nav_count, 'pages | skipped (no body/head tag):', nav_skipped or 'none')
