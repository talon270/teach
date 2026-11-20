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

# The day plan's data: plan.html carries its days, tests, scope and tick key as JSON (written by
# plan.py). The dashboard picks the viewer's local date in the browser, so a page built on Monday
# still shows Thursday on Thursday. Ticks go to the plan's own localStorage key: one store.
plan_json, plan_data = 'null', {}
if os.path.exists('plan.html'):
    m = re.search(r'<script type="application/json" id="plan-data">(.*?)</script>', open('plan.html', encoding='utf8').read(), re.S)
    if m:
        plan_data = json.loads(m.group(1).replace('<\\/', '</'))  # fail the build here, not in the browser
        plan_json = m.group(1)
SCOPE = plan_data.get('scope', {})              # end-sem scope per course, from plan.py
PLAN_COURSES = plan_data.get('courses', [])     # courses on the day plan, from plan.py
OFF = {p for v in plan_data.get('off', {}).values() for p in v}   # lessons not on the end-sem
EXAMS = plan_data.get('exams', [])

# Tracking. Every published page except this one records, in this browser only (localStorage
# key teach-track-v1): visits, active minutes per day, and each finished lesson quiz (score and
# date). Active time counts only while the tab is visible and the reader did something in the
# last 3 minutes. A quiz is finished when every question in the page's kit quizzes is answered.
# teachTrack.auto(plan) ticks a day-plan item from these records by the item's "auto" rule
# (plan.py box()), and only when the item was never ticked or unticked by hand.
TRACK_JS = r"""(function(){"use strict";
var K="teach-track-v1",P=__PATH__;
function rd(){try{var s=JSON.parse(localStorage.getItem(K)||"{}");return s&&typeof s==="object"?s:{}}catch(e){return{}}}
function wr(s){try{localStorage.setItem(K,JSON.stringify(s));return true}catch(e){return false}}
function pad(x){return String(x).padStart(2,"0")}
function day(t){t=t||new Date();return t.getFullYear()+"-"+pad(t.getMonth()+1)+"-"+pad(t.getDate())}
function upd(fn){var s=rd();s.v=1;s.pages=s.pages||{};s.days=s.days||{};var pg=s.pages[P]=s.pages[P]||{visits:0,secs:0};fn(s,pg);wr(s)}
function quizDays(pages,p){return((pages[p]||{}).quiz||[]).map(function(a){return a.d})}
function auto(plan){
  var T=rd(),st={};try{st=JSON.parse(localStorage.getItem(plan.key)||"{}")||{}}catch(e){st={}}
  var pages=T.pages||{},days=T.days||{},done=T.auto||{},changed=false;
  function ok(a,date){
    if(a.lessons)return a.lessons.length>0&&a.lessons.every(function(p){return quizDays(pages,p).some(function(d){return!a.since||d>=date})});
    if(a.course){
      var lp=a.course+"/lessons/",np="notes/"+a.course+"/",p,d,q,s;
      for(p in pages)if(p.indexOf(lp)===0&&quizDays(pages,p).some(function(d){return d>=date}))return true;
      for(d in days)if(d>=date){s=0;for(q in(days[d].pages||{}))if(q.indexOf(np)===0)s+=days[d].pages[q];if(s>=300)return true}
    }
    return false}
  plan.days.forEach(function(D){D.items.forEach(function(it){
    if(it.auto&&!(it.k in st)&&ok(it.auto,D.date)){st[it.k]=true;done[it.k]=1;changed=true}})});
  if(changed){try{localStorage.setItem(plan.key,JSON.stringify(st))}catch(e){}T.auto=done;wr(T)}
  return done}
window.teachTrack={key:K,read:rd,write:wr,day:day,auto:auto};
if(!P)return;
upd(function(s,pg){var n=Date.now();pg.visits++;pg.first=pg.first||n;pg.last=n});
var seen=Date.now(),last=Date.now();
["pointerdown","keydown","scroll","wheel","touchstart","input"].forEach(function(e){addEventListener(e,function(){seen=Date.now()},{passive:true,capture:true})});
setInterval(function(){var n=Date.now(),dt=Math.min(n-last,20000);last=n;
  if(document.visibilityState!=="visible"||n-seen>180000)return;
  var sec=Math.round(dt/1000);
  upd(function(s,pg){var d=day(),D=s.days[d]=s.days[d]||{secs:0,pages:{}};pg.secs+=sec;D.secs+=sec;D.pages[P]=(D.pages[P]||0)+sec})},15000);
var finished=false;
document.addEventListener("click",function(e){
  if(finished||!(e.target.closest&&e.target.closest("[data-quiz] .opt")))return;
  setTimeout(function(){
    var qs=[].slice.call(document.querySelectorAll("[data-quiz] .quiz-q"));
    if(!qs.length||qs.some(function(q){return!q.querySelector(".opt:disabled")}))return;
    finished=true;
    var wrong=qs.filter(function(q){return q.querySelector(".opt.wrong")}).length;
    upd(function(s,pg){pg.quiz=(pg.quiz||[]).concat([{t:Date.now(),d:day(),r:qs.length-wrong,n:qs.length}]).slice(-20)})},0)});
})();"""

