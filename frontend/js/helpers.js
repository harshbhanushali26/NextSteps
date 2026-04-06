/* ═══════════════════════════════════════════════
   NextSteps — Helpers
   Shared utility functions
═══════════════════════════════════════════════ */

function setTag(t, ok) {
  const e = document.getElementById('tn-tag');
  e.textContent = t;
  e.classList.toggle('ok', ok);
}

function countUp(id, target, dur, sfx) {
  sfx = sfx || '';
  const el = document.getElementById(id);
  if (!el) return;
  let v = 0;
  const step = target / (dur / 16);
  const t = setInterval(function() {
    v = Math.min(v + step, target);
    el.textContent = Math.round(v) + sfx;
    if (v >= target) clearInterval(t);
  }, 16);
}

function animSteps(barId, steps, ms) {
  return new Promise(function(res) {
    const bar = document.getElementById(barId);
    let i = 0;
    const run = function() {
      if (i >= steps.length) { res(); return; }
      if (bar) bar.style.width = steps[i][0] + '%';
      const rid = steps[i][1];
      if (rid) {
        if (i > 0) {
          const pr = document.getElementById(steps[i - 1][1]);
          if (pr) { pr.classList.remove('active'); pr.classList.add('done'); }
        }
        const rw = document.getElementById(rid);
        if (rw) rw.classList.add('active');
      }
      i++;
      setTimeout(run, ms);
    };
    run();
  });
}

function updBar(ph) {
  ['sb1', 'sb2', 'sb3', 'sb4'].forEach(function(id, i) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('done', 'act');
    if (ph > 0) {
      if (i < ph - 1) el.classList.add('done');
      else if (i === ph - 1) el.classList.add('act');
    }
  });
}

function updPP(ph) {
  ['pp1', 'pp2', 'pp3', 'pp4'].forEach(function(id, i) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('done', 'act');
    if (ph > 0) {
      if (i < ph) el.classList.add('done');
      else if (i === ph) el.classList.add('act');
    }
  });
}
