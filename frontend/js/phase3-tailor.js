/* ═══════════════════════════════════════════════
   NextSteps — Phase 3: Tailor
   Resume bullets, cover letter, ATS scoring
═══════════════════════════════════════════════ */

async function runTailor() {
  document.getElementById('tbtn').disabled = true;
  document.getElementById('tld').style.display = 'block';
  document.getElementById('tr').style.display = 'none';
  document.getElementById('terr').style.display = 'none';
  setTag('Generating…', false);

  const stepAnim = animSteps('tb', [
    [20, 't0'], [50, 't1'], [75, 't2'], [95, 't3']
  ], 900);

  try {
    const body = {
      profile: S.profile,
      jd: S.jd,
      gap_report: S.gap_report,
      company_ctx: S.company_ctx,
    };
    const res = await fetch(API + '/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    await stepAnim;

    if (!res.ok) {
      const err = await res.json().catch(function() { return { detail: 'HTTP ' + res.status }; });
      throw new Error(err.detail || 'HTTP ' + res.status);
    }

    const data = await res.json();
    S.tailored_bullets = data.tailored_bullets || [];
    S.cover_letter = data.cover_letter || '';
    S.ats = data.ats || null;
    S.tailored = true;
    renderTailorResults();
  } catch (err) {
    document.getElementById('tld').style.display = 'none';
    document.getElementById('terr').style.display = 'block';
    document.getElementById('terr').textContent = '❌ Apply failed: ' + err.message;
  }
  document.getElementById('tbtn').disabled = false;
}

function renderTailorResults() {
  document.getElementById('tld').style.display = 'none';
  document.getElementById('tr').style.display = 'block';
  setTag('Package ready ✓', true);

  document.getElementById('bulc').innerHTML = S.tailored_bullets.map(function(b) {
    return '<div class="bp2">' +
      '<div class="bc"><div class="bclbl">Original</div><div class="bctxt">' + b.original + '</div></div>' +
      '<div class="bc tai"><div class="bclbl">Tailored ✓</div><div class="bctxt">' + b.tailored + '</div></div>' +
      '</div>';
  }).join('');

  if (S.ats) {
    renderATS(S.ats);
    document.getElementById('ats-panel').style.display = 'block';
  }

  const cl = document.getElementById('cl');
  cl.textContent = '';
  cl.classList.add('sc2');
  const txt = S.cover_letter;
  let i = 0;
  const timer = setInterval(function() {
    cl.textContent += txt[i] || '';
    i++;
    if (i >= txt.length) { clearInterval(timer); cl.classList.remove('sc2'); }
  }, 8);

  updBar(3); updPP(3); saveSession();
}

function renderATS(ats) {
  var score = ats.ats_score || 0;
  var color = score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--yellow)' : 'var(--red)';
  var numEl = document.getElementById('ats-num');
  numEl.textContent = score + '/100';
  numEl.style.color = color;

  var vEl = document.getElementById('ats-verdict');
  vEl.textContent = ats.verdict || '';
  vEl.style.background = score >= 70 ? 'rgba(29,233,128,0.1)' : score >= 50 ? 'rgba(251,191,36,0.1)' : 'rgba(248,113,113,0.1)';
  vEl.style.color = color;

  document.getElementById('ats-hits').innerHTML = (ats.keyword_hits || []).map(function(k) {
    return '<span class="chip cg2">' + k + '</span>';
  }).join('');
  document.getElementById('ats-miss').innerHTML = (ats.keyword_misses || []).map(function(k) {
    return '<span class="chip cr">' + k + '</span>';
  }).join('');

  if ((ats.improvements || []).length) {
    document.getElementById('ats-impr-wrap').style.display = 'block';
    document.getElementById('ats-impr').innerHTML = ats.improvements.map(function(item) {
      return '<li>' + item + '</li>';
    }).join('');
  }
}

// ── Copy / Download helpers ───────────────────────────────────────────────────
function cpBullets(btn) {
  navigator.clipboard?.writeText(S.tailored_bullets.map(function(b) { return '• ' + b.tailored; }).join('\n'));
  flash(btn, '📋 Copy All Tailored');
}

function dlBullets() {
  dl(S.tailored_bullets.map(function(b) { return '• ' + b.tailored; }).join('\n'), 'tailored_bullets.txt');
}

function cpCL(btn) {
  navigator.clipboard?.writeText(document.getElementById('cl').textContent);
  flash(btn, '📋 Copy');
}

function dlCL() {
  dl(document.getElementById('cl').textContent, 'cover_letter.txt');
}

function flash(btn, orig) {
  btn.textContent = '✓ Copied!';
  btn.classList.add('ok');
  setTimeout(function() { btn.textContent = orig; btn.classList.remove('ok'); }, 2200);
}

function dl(text, name) {
  var a = document.createElement('a');
  a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(text);
  a.download = name;
  a.click();
}