def track_js(path):
    return TRACK_JS.replace('__PATH__', json.dumps(path))

# 3b. the dashboard (pre-rendered lists; the browser fills in status from the records)
exam_by = {}
for e in EXAMS:
    exam_by.setdefault(e['course'], []).append(e)

def item_li(p, t, sub=''):
    return (f'<li data-p="{esc(p)}"><a href="{href(p)}">{esc(t)}</a>' + (f' <span class="sub">{esc(sub)}</span>' if sub else '')
            + '<span class="st"></span></li>')

blocks = []
order = [x for x in data if x[0] in PLAN_COURSES] + [x for x in data if x[0] not in PLAN_COURSES]
for c, idx, lessons, refs, revision, weekly in order:
    inplan = c in PLAN_COURSES
    rows = ''.join(f'<li class="ls" data-p="{esc(p)}"' + (' data-off' if p in OFF else '') + f'><a href="{href(p)}">{esc(t)}</a><span class="st"></span></li>'
                   for p, t, _ in lessons)
    others = []
    for label, items in (('Reference', refs), ('Cheat sheets and revision', revision), ('Notes and drills, by week', weekly)):
        if items:
            others.append(f'<h4>{label} <span class="n">{len(items)}</span></h4><ul class="pages">' + ''.join(item_li(*x) for x in items) + '</ul>')
    n_other = len(refs) + len(revision) + len(weekly)
    tests = ''.join(f'<span class="test" data-date="{esc(e["date"])}">{esc(e["what"])} · {datetime.date.fromisoformat(e["date"]):%a %-d %b}<b></b></span>'
                    for e in exam_by.get(c, []))
    blocks.append(
        f'<section class="course card" id="{esc(c)}"' + (' data-plan' if inplan else '') + '>'
        f'<header><h2><a href="{href(idx)}">{esc(c)}</a></h2>'
        + ('' if inplan else '<span class="chip">Not on the day plan</span>') + f'{tests}</header>'
        + (f'<p class="scope">{esc(SCOPE[c])}</p>' if c in SCOPE else '')
        + (f'<div class="meter" aria-hidden="true"><i class="d"></i><i class="o"></i></div><p class="tally">{len(lessons)} lessons</p>' if lessons else '')
        + (f'<ol class="lessons">{rows}</ol>' if lessons else '')
        + (f'<details><summary>Reference, cheat sheets and notes <span class="n">{n_other}</span> <span class="seen"></span></summary>{"".join(others)}</details>' if others else '')
        + '</section>')

nav = ''.join(f'<a href="#{esc(c)}">{esc(c)}</a>' for c, *_ in order)
total = sum(len(l) + len(r) + len(a) + len(b) for _, _, l, r, a, b in data)
today = datetime.date.today().isoformat()

PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Teach · __SEM__</title>
<style>
__FONTS__
:root { --bg:#f8efd9; --surface:#fff; --ink:#111; --muted:#4a443b; --accent:#e23a28; --accent-soft:#ffd9cf;
  --bw:3px; --sh:5px 5px 0 var(--ink); --r:10px;
  --display:"Archivo Black","Arial Black",sans-serif; --body:"Inter","Helvetica Neue",Arial,sans-serif; color-scheme:light; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 var(--body); }
main { max-width:72rem; margin:0 auto; padding:1.6rem 1rem 4rem; }
h1 { font:2.4rem/1.05 var(--display); margin:.2rem 0 .4rem; text-wrap:balance; }
h2 { font:1.35rem/1.2 var(--display); margin:0; text-wrap:balance; }
h3 { font:700 .78rem/1.2 var(--body); text-transform:uppercase; letter-spacing:.07em; margin:0 0 .7rem; color:var(--muted); }
h4 { font:600 .8rem/1 var(--body); text-transform:uppercase; letter-spacing:.06em; margin:1rem 0 .4rem; color:var(--muted); }
p { text-wrap:pretty; }
a { color:var(--ink); text-decoration-thickness:2px; text-underline-offset:3px; }
a:hover, a:focus-visible { background:var(--accent-soft); outline:none; }
.lede { color:var(--muted); margin:0; max-width:44rem; }
.num, .n, .tally, .st, .test b, .kpi .big { font-variant-numeric:tabular-nums; }
.top { display:flex; flex-wrap:wrap; gap:.6rem; margin:1rem 0 1.4rem; }
.top a { border:var(--bw) solid var(--ink); border-radius:var(--r); background:var(--surface); padding:.35rem .8rem; font-weight:600; text-decoration:none; box-shadow:3px 3px 0 var(--ink); }
.top a.plan { background:var(--accent); color:var(--surface); }
.top a:hover { background:var(--accent-soft); }
.top a.plan:hover { background:#c92f1f; }
.card { background:var(--surface); border:var(--bw) solid var(--ink); border-radius:var(--r); box-shadow:var(--sh); padding:1rem 1.2rem; min-width:0; }
@supports (corner-shape: squircle) { .card, .top a { corner-shape:squircle; border-radius:18px; } }
.n, .sub { font:500 .8rem var(--body); color:var(--muted); }

/* KPI row */
.kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(12.5rem, 1fr)); gap:1rem; margin:0 0 1.4rem; }
.kpi { display:flex; flex-direction:column; gap:.15rem; }
.kpi h3 { margin:0; }
.kpi .big { font:2.1rem/1.1 var(--display); }
.kpi .big small { font:600 .95rem var(--body); color:var(--muted); margin-left:.25rem; }
.kpi .sub { font-size:.85rem; }
.kpi.alert { background:var(--ink); color:var(--bg); }
.kpi.alert h3, .kpi.alert .sub, .kpi.alert .big small { color:var(--bg); }
.bar { height:10px; border:2px solid var(--ink); border-radius:999px; overflow:hidden; margin:.35rem 0 .1rem; background:var(--bg); }
.bar i { display:block; height:100%; width:0; background:var(--accent); }

