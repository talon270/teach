/* DOM207 lesson kit: three reusable, self-initialising components.
 *
 * 1. Recall (warm-up retrieval)
 *    <div class="recall-item"><p class="q">…</p><textarea></textarea>
 *      <div class="answer">…</div></div>
 *    The reveal button unlocks only after the learner writes an attempt.
 *
 * 2. Quiz (multiple choice, instant feedback)
 *    <div data-quiz="ID"></div> + <script type="application/json" id="ID">
 *      [{"stem": "...", "options": ["..", ".."], "answer": 0, "why": "..."}]
 *    </script>   (answer = zero-based index; "why" may contain HTML)
 *
 * 3. Hunt (find the answer in real output)
 *    <div class="hunt" data-hunt="ID"><div class="task"></div>
 *      <pre>… <button class="zone" data-zone="fp" data-what="the p-value of …">2e-16</button> …</pre>
 *      <div class="done">…</div></div>
 *    + <script type="application/json" id="ID">
 *      [{"prompt": "...", "accept": ["fp"], "ok": "..."}]
 *    </script>
 */
(function () {
  "use strict";

  const readJSON = (id) => JSON.parse(document.getElementById(id).textContent);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html !== undefined) n.innerHTML = html;
    return n;
  };

  /* ---------- 1. Recall ---------- */
  function initRecall(item) {
    const ta = item.querySelector("textarea");
    const answer = item.querySelector(".answer");
    const reveal = el("button", "btn ghost", "Write an attempt first");
    reveal.type = "button";
    reveal.disabled = true;
    const row = el("div", "row");
    row.appendChild(reveal);
    answer.before(row);

    const self = el("div", "row self");
    const got = el("button", "btn ghost", "I got it");
    const missed = el("button", "btn ghost", "I missed it");
    got.type = missed.type = "button";
    self.append(got, missed);
    answer.after(self);

    ta.addEventListener("input", () => {
      const ready = ta.value.trim().length >= 3;
      reveal.disabled = !ready;
      reveal.textContent = ready ? "Show answer" : "Write an attempt first";
    });
    reveal.addEventListener("click", () => {
      item.classList.add("revealed");
      reveal.disabled = true;
      reveal.textContent = "Answer shown";
    });
    const mark = (m) => {
      item.dataset.mark = m;
      got.setAttribute("aria-pressed", m === "got");
      missed.setAttribute("aria-pressed", m === "missed");
      got.textContent = m === "got" ? "✓ Got it" : "I got it";
      missed.textContent = m === "missed" ? "✗ Missed: review it" : "I missed it";
    };
    got.addEventListener("click", () => mark("got"));
    missed.addEventListener("click", () => mark("missed"));
  }

  /* ---------- 2. Quiz ---------- */
  function initQuiz(host) {
    const qs = readJSON(host.dataset.quiz);
    let answered = 0, right = 0;

    const bar = el("div", "score-bar");
    const label = el("span", "score", `0 / ${qs.length}`);
    const prog = el("div", "progress");
    const fill = el("i");
    prog.appendChild(fill);
    prog.setAttribute("role", "progressbar");
    prog.setAttribute("aria-valuemin", "0");
    prog.setAttribute("aria-valuemax", String(qs.length));
    bar.append(el("span", null, "Score"), prog, label);

    qs.forEach((q, qi) => {
      const box = el("div", "quiz-q");
      box.appendChild(el("p", "stem", `<span class="n">Question ${qi + 1} of ${qs.length}</span>${q.stem}`));
      const opts = el("div", "opts");
      const fb = el("div", "feedback");
      fb.setAttribute("aria-live", "polite");
      const buttons = q.options.map((text, oi) => {
        const b = el("button", "opt", `<span class="key"><span>${"ABCD"[oi]}</span></span><span>${text}</span>`);
        b.type = "button";
        b.addEventListener("click", () => {
          buttons.forEach((x) => (x.disabled = true));
          const ok = oi === q.answer;
          b.classList.add(ok ? "right" : "wrong");
          if (!ok) buttons[q.answer].classList.add("right");
          answered++;
          if (ok) right++;
          fb.innerHTML = `<span class="verdict">${ok ? "✓ Right" : "✗ Not quite: the answer is " + "ABCD"[q.answer]}</span>${q.why}`;
          fb.classList.add("show");
          label.textContent = `${right} / ${qs.length}`;
          fill.style.width = `${(answered / qs.length) * 100}%`;
          prog.setAttribute("aria-valuenow", String(answered));
        });
        opts.appendChild(b);
        return b;
      });
      box.append(opts, fb);
      host.appendChild(box);
    });
    host.appendChild(bar);
  }

  /* ---------- 3. Hunt ---------- */
  function initHunt(host) {
    const tasks = readJSON(host.dataset.hunt);
    const task = host.querySelector(".task");
    const zones = [...host.querySelectorAll(".zone")];
    zones.forEach((z) => (z.type = "button"));
    let i = 0;

    const step = el("div", "step");
    const prompt = el("p", "prompt");
    const fb = el("p", "fb");
    fb.setAttribute("aria-live", "polite");
    const next = el("button", "btn ghost", "Next");
    next.type = "button";
    const row = el("div", "row");
    row.appendChild(next);
    row.hidden = true;
    task.append(step, prompt, fb, row);

    const show = () => {
      step.textContent = `Find ${i + 1} of ${tasks.length}`;
      prompt.innerHTML = tasks[i].prompt;
      fb.textContent = "";
      fb.className = "fb";
      row.hidden = true;
      zones.forEach((z) => z.classList.remove("miss"));
    };

    zones.forEach((z) =>
      z.addEventListener("click", () => {
        if (i >= tasks.length || !row.hidden) return;
        const t = tasks[i];
        zones.forEach((x) => x.classList.remove("miss"));
        if (t.accept.includes(z.dataset.zone)) {
          z.classList.add("found");
          fb.className = "fb ok";
          fb.innerHTML = t.ok;
          row.hidden = false;
          next.textContent = i === tasks.length - 1 ? "Finish" : "Next";
          next.focus({ preventScroll: true });
        } else {
          z.classList.add("miss");
          fb.className = "fb no";
          fb.innerHTML = `That is ${z.dataset.what}. Try again.`;
        }
      })
    );
    next.addEventListener("click", () => {
      i++;
      if (i < tasks.length) return show();
      step.textContent = `All ${tasks.length} found`;
      prompt.textContent = "Every answer is highlighted in the output. Summary below it.";
      fb.textContent = "";
      fb.className = "fb";
      row.hidden = true;
      host.classList.add("complete");
    });
    show();
  }

  /* ---------- 4. Check (type the answer, marked at once) ----------
   * <div class="check" data-answer="4||four" [data-tol="0.01"]>
   *   <p class="q">…</p> [optional code cell] <div class="explain">…</div></div>
   * Answers are separated by "||". Numbers compare within data-tol (default 0.0005).
   * Text compares case-blind, ignoring quotes, extra spaces and a leading "[1]".
   */
  const norm = (s) =>
    s.trim().toLowerCase()
      .replace(/^\[1\]\s*/, "")
      .replace(/["'‘’“”`]/g, "")
      .replace(/\s*,\s*/g, ",")
      .replace(/\s+/g, " ")
      .trim();
  const asNum = (s) => {
    let t = s.trim().replace(/^\[1\]\s*/, "").replace(/−/g, "-");
    if (/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(t)) t = t.replace(/,/g, "");
    return /^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?%?$/i.test(t) ? parseFloat(t) : NaN;
  };
  function initCheck(box) {
    const answers = box.dataset.answer.split("||");
    const tol = parseFloat(box.dataset.tol || "0.0005");
    const explain = box.querySelector(".explain");
    const input = el("input", "ans");
    input.type = "text";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("aria-label", "Your answer");
    input.placeholder = "Type your answer";
    const go = el("button", "btn", "Check");
    go.type = "button";
    const reveal = el("button", "btn ghost", "Show answer");
    reveal.type = "button";
    reveal.hidden = true;
    const row = el("div", "row");
    row.append(input, go, reveal);
    const fb = el("p", "fb");
    fb.setAttribute("aria-live", "polite");
    (explain || box.lastElementChild).before(row, fb);
    let tries = 0;

    const ok = (v) => {
      const n = asNum(v);
      return answers.some((a) => {
        const m = asNum(a);
        if (!isNaN(n) && !isNaN(m)) return Math.abs(n - m) <= tol;
        return norm(v) === norm(a);
      });
    };
    const finish = (right) => {
      box.classList.add("done", right ? "right" : "shown");
      input.disabled = go.disabled = true;
      reveal.hidden = true;
      fb.className = "fb " + (right ? "ok" : "no");
      fb.innerHTML = right ? "Right." : `Answer: <code>${answers[0]}</code>`;
    };
    const submit = () => {
      if (!input.value.trim() || box.classList.contains("done")) return;
      if (ok(input.value)) return finish(true);
      tries++;
      fb.className = "fb no";
      fb.textContent = tries === 1 ? "Not that. Look again and try once more." : "Still not it. Try again, or show the answer.";
      if (tries >= 2) reveal.hidden = false;
    };
    go.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    reveal.addEventListener("click", () => finish(false));
  }

  document.querySelectorAll(".recall-item").forEach(initRecall);
  document.querySelectorAll("[data-quiz]").forEach(initQuiz);
  document.querySelectorAll("[data-hunt]").forEach(initHunt);
  document.querySelectorAll(".check[data-answer]").forEach(initCheck);
})();