/* main grid */
.grid { display:grid; grid-template-columns:minmax(0, 1.55fr) minmax(0, 1fr); gap:1.4rem; align-items:start; margin-bottom:1.6rem; }
.side { display:grid; gap:1.4rem; }
@media (max-width:52rem) { .grid { grid-template-columns:minmax(0, 1fr); } }

/* Today */
.today h2 { display:flex; flex-wrap:wrap; gap:.3rem .8rem; align-items:baseline; margin-bottom:.4rem; }
.today h2 .when { font:500 .95rem var(--body); color:var(--muted); }
.tasks { list-style:none; padding:0; margin:0; }
.tasks li + li { border-top:1px solid color-mix(in srgb, var(--ink) 18%, transparent); }
.tasks label { display:grid; grid-template-columns:26px 5.2rem 1fr; gap:.6rem; align-items:start; padding:.5rem 0; min-height:44px; cursor:pointer; }
.tasks input { width:20px; height:20px; margin:.15rem 0 0; accent-color:var(--accent); cursor:pointer; }
.tasks .tag { font:700 .75rem/1.9 var(--body); letter-spacing:.04em; }
.tasks li.extra .tag { color:var(--muted); }
.tasks li.done .body, .tasks li.done .body a { text-decoration:line-through; color:var(--muted); }
.auto-mark { display:inline-block; margin-left:.4rem; font:700 .68rem/1 var(--body); letter-spacing:.05em; text-transform:uppercase; border:1.5px solid currentColor; border-radius:4px; padding:.15rem .3rem; text-decoration:none; vertical-align:1px; }
.today .foot { margin:.7rem 0 0; font-size:.88rem; color:var(--muted); }
.today .foot a { font-weight:600; }
@media (max-width:30rem) { .tasks label { grid-template-columns:26px 1fr; } .tasks .body { grid-column:2; } }

/* Tests */
.exams { list-style:none; margin:0; padding:0; display:grid; gap:.45rem; }
.exams li { display:grid; grid-template-columns:4.6rem 1fr; gap:.7rem; align-items:center; }
.exams .cd { font:700 .82rem/1 var(--body); text-align:center; border:2px solid var(--ink); border-radius:6px; padding:.35rem .2rem; font-variant-numeric:tabular-nums; }
.exams li.soon .cd { background:var(--ink); color:var(--bg); outline:2px solid var(--accent); outline-offset:1px; }
.exams .what { font-size:.92rem; }
.exams .what span { color:var(--muted); }

/* Study-time chart: HTML columns, one axis (minutes) */
.chart { position:relative; }
.cols { display:grid; grid-template-columns:repeat(14, minmax(0, 1fr)); gap:4px; height:130px; align-items:end; border-bottom:2px solid var(--ink); position:relative; }
.cols .gl { position:absolute; left:0; right:0; border-top:1px dashed color-mix(in srgb, var(--ink) 25%, transparent); pointer-events:none; }
.cols .gl span { position:absolute; right:0; top:-1.1rem; font:500 .7rem var(--body); color:var(--muted); }
.col { position:relative; height:100%; display:flex; align-items:flex-end; cursor:default; outline:none; }
.col::after { content:""; position:absolute; inset:-4px -2px; }
.col .b { width:100%; background:var(--ink); border-radius:4px 4px 0 0; min-height:0; }
.col .pl { position:absolute; left:-1px; right:-1px; height:0; border-top:3px solid var(--accent); }
.col.pre .b { background:transparent; }
.col.today .b { background:var(--accent); }
.col:hover .b, .col:focus-visible .b { outline:2px solid var(--accent); outline-offset:1px; }
.xl { display:grid; grid-template-columns:repeat(14, minmax(0, 1fr)); gap:4px; font:500 .68rem/1.4 var(--body); color:var(--muted); text-align:center; margin-top:.25rem; font-variant-numeric:tabular-nums; }
.legend { display:flex; flex-wrap:wrap; gap:.3rem 1rem; font-size:.8rem; color:var(--muted); margin:.6rem 0 0; }
.legend i { display:inline-block; width:12px; height:12px; border-radius:3px; background:var(--ink); vertical-align:-1px; margin-right:.35rem; }
.legend i.pl { height:0; border-top:3px solid var(--accent); border-radius:0; vertical-align:3px; background:none; }
.tip { position:absolute; z-index:5; pointer-events:none; background:var(--ink); color:var(--bg); font:500 .8rem/1.35 var(--body); padding:.4rem .55rem; border-radius:6px; white-space:nowrap; transform:translate(-50%, -100%); display:none; }
.empty { font-size:.88rem; color:var(--muted); margin:.4rem 0 0; }

/* Recent */
.recent { list-style:none; margin:0; padding:0; display:grid; gap:.35rem; font-size:.92rem; }
.recent li { display:flex; justify-content:space-between; gap:.8rem; }
.recent li a { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.recent li span { color:var(--muted); white-space:nowrap; font-size:.82rem; font-variant-numeric:tabular-nums; }

/* Courses */
.courses { display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 30rem), 1fr)); gap:1.4rem; }
.course header { display:flex; flex-wrap:wrap; gap:.4rem .6rem; align-items:center; margin-bottom:.5rem; }
.course header h2 { margin-right:auto; }
.chip, .test { font:600 .76rem/1 var(--body); border:2px solid var(--ink); border-radius:6px; padding:.3rem .45rem; }
.test b { font-weight:700; margin-left:.35rem; }
.test.soon { background:var(--ink); color:var(--bg); }
.test.past { opacity:.55; text-decoration:line-through; }
.chip { color:var(--muted); border-color:var(--muted); }
.scope { margin:.2rem 0 .6rem; padding:.45rem .7rem; border-left:4px solid var(--accent); background:var(--accent-soft); font-size:.88rem; }
.meter { display:flex; gap:2px; height:12px; border:2px solid var(--ink); border-radius:999px; overflow:hidden; background:var(--bg); }
.meter i { display:block; height:100%; width:0; }
.meter .d { background:var(--ink); }
.meter .o { background:var(--accent); }
.tally { font-size:.85rem; color:var(--muted); margin:.3rem 0 .6rem; }
.tally .k { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 .3rem 0 .1rem; vertical-align:-1px; }
.tally .k.d { background:var(--ink); } .tally .k.o { background:var(--accent); }
.lessons { list-style:none; margin:0; padding:0; }
.lessons li, .pages li { display:flex; gap:.6rem; align-items:baseline; justify-content:space-between; padding:.22rem 0; }
.lessons li a, .pages li a { min-width:0; }
.st { flex:none; font:600 .74rem/1.2 var(--body); color:var(--muted); white-space:nowrap; }
.st.done { color:var(--ink); }
.st.done::before { content:""; display:inline-block; width:.55rem; height:.55rem; border-radius:2px; background:var(--ink); margin-right:.3rem; }
.st.opened::before { content:""; display:inline-block; width:.55rem; height:.55rem; border-radius:2px; background:var(--accent); margin-right:.3rem; }
.lessons li[data-off] a { color:var(--muted); }
.pages { list-style:none; margin:0; padding:0; }
details { margin-top:.8rem; border-top:2px solid var(--ink); padding-top:.5rem; }
summary { cursor:pointer; font-weight:600; min-height:44px; display:flex; align-items:center; gap:.4rem; }
summary .seen { font:500 .8rem var(--body); color:var(--muted); }

/* Data */
.data { margin-top:1.6rem; display:flex; flex-wrap:wrap; gap:.6rem 1rem; align-items:center; font-size:.88rem; color:var(--muted); }
.data button, .data label.btn { font:600 .85rem var(--body); color:var(--ink); background:var(--surface); border:2px solid var(--ink); border-radius:8px; padding:.45rem .8rem; min-height:44px; cursor:pointer; box-shadow:2px 2px 0 var(--ink); }
.data button:hover, .data label.btn:hover, .data button:focus-visible, .data label.btn:focus-within { background:var(--accent-soft); }
.data input[type=file] { position:absolute; opacity:0; width:1px; height:1px; }
.data .msg { color:var(--ink); font-weight:600; }
footer { color:var(--muted); font-size:.85rem; margin-top:1rem; }
@media (max-width:30rem) { h1 { font-size:1.9rem; } .kpi .big { font-size:1.7rem; } }
</style>
</head>
<body>
<main>
<h1>Teach · __SEM__</h1>
<p class="lede">Your progress on every course, from what you open and the quizzes you finish in this browser. __TOTAL__ pages.</p>
<nav class="top" aria-label="Courses"><a class="plan" href="plan.html">Day plan</a>__NAV__</nav>

<section class="kpis" aria-label="Progress at a glance">
  <div class="card kpi" id="k-test"><h3>Next test</h3><div class="big">–</div><div class="sub"></div></div>
  <div class="card kpi" id="k-plan"><h3>Day plan so far</h3><div class="big">–</div><div class="bar"><i></i></div><div class="sub"></div></div>
  <div class="card kpi" id="k-lessons"><h3>Lessons finished</h3><div class="big">–</div><div class="bar"><i></i></div><div class="sub"></div></div>
  <div class="card kpi" id="k-time"><h3>Study time, 7 days</h3><div class="big">–</div><div class="sub"></div></div>
  <div class="card kpi" id="k-streak"><h3>Days fully on plan</h3><div class="big">–</div><div class="sub"></div></div>
</section>

<div class="grid">
  <section class="card today" id="today" aria-live="polite"><h2>Today</h2><p class="foot">Loading the day plan.</p></section>
  <div class="side">
    <section class="card" aria-labelledby="h-tests"><h3 id="h-tests">Tests</h3><ul class="exams" id="exams"></ul></section>
    <section class="card chart" aria-labelledby="h-time"><h3 id="h-time">Minutes studied, last 14 days</h3><div id="chart"></div><div class="tip" id="tip" role="status"></div></section>
    <section class="card" aria-labelledby="h-recent"><h3 id="h-recent">Recently opened</h3><ul class="recent" id="recent"></ul></section>
  </div>
</div>

<div class="courses">__BLOCKS__</div>

<div class="data" id="data">
  <span>Progress is saved in this browser only. Keep a copy, or move it to another device:</span>
  <button type="button" id="save">Save a copy</button>
  <label class="btn">Load a copy<input type="file" id="load" accept="application/json,.json"></label>
  <span class="msg" id="msg" role="status"></span>
</div>
<footer>Rebuilt __TODAY__. Course readings (PDFs) are not published, so links to them do not open here.</footer>
</main>
<script type="application/json" id="plan-data">__PLAN__</script>
<script>__TRACK__</script>
<script>
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})[ch]);
  const T = window.teachTrack;
  let plan = null;
  try { plan = JSON.parse($("#plan-data").textContent); } catch (e) { plan = null; }
  if (plan && !(plan.days && plan.days.length)) plan = null;
  const DAY = 864e5;
  // Local date, never UTC: at 01:00 IST the UTC date is still yesterday.
  const todayISO = () => T.day(new Date());
  const shift = (iso, n) => { const d = new Date(iso + "T00:00"); d.setDate(d.getDate() + n); return T.day(d); };
  const diff = (a, b) => Math.round((new Date(a + "T00:00") - new Date(b + "T00:00")) / DAY);
  const fmt = (iso, o = { weekday: "short", day: "numeric", month: "short" }) => new Date(iso + "T00:00").toLocaleDateString("en-GB", o);
  const dur = (sec) => { const m = Math.round(sec / 60); return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`; };
  const ago = (t) => { const m = Math.round((Date.now() - t) / 6e4);
    return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };
  const when = (n) => n === 0 ? "today" : n === 1 ? "tomorrow" : `in ${n} days`;
  const readPlan = () => { try { return JSON.parse(localStorage.getItem(plan.key) || "{}") || {}; } catch (e) { return {}; } };
  const writePlan = (s) => { try { localStorage.setItem(plan.key, JSON.stringify(s)); } catch (e) {} };
  const titles = {"plan.html": "Day plan"};
  $$("[data-p] > a").forEach((a) => { titles[a.parentElement.dataset.p] = a.textContent; });

  function status(pg) {
    const q = (pg && pg.quiz) || [];
    if (q.length) {
      const best = q.reduce((b, a) => (a.r / a.n > b.r / b.n ? a : b), q[0]), last = q[q.length - 1];
      return { s: "done", text: `Quiz ${best.r}/${best.n}` + (q.length > 1 ? ` · ${q.length}x` : "") + ` · ${fmt(last.d, { day: "numeric", month: "short" })}` };
    }
    if (pg && pg.visits) return { s: "opened", text: `Opened · ${dur(pg.secs || 0)}` };
    return { s: "", text: "" };
  }

  function render() {
    const today = todayISO();
    const autoK = plan ? T.auto(plan) : {};
    const st = plan ? readPlan() : {};
    const tr = T.read(), pages = tr.pages || {}, days = tr.days || {};

    // 1. course cards
    let lDone = 0, lOpen = 0, lAll = 0;
    $$(".course").forEach((card) => {
      let d = 0, o = 0, n = 0;
      $$("[data-p]", card).forEach((li) => {
        const r = status(pages[li.dataset.p]), off = li.hasAttribute("data-off"), lesson = li.classList.contains("ls");
        const span = $(".st", li);
        span.className = "st " + r.s;
        span.textContent = off && !r.s ? "Not on end-sem" : r.text;
        if (!lesson || off) return;
        n++; if (r.s === "done") d++; else if (r.s === "opened") o++;
      });
      const m = $(".meter", card);
      if (m && n) {
        $(".d", m).style.width = `${(d / n) * 100}%`; $(".o", m).style.width = `${(o / n) * 100}%`;
        const offN = $$(".ls[data-off]", card).length;
        $(".tally", card).innerHTML = `<span class="k d"></span>${d} finished · <span class="k o"></span>${o} opened · ${n - d - o} not started`
          + (offN ? ` · ${offN} not on the end-sem` : "");
      }
      const notes = $$(".pages [data-p]", card), seen = notes.filter((li) => pages[li.dataset.p]).length;
      const sum = $("summary .seen", card); if (sum) sum.textContent = seen ? `· ${seen} opened` : "";
      $$(".test", card).forEach((t) => { const k = diff(t.dataset.date, today);
        t.classList.toggle("past", k < 0); t.classList.toggle("soon", k >= 0 && k <= 3); $("b", t).textContent = k < 0 ? "" : when(k); });
      if (card.hasAttribute("data-plan")) { lDone += d; lOpen += o; lAll += n; }
    });

    // 2. KPIs
    const exams = (plan ? plan.exams || [] : []).filter((x) => diff(x.date, today) >= 0);
    const kt = $("#k-test");
    if (exams.length) {
      const x = exams[0], k = diff(x.date, today);
      $(".big", kt).innerHTML = k === 0 ? "Today" : k === 1 ? "Tomorrow" : `${k}<small>days</small>`;
      $(".sub", kt).textContent = `${x.course} ${x.what} · ${fmt(x.date)}${x.time ? " " + x.time : ""}`;
      kt.classList.toggle("alert", k <= 2);
    } else { $(".big", kt).textContent = "None"; $(".sub", kt).textContent = "No dated test ahead."; }

    const kp = $("#k-plan");
    if (plan) {
      const core = plan.days.flatMap((D) => D.items.filter((i) => !i.extra).map((i) => ({ i, date: D.date })));
      const due = core.filter((x) => x.date <= today), dueDone = due.filter((x) => st[x.i.k]).length;
      const all = core.filter((x) => st[x.i.k]).length;
      $(".big", kp).innerHTML = `${dueDone}<small>/ ${due.length}</small>`;
      $(".bar i", kp).style.width = due.length ? `${(dueDone / due.length) * 100}%` : "0";
      $(".sub", kp).textContent = due.length ? `core items due by today · ${all} of ${core.length} in the whole plan` : `The plan starts ${fmt(plan.days[0].date)}.`;
    }
    const kl = $("#k-lessons");
    $(".big", kl).innerHTML = `${lDone}<small>/ ${lAll}</small>`;
    $(".bar i", kl).style.width = lAll ? `${(lDone / lAll) * 100}%` : "0";
    $(".sub", kl).textContent = `quiz done, end-sem scope · ${lOpen} opened, not finished`;

    const week = Array.from({ length: 7 }, (_, i) => shift(today, -i));
    const secs = week.reduce((s, d) => s + ((days[d] && days[d].secs) || 0), 0);
    const tracked = Object.keys(days).sort();
    $("#k-time .big").textContent = tracked.length ? dur(secs) : "–";
    $("#k-time .sub").textContent = tracked.length
      ? `today ${dur((days[today] && days[today].secs) || 0)} · counted since ${fmt(tracked[0], { day: "numeric", month: "short" })}`
      : "Counts the time you spend on lesson and note pages, from your next visit.";

    const ks = $("#k-streak");
    if (plan) {
      const full = (D) => D.items.filter((i) => !i.extra).every((i) => st[i.k]);
      const byDate = Object.fromEntries(plan.days.map((D) => [D.date, D]));
      let k = 0, d = byDate[today] && full(byDate[today]) ? today : shift(today, -1);
      while (byDate[d] && full(byDate[d])) { k++; d = shift(d, -1); }
      $(".big", ks).innerHTML = `${k}<small>${k === 1 ? "day" : "days"}</small>`;
      $(".sub", ks).textContent = "in a row with every core item ticked";
    }

    // 3. Today
    renderToday(today, st, autoK);

    // 4. Tests list
    $("#exams").innerHTML = exams.length ? exams.map((x) => { const k = diff(x.date, today);
      return `<li class="${k <= 2 ? "soon" : ""}"><span class="cd">${k === 0 ? "Today" : k === 1 ? "Tmrw" : k + " days"}</span>`
        + `<span class="what"><b>${esc(x.course)}</b> ${esc(x.what)}<br><span>${fmt(x.date)}${x.time ? " · " + esc(x.time) : ""}</span></span></li>`; }).join("")
      : `<li class="empty">No dated test ahead.</li>`;

    // 5. chart
    renderChart(today, days, tracked[0]);

    // 6. recent
    const rec = Object.entries(pages).filter(([, v]) => v.last).sort((a, b) => b[1].last - a[1].last).slice(0, 7);
    $("#recent").innerHTML = rec.length ? rec.map(([p, v]) => `<li><a href='${esc(encodeURI(p))}'>${esc(titles[p] || p.split("/").pop().replace(/\.html$/, ""))}</a><span>${ago(v.last)}</span></li>`).join("")
      : `<li class="empty">Nothing yet. Open a lesson and it shows here.</li>`;
  }

  function renderToday(today, st, autoK) {
    const box = $("#today");
    if (!plan) { box.innerHTML = '<h2>Today</h2><p class="foot">The day plan was not found when this page was built. <a href="plan.html">Open the day plan</a>.</p>'; return; }
    const day = plan.days.find((d) => d.date === today);
    if (!day) {
      const msg = today < plan.days[0].date ? `The day plan starts on ${esc(plan.days[0].label)}.`
        : `The day plan ended on ${esc(plan.days[plan.days.length - 1].label)}. Nothing is scheduled for today.`;
      box.innerHTML = `<h2>Today</h2><p class="foot">${msg} <a href="plan.html">Open the day plan</a>.</p>`; return;
    }
    const missed = plan.days.filter((d) => d.date < today).reduce((m, d) => m + d.items.filter((i) => !i.extra && !st[i.k]).length, 0);
    const rows = day.items.map((i) => `<li class="${i.extra ? "extra" : ""}${st[i.k] ? " done" : ""}"><label>`
      + `<input type="checkbox" data-k="${esc(i.k)}"${st[i.k] ? " checked" : ""}>`
      + `<span class="tag">${esc(i.tag)}</span><span class="body">${i.html}${st[i.k] && autoK[i.k] ? '<span class="auto-mark" title="Ticked by itself from your quiz or reading">auto</span>' : ""}</span></label></li>`).join("");
    const back = missed ? `${missed} core item${missed > 1 ? "s" : ""} from earlier days not ticked. ` : (day.date > plan.days[0].date ? "Every core item from earlier days is ticked. " : "");
    box.innerHTML = `<h2>Today <span class="when">${esc(day.label)} · about ${day.mins} min + extra</span></h2><ul class="tasks">${rows}</ul>`
      + `<p class="foot">${back}<a href="plan.html#today">Open the day plan</a><br>A lesson task ticks itself when you finish its quiz. RECALL ticks when you redo the quiz on or after its day.</p>`;
    $$(".tasks input", box).forEach((b) => b.addEventListener("change", () => {
      const s = readPlan(); s[b.dataset.k] = b.checked; writePlan(s); render();
      const again = $(`.tasks input[data-k="${b.dataset.k}"]`); if (again) again.focus();
    }));
  }

  function renderChart(today, days, first) {
    const host = $("#chart"), tip = $("#tip");
    const list = Array.from({ length: 14 }, (_, i) => shift(today, i - 13));
    const planMin = Object.fromEntries((plan ? plan.days : []).map((D) => [D.date, D.mins]));
    const vals = list.map((d) => ({ d, m: Math.round(((days[d] && days[d].secs) || 0) / 60), p: planMin[d] || 0, pre: !first || d < first }));
    const top = Math.max(60, ...vals.map((v) => Math.max(v.m, v.p)));
    const max = Math.ceil(top / 30) * 30;
    const cols = vals.map((v) => {
      const lab = `${fmt(v.d)}: ` + (v.pre ? "before tracking began" : `${v.m} min studied`) + (v.p ? `, ${v.p} min planned` : "");
      return `<div class="col${v.pre ? " pre" : ""}${v.d === today ? " today" : ""}" tabindex="0" role="img" aria-label="${esc(lab)}" data-tip="${esc(lab)}">`
        + `<div class="b" style="height:${(v.m / max) * 100}%"></div>`
        + (v.p ? `<div class="pl" style="bottom:${(v.p / max) * 100}%"></div>` : "") + `</div>`;
    }).join("");
    const xl = list.map((d, i) => `<span>${i % 2 === 1 || d === today ? new Date(d + "T00:00").getDate() : ""}</span>`).join("");
    host.innerHTML = `<div class="cols"><div class="gl" style="bottom:100%"><span>${max} min</span></div><div class="gl" style="bottom:50%"><span>${max / 2}</span></div>${cols}</div>`
      + `<div class="xl" aria-hidden="true">${xl}</div>`
      + `<div class="legend"><span><i></i>Minutes on lesson and note pages</span><span><i class="pl"></i>Planned for the day</span></div>`
      + (first ? "" : `<p class="empty">No minutes yet: counting starts with your next lesson or note in this browser.</p>`);
    $$(".col", host).forEach((c) => {
      const show = () => { const r = c.getBoundingClientRect(), h = host.parentElement.getBoundingClientRect();
        tip.textContent = c.dataset.tip; tip.style.display = "block";
        const w = tip.offsetWidth / 2, x = Math.min(Math.max(r.left + r.width / 2 - h.left, w + 4), h.width - w - 4);
        tip.style.left = `${x}px`; tip.style.top = `${r.top - h.top + 30}px`; };
      const hide = () => { tip.style.display = "none"; };
      c.addEventListener("pointerenter", show); c.addEventListener("pointerleave", hide);
      c.addEventListener("focus", show); c.addEventListener("blur", hide);
    });
  }

  // Save and load a copy. Loading merges: nothing already here is lost, a re-loaded copy adds nothing twice.
  $("#save").addEventListener("click", () => {
    const out = { kind: "teach-progress", saved: new Date().toISOString(), track: T.read(), plan: plan ? { key: plan.key, state: readPlan() } : null };
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" })),
      download: `teach-progress-${todayISO()}.json` });
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    $("#msg").textContent = "Copy saved to your downloads.";
  });
  $("#load").addEventListener("change", async (e) => {
    const f = e.target.files[0]; e.target.value = ""; if (!f) return;
    let x; try { x = JSON.parse(await f.text()); } catch (err) { x = null; }
    if (!x || x.kind !== "teach-progress") { $("#msg").textContent = "That file is not a teach progress copy. Nothing changed."; return; }
    const cur = T.read(), inc = x.track || {};
    cur.v = 1; cur.pages = cur.pages || {}; cur.days = cur.days || {}; cur.auto = Object.assign({}, inc.auto || {}, cur.auto || {});
    for (const [p, v] of Object.entries(inc.pages || {})) {
      const c = cur.pages[p] || { visits: 0, secs: 0 };
      const seen = new Set((c.quiz || []).map((a) => a.t));
      cur.pages[p] = { visits: Math.max(c.visits || 0, v.visits || 0), secs: Math.max(c.secs || 0, v.secs || 0),
        first: Math.min(c.first || Infinity, v.first || Infinity) === Infinity ? undefined : Math.min(c.first || Infinity, v.first || Infinity),
        last: Math.max(c.last || 0, v.last || 0),
        quiz: (c.quiz || []).concat((v.quiz || []).filter((a) => !seen.has(a.t))).sort((a, b) => a.t - b.t).slice(-20) };
    }
    for (const [d, v] of Object.entries(inc.days || {})) {
      const c = cur.days[d] || { secs: 0, pages: {} }, pg = Object.assign({}, c.pages || {});
      for (const [p, s] of Object.entries(v.pages || {})) pg[p] = Math.max(pg[p] || 0, s);
      cur.days[d] = { secs: Math.max(c.secs || 0, v.secs || 0), pages: pg };
    }
    let added = 0;
    if (plan && x.plan && x.plan.key === plan.key) {
      const s = readPlan(); for (const [k, v] of Object.entries(x.plan.state || {})) if (!(k in s)) { s[k] = v; added++; }
      writePlan(s);
    }
    $("#msg").textContent = T.write(cur) ? `Copy loaded and merged (${Object.keys(inc.pages || {}).length} pages, ${added} new ticks).` : "This browser would not save the copy. Nothing changed.";
    render();
  });

  render();
  // Another tab finished a quiz or ticked an item: update at once.
  addEventListener("storage", (e) => { if (!e.key || e.key === T.key || (plan && e.key === plan.key)) render(); });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") render(); });
})();
</script>
</body>
</html>
'''
page = (PAGE.replace('__FONTS__', fonts).replace('__SEM__', SEM).replace('__TOTAL__', str(total)).replace('__NAV__', nav)
        .replace('__BLOCKS__', ''.join(blocks)).replace('__TODAY__', today).replace('__TRACK__', track_js(None))
        .replace('__PLAN__', plan_json))
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
    head = f'<!--teach-nav--><style>{NAV_CSS}</style><script>{NAV_JS}</script><script>{track_js(f)}</script><!--/teach-nav-->'
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
    if f == 'plan.html':
        # tick plan items from the tracker before the plan's own script reads its ticks
        out = re.sub(r'<!--teach-auto-->.*?<!--/teach-auto-->', '', out, flags=re.S)
        anchor = re.search(r'<script type="application/json" id="plan-data">.*?</script>', out, re.S)
        if anchor:
            out = (out[:anchor.end()] + '<!--teach-auto--><script>try{teachTrack.auto(JSON.parse(document.getElementById("plan-data").textContent))}catch(e){}</script><!--/teach-auto-->'
                   + out[anchor.end():])
    nav_count += 1
    if out != cur:
        write_keep(f, out)
print('nav bars:', nav_count, 'pages | skipped (no body/head tag):', nav_skipped or 'none')
